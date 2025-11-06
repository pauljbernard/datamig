# Extract District Data Skill

You are a data extraction specialist operating autonomously. Your mission: Extract all data for a specified district while maintaining referential integrity across all 5 data stores.

## Input Parameters

When invoked, you will receive:
- `district_id`: The district to extract (e.g., "district-001")
- `district_manifest`: Path to district manifest JSON (optional, default: `data/manifests/district-manifest.json`)
- `extraction_order`: Path to extraction order JSON (optional, default: `data/analysis/extraction-order.json`)
- `output_dir`: Output directory (optional, default: `data/staging/{district_id}`)

## Autonomous Execution Plan

Execute the following workflow without human intervention:

### 1. Load Configuration

Read required configuration files:

```python
# Load district metadata
district_manifest = read_json('data/manifests/district-manifest.json')
district = find_district(district_manifest, district_id)

# Load extraction order (topologically sorted tables)
extraction_order = read_json('data/analysis/extraction-order.json')

# Load schema analysis (for FK information)
schema = read_json('data/analysis/schema-analysis.json')
```

### 2. Create Output Directory Structure

```bash
data/staging/{district_id}/
├── ids/          # IDS data store extracts
├── hcp1/         # HCP1 data store extracts
├── hcp2/         # HCP2 data store extracts
├── adb/          # ADB data store extracts
├── sp/           # SP (Neo4j) graph extracts
└── extraction-manifest.json  # Metadata about extraction
```

### 3. Extract PostgreSQL Data Stores (IDS, HCP1, HCP2, ADB)

For each PostgreSQL data store, extract tables in topological order:

#### Extraction Algorithm

```python
def extract_store(store_name, extraction_order, district_id):
    """
    Extract data for a store following topological order.
    """
    output_dir = f"data/staging/{district_id}/{store_name}"
    extracted_tables = []

    for table_name in extraction_order[store_name]:
        try:
            # Build district-filtered query
            query = build_district_query(table_name, district_id, schema)

            # Execute via MCP server
            data = execute_mcp_query(f"postgres-{store_name}-prod", query)

            # Write to Parquet file
            write_parquet(f"{output_dir}/{table_name}.parquet", data)

            # Log metrics
            record_count = len(data)
            log_extraction(store_name, table_name, record_count)

            extracted_tables.append({
                'table': table_name,
                'records': record_count,
                'file': f"{table_name}.parquet"
            })

        except Exception as e:
            log_error(f"Failed to extract {store_name}.{table_name}: {e}")
            # Continue with other tables (don't fail entire extraction)

    return extracted_tables
```

#### Build District-Filtered Query

The key challenge: filtering by district across all tables.

**Strategy 1: Direct district_id column**
```sql
-- Tables with direct district_id FK
SELECT * FROM students WHERE district_id = $district_id;
```

**Strategy 2: Indirect via parent table**
```sql
-- Tables that reference a parent with district_id
SELECT e.* FROM enrollments e
JOIN students s ON e.student_id = s.id
WHERE s.district_id = $district_id;
```

**Strategy 3: Multi-hop traversal**
```sql
-- Tables multiple hops away
SELECT a.* FROM assignments a
JOIN classes c ON a.class_id = c.id
JOIN schools s ON c.school_id = s.id
WHERE s.district_id = $district_id;
```

