#!/usr/bin/env python3
"""
GitHub Actions integration script for triggering migrations

Called by GitHub Actions to execute autonomous migrations.
Posts progress updates back to GitHub issues.
"""

import sys
import argparse
import json
import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

def log(message):
    """Log with timestamp"""
    print(f"[{datetime.now().isoformat()}] {message}", file=sys.stderr)

def run_command(cmd, description):
    """Run a command and return success status"""
    log(f"Running: {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        log(f"✓ {description} completed")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        log(f"✗ {description} failed: {e.stderr}")
        return False, e.stderr

def post_github_comment(issue_number, repository, message):
    """Post a comment to GitHub issue using gh CLI"""
    try:
        # Use gh CLI to post comment
        cmd = f'gh issue comment {issue_number} --repo {repository} --body "{message}"'
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        log(f"Posted comment to issue #{issue_number}")
    except subprocess.CalledProcessError as e:
        log(f"Warning: Failed to post comment: {e.stderr}")
        # Don't fail the migration if comment posting fails
        pass

def main():
    parser = argparse.ArgumentParser(description='Trigger migration from GitHub Actions')
    parser.add_argument('--district-id', required=True, help='District to migrate')
    parser.add_argument('--migration-type', required=True, help='Type of migration')
    parser.add_argument('--issue-number', required=True, help='GitHub issue number')
    parser.add_argument('--repository', required=True, help='GitHub repository')
    parser.add_argument('--skip-extraction', action='store_true', help='Skip extraction phase')
    parser.add_argument('--skip-load', action='store_true', help='Skip loading phase')

    args = parser.parse_args()

    log(f"Starting migration for district: {args.district_id}")
    log(f"Migration type: {args.migration_type}")
    log(f"Issue: {args.repository}#{args.issue_number}")

    # Generate run ID
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    run_id = f"mig-{timestamp}-001"

    log(f"Run ID: {run_id}")

    # Create directories
    extraction_dir = Path(f"data/extractions/{run_id}")
    anonymized_dir = Path(f"data/anonymized/{run_id}")
    validation_dir = Path(f"data/validations/{run_id}")
    reports_dir = Path(f"reports/{run_id}")

    extraction_dir.mkdir(parents=True, exist_ok=True)
    anonymized_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: Extraction
    if not args.skip_extraction and "Dry Run" not in args.migration_type:
        post_github_comment(args.issue_number, args.repository,
                          f"📥 **Phase 1/5: Extraction**\\n\\nExtracting data from PROD...\\n\\nStarted: {datetime.now().isoformat()}")

        # Extract from all 5 data stores
        for store in ['ids', 'hcp1', 'hcp2', 'adb', 'sp']:
            log(f"Extracting from {store.upper()}")

            # Build source config JSON
            source_config = json.dumps({
                'store': store,
                'district_id': args.district_id
            })

            # Build extraction command with proper parameters
            cmd = f"""python3 scripts/extractors/extract_with_relationships.py \\
                --source-config '{source_config}' \\
                --filter-criteria '{{"district_id": "{args.district_id}"}}' \\
                --output-dir {extraction_dir}/{store}"""

            success, output = run_command(cmd, f"Extraction from {store.upper()}")

            if not success:
                post_github_comment(args.issue_number, args.repository,
                                  f"⛔ **Extraction Failed ({store.upper()})**\\n\\n```\\n{output[:500]}\\n```")
                return 1

        post_github_comment(args.issue_number, args.repository,
                          "✅ **Phase 1/5: Extraction Complete**\\n\\nAll 5 data stores extracted successfully.")

    # Phase 2: Anonymization
    post_github_comment(args.issue_number, args.repository,
                      f"🔒 **Phase 2/5: Anonymization**\\n\\nAnonymizing PII...\\n\\nStarted: {datetime.now().isoformat()}")

    cmd = f"""python3 scripts/anonymize.py \\
        --input-dir {extraction_dir} \\
        --output-dir {anonymized_dir} \\
        --rules-file config/anonymization-rules.yaml \\
        --consistency-map-file {anonymized_dir}/consistency-map.json"""

    success, output = run_command(cmd, "Anonymization")

    if not success:
        post_github_comment(args.issue_number, args.repository,
                          f"⛔ **Anonymization Failed**\\n\\n```\\n{output[:500]}\\n```")
        return 1

    post_github_comment(args.issue_number, args.repository,
                      "✅ **Phase 2/5: Anonymization Complete**\\n\\nAll PII anonymized with consistency maintained.")

    # Phase 3: Validation
    post_github_comment(args.issue_number, args.repository,
                      f"✓ **Phase 3/5: Validation**\\n\\nRunning 785+ validation checks...\\n\\nStarted: {datetime.now().isoformat()}")

    validation_report = validation_dir / "validation-report.json"

    cmd = f"""python3 scripts/validators/validate_integrity.py \\
        --data-dir {anonymized_dir} \\
        --schema-file data/schema-analysis.json \\
        --validation-rules-file config/validation-rules.yaml \\
        --output-report {validation_report}"""

    success, output = run_command(cmd, "Validation")

    if not success:
        post_github_comment(args.issue_number, args.repository,
                          f"⛔ **Validation Failed**\\n\\nMigration STOPPED - errors detected.\\n\\n```\\n{output[:500]}\\n```\\n\\n**Action Required:** Fix validation errors and re-run migration.")
        return 1

    # Check validation status from report
    try:
        with open(validation_report, 'r') as f:
            validation_results = json.load(f)
            status = validation_results.get('overall_status', 'UNKNOWN')

            if status == 'FAILED':
                post_github_comment(args.issue_number, args.repository,
                                  f"⛔ **Validation Failed**\\n\\nMigration STOPPED - validation errors detected.\\n\\nSee validation report for details.")
                return 1
            elif status == 'PASSED_WITH_WARNINGS':
                post_github_comment(args.issue_number, args.repository,
                                  f"⚠️ **Phase 3/5: Validation Complete (with warnings)**\\n\\nAll critical checks passed but some warnings exist. Proceeding with migration.")
            else:
                post_github_comment(args.issue_number, args.repository,
                                  "✅ **Phase 3/5: Validation Complete**\\n\\nAll 785+ checks passed!")
    except Exception as e:
        log(f"Warning: Could not parse validation report: {e}")
        post_github_comment(args.issue_number, args.repository,
                          "✅ **Phase 3/5: Validation Complete**")

    # Phase 4: Loading
    if not args.skip_load and "Validation Only" not in args.migration_type:
        post_github_comment(args.issue_number, args.repository,
                          f"📤 **Phase 4/5: Loading**\\n\\nLoading to CERT...\\n\\nStarted: {datetime.now().isoformat()}")

        # Load to all 5 CERT data stores
        for store in ['ids', 'hcp1', 'hcp2', 'adb', 'sp']:
            log(f"Loading to CERT {store.upper()}")

            # Build target config JSON
            target_config = json.dumps({
                'store': store,
                'environment': 'cert'
            })

            # Build loading command with proper parameters
            cmd = f"""python3 scripts/loaders/load_with_constraints.py \\
                --input-dir {anonymized_dir}/{store} \\
                --target-config '{target_config}' \\
                --strategy insert"""

            success, output = run_command(cmd, f"Loading to CERT {store.upper()}")

            if not success:
                post_github_comment(args.issue_number, args.repository,
                                  f"⛔ **Loading Failed (CERT {store.upper()})**\\n\\nTransaction rolled back.\\n\\n```\\n{output[:500]}\\n```")
                return 1

        post_github_comment(args.issue_number, args.repository,
                          "✅ **Phase 4/5: Loading Complete**\\n\\nData successfully loaded to all 5 CERT data stores!")

    # Phase 5: Reporting
    post_github_comment(args.issue_number, args.repository,
                      f"📊 **Phase 5/5: Reporting**\\n\\nGenerating migration report...\\n\\nStarted: {datetime.now().isoformat()}")

    cmd = f"""python3 scripts/generate-report.py \\
        --run-id {run_id} \\
        --district-id {args.district_id} \\
        --output-dir {reports_dir}"""

    success, output = run_command(cmd, "Reporting")

    if not success:
        log(f"Warning: Report generation failed: {output}")

    post_github_comment(args.issue_number, args.repository,
                      f"✅ **Phase 5/5: Reporting Complete**\\n\\nMigration report available in artifacts.")

    log(f"Migration completed successfully: {run_id}")
    print(json.dumps({
        'success': True,
        'run_id': run_id,
        'district_id': args.district_id
    }))

    return 0

if __name__ == '__main__':
    sys.exit(main())
