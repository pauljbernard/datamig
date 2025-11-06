# Anonymize PII Skill

You are a data anonymization specialist operating autonomously. Your mission: Anonymize all PII (Personally Identifiable Information) in extracted data while preserving referential integrity and data utility.

## Input Parameters

- `district_id`: The district whose data to anonymize
- `input_dir`: Directory with extracted data (default: `data/staging/{district_id}`)
- `output_dir`: Directory for anonymized data (default: `data/anonymized/{district_id}`)
- `rules_file`: Anonymization rules (default: `config/anonymization-rules.yaml`)

## Autonomous Execution Plan

### 1. Load Anonymization Rules

Read configuration from `config/anonymization-rules.yaml`:

```yaml
rules:
  # Email addresses
  - field_pattern: ".*email.*"
    strategy: faker
    faker_type: email
    preserve_domain: false

  # Social Security Numbers
  - field_pattern: ".*ssn.*|.*social_security.*"
    strategy: hash
    hash_algorithm: sha256
    salt: "${ENV_ANONYMIZATION_SALT}"

  # Names
  - field_pattern: ".*first_name.*|.*last_name.*|.*full_name.*"
    strategy: faker
    faker_type: name
    consistent_per_id: true

  # Phone numbers
  - field_pattern: ".*phone.*|.*mobile.*|.*telephone.*"
    strategy: faker
    faker_type: phone_number

  # Addresses
  - field_pattern: ".*address.*|.*street.*|.*city.*|.*zip.*|.*postal.*"
    strategy: faker
    faker_type: address

  # Student/Staff IDs (preserve for FKs)
  - field_pattern: ".*_id$"
    strategy: preserve
    reason: "Foreign key - must maintain integrity"
```

### 2. Detect PII Fields

For each Parquet file in input directory:

```python
def detect_pii_fields(table_name, columns, rules):
    """
    Identify which columns contain PII based on rules.
    """
    pii_fields = []

    for column in columns:
        for rule in rules:
            if re.match(rule['field_pattern'], column, re.IGNORECASE):
                pii_fields.append({
                    'column': column,
                    'strategy': rule['strategy'],
                    'config': rule
                })
                break

    return pii_fields
```

### 3. Initialize Consistency Map

Critical: Same PII value must map to same anonymized value across ALL tables.

```python
# Example: "John Doe" in students table → "Alice Smith"
#          "John Doe" in staff table → "Alice Smith" (SAME)

consistency_map = {
    'first_names': {},   # "John" → "Alice"
    'last_names': {},    # "Doe" → "Smith"
    'emails': {},        # "john@example.com" → "alice789@example.com"
    'phones': {},        # "555-1234" → "555-9876"
    'ssns': {},          # "123-45-6789" → <hashed value>
}
```

### 4. Apply Anonymization Strategies

#### Strategy 1: Consistent Hashing (for SSN, sensitive IDs)

```python
def anonymize_hash(value, salt):
    """
    Hash value with salt. Same input → same output.
    Irreversible, preserves uniqueness.
    """
    import hashlib
    return hashlib.sha256(f"{value}{salt}".encode()).hexdigest()[:16]
```

#### Strategy 2: Faker (for names, emails, phones, addresses)

```python
from faker import Faker
fake = Faker()

def anonymize_faker(value, faker_type, consistency_map, key):
    """
    Generate realistic fake data. Use consistency map to ensure
    same value gets same fake replacement.
    """
    if value in consistency_map[key]:
        return consistency_map[key][value]

    # Generate new fake value
    if faker_type == 'name':
        fake_value = fake.name()
    elif faker_type == 'email':
        fake_value = fake.email()
    elif faker_type == 'phone_number':
        fake_value = fake.phone_number()
    elif faker_type == 'address':
        fake_value = fake.address()
    else:
        fake_value = fake.text(max_nb_chars=20)

    # Store in consistency map
    consistency_map[key][value] = fake_value

    return fake_value
```

#### Strategy 3: Tokenization (reversible if needed)

```python
def anonymize_tokenize(value, token_map):
    """
    Replace with token. Optionally reversible.
    """
    if value not in token_map:
        token_map[value] = f"TOKEN_{len(token_map):08d}"
    return token_map[value]
```

#### Strategy 4: Nullification (for highly sensitive data)

```python
def anonymize_nullify(value):
    """
    Remove data entirely by replacing with NULL.
    """
    return None
```

### 5. Process All Tables

```python
def anonymize_district_data(district_id, input_dir, output_dir, rules):
    """
    Anonymize all extracted data for a district.
    """
    consistency_map = initialize_consistency_map()
    stores = ['ids', 'hcp1', 'hcp2', 'adb', 'sp']

    for store in stores:
        store_input = f"{input_dir}/{store}"
        store_output = f"{output_dir}/{store}"

        # Get all parquet files
        files = glob(f"{store_input}/*.parquet")

        for file_path in files:
            table_name = os.path.basename(file_path).replace('.parquet', '')

            # Load data
            df = pd.read_parquet(file_path)

            # Detect PII fields
            pii_fields = detect_pii_fields(table_name, df.columns, rules)

            # Anonymize each PII field
            for pii_field in pii_fields:
                column = pii_field['column']
                strategy = pii_field['strategy']
                config = pii_field['config']

                if strategy == 'hash':
                    df[column] = df[column].apply(
                        lambda x: anonymize_hash(x, config['salt']) if pd.notna(x) else None
                    )
                elif strategy == 'faker':
                    df[column] = df[column].apply(
                        lambda x: anonymize_faker(x, config['faker_type'], consistency_map, column) if pd.notna(x) else None
                    )
                elif strategy == 'tokenize':
                    df[column] = df[column].apply(
                        lambda x: anonymize_tokenize(x, consistency_map.get('tokens', {})) if pd.notna(x) else None
                    )
                elif strategy == 'nullify':
                    df[column] = None
                elif strategy == 'preserve':
                    pass  # Don't anonymize (FK fields, etc.)

            # Write anonymized data
            df.to_parquet(f"{store_output}/{table_name}.parquet", compression='snappy')

            log_anonymization(store, table_name, len(pii_fields), len(df))

    return consistency_map
```

