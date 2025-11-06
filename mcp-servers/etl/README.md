# ETL MCP Server

Custom MCP server providing high-level ETL operations for the data migration project. This server acts as a bridge between Claude Code and Python-based ETL scripts.

## Features

- **Extract with Relationships**: Extract data maintaining FK relationships using topological ordering
- **Anonymize Dataset**: Apply PII anonymization rules while preserving referential integrity
- **Validate Integrity**: Comprehensive data validation (schema, FK, business rules)
- **Load with Constraints**: Dependency-aware loading with transaction management

## Installation

```bash
cd mcp-servers/etl
npm install
```

## Architecture

The ETL MCP server is a lightweight Node.js wrapper that:
1. Receives tool requests from Claude Code via MCP protocol
2. Invokes corresponding Python scripts with JSON input
3. Returns Python script output as MCP tool results

This design allows:
- Complex data processing in Python (pandas, NumPy, etc.)
- Simple integration with Claude Code via MCP
- Easy testing and debugging of Python scripts independently

## Tools Provided

### 1. `extract_with_relationships`

Extract data from source database with relationship resolution.

**Input**:
```json
{
  "source_config": {
    "store": "ids",
    "connection": "postgres-ids-prod"
  },
  "filter": {
    "district_id": "district-001"
  },
  "extraction_order": ["districts", "schools", "students", "enrollments"],
  "output_dir": "data/staging/district-001"
}
```

**Python Script**: `scripts/extractors/extract_with_relationships.py`

### 2. `anonymize_dataset`

Anonymize PII fields in extracted dataset.

**Input**:
```json
{
  "input_dir": "data/staging/district-001",
  "output_dir": "data/anonymized/district-001",
  "rules_file": "config/anonymization-rules.yaml",
  "consistency_map": "data/anonymized/district-001/consistency-map.encrypted"
}
```

**Python Script**: `scripts/anonymize.py`

### 3. `validate_referential_integrity`

Validate data integrity and business rules.

**Input**:
```json
{
  "data_dir": "data/anonymized/district-001",
  "schema_file": "data/analysis/schema-analysis.json",
  "validation_rules": "config/validation-rules.yaml",
  "output_report": "data/anonymized/district-001/validation-report.json"
}
```

**Python Script**: `scripts/validators/validate_integrity.py`

### 4. `load_with_constraints`

Load data to target database with constraint management.

**Input**:
```json
{
  "input_dir": "data/anonymized/district-001",
  "target_config": {
    "store": "ids",
    "connection": "postgres-ids-cert"
  },
  "loading_order": ["districts", "schools", "students", "enrollments"],
  "strategy": "insert"
}
```

**Python Script**: `scripts/loaders/load_with_constraints.py`

## Python Script Contract

All Python scripts must:
1. Read JSON input from stdin
2. Process data according to input parameters
3. Write JSON output to stdout
4. Exit with code 0 on success, non-zero on failure
5. Log errors to stderr

**Example Python Script Template**:
```python
#!/usr/bin/env python3
import json
import sys

def main():
    # Read input from stdin
    input_data = json.load(sys.stdin)

    # Process data
    try:
        result = process(input_data)

        # Write output to stdout
        json.dump(result, sys.stdout, indent=2)
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## Configuration

Set the PROJECT_ROOT environment variable to the project root directory:

```bash
export PROJECT_ROOT="/Users/colossus/development/datamig"
```

If not set, it defaults to the current working directory.

## Testing

Test individual Python scripts:

```bash
echo '{"input": "test"}' | python3 scripts/extractors/extract_with_relationships.py
```

Test the MCP server:

```bash
node index.js
```

## Error Handling

- Python script errors are captured and returned as MCP tool errors
- Stderr output is included in error messages for debugging
- Non-zero exit codes trigger error responses

## Performance

- Python processes are spawned per request (no persistent process)
- For long-running operations, consider implementing progress callbacks
- Large datasets should use streaming/chunking in Python scripts

## Dependencies

Python scripts may require:
- pandas
- pyarrow (for Parquet files)
- sqlalchemy
- psycopg2-binary
- neo4j-driver
- faker (for anonymization)
- pyyaml
- great-expectations (for validation)

Install Python dependencies:
```bash
pip install pandas pyarrow sqlalchemy psycopg2-binary neo4j faker pyyaml great-expectations
```
