# Load to CERT Skill

You are a data loading specialist operating autonomously. Your mission: Load validated, anonymized data into CERT databases with transaction safety and constraint management.

## Input Parameters

- `district_id`: District whose data to load
- `input_dir`: Directory with validated data (default: `data/anonymized/{district_id}`)
- `loading_order`: Topologically sorted load order (default: from `data/analysis/extraction-order.json`)
- `strategy`: Loading strategy (default: "insert") - options: insert, upsert, merge

## Autonomous Execution Plan

### 1. Pre-Load Validation

CRITICAL: Verify validation passed before loading:

```python
# Load validation report
validation_report = read_json(f'{input_dir}/validation-report.json')

if validation_report['overall_status'] == 'FAILED':
    raise Exception("Validation FAILED - cannot load data to CERT")

if validation_report['summary']['total_errors'] > 0:
    raise Exception(f"{validation_report['summary']['total_errors']} validation errors - cannot proceed")

log_info(f"Validation status: {validation_report['overall_status']}")
log_info(f"Warnings: {validation_report['summary']['total_warnings']}")
```

### 2. Check CERT Connectivity

Test connection to all CERT databases:

```python
def check_cert_connectivity():
    """Test all CERT database connections."""
    cert_stores = {
        'ids': 'postgres-ids-cert',
        'hcp1': 'postgres-hcp1-cert',
        'hcp2': 'postgres-hcp2-cert',
        'adb': 'postgres-adb-cert',
        'sp': 'neo4j-sp-cert'
    }

    for store, mcp_server in cert_stores.items():
        try:
            result = mcp_query(mcp_server, "SELECT 1")
            log_info(f"✓ {store} CERT connection OK")
        except Exception as e:
            raise Exception(f"Cannot connect to {store} CERT: {e}")
```

### 3. Estimate Load Time

```python
def estimate_load_time(input_dir):
    """Estimate how long load will take."""
    total_records = 0
    for file_path in glob(f"{input_dir}/**/*.parquet", recursive=True):
        df = pd.read_parquet(file_path)
        total_records += len(df)

    # Loading: ~30,000 records/minute (conservative)
    minutes = total_records / 30000
    return round(minutes / 60, 1)  # hours
```

### 4. (Optional) Create CERT Backup

```python
def backup_cert_before_load(district_id):
    """
    Optionally create backup of CERT before loading.
    WARNING: This requires significant disk space.
    """
    if os.getenv('ENABLE_CERT_BACKUP') == 'true':
        log_info("Creating CERT backup...")
        # Implementation depends on database tools (pg_dump, etc.)
        # Skipped for autonomous execution unless explicitly enabled
    else:
        log_info("CERT backup skipped (not enabled)")
```

### 5. Load PostgreSQL Stores (IDS, HCP1, HCP2, ADB)

Load in topological order to respect FK constraints:

```python
def load_postgres_store(store_name, input_dir, loading_order, strategy):
    """
    Load data to a PostgreSQL CERT store.
    """
    mcp_server = f"postgres-{store_name}-cert"
    loaded_tables = []

    # Start transaction
    begin_transaction(mcp_server)

    try:
        for table_name in loading_order[store_name]:
            file_path = f"{input_dir}/{store_name}/{table_name}.parquet"

            if not os.path.exists(file_path):
                log_warning(f"File not found: {file_path}, skipping")
                continue

            # Load data
            df = pd.read_parquet(file_path)
            record_count = len(df)

            # Execute load based on strategy
            if strategy == 'insert':
                load_insert(mcp_server, table_name, df)
            elif strategy == 'upsert':
                load_upsert(mcp_server, table_name, df)
            elif strategy == 'merge':
                load_merge(mcp_server, table_name, df)

            log_info(f"Loaded {record_count} records to {store_name}.{table_name}")

            loaded_tables.append({
                'table': table_name,
                'records': record_count,
                'status': 'SUCCESS'
            })

        # Commit transaction
        commit_transaction(mcp_server)
        log_info(f"✓ {store_name} load committed")

        return loaded_tables

    except Exception as e:
        # Rollback on any error
        rollback_transaction(mcp_server)
        log_error(f"✗ {store_name} load failed, rolled back: {e}")
        raise
```

#### Loading Strategies

