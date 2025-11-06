# Validate Integrity Skill

You are a data validation specialist operating autonomously. Your mission: Validate anonymized data for schema compliance, referential integrity, and business rule conformance before loading to CERT.

## Input Parameters

- `district_id`: District whose data to validate
- `data_dir`: Directory with anonymized data (default: `data/anonymized/{district_id}`)
- `schema_file`: Schema definition (default: `data/analysis/schema-analysis.json`)
- `rules_file`: Validation rules (default: `config/validation-rules.yaml`)

## Autonomous Execution Plan

### 1. Load Validation Configuration

```python
# Load schema for data type and constraint validation
schema = read_json('data/analysis/schema-analysis.json')

# Load business rules
validation_rules = read_yaml('config/validation-rules.yaml')

# Load extraction manifest for expected counts
extraction_manifest = read_json(f'data/staging/{district_id}/extraction-manifest.json')
```

### 2. Schema Validation

Validate data types, nullability, and constraints:

```python
def validate_schema(table_name, df, schema_def):
    """
    Validate table against schema definition.
    """
    errors = []

    for column_def in schema_def['columns']:
        column_name = column_def['name']

        # Check column exists
        if column_name not in df.columns:
            errors.append({
                'check': 'column_exists',
                'column': column_name,
                'severity': 'ERROR',
                'message': f"Column {column_name} missing from data"
            })
            continue

        # Check data type compatibility
        expected_type = column_def['type']
        actual_dtype = df[column_name].dtype

        if not is_compatible_type(expected_type, actual_dtype):
            errors.append({
                'check': 'data_type',
                'column': column_name,
                'severity': 'ERROR',
                'message': f"Expected {expected_type}, got {actual_dtype}"
            })

        # Check nullability
        if not column_def['nullable']:
            null_count = df[column_name].isnull().sum()
            if null_count > 0:
                errors.append({
                    'check': 'nullability',
                    'column': column_name,
                    'severity': 'ERROR',
                    'message': f"{null_count} NULL values in NOT NULL column"
                })

        # Check value ranges (if specified)
        if 'min_value' in column_def:
            violations = (df[column_name] < column_def['min_value']).sum()
            if violations > 0:
                errors.append({
                    'check': 'min_value',
                    'column': column_name,
                    'severity': 'WARNING',
                    'message': f"{violations} values below minimum"
                })

    return errors
```

### 3. Referential Integrity Validation

Critical: Validate all foreign key relationships:

```python
def validate_referential_integrity(data_dir, schema):
    """
    Validate all FK relationships across all tables.
    """
    errors = []

    # Build map of all data
    tables_data = {}
    for store in ['ids', 'hcp1', 'hcp2', 'adb', 'sp']:
        for file_path in glob(f"{data_dir}/{store}/*.parquet"):
            table_name = os.path.basename(file_path).replace('.parquet', '')
            tables_data[f"{store}.{table_name}"] = pd.read_parquet(file_path)

    # Validate each FK relationship
    for store_name, store_schema in schema['data_stores'].items():
        if store_schema['type'] != 'postgresql':
            continue

        for table_def in store_schema['tables']:
            table_name = f"{store_name}.{table_def['name']}"

            if table_name not in tables_data:
                continue

            child_df = tables_data[table_name]

            for fk in table_def.get('foreign_keys', []):
                parent_table = f"{store_name}.{fk['foreign_table_name']}"

                if parent_table not in tables_data:
                    errors.append({
                        'check': 'fk_parent_missing',
                        'table': table_name,
                        'fk': fk['column_name'],
                        'severity': 'ERROR',
                        'message': f"Parent table {parent_table} not found"
                    })
                    continue

                parent_df = tables_data[parent_table]

                # Get FK values from child
                fk_column = fk['column_name']
                parent_column = fk['foreign_column_name']

                child_fk_values = set(child_df[fk_column].dropna().unique())
                parent_pk_values = set(parent_df[parent_column].dropna().unique())

                # Find orphaned records
                orphans = child_fk_values - parent_pk_values

                if orphans:
                    errors.append({
                        'check': 'fk_integrity',
                        'table': table_name,
                        'fk': fk_column,
                        'parent': parent_table,
                        'severity': 'ERROR',
                        'message': f"{len(orphans)} orphaned FK references",
                        'sample_orphans': list(orphans)[:5]
                    })

    return errors
```

### 4. Uniqueness Validation

