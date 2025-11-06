#!/usr/bin/env python3
"""
Anonymize PII in extracted dataset

Applies anonymization rules to extracted data while maintaining FK integrity.
Accepts JSON input via stdin, outputs JSON results via stdout.
"""

import sys
import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import yaml
from faker import Faker
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Faker
fake = Faker()

def log_error(message):
    """Log error message to stderr"""
    print(f"ERROR: {message}", file=sys.stderr)

def log_info(message):
    """Log info message to stderr"""
    print(f"INFO: {message}", file=sys.stderr)

class ConsistencyMap:
    """Maintains consistent mapping of original values to anonymized values"""

    def __init__(self):
        self.mappings = {}

    def get(self, rule_name: str, original_value: Any) -> Any:
        """Get anonymized value for original value, or None if not mapped yet"""
        if original_value is None or pd.isna(original_value):
            return None

        key = f"{rule_name}:{original_value}"
        return self.mappings.get(key)

    def set(self, rule_name: str, original_value: Any, anonymized_value: Any):
        """Store mapping from original to anonymized value"""
        if original_value is None or pd.isna(original_value):
            return

        key = f"{rule_name}:{original_value}"
        self.mappings[key] = anonymized_value

    def to_dict(self) -> Dict:
        """Export mappings as dictionary"""
        return self.mappings

    def from_dict(self, mappings: Dict):
        """Import mappings from dictionary"""
        self.mappings = mappings

def load_anonymization_rules(rules_file: str) -> Dict:
    """Load anonymization rules from YAML file"""
    with open(rules_file, 'r') as f:
        return yaml.safe_load(f)

def anonymize_faker(value: Any, faker_type: str, consistency_map: ConsistencyMap, rule_name: str, faker_args: Dict = None) -> Any:
    """Anonymize using Faker library"""
    if value is None or pd.isna(value):
        return None

    # Check consistency map first
    mapped = consistency_map.get(rule_name, value)
    if mapped is not None:
        return mapped

    # Generate fake value
    faker_args = faker_args or {}

    try:
        if faker_type == 'email':
            fake_value = fake.email()
        elif faker_type == 'first_name':
            fake_value = fake.first_name()
        elif faker_type == 'last_name':
            fake_value = fake.last_name()
        elif faker_type == 'name':
            fake_value = fake.name()
        elif faker_type == 'phone_number':
            fake_value = fake.phone_number()
        elif faker_type == 'street_address':
            fake_value = fake.street_address()
        elif faker_type == 'city':
            fake_value = fake.city()
        elif faker_type == 'zipcode':
            fake_value = fake.zipcode()
        elif faker_type == 'date_of_birth':
            min_age = faker_args.get('minimum_age', 5)
            max_age = faker_args.get('maximum_age', 85)
            fake_value = fake.date_of_birth(minimum_age=min_age, maximum_age=max_age)
        elif faker_type == 'user_name':
            fake_value = fake.user_name()
        elif faker_type == 'ipv4':
            fake_value = fake.ipv4()
        elif faker_type == 'url':
            fake_value = fake.url()
        else:
            log_error(f"Unknown faker type: {faker_type}")
            fake_value = f"FAKE_{faker_type.upper()}"

        # Store in consistency map
        consistency_map.set(rule_name, value, fake_value)

        return fake_value

    except Exception as e:
        log_error(f"Faker error for {faker_type}: {e}")
        return f"ANONYMIZED_{faker_type.upper()}"

def anonymize_hash(value: Any, salt: str, hash_algorithm: str = 'sha256') -> Any:
    """Anonymize using one-way hash"""
    if value is None or pd.isna(value):
        return None

    # Convert to string and add salt
    str_value = str(value) + salt

    # Hash
    if hash_algorithm == 'sha256':
        hashed = hashlib.sha256(str_value.encode()).hexdigest()
    elif hash_algorithm == 'sha512':
        hashed = hashlib.sha512(str_value.encode()).hexdigest()
    else:
        log_error(f"Unknown hash algorithm: {hash_algorithm}")
        hashed = hashlib.sha256(str_value.encode()).hexdigest()

    # Return first 16 characters (for readability)
    return hashed[:16]