**Implementation**:
```python
def build_district_query(table_name, district_id, schema):
    """
    Build a district-filtered SELECT query for any table.
    """
    table_info = schema['data_stores'][store_name]['tables'][table_name]

    # Check if table has direct district_id column
    if has_column(table_info, 'district_id'):
        return f"SELECT * FROM {table_name} WHERE district_id = '{district_id}'"

    # Find FK path to a table with district_id
    path = find_path_to_district(table_name, schema)

    if not path:
        # No FK path to district - extract all (reference tables, etc.)
        log_warning(f"{table_name} has no district FK - extracting all records")
        return f"SELECT * FROM {table_name}"

    # Build JOIN query following FK path
    joins = []
    current = table_name
    for fk in path:
        parent = fk['foreign_table_name']
        join_col = fk['column_name']
        parent_col = fk['foreign_column_name']
        joins.append(f"JOIN {parent} ON {current}.{join_col} = {parent}.{parent_col}")
        current = parent

    # Last table in path should have district_id
    where_clause = f"WHERE {current}.district_id = '{district_id}'"

    query = f"""
        SELECT {table_name}.*
        FROM {table_name}
        {' '.join(joins)}
        {where_clause}
    """

    return query
```

#### Handle Special Cases

**Circular Dependencies**:
```python
# For tables in circular dependency, use the break strategy
if table_name in circular_dependency_tables:
    # Extract without validating the circular FK
    query += " -- Note: Circular FK validation disabled"
```

**Many-to-Many Junction Tables**:
```python
# Extract after both parent tables
# e.g., student_courses requires both students and courses extracted first
if is_junction_table(table_name):
    ensure_parents_extracted(table_name, extracted_tables)
```

**Large Tables with Pagination**:
```python
# For tables with >1M rows, use chunked extraction
if estimated_rows > 1000000:
    extract_in_chunks(table_name, chunk_size=100000)
```

### 4. Extract Neo4j Graph Database (SP)

Neo4j extraction uses Cypher traversal from district root nodes:

```cypher
// Find all nodes connected to district
MATCH path = (d:District {id: $districtId})-[*0..10]-(connected)
RETURN
  d,
  connected,
  relationships(path) as rels
LIMIT 100000
```

**Extraction Strategy**:
```python
def extract_neo4j(district_id):
    """
    Extract Neo4j graph for district.
    """
    # Use traverse_from_node tool
    result = mcp_neo4j.traverse_from_node(
        node_label='District',
        node_property='id',
        node_value=district_id,
        max_depth=10
    )

    # Convert to nodes and relationships
    nodes = extract_nodes(result)
    relationships = extract_relationships(result)

    # Write to Parquet files
    write_parquet(f"data/staging/{district_id}/sp/nodes.parquet", nodes)
    write_parquet(f"data/staging/{district_id}/sp/relationships.parquet", relationships)

    return {
        'nodes': len(nodes),
        'relationships': len(relationships)
    }
```

### 5. Validate Extraction Completeness

After extraction, validate that data is complete:

```python
def validate_extraction(district_id, extracted_data):
    """
    Validate extracted data meets expectations.
    """
    validations = []

    # 1. Check record counts are reasonable
    expected_students = district_manifest[district_id]['metrics']['students']
    actual_students = extracted_data['ids']['students']['records']

    if actual_students < expected_students * 0.9:  # Within 10% is OK
        validations.append({
            'check': 'student_count',
            'status': 'WARNING',
            'message': f"Expected ~{expected_students}, got {actual_students}"
        })

    # 2. Check no missing FK references
    # All FK values in child tables should exist in parent tables
    for fk in schema['foreign_keys']:
        parent_records = load_parquet(f"{district_id}/{fk['parent_table']}.parquet")
        child_records = load_parquet(f"{district_id}/{fk['child_table']}.parquet")

        parent_ids = set(parent_records[fk['parent_column']])
        child_fk_values = set(child_records[fk['child_column']])

        orphans = child_fk_values - parent_ids

        if orphans:
            validations.append({
                'check': f"fk_{fk['child_table']}_{fk['parent_table']}",
                'status': 'ERROR',
                'message': f"Found {len(orphans)} orphaned FK references"
            })

    # 3. Check all expected tables extracted
    missing_tables = []
    for store, tables in extraction_order.items():
        for table in tables:
            file_path = f"{district_id}/{store}/{table}.parquet"
            if not file_exists(file_path):
                missing_tables.append(f"{store}.{table}")

    if missing_tables:
        validations.append({
            'check': 'missing_tables',
            'status': 'ERROR',
            'message': f"Missing {len(missing_tables)} tables: {missing_tables[:5]}"
        })

    return validations
```

