#!/usr/bin/env python3
"""
Load data to CERT with constraint management

Loads data to target databases with transaction safety and conflict resolution.
Accepts JSON input via stdin, outputs JSON results via stdout.
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import psycopg2
from neo4j import GraphDatabase
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def log_error(message):
    """Log error message to stderr"""
    print(f"ERROR: {message}", file=sys.stderr)

def log_info(message):
    """Log info message to stderr"""
    print(f"INFO: {message}", file=sys.stderr)

def get_cert_db_connection(store, connection=None):
    """Get CERT database connection for specified store"""
    env_prefix = f"CERT_{store.upper()}"

    if store.lower() in ['ids', 'hcp1', 'hcp2', 'adb']:
        # PostgreSQL connection
        conn_params = {
            'host': os.getenv(f"{env_prefix}_HOST", f"cert-{store.lower()}-rds.amazonaws.com"),
            'port': int(os.getenv(f"{env_prefix}_PORT", "5432")),
            'database': os.getenv(f"{env_prefix}_DATABASE", f"{store.lower()}_db"),
            'user': os.getenv(f"{env_prefix}_USER", "admin_user"),
            'password': os.getenv(f"{env_prefix}_PASSWORD"),
        }

        if not conn_params['password']:
            raise ValueError(f"Missing password for {store}: {env_prefix}_PASSWORD not set")

        return psycopg2.connect(**conn_params)

    elif store.lower() == 'sp':
        # Neo4j connection
        neo4j_uri = os.getenv("NEO4J_CERT_URI", "bolt://cert-graph-db.amazonaws.com:7687")
        neo4j_user = os.getenv("NEO4J_CERT_USER", "admin")
        neo4j_password = os.getenv("NEO4J_CERT_PASSWORD")

        if not neo4j_password:
            raise ValueError("Missing NEO4J_CERT_PASSWORD")

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        return driver

    else:
        raise ValueError(f"Unknown store: {store}")

def load_postgres_table_insert(conn, store, table, df) -> Dict:
    """Load data using INSERT strategy"""
    try:
        cursor = conn.cursor()

        # Generate INSERT statement
        columns = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        # Insert rows
        rows_inserted = 0
        for _, row in df.iterrows():
            try:
                cursor.execute(insert_sql, tuple(row))
                rows_inserted += 1
            except psycopg2.IntegrityError as e:
                # Duplicate key or constraint violation
                log_error(f"Insert failed for {table}: {e}")
                conn.rollback()
                raise

        cursor.close()

        log_info(f"Inserted {rows_inserted} rows into {store}.{table}")

        return {
            'table': table,
            'store': store,
            'rows_loaded': rows_inserted,
            'strategy': 'insert',
            'success': True
        }

    except Exception as e:
        log_error(f"Failed to load {store}.{table}: {e}")
        return {
            'table': table,
            'store': store,
            'rows_loaded': 0,
            'strategy': 'insert',
            'error': str(e),
            'success': False
        }

def load_postgres_table_upsert(conn, store, table, df) -> Dict:
    """Load data using UPSERT strategy (ON CONFLICT)"""
    try:
        cursor = conn.cursor()

        # Generate UPSERT statement
        columns = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        update_set = ', '.join([f"{col} = EXCLUDED.{col}" for col in df.columns if col != 'id'])

        upsert_sql = f"""
            INSERT INTO {table} ({columns})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET
            {update_set}
        """

        # Upsert rows
        rows_loaded = 0
        for _, row in df.iterrows():
            cursor.execute(upsert_sql, tuple(row))
            rows_loaded += 1

        cursor.close()

        log_info(f"Upserted {rows_loaded} rows into {store}.{table}")

        return {
            'table': table,
            'store': store,
            'rows_loaded': rows_loaded,
            'strategy': 'upsert',
            'success': True
        }

    except Exception as e:
        log_error(f"Failed to upsert {store}.{table}: {e}")
        return {
            'table': table,
            'store': store,
            'rows_loaded': 0,
            'strategy': 'upsert',
            'error': str(e),
            'success': False
        }

def load_postgres_table_merge(conn, store, table, df) -> Dict:
    """Load data using MERGE strategy (complex conflict resolution)"""
    # For this implementation, merge is the same as upsert
    # In production, you might have custom merge logic
    return load_postgres_table_upsert(conn, store, table, df)

def load_neo4j_graph(driver, nodes_file: Path, rels_file: Path) -> Dict:
    """Load Neo4j graph data"""
    try:
        with driver.session() as session:
            # Load nodes
            nodes_df = pd.read_parquet(nodes_file)

            log_info(f"Loading {len(nodes_df)} nodes to Neo4j")

            nodes_loaded = 0
            for _, node in nodes_df.iterrows():
                # Extract labels and properties
                labels = node.get('_labels', ['Node'])
                if isinstance(labels, str):
                    labels = [labels]

                props = {k: v for k, v in node.items() if not k.startswith('_') and pd.notna(v)}

                # Create node
                labels_str = ':'.join(labels)
                props_str = ', '.join([f"{k}: ${k}" for k in props.keys()])

                query = f"MERGE (n:{labels_str} {{id: $id}}) SET n = {{{props_str}}}"

                session.run(query, **props)
                nodes_loaded += 1

            # Load relationships
            rels_df = pd.read_parquet(rels_file)

            log_info(f"Loading {len(rels_df)} relationships to Neo4j")

            rels_loaded = 0
            for _, rel in rels_df.iterrows():
                start_id = rel['start_id']
                rel_type = rel['type']
                end_id = rel['end_id']
                props = rel.get('properties', {})

                # Create relationship
                query = f"""
                    MATCH (a), (b)
                    WHERE id(a) = $start_id AND id(b) = $end_id
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r = $props
                """

                session.run(query, start_id=start_id, end_id=end_id, props=props)
                rels_loaded += 1

            log_info(f"Loaded {nodes_loaded} nodes and {rels_loaded} relationships to Neo4j")

            return {
                'store': 'sp',
                'nodes_loaded': nodes_loaded,
                'relationships_loaded': rels_loaded,
                'success': True
            }

    except Exception as e:
        log_error(f"Failed to load to Neo4j: {e}")
        return {
            'store': 'sp',
            'nodes_loaded': 0,
            'relationships_loaded': 0,
            'error': str(e),
            'success': False
        }

def load_with_constraints(input_dir: str, target_config: Dict, loading_order: List[str], strategy: str) -> Dict:
    """
    Main loading function

    Args:
        input_dir: Directory containing data to load
        target_config: Dict with target store information
        loading_order: List of tables in loading order
        strategy: Loading strategy ('insert', 'upsert', 'merge')

    Returns:
        Dict with loading results
    """
    start_time = datetime.now()
    store = target_config['store'].lower()

    results = {
        'run_timestamp': start_time.isoformat(),
        'store': store,
        'strategy': strategy,
        'tables_loaded': [],
        'total_rows_loaded': 0,
        'success': True,
        'errors': []
    }

    conn = None

    try:
        # Connect to target database
        log_info(f"Connecting to CERT {store} database")
        conn = get_cert_db_connection(store, target_config.get('connection'))

        if store == 'sp':
            # Neo4j loading
            nodes_file = Path(input_dir) / "sp_nodes.parquet"
            rels_file = Path(input_dir) / "sp_relationships.parquet"

            if not nodes_file.exists() or not rels_file.exists():
                raise FileNotFoundError(f"Neo4j data files not found in {input_dir}")

            neo4j_result = load_neo4j_graph(conn, nodes_file, rels_file)
            results['neo4j'] = neo4j_result
            results['total_rows_loaded'] = neo4j_result.get('nodes_loaded', 0) + neo4j_result.get('relationships_loaded', 0)
            results['success'] = neo4j_result.get('success', False)

            conn.close()

        else:
            # PostgreSQL loading with transactions
            log_info("Starting transaction")

            # Begin transaction
            conn.autocommit = False

            try:
                # Load tables in order
                for table_name in loading_order:
                    # Find Parquet file for this table
                    parquet_file = Path(input_dir) / f"{store}_{table_name}.parquet"

                    if not parquet_file.exists():
                        log_info(f"Skipping {table_name} (file not found)")
                        continue

                    # Load data
                    df = pd.read_parquet(parquet_file)

                    if len(df) == 0:
                        log_info(f"Skipping {table_name} (no data)")
                        continue

                    # Apply loading strategy
                    if strategy == 'insert':
                        table_result = load_postgres_table_insert(conn, store, table_name, df)
                    elif strategy == 'upsert':
                        table_result = load_postgres_table_upsert(conn, store, table_name, df)
                    elif strategy == 'merge':
                        table_result = load_postgres_table_merge(conn, store, table_name, df)
                    else:
                        raise ValueError(f"Unknown strategy: {strategy}")

                    results['tables_loaded'].append(table_result)

                    if table_result['success']:
                        results['total_rows_loaded'] += table_result['rows_loaded']
                    else:
                        results['errors'].append(table_result.get('error', 'Unknown error'))
                        results['success'] = False
                        raise Exception(f"Failed to load {table_name}")

                # Commit transaction
                log_info("Committing transaction")
                conn.commit()

                log_info(f"Successfully loaded {results['total_rows_loaded']} rows")

            except Exception as e:
                # Rollback on error
                log_error(f"Rolling back transaction due to error: {e}")
                conn.rollback()
                raise

            finally:
                conn.close()

        results['duration_seconds'] = (datetime.now() - start_time).total_seconds()

        # Write load manifest
        manifest_file = Path(input_dir) / "load-manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(results, f, indent=2)

        log_info(f"Loading complete: {results['total_rows_loaded']} rows loaded")

        return results

    except Exception as e:
        log_error(f"Loading failed: {e}")

        if conn and store != 'sp':
            try:
                conn.rollback()
            except:
                pass

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
        input_dir = input_data['input_dir']
        target_config = input_data['target_config']
        loading_order = input_data.get('loading_order', [])
        strategy = input_data.get('strategy', 'insert')

        # Perform loading
        result = load_with_constraints(
            input_dir=input_dir,
            target_config=target_config,
            loading_order=loading_order,
            strategy=strategy
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