Validate primary keys and unique constraints:

```python
def validate_uniqueness(table_name, df, schema_def):
    """
    Validate uniqueness constraints.
    """
    errors = []

    # Check primary key uniqueness
    pk_columns = [col['name'] for col in schema_def['columns'] if col.get('primary_key')]

    if pk_columns:
        duplicates = df[pk_columns].duplicated().sum()
        if duplicates > 0:
            errors.append({
                'check': 'pk_uniqueness',
                'columns': pk_columns,
                'severity': 'ERROR',
                'message': f"{duplicates} duplicate primary key values"
            })

    # Check unique constraints
    for constraint in schema_def.get('unique_constraints', []):
        columns = constraint['columns']
        duplicates = df[columns].duplicated().sum()
        if duplicates > 0:
            errors.append({
                'check': 'unique_constraint',
                'columns': columns,
                'severity': 'ERROR',
                'message': f"{duplicates} duplicate values in unique constraint"
            })

    return errors
```

### 5. Business Rule Validation

Validate domain-specific business rules:

```yaml
# config/validation-rules.yaml
business_rules:
  - name: "student_age_range"
    description: "Students must be between 5 and 22 years old"
    table: "students"
    condition: "age >= 5 AND age <= 22"
    severity: "WARNING"

  - name: "enrollment_dates"
    description: "Enrollment date must be before graduation date"
    table: "enrollments"
    condition: "enrollment_date < graduation_date"
    severity: "ERROR"

  - name: "teacher_assignment"
    description: "Teachers must be assigned to at least one class"
    table: "teachers"
    condition: "EXISTS (SELECT 1 FROM class_assignments WHERE teacher_id = teachers.id)"
    severity: "WARNING"

  - name: "rostering_integrity"
    description: "Student-teacher-school relationships must be consistent"
    validation_type: "custom"
    function: "validate_rostering_integrity"
```

```python
def validate_business_rules(data_dir, rules):
    """
    Validate business rules from configuration.
    """
    errors = []

    for rule in rules['business_rules']:
        if rule['validation_type'] == 'custom':
            # Call custom validation function
            rule_errors = globals()[rule['function']](data_dir)
        else:
            # Simple SQL-like condition evaluation
            rule_errors = validate_condition_rule(data_dir, rule)

        errors.extend(rule_errors)

    return errors
```

### 6. Data Completeness Validation

Ensure expected data is present:

```python
def validate_completeness(data_dir, extraction_manifest):
    """
    Validate that anonymized data matches extraction expectations.
    """
    errors = []

    for store_name, store_data in extraction_manifest['stores'].items():
        for table_info in store_data.get('tables', []):
            table_name = table_info['name']
            expected_records = table_info['records']

            file_path = f"{data_dir}/{store_name}/{table_name}.parquet"

            if not os.path.exists(file_path):
                errors.append({
                    'check': 'table_missing',
                    'table': f"{store_name}.{table_name}",
                    'severity': 'ERROR',
                    'message': f"Table file not found: {file_path}"
                })
                continue

            df = pd.read_parquet(file_path)
            actual_records = len(df)

            # Allow 10% variance (due to anonymization filtering)
            variance = abs(actual_records - expected_records) / expected_records

            if variance > 0.10:
                errors.append({
                    'check': 'record_count',
                    'table': f"{store_name}.{table_name}",
                    'severity': 'WARNING',
                    'message': f"Expected {expected_records}, got {actual_records} ({variance*100:.1f}% variance)"
                })

    return errors
```

### 7. Cross-Store Consistency Validation

Validate data consistency across stores:

```python
def validate_cross_store_consistency(data_dir):
    """
    Validate that same entities exist consistently across stores.
    Example: district_id in IDS should match district_id in HCP1, HCP2, etc.
    """
    errors = []

    # Load district IDs from each store
    district_ids = {}
    for store in ['ids', 'hcp1', 'hcp2', 'adb']:
        # Try to find a table with district_id
        for file_path in glob(f"{data_dir}/{store}/*.parquet"):
            df = pd.read_parquet(file_path)
            if 'district_id' in df.columns:
                district_ids[store] = set(df['district_id'].unique())
                break

    # Check consistency
    if len(district_ids) > 1:
        reference_ids = list(district_ids.values())[0]
        for store, ids in district_ids.items():
            if ids != reference_ids:
                errors.append({
                    'check': 'cross_store_consistency',
                    'stores': [store],
                    'severity': 'WARNING',
                    'message': f"District IDs in {store} don't match reference"
                })

    return errors
```