### 6. Generate Extraction Manifest

Create `data/staging/{district_id}/extraction-manifest.json`:

```json
{
  "extraction_id": "ext-20251106-001",
  "district_id": "district-001",
  "district_name": "Large Urban District A",
  "started_at": "2025-11-06T14:00:00Z",
  "completed_at": "2025-11-06T16:15:00Z",
  "duration_minutes": 135,
  "status": "SUCCESS",
  "stores": {
    "ids": {
      "tables_extracted": 45,
      "total_records": 250000,
      "total_size_mb": 1200,
      "duration_minutes": 45,
      "tables": [
        {"name": "districts", "records": 1, "size_mb": 0.001},
        {"name": "schools", "records": 150, "size_mb": 2.5},
        {"name": "students", "records": 75000, "size_mb": 850}
      ]
    },
    "hcp1": {
      "tables_extracted": 32,
      "total_records": 180000,
      "total_size_mb": 850,
      "duration_minutes": 30
    },
    "hcp2": {
      "tables_extracted": 28,
      "total_records": 120000,
      "total_size_mb": 600,
      "duration_minutes": 22
    },
    "adb": {
      "tables_extracted": 52,
      "total_records": 200000,
      "total_size_mb": 1500,
      "duration_minutes": 35
    },
    "sp": {
      "nodes_extracted": 100000,
      "relationships_extracted": 250000,
      "total_size_mb": 400,
      "duration_minutes": 3
    }
  },
  "totals": {
    "tables": 157,
    "records": 750000,
    "size_mb": 4550
  },
  "validation": {
    "status": "PASSED",
    "checks_run": 487,
    "warnings": 3,
    "errors": 0
  }
}
```

### 7. Report Completion

Generate summary and report back:

```
✓ District Data Extraction Complete

District: district-001 (Large Urban District A)
Duration: 2.25 hours

Extraction Summary:
- IDS: 250,000 records (45 tables, 1.2 GB)
- HCP1: 180,000 records (32 tables, 850 MB)
- HCP2: 120,000 records (28 tables, 600 MB)
- ADB: 200,000 records (52 tables, 1.5 GB)
- SP (Graph): 100,000 nodes, 250,000 relationships (400 MB)

Total: 750,000 records, 4.5 GB

Validation: PASSED
- FK integrity: ✓ All foreign keys valid
- Record counts: ✓ Within expected ranges
- Completeness: ✓ All tables extracted

Output: data/staging/district-001/

Next step: Anonymize PII
```

## Tools Available

- **MCP Servers**: All PROD database connections
- **ETL MCP**: `extract_with_relationships` tool (for complex extractions)
- **Python Scripts**: `scripts/extractors/*.py`
- **Write Tool**: For creating Parquet files and manifest

## Success Criteria

- ✓ All tables extracted in dependency order
- ✓ No missing FK references (orphaned records)
- ✓ Record counts match expectations (within 10%)
- ✓ All 5 data stores processed
- ✓ Extraction manifest generated
- ✓ Output files in Parquet format

## Error Handling

**Connection Failures**:
- Retry up to 3 times with exponential backoff
- If store unreachable, log error and continue with other stores

**Query Timeouts**:
- For large tables, switch to chunked extraction
- Process in batches of 100K records

**Missing FK Paths**:
- For tables with no district FK path, extract all records (usually small reference tables)
- Document in extraction manifest

**Disk Space**:
- Check available space before extraction
- Compress Parquet files with snappy compression

Do NOT fail the entire extraction due to individual table errors. Extract as much as possible and document failures in the manifest.

Execute this entire workflow autonomously. Report progress every 10 tables extracted.
