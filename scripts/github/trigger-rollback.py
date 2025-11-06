#!/usr/bin/env python3
"""
GitHub Actions integration script for triggering rollbacks

Called by GitHub Actions to execute autonomous rollbacks.
Posts progress updates back to GitHub issues.
"""

import sys
import argparse
import json
import subprocess
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
        # Don't fail the rollback if comment posting fails
        pass

def main():
    parser = argparse.ArgumentParser(description='Trigger rollback from GitHub Actions')
    parser.add_argument('--run-id', required=True, help='Migration run ID to rollback')
    parser.add_argument('--district-id', required=True, help='District to rollback')
    parser.add_argument('--reason', required=True, help='Reason for rollback')
    parser.add_argument('--issue-number', required=True, help='GitHub issue number')
    parser.add_argument('--repository', required=True, help='GitHub repository')

    args = parser.parse_args()

    log(f"Starting rollback for run: {args.run_id}")
    log(f"District: {args.district_id}")
    log(f"Reason: {args.reason}")

    # Create rollback logs directory
    rollback_logs_dir = Path(f"logs/rollbacks/{args.run_id}")
    rollback_logs_dir.mkdir(parents=True, exist_ok=True)

    # Post start comment
    post_github_comment(args.issue_number, args.repository,
                      f"⚠️ **Rollback Started**\\n\\nDeleting all data for district {args.district_id} from CERT...\\n\\nReason: {args.reason}\\n\\nStarted: {datetime.now().isoformat()}")

    # Execute rollback in REVERSE dependency order
    # Delete from child tables first, then parent tables
    stores_reverse = ['sp', 'adb', 'hcp2', 'hcp1', 'ids']

    for store in stores_reverse:
        log(f"Rolling back CERT {store.upper()}")

        post_github_comment(args.issue_number, args.repository,
                          f"🗑️ Deleting data from CERT {store.upper()}...")

        # Build target config JSON
        target_config = json.dumps({
            'store': store,
            'environment': 'cert'
        })

        # Build rollback command
        cmd = f"""python3 scripts/rollback.py \\
            --target-config '{target_config}' \\
            --district-id '{args.district_id}' \\
            --run-id '{args.run_id}' \\
            --log-file {rollback_logs_dir}/rollback-{store}.log"""

        success, output = run_command(cmd, f"Rollback from CERT {store.upper()}")

        if not success:
            post_github_comment(args.issue_number, args.repository,
                              f"⛔ **Rollback Failed (CERT {store.upper()})**\\n\\n```\\n{output[:500]}\\n```\\n\\n**MANUAL INTERVENTION REQUIRED**\\n\\nPartial rollback may have occurred. Contact DBA.")
            return 1

    # Rollback completed successfully
    post_github_comment(args.issue_number, args.repository,
                      f"✅ **Rollback Completed Successfully**\\n\\nAll data for district {args.district_id} has been removed from CERT.\\n\\nCompleted: {datetime.now().isoformat()}")

    log("Rollback completed successfully")
    print("Rollback completed successfully")

    return 0

if __name__ == '__main__':
    sys.exit(main())