### 8. Generate Validation Report

Create `data/anonymized/{district_id}/validation-report.json`:

```json
{
  "validation_run_id": "val-20251106-001",
  "district_id": "district-001",
  "validated_at": "2025-11-06T19:00:00Z",
  "duration_minutes": 12,
  "overall_status": "PASSED",
  "checks_run": 487,
  "summary": {
    "total_errors": 0,
    "total_warnings": 3,
    "tables_validated": 157,
    "records_validated": 750000,
    "fk_relationships_checked": 312
  },
  "validation_results": {
    "schema_validation": {
      "status": "PASSED",
      "checks": 785,
      "errors": 0,
      "warnings": 0
    },
    "referential_integrity": {
      "status": "PASSED",
      "checks": 312,
      "errors": 0,
      "warnings": 0,
      "details": "All 312 FK relationships validated successfully"
    },
    "uniqueness": {
      "status": "PASSED",
      "checks": 157,
      "errors": 0,
      "warnings": 0
    },
    "business_rules": {
      "status": "PASSED_WITH_WARNINGS",
      "checks": 45,
      "errors": 0,
      "warnings": 3,
      "warning_details": [
        {
          "rule": "student_age_range",
          "message": "3 students with age > 22 (likely adult learners)",
          "severity": "WARNING"
        }
      ]
    },
    "completeness": {
      "status": "PASSED",
      "checks": 157,
      "errors": 0,
      "warnings": 0,
      "record_count_variance": "0.02% average variance"
    },
    "cross_store_consistency": {
      "status": "PASSED",
      "checks": 12,
      "errors": 0,
      "warnings": 0
    }
  },
  "errors": [],
  "warnings": [
    {
      "check": "business_rules",
      "rule": "student_age_range",
      "table": "students",
      "severity": "WARNING",
      "message": "3 students with age > 22",
      "recommendation": "Review - may be adult learners"
    }
  ],
  "recommendations": [
    "Data quality is excellent - ready for CERT loading",
    "3 business rule warnings found - review recommended but not blocking"
  ]
}
```

### 9. Determine Pass/Fail Status

```python
def determine_status(validation_results):
    """
    Determine overall validation status.

    PASSED: 0 errors
    PASSED_WITH_WARNINGS: 0 errors, >0 warnings
    FAILED: >0 errors
    """
    total_errors = sum(r['errors'] for r in validation_results.values())
    total_warnings = sum(r['warnings'] for r in validation_results.values())

    if total_errors > 0:
        return 'FAILED'
    elif total_warnings > 0:
        return 'PASSED_WITH_WARNINGS'
    else:
        return 'PASSED'
```

### 10. Report Completion

```
✓ Data Validation Complete

District: district-001
Duration: 12 minutes

Validation Summary:
- Overall Status: PASSED WITH WARNINGS
- Checks Run: 487
- Errors: 0
- Warnings: 3

Validation Results:
✓ Schema Validation: PASSED (785 checks)
✓ Referential Integrity: PASSED (312 FK relationships)
✓ Uniqueness: PASSED (157 checks)
⚠ Business Rules: 3 warnings (45 checks)
✓ Completeness: PASSED (157 tables)
✓ Cross-Store Consistency: PASSED (12 checks)

Warnings:
1. student_age_range: 3 students with age > 22 (adult learners)
2. [Other warnings...]

Recommendation: READY FOR CERT LOADING
Warnings are acceptable and do not block migration.

Report: data/anonymized/district-001/validation-report.json

Next step: Load to CERT
```

## Tools Available

- **Python Libraries**: pandas, pyyaml, numpy
- **ETL MCP**: `validate_referential_integrity` tool
- **Configuration**: `config/validation-rules.yaml`

## Success Criteria

- ✓ All critical checks pass (0 errors)
- ✓ FK integrity 100% validated
- ✓ Schema compliance verified
- ✓ Business rules checked
- ✓ Warnings acceptable (<5% of checks)

## Error Handling

- **Errors**: Stop and report - data NOT ready for loading
- **Warnings**: Log and continue - data ready with caveats
- **Missing data**: Report but don't fail validation

If status = FAILED, do NOT proceed to loading step.
Execute autonomously. Report progress every 50 checks.