def anonymize_tokenize(value: Any, consistency_map: ConsistencyMap, rule_name: str) -> Any:
    """Anonymize using token replacement"""
    if value is None or pd.isna(value):
        return None

    # Check consistency map first
    mapped = consistency_map.get(rule_name, value)
    if mapped is not None:
        return mapped

    # Generate token
    token_num = len([k for k in consistency_map.mappings.keys() if k.startswith(f"{rule_name}:")]) + 1
    token = f"TOKEN_{token_num:08d}"

    # Store in consistency map
    consistency_map.set(rule_name, value, token)

    return token

def anonymize_nullify(value: Any) -> Any:
    """Anonymize by setting to NULL"""
    return None

def anonymize_preserve(value: Any) -> Any:
    """Preserve original value (for FK columns, non-PII)"""
    return value

def apply_anonymization_rule(value: Any, rule: Dict, consistency_map: ConsistencyMap, salt: str) -> Any:
    """Apply a single anonymization rule to a value"""
    strategy = rule['strategy']

    if strategy == 'faker':
        return anonymize_faker(
            value,
            rule['faker_type'],
            consistency_map,
            rule['name'],
            rule.get('faker_args')
        )
    elif strategy == 'hash':
        return anonymize_hash(value, salt, rule.get('hash_algorithm', 'sha256'))
    elif strategy == 'tokenize':
        return anonymize_tokenize(value, consistency_map, rule['name'])
    elif strategy == 'nullify':
        return anonymize_nullify(value)
    elif strategy == 'preserve':
        return anonymize_preserve(value)
    else:
        log_error(f"Unknown anonymization strategy: {strategy}")
        return value

def match_field_to_rule(field_name: str, rules: List[Dict]) -> Dict:
    """Find first matching rule for a field"""
    for rule in rules:
        pattern = rule['field_pattern']
        if re.search(pattern, field_name, re.IGNORECASE):
            return rule
    return None

def check_pii_leaks(df: pd.DataFrame, rules: List[Dict]) -> List[str]:
    """Check for potential PII leaks in anonymized data"""
    leaked_fields = []

    for column in df.columns:
        # Check if column should have been anonymized
        rule = match_field_to_rule(column, rules)

        if rule and rule['strategy'] != 'preserve':
            # Check if values look like original data
            sample_values = df[column].dropna().head(10).tolist()

            for value in sample_values:
                str_value = str(value)

                # Simple heuristics for PII detection
                if rule['strategy'] == 'faker' and rule['faker_type'] == 'email':
                    # Check for real email patterns (not faker patterns)
                    if '@' in str_value and not str_value.endswith('.example.org'):
                        leaked_fields.append(column)
                        break

                elif rule['strategy'] == 'faker' and 'name' in rule['faker_type']:
                    # Check for suspiciously short or common names
                    if len(str_value) < 3:
                        leaked_fields.append(column)
                        break

    return list(set(leaked_fields))

def anonymize_parquet_file(input_file: Path, output_file: Path, rules: List[Dict], consistency_map: ConsistencyMap, salt: str) -> Dict:
    """Anonymize a single Parquet file"""
    try:
        # Read Parquet file
        df = pd.read_parquet(input_file)

        log_info(f"Anonymizing {input_file.name}: {len(df)} records, {len(df.columns)} columns")

        anonymized_fields = []
        fields_by_rule = {}

        # Apply rules to each column
        for column in df.columns:
            rule = match_field_to_rule(column, rules)

            if rule:
                log_info(f"  Column '{column}' matched rule '{rule['name']}' (strategy: {rule['strategy']})")

                # Apply anonymization
                df[column] = df[column].apply(
                    lambda x: apply_anonymization_rule(x, rule, consistency_map, salt)
                )

                anonymized_fields.append(column)

                # Track which fields were processed by each rule
                if rule['name'] not in fields_by_rule:
                    fields_by_rule[rule['name']] = []
                fields_by_rule[rule['name']].append(column)

        # Check for PII leaks
        leaked_fields = check_pii_leaks(df, rules)

        # Write anonymized data
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)

        return {
            'file': input_file.name,
            'records': len(df),
            'columns': len(df.columns),
            'anonymized_fields': anonymized_fields,
            'fields_by_rule': fields_by_rule,
            'pii_leaks': leaked_fields,
            'success': True
        }

    except Exception as e:
        log_error(f"Failed to anonymize {input_file}: {e}")
        return {
            'file': input_file.name,
            'error': str(e),
            'success': False
        }