### 6. Validate Anonymization

After anonymization, verify no PII leaks:

```python
def validate_anonymization(output_dir):
    """
    Scan anonymized data for potential PII leaks.
    """
    pii_patterns = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
    ]

    leaks = []

    for file_path in glob(f"{output_dir}/**/*.parquet", recursive=True):
        df = pd.read_parquet(file_path)

        for column in df.columns:
            for value in df[column].dropna().astype(str).unique()[:1000]:  # Sample
                for pattern in pii_patterns:
                    if re.search(pattern, str(value)):
                        leaks.append({
                            'file': file_path,
                            'column': column,
                            'pattern': pattern,
                            'sample': value[:20] + '...'
                        })

    return leaks
```

### 7. Generate Anonymization Report

Create `data/anonymized/{district_id}/anonymization-report.json`:

```json
{
  "district_id": "district-001",
  "anonymized_at": "2025-11-06T18:30:00Z",
  "duration_minutes": 28,
  "status": "SUCCESS",
  "rules_applied": 12,
  "stores_processed": {
    "ids": {
      "tables": 45,
      "pii_fields_found": 87,
      "records_anonymized": 250000
    },
    "hcp1": {
      "tables": 32,
      "pii_fields_found": 65,
      "records_anonymized": 180000
    },
    "hcp2": {
      "tables": 28,
      "pii_fields_found": 54,
      "records_anonymized": 120000
    },
    "adb": {
      "tables": 52,
      "pii_fields_found": 102,
      "records_anonymized": 200000
    },
    "sp": {
      "nodes": 100000,
      "pii_properties_found": 45,
      "properties_anonymized": 150000
    }
  },
  "totals": {
    "tables_processed": 157,
    "pii_fields_anonymized": 353,
    "records_processed": 750000,
    "unique_values_mapped": 42500
  },
  "consistency": {
    "first_names_mapped": 12500,
    "last_names_mapped": 15000,
    "emails_mapped": 8000,
    "phones_mapped": 7000
  },
  "validation": {
    "pii_leak_scan": "PASSED",
    "leaks_found": 0,
    "samples_scanned": 150000
  },
  "consistency_map_location": "data/anonymized/district-001/consistency-map.encrypted"
}
```

### 8. Encrypt and Save Consistency Map

```python
def save_consistency_map(consistency_map, output_file):
    """
    Encrypt and save consistency map for audit/reversal if needed.
    """
    import json
    from cryptography.fernet import Fernet

    # Generate key (or load from secure storage)
    key = Fernet.generate_key()
    cipher = Fernet(key)

    # Serialize map
    map_json = json.dumps(consistency_map)

    # Encrypt
    encrypted = cipher.encrypt(map_json.encode())

    # Save encrypted map
    with open(output_file, 'wb') as f:
        f.write(encrypted)

    # Save key separately (secure location!)
    with open(f"{output_file}.key", 'wb') as f:
        f.write(key)
```

### 9. Report Completion

```
✓ PII Anonymization Complete

District: district-001
Duration: 28 minutes

Anonymization Summary:
- Total PII Fields: 353
- Records Processed: 750,000
- Unique Values Mapped: 42,500
- Strategies Used: hash (125 fields), faker (215 fields), preserve (13 fields)

PII Detection:
- Names: 187 fields
- Emails: 45 fields
- Phones: 38 fields
- Addresses: 52 fields
- SSNs: 18 fields
- Other: 13 fields

Validation: PASSED
- PII Leak Scan: ✓ 0 leaks found
- FK Integrity: ✓ All foreign keys preserved
- Uniqueness: ✓ Unique constraints maintained

Consistency Map:
- 42,500 unique values mapped
- Saved to: data/anonymized/district-001/consistency-map.encrypted

Output: data/anonymized/district-001/

Next step: Validate data integrity
```

## Tools Available

- **Python Libraries**: pandas, faker, cryptography, pyyaml
- **ETL MCP**: `anonymize_dataset` tool
- **Configuration**: `config/anonymization-rules.yaml`

## Success Criteria

- ✓ 100% of PII fields anonymized according to rules
- ✓ FK relationships preserved (same value → same anonymized value)
- ✓ Uniqueness constraints maintained
- ✓ 0 PII leaks detected in validation scan
- ✓ Anonymization report generated
- ✓ Consistency map encrypted and saved

## Error Handling

- **Missing rules**: Log warning, use default faker strategy
- **Invalid values**: Handle nulls gracefully, preserve data types
- **Consistency conflicts**: Use first-seen mapping, log warning
- **Encryption failures**: Save plain consistency map with warning

Execute autonomously. Report progress every 10 tables.