**Strategy 1: INSERT (default)**
```python
def load_insert(mcp_server, table_name, df):
    """
    Insert new records only. Fails if records already exist.
    """
    # Convert DataFrame to INSERT statements
    for chunk in chunked(df, 1000):
        values = []
        for _, row in chunk.iterrows():
            row_values = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in row])
            values.append(f"({row_values})")

        sql = f"""
            INSERT INTO {table_name} ({', '.join(df.columns)})
            VALUES {', '.join(values)}
        """

        execute_mcp(mcp_server, sql)
```

**Strategy 2: UPSERT**
```python
def load_upsert(mcp_server, table_name, df):
    """
    Insert new records or update existing (PostgreSQL ON CONFLICT).
    """
    pk_columns = get_primary_key_columns(table_name)

    for chunk in chunked(df, 1000):
        # Build INSERT ... ON CONFLICT UPDATE
        sql = f"""
            INSERT INTO {table_name} ({', '.join(df.columns)})
            VALUES ...
            ON CONFLICT ({', '.join(pk_columns)})
            DO UPDATE SET
                {', '.join([f"{col} = EXCLUDED.{col}" for col in df.columns if col not in pk_columns])}
        """

        execute_mcp(mcp_server, sql)
```

**Strategy 3: MERGE**
```python
def load_merge(mcp_server, table_name, df):
    """
    Complex merge logic with conflict resolution.
    """
    # Check which records exist
    existing_ids = get_existing_ids(mcp_server, table_name, df)

    # Split into inserts and updates
    new_records = df[~df['id'].isin(existing_ids)]
    update_records = df[df['id'].isin(existing_ids)]

    # Insert new
    if len(new_records) > 0:
        load_insert(mcp_server, table_name, new_records)

    # Update existing
    if len(update_records) > 0:
        for _, row in update_records.iterrows():
            # Custom conflict resolution logic here
            update_record(mcp_server, table_name, row)
```

### 6. Load Neo4j Graph Store (SP)

```python
def load_neo4j_store(input_dir):
    """
    Load graph data to Neo4j CERT.
    """
    mcp_server = "neo4j-sp-cert"

    # Load nodes
    nodes_file = f"{input_dir}/sp/nodes.parquet"
    nodes_df = pd.read_parquet(nodes_file)

    # Load relationships
    rels_file = f"{input_dir}/sp/relationships.parquet"
    rels_df = pd.read_parquet(rels_file)

    # Create nodes in batches
    for label in nodes_df['labels'].unique():
        label_nodes = nodes_df[nodes_df['labels'] == label]

        for chunk in chunked(label_nodes, 1000):
            # Build Cypher CREATE statement
            cypher = f"""
                UNWIND $nodes AS node
                CREATE (n:{label})
                SET n = node.properties
            """

            nodes_data = chunk.to_dict('records')
            execute_neo4j(mcp_server, cypher, {'nodes': nodes_data})

    # Create relationships
    for rel_type in rels_df['type'].unique():
        type_rels = rels_df[rels_df['type'] == rel_type]

        for chunk in chunked(type_rels, 1000):
            cypher = f"""
                UNWIND $rels AS rel
                MATCH (start) WHERE id(start) = rel.start
                MATCH (end) WHERE id(end) = rel.end
                CREATE (start)-[r:{rel_type}]->(end)
                SET r = rel.properties
            """

            rels_data = chunk.to_dict('records')
            execute_neo4j(mcp_server, cypher, {'rels': rels_data})

    log_info(f"✓ Loaded {len(nodes_df)} nodes and {len(rels_df)} relationships to Neo4j CERT")
```

### 7. Post-Load Validation

Verify data loaded correctly:

```python
def validate_cert_load(district_id, load_manifest):
    """
    Validate data in CERT matches expectations.
    """
    errors = []

    for store_name, tables in load_manifest.items():
        mcp_server = f"postgres-{store_name}-cert" if store_name != 'sp' else 'neo4j-sp-cert'

        for table_info in tables:
            table_name = table_info['table']
            expected_count = table_info['records']

            # Query actual count in CERT
            if store_name != 'sp':
                result = mcp_query(mcp_server, f"SELECT COUNT(*) FROM {table_name} WHERE district_id = '{district_id}'")
                actual_count = result[0]['count']
            else:
                # Neo4j count
                result = execute_neo4j(mcp_server, f"MATCH (n:{table_name} {{district_id: '{district_id}'}}) RETURN count(n) as count")
                actual_count = result[0]['count']

            if actual_count != expected_count:
                errors.append({
                    'table': f"{store_name}.{table_name}",
                    'expected': expected_count,
                    'actual': actual_count,
                    'message': f"Record count mismatch"
                })

    return errors
```