def anonymize_dataset(input_dir: str, output_dir: str, rules_file: str, consistency_map_file: str) -> Dict:
    """
    Main anonymization function

    Args:
        input_dir: Directory containing extracted data
        output_dir: Directory to write anonymized data
        rules_file: Path to anonymization rules YAML
        consistency_map_file: Path to consistency map file

    Returns:
        Dict with anonymization results
    """
    start_time = datetime.now()

    results = {
        'run_timestamp': start_time.isoformat(),
        'input_dir': input_dir,
        'output_dir': output_dir,
        'files_processed': [],
        'total_records': 0,
        'total_fields_anonymized': 0,
        'pii_leaks_detected': [],
        'success': True,
        'errors': []
    }

    try:
        # Load anonymization rules
        log_info(f"Loading anonymization rules from {rules_file}")
        rules_config = load_anonymization_rules(rules_file)
        rules = rules_config.get('rules', [])

        log_info(f"Loaded {len(rules)} anonymization rules")

        # Get anonymization salt
        salt = os.getenv('ANONYMIZATION_SALT')
        if not salt:
            raise ValueError("ANONYMIZATION_SALT environment variable not set")

        # Initialize or load consistency map
        consistency_map = ConsistencyMap()

        if os.path.exists(consistency_map_file):
            log_info(f"Loading existing consistency map from {consistency_map_file}")
            with open(consistency_map_file, 'r') as f:
                consistency_map.from_dict(json.load(f))

        # Find all Parquet files in input directory
        input_path = Path(input_dir)
        parquet_files = list(input_path.glob("*.parquet"))

        log_info(f"Found {len(parquet_files)} Parquet files to anonymize")

        # Process each file
        for parquet_file in parquet_files:
            output_file = Path(output_dir) / parquet_file.name

            file_result = anonymize_parquet_file(
                parquet_file,
                output_file,
                rules,
                consistency_map,
                salt
            )

            results['files_processed'].append(file_result)

            if file_result['success']:
                results['total_records'] += file_result['records']
                results['total_fields_anonymized'] += len(file_result['anonymized_fields'])

                if file_result['pii_leaks']:
                    results['pii_leaks_detected'].extend(file_result['pii_leaks'])

            else:
                results['errors'].append(file_result.get('error', 'Unknown error'))
                results['success'] = False

        # Save consistency map
        log_info(f"Saving consistency map to {consistency_map_file}")
        Path(consistency_map_file).parent.mkdir(parents=True, exist_ok=True)

        with open(consistency_map_file, 'w') as f:
            json.dump(consistency_map.to_dict(), f, indent=2)

        # Check for PII leaks
        if results['pii_leaks_detected']:
            log_error(f"PII LEAK DETECTED in fields: {results['pii_leaks_detected']}")
            results['success'] = False
            results['pii_leak_check'] = 'FAILED'
        else:
            results['pii_leak_check'] = 'PASSED'

        results['duration_seconds'] = (datetime.now() - start_time).total_seconds()

        # Write anonymization report
        report_file = Path(output_dir) / "anonymization-report.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)

        log_info(f"Anonymization complete: {results['total_records']} records, {results['total_fields_anonymized']} fields anonymized")

        return results

    except Exception as e:
        log_error(f"Anonymization failed: {e}")
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
        output_dir = input_data['output_dir']
        rules_file = input_data.get('rules_file', 'config/anonymization-rules.yaml')
        consistency_map_file = input_data.get('consistency_map', os.path.join(output_dir, 'consistency-map.json'))

        # Perform anonymization
        result = anonymize_dataset(
            input_dir=input_dir,
            output_dir=output_dir,
            rules_file=rules_file,
            consistency_map_file=consistency_map_file
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
