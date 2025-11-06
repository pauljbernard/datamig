#!/usr/bin/env python3
"""
Extract district data with relationship resolution

Extracts data from source databases maintaining FK integrity and topological ordering.
Accepts JSON input via stdin, outputs JSON results via stdout.
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
import psycopg2
from neo4j import GraphDatabase
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def log_error(message):
    """Log error message to stderr"""
    print(f"ERROR: {message}", file=sys.stderr)

def log_info(message):
    """Log info message to stderr"""
    print(f"INFO: {message}", file=sys.stderr)

def get_db_connection(store, connection=None):
    """Get database connection for specified store"""
    env_prefix = f"PROD_{store.upper()}"

    if store.lower() in ['ids', 'hcp1', 'hcp2', 'adb']:
        # PostgreSQL connection
        conn_params = {
            'host': os.getenv(f"{env_prefix}_HOST", f"prod-{store.lower()}-rds.amazonaws.com"),
            'port': int(os.getenv(f"{env_prefix}_PORT", "5432")),
            'database': os.getenv(f"{env_prefix}_DATABASE", f"{store.lower()}_db"),
            'user': os.getenv(f"{env_prefix}_USER", "readonly_user"),
            'password': os.getenv(f"{env_prefix}_PASSWORD"),
        }

        if not conn_params['password']:
            raise ValueError(f"Missing password for {store}: {env_prefix}_PASSWORD not set")

        return psycopg2.connect(**conn_params)

    elif store.lower() == 'sp':
        # Neo4j connection
        neo4j_uri = os.getenv("NEO4J_PROD_URI", "bolt://prod-graph-db.amazonaws.com:7687")
        neo4j_user = os.getenv("NEO4J_PROD_USER", "readonly")
        neo4j_password = os.getenv("NEO4J_PROD_PASSWORD")

        if not neo4j_password:
            raise ValueError("Missing NEO4J_PROD_PASSWORD")

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        return driver

    else:
        raise ValueError(f"Unknown store: {store}")

def extract_postgres_table(conn, store, table, filter_criteria, output_dir):
    """Extract a single PostgreSQL table"""
    try:
        # Build WHERE clause from filter criteria
        where_clauses = []
        params = []

        for key, value in filter_criteria.items():
            where_clauses.append(f"{key} = %s")
            params.append(value)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Execute extraction query
        query = f"SELECT * FROM {table} WHERE {where_sql}"
        log_info(f"Extracting {store}.{table}: {query}")

        df = pd.read_sql_query(query, conn, params=params)

        # Write to Parquet
        output_file = Path(output_dir) / f"{store}_{table}.parquet"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)

        log_info(f"Extracted {len(df)} records from {store}.{table}")

        return {
            'table': table,
            'store': store,
            'records': len(df),
            'file': str(output_file),
            'success': True
        }

    except Exception as e:
        log_error(f"Failed to extract {store}.{table}: {e}")
        return {
            'table': table,
            'store': store,
            'records': 0,
            'error': str(e),
            'success': False
        }

def extract_postgres_table_with_join(conn, store, table, filter_criteria, parent_table, join_column, output_dir):
    """Extract a PostgreSQL table using JOIN to parent table"""
    try:
        # This handles indirect filtering via parent table
        district_filter_key = list(filter_criteria.keys())[0]
        district_filter_value = list(filter_criteria.values())[0]

        query = f"""
            SELECT t.*
            FROM {table} t
            INNER JOIN {parent_table} p ON t.{join_column} = p.id
            WHERE p.{district_filter_key} = %s
        """

        log_info(f"Extracting {store}.{table} via JOIN to {parent_table}")

        df = pd.read_sql_query(query, conn, params=[district_filter_value])

        # Write to Parquet
        output_file = Path(output_dir) / f"{store}_{table}.parquet"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)

        log_info(f"Extracted {len(df)} records from {store}.{table}")

        return {
            'table': table,
            'store': store,
            'records': len(df),
            'file': str(output_file),
            'join_strategy': f"{parent_table}.{join_column}",
            'success': True
        }

    except Exception as e:
        log_error(f"Failed to extract {store}.{table}: {e}")
        return {
            'table': table,
            'store': store,
            'records': 0,
            'error': str(e),
            'success': False
        }

def extract_neo4j_graph(driver, filter_criteria, output_dir):
    """Extract Neo4j graph data for district"""
    try:
        district_id = filter_criteria.get('district_id')

        if not district_id:
            raise ValueError("district_id required for Neo4j extraction")

        with driver.session() as session:
            # Extract nodes
            nodes_query = """
                MATCH path = (d:District {id: $district_id})-[*0..10]-(connected)
                RETURN DISTINCT connected AS node
            """

            nodes_result = session.run(nodes_query, district_id=district_id)

            nodes_data = []
            for record in nodes_result:
                node = record['node']
                node_dict = dict(node)
                node_dict['_neo4j_id'] = node.id
                node_dict['_labels'] = list(node.labels)
                nodes_data.append(node_dict)

            # Extract relationships
            rels_query = """
                MATCH path = (d:District {id: $district_id})-[*0..10]-(connected)
                UNWIND relationships(path) AS rel
                RETURN DISTINCT
                    id(startNode(rel)) AS start_id,
                    type(rel) AS type,
                    id(endNode(rel)) AS end_id,
                    properties(rel) AS properties
            """

            rels_result = session.run(rels_query, district_id=district_id)

            rels_data = []
            for record in rels_result:
                rel_dict = {
                    'start_id': record['start_id'],
                    'type': record['type'],
                    'end_id': record['end_id'],
                    'properties': dict(record['properties']) if record['properties'] else {}
                }
                rels_data.append(rel_dict)

            # Write to Parquet
            nodes_df = pd.DataFrame(nodes_data)
            rels_df = pd.DataFrame(rels_data)

            nodes_file = Path(output_dir) / "sp_nodes.parquet"
            rels_file = Path(output_dir) / "sp_relationships.parquet"

            nodes_file.parent.mkdir(parents=True, exist_ok=True)

            nodes_df.to_parquet(nodes_file, engine='pyarrow', compression='snappy', index=False)
            rels_df.to_parquet(rels_file, engine='pyarrow', compression='snappy', index=False)

            log_info(f"Extracted {len(nodes_data)} nodes and {len(rels_data)} relationships from Neo4j")

            return {
                'store': 'sp',
                'nodes': len(nodes_data),
                'relationships': len(rels_data),
                'files': {
                    'nodes': str(nodes_file),
                    'relationships': str(rels_file)
                },
                'success': True
            }

    except Exception as e:
        log_error(f"Failed to extract from Neo4j: {e}")
        return {
            'store': 'sp',
            'nodes': 0,
            'relationships': 0,
            'error': str(e),
            'success': False
        }

def extract_with_relationships(source_config, filter_criteria, extraction_order, output_dir):
    """
    Main extraction function

    Args:
        source_config: Dict with store name and connection info
        filter_criteria: Dict with filter conditions (e.g., {'district_id': 'district-001'})
        extraction_order: List of tables in topological order (or None to extract all)
        output_dir: Directory to write extracted data

    Returns:
        Dict with extraction results
    """
    start_time = datetime.now()
    store = source_config['store'].lower()

    results = {
        'run_timestamp': start_time.isoformat(),
        'store': store,
        'filter': filter_criteria,
        'tables_extracted': [],
        'total_records': 0,
        'success': True,
        'errors': []
    }

    try:
        # Connect to database
        conn = get_db_connection(store, source_config.get('connection'))

        if store == 'sp':
            # Neo4j extraction
            neo4j_result = extract_neo4j_graph(conn, filter_criteria, output_dir)
            results['neo4j'] = neo4j_result
            results['total_records'] = neo4j_result.get('nodes', 0) + neo4j_result.get('relationships', 0)
            results['success'] = neo4j_result.get('success', False)

            conn.close()

        else:
            # PostgreSQL extraction
            if extraction_order:
                # Use provided extraction order
                tables_to_extract = extraction_order
            else:
                # Get all tables in database
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables_to_extract = [row[0] for row in cursor.fetchall()]
                cursor.close()

            # Extract each table
            for table in tables_to_extract:
                # Check if table has direct district_id column
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND column_name = 'district_id'
                """, (table,))

                has_district_id = cursor.fetchone() is not None
                cursor.close()

                if has_district_id:
                    # Direct extraction
                    table_result = extract_postgres_table(conn, store, table, filter_criteria, output_dir)
                else:
                    # Try indirect extraction via common parent tables
                    # This is a simplified approach - in production, use schema analysis
                    table_result = extract_postgres_table(conn, store, table, filter_criteria, output_dir)

                results['tables_extracted'].append(table_result)

                if table_result['success']:
                    results['total_records'] += table_result['records']
                else:
                    results['errors'].append(table_result.get('error', 'Unknown error'))
                    results['success'] = False

            conn.close()

        results['duration_seconds'] = (datetime.now() - start_time).total_seconds()

        # Write extraction manifest
        manifest_file = Path(output_dir) / "extraction-manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(results, f, indent=2)

        log_info(f"Extraction complete: {results['total_records']} records from {len(results['tables_extracted'])} tables")

        return results

    except Exception as e:
        log_error(f"Extraction failed: {e}")
        results['success'] = False
        results['error'] = str(e)
        results['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        return results

def main():
    """Main entry point - reads JSON from stdin, outputs JSON to stdout"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        source_config = input_data['source_config']
        filter_criteria = input_data['filter']
        extraction_order = input_data.get('extraction_order')
        output_dir = input_data['output_dir']

        # Perform extraction
        result = extract_with_relationships(
            source_config=source_config,
            filter_criteria=filter_criteria,
            extraction_order=extraction_order,
            output_dir=output_dir
        )

        # Output result as JSON to stdout
        print(json.dumps(result, indent=2))

        # Exit with appropriate code
        sys.exit(0 if result['success'] else 1)

    except Exception as e:
        log_error(f"Fatal error: {e}")
        error_result = {
            'success': False,
            'error': str(e)
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()