### 8. Re-run Integrity Checks on CERT

```python
def verify_fk_integrity_on_cert(district_id):
    """
    Re-validate FK relationships in CERT environment.
    """
    # Use same validation logic as validate-integrity skill
    # but query from CERT databases instead of Parquet files

    errors = []

    # Example: Verify student FK references exist in schools
    students = mcp_query('postgres-ids-cert', f"SELECT school_id FROM students WHERE district_id = '{district_id}'")
    schools = mcp_query('postgres-ids-cert', f"SELECT id FROM schools WHERE district_id = '{district_id}'")

    student_school_ids = set(s['school_id'] for s in students)
    school_ids = set(s['id'] for s in schools)

    orphans = student_school_ids - school_ids

    if orphans:
        errors.append({
            'check': 'fk_students_schools',
            'orphans': len(orphans),
            'message': 'Students reference non-existent schools'
        })

    return errors
```

### 9. Generate Load Report

Create `data/loads/{district_id}/load-report.json`:

```json
{
  "load_run_id": "load-20251106-001",
  "district_id": "district-001",
  "started_at": "2025-11-06T20:00:00Z",
  "completed_at": "2025-11-06T21:45:00Z",
  "duration_minutes": 105,
  "overall_status": "SUCCESS",
  "strategy": "insert",
  "stores": {
    "ids": {
      "status": "SUCCESS",
      "tables_loaded": 45,
      "records_loaded": 250000,
      "duration_minutes": 32,
      "transaction": "COMMITTED"
    },
    "hcp1": {
      "status": "SUCCESS",
      "tables_loaded": 32,
      "records_loaded": 180000,
      "duration_minutes": 24,
      "transaction": "COMMITTED"
    },
    "hcp2": {
      "status": "SUCCESS",
      "tables_loaded": 28,
      "records_loaded": 120000,
      "duration_minutes": 18,
      "transaction": "COMMITTED"
    },
    "adb": {
      "status": "SUCCESS",
      "tables_loaded": 52,
      "records_loaded": 200000,
      "duration_minutes": 28,
      "transaction": "COMMITTED"
    },
    "sp": {
      "status": "SUCCESS",
      "nodes_loaded": 100000,
      "relationships_loaded": 250000,
      "duration_minutes": 3
    }
  },
  "totals": {
    "tables_loaded": 157,
    "records_loaded": 750000
  },
  "post_load_validation": {
    "status": "PASSED",
    "record_count_verification": "PASSED",
    "fk_integrity_verification": "PASSED",
    "errors": 0
  }
}
```

### 10. Report Completion

```
✓ CERT Load Complete

District: district-001
Duration: 1.75 hours
Strategy: INSERT

Load Summary:
- IDS: 250,000 records (45 tables) ✓ COMMITTED
- HCP1: 180,000 records (32 tables) ✓ COMMITTED
- HCP2: 120,000 records (28 tables) ✓ COMMITTED
- ADB: 200,000 records (52 tables) ✓ COMMITTED
- SP (Graph): 100,000 nodes, 250,000 relationships ✓ COMMITTED

Total: 750,000 records loaded successfully

Post-Load Validation: PASSED
- Record counts: ✓ All match expectations
- FK integrity: ✓ All relationships valid in CERT
- Data accessibility: ✓ All tables queryable

CERT Environment Status: READY FOR TESTING

Report: data/loads/district-001/load-report.json

Next step: Generate migration report
```

## Tools Available

- **MCP Servers**: All CERT database connections
- **ETL MCP**: `load_with_constraints` tool
- **Python Libraries**: pandas, sqlalchemy

## Success Criteria

- ✓ All tables loaded in dependency order
- ✓ All transactions committed successfully
- ✓ Record counts match source
- ✓ FK integrity validated on CERT
- ✓ 0 load errors

## Error Handling

**Load Failures**:
- Immediate rollback of current store transaction
- Log detailed error with table/record information
- Stop loading remaining stores
- Report failure status

**FK Violations**:
- Should not occur if validation passed
- If detected, rollback and investigate

**Transaction Timeout**:
- Increase timeout for large loads
- Consider chunking very large tables

If ANY store fails to load, entire migration is considered FAILED.
Rollback completed, CERT remains in pre-migration state.

Execute autonomously. Report progress every 10 tables loaded.
