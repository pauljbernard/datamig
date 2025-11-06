#!/usr/bin/env python3
"""
Generate comprehensive migration report

Aggregates metrics from all migration phases and generates detailed reports.
Can be called directly or via JSON stdin input.
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import argparse

def log_error(message):
    """Log error message to stderr"""
    print(f"ERROR: {message}", file=sys.stderr)

def log_info(message):
    """Log info message to stderr"""
    print(f"INFO: {message}", file=sys.stderr)

def load_json_file(file_path: Path) -> Dict:
    """Load JSON file"""
    if not file_path.exists():
        return {}

    with open(file_path, 'r') as f:
        return json.load(f)

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def generate_executive_summary(run_id: str, district_id: str, metrics: Dict) -> str:
    """Generate executive summary section"""
    status_emoji = "✅" if metrics.get('overall_success', False) else "⛔"

    summary = f"""# Migration Report: {district_id}

**Run ID:** {run_id}
**Status:** {status_emoji} {metrics.get('overall_status', 'UNKNOWN')}
**Duration:** {format_duration(metrics.get('total_duration', 0))}
**Timestamp:** {metrics.get('start_time', 'N/A')} - {metrics.get('end_time', 'N/A')}

## Executive Summary

"""

    if metrics.get('overall_success', False):
        summary += f"Successfully migrated district \"{metrics.get('district_name', district_id)}\" from PROD to CERT.\n\n"
    else:
        summary += f"Migration FAILED for district \"{metrics.get('district_name', district_id)}\".\n\n"

    summary += f"""- **Records Extracted:** {metrics.get('records_extracted', 0):,}
- **PII Fields Anonymized:** {metrics.get('fields_anonymized', 0)}
- **Validation Status:** {metrics.get('validation_status', 'UNKNOWN')} ({metrics.get('validation_warnings', 0)} warnings)
- **Records Loaded to CERT:** {metrics.get('records_loaded', 0):,}

"""

    if metrics.get('overall_success', False):
        summary += "CERT environment is ready for testing.\n\n"
    else:
        summary += f"**Error:** {metrics.get('error_message', 'See details below')}\n\n"

    return summary

def generate_phase_breakdown(metrics: Dict) -> str:
    """Generate phase breakdown section"""
    breakdown = "## Phase Breakdown\n\n"

    phases = [
        ('extraction', 'Extraction', metrics.get('extraction_duration', 0)),
        ('anonymization', 'Anonymization', metrics.get('anonymization_duration', 0)),
        ('validation', 'Validation', metrics.get('validation_duration', 0)),
        ('loading', 'Loading', metrics.get('loading_duration', 0)),
        ('reporting', 'Reporting', metrics.get('reporting_duration', 0))
    ]

    for phase_key, phase_name, duration in phases:
        phase_data = metrics.get(phase_key, {})

        breakdown += f"### Phase: {phase_name} ({format_duration(duration)})\n\n"

        if phase_key == 'extraction':
            breakdown += f"- Connected to {len(phase_data.get('stores', []))} data stores\n"
            breakdown += f"- Extracted {phase_data.get('tables_extracted', 0)} tables\n"
            breakdown += f"- Total records: {phase_data.get('total_records', 0):,}\n"
            if phase_data.get('circular_dependencies'):
                breakdown += f"- Handled {len(phase_data['circular_dependencies'])} circular dependencies\n"

        elif phase_key == 'anonymization':
            breakdown += f"- Applied {len(phase_data.get('rules_applied', []))} PII detection rules\n"
            breakdown += f"- Anonymized {phase_data.get('fields_anonymized', 0)} fields\n"
            breakdown += f"- Processed {phase_data.get('records_processed', 0):,} records\n"
            breakdown += f"- PII leak check: {phase_data.get('pii_leak_check', 'UNKNOWN')}\n"

        elif phase_key == 'validation':
            breakdown += f"- Ran {phase_data.get('total_checks', 0)} validation checks\n"
            breakdown += f"- Status: {phase_data.get('overall_status', 'UNKNOWN')}\n"
            breakdown += f"- Passed: {phase_data.get('total_passed', 0)}\n"
            breakdown += f"- Failed: {phase_data.get('total_failed', 0)}\n"
            breakdown += f"- Warnings: {phase_data.get('total_warnings', 0)}\n"

        elif phase_key == 'loading':
            breakdown += f"- Loaded to {len(phase_data.get('stores', []))} CERT data stores\n"
            breakdown += f"- Tables loaded: {len(phase_data.get('tables_loaded', []))}\n"
            breakdown += f"- Total rows: {phase_data.get('total_rows_loaded', 0):,}\n"
            breakdown += f"- Strategy: {phase_data.get('strategy', 'N/A')}\n"

        breakdown += "\n"

    return breakdown

def generate_warnings_section(metrics: Dict) -> str:
    """Generate warnings section"""
    warnings = metrics.get('validation', {}).get('warnings', [])

    if not warnings:
        return ""

    section = "## Warnings\n\n"

    for i, warning in enumerate(warnings[:10], 1):  # Limit to first 10
        section += f"{i}. **{warning.get('rule', warning.get('check', 'Unknown'))}**: {warning.get('message', 'No message')}\n"
        section += f"   - Table: {warning.get('table', 'N/A')}\n"
        section += f"   - Severity: {warning.get('severity', 'WARNING')}\n"
        section += "\n"

    if len(warnings) > 10:
        section += f"... and {len(warnings) - 10} more warnings (see validation report for details)\n\n"

    return section

def generate_errors_section(metrics: Dict) -> str:
    """Generate errors section"""
    errors = metrics.get('validation', {}).get('errors', [])

    if not errors:
        return ""

    section = "## Errors\n\n"

    for i, error in enumerate(errors, 1):
        section += f"{i}. **{error.get('rule', error.get('check', 'Unknown'))}**: {error.get('message', 'No message')}\n"
        section += f"   - Table: {error.get('table', 'N/A')}\n"
        section += f"   - Severity: {error.get('severity', 'ERROR')}\n"
        section += "\n"

    return section

def generate_recommendations(metrics: Dict) -> str:
    """Generate recommendations section"""
    recommendations = "## Recommendations\n\n"

    if metrics.get('overall_success', False):
        recommendations += "1. ✅ CERT is ready for QA testing\n"

        warnings_count = metrics.get('validation_warnings', 0)
        if warnings_count > 0:
            recommendations += f"2. Review the {warnings_count} warnings above (non-blocking)\n"

        recommendations += "3. Run `/validate-migration mig-{run_id}` for post-load validation\n"
        recommendations += "4. Begin QA test plan execution\n"

    else:
        recommendations += "1. ⛔ Migration FAILED - do NOT proceed to testing\n"
        recommendations += "2. Review errors above and fix root causes\n"
        recommendations += "3. Run `/rollback mig-{run_id}` to clean up partial data\n"
        recommendations += "4. Re-run migration after fixes\n"

    recommendations += "\n"

    return recommendations

def generate_artifacts_section(run_id: str, district_id: str) -> str:
    """Generate artifacts section"""
    return f"""## Artifacts

- **Extracted Data:** `data/staging/{district_id}/`
- **Anonymized Data:** `data/anonymized/{district_id}/`
- **Load Manifest:** `data/loads/{district_id}/load-manifest.json`
- **Validation Report:** `data/anonymized/{district_id}/validation-report.json`
- **Logs:** `logs/{run_id}.log`

"""

def collect_metrics(run_id: str, district_id: str) -> Dict:
    """Collect metrics from all migration phases"""
    metrics = {
        'run_id': run_id,
        'district_id': district_id,
        'overall_success': True,
        'overall_status': 'SUCCESS',
        'total_duration': 0,
        'start_time': None,
        'end_time': None
    }

    # Load extraction manifest
    extraction_manifest_file = Path('data') / 'staging' / district_id / 'extraction-manifest.json'
    if extraction_manifest_file.exists():
        extraction_data = load_json_file(extraction_manifest_file)
        metrics['extraction'] = extraction_data
        metrics['records_extracted'] = extraction_data.get('total_records', 0)
        metrics['extraction_duration'] = extraction_data.get('duration_seconds', 0)
        metrics['total_duration'] += metrics['extraction_duration']

        if metrics['start_time'] is None:
            metrics['start_time'] = extraction_data.get('run_timestamp', '')

    # Load anonymization report
    anon_report_file = Path('data') / 'anonymized' / district_id / 'anonymization-report.json'
    if anon_report_file.exists():
        anon_data = load_json_file(anon_report_file)
        metrics['anonymization'] = anon_data
        metrics['fields_anonymized'] = anon_data.get('total_fields_anonymized', 0)
        metrics['anonymization_duration'] = anon_data.get('duration_seconds', 0)
        metrics['total_duration'] += metrics['anonymization_duration']

        if not anon_data.get('success', True):
            metrics['overall_success'] = False
            metrics['overall_status'] = 'FAILED'
            metrics['error_message'] = anon_data.get('error', 'Anonymization failed')

    # Load validation report
    validation_report_file = Path('data') / 'anonymized' / district_id / 'validation-report.json'
    if validation_report_file.exists():
        validation_data = load_json_file(validation_report_file)
        metrics['validation'] = validation_data
        metrics['validation_status'] = validation_data.get('overall_status', 'UNKNOWN')
        metrics['validation_warnings'] = validation_data.get('total_warnings', 0)
        metrics['validation_duration'] = validation_data.get('duration_seconds', 0)
        metrics['total_duration'] += metrics['validation_duration']

        if validation_data.get('overall_status') == 'FAILED':
            metrics['overall_success'] = False
            metrics['overall_status'] = 'FAILED'
            metrics['error_message'] = f"Validation failed: {validation_data.get('total_failed', 0)} checks failed"

    # Load load manifest
    load_manifest_file = Path('data') / 'loads' / district_id / 'load-manifest.json'
    if load_manifest_file.exists():
        load_data = load_json_file(load_manifest_file)
        metrics['loading'] = load_data
        metrics['records_loaded'] = load_data.get('total_rows_loaded', 0)
        metrics['loading_duration'] = load_data.get('duration_seconds', 0)
        metrics['total_duration'] += metrics['loading_duration']

        if not load_data.get('success', True):
            metrics['overall_success'] = False
            metrics['overall_status'] = 'FAILED'
            metrics['error_message'] = load_data.get('error', 'Loading failed')

        metrics['end_time'] = load_data.get('run_timestamp', '')

    return metrics

def generate_report(run_id: str, district_id: str, output_dir: str = 'data/reports') -> Dict:
    """
    Main report generation function

    Args:
        run_id: Migration run ID
        district_id: District ID
        output_dir: Directory to write reports

    Returns:
        Dict with report generation results
    """
    start_time = datetime.now()

    log_info(f"Generating report for run {run_id}, district {district_id}")

    # Collect metrics from all phases
    metrics = collect_metrics(run_id, district_id)

    # Generate Markdown report
    markdown_report = ""
    markdown_report += generate_executive_summary(run_id, district_id, metrics)
    markdown_report += generate_phase_breakdown(metrics)
    markdown_report += generate_warnings_section(metrics)
    markdown_report += generate_errors_section(metrics)
    markdown_report += generate_recommendations(metrics)
    markdown_report += generate_artifacts_section(run_id, district_id)

    # Write reports
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Markdown report
    markdown_file = output_path / f"{run_id}.md"
    with open(markdown_file, 'w') as f:
        f.write(markdown_report)

    log_info(f"Generated Markdown report: {markdown_file}")

    # JSON report
    json_file = output_path / f"{run_id}.json"
    with open(json_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    log_info(f"Generated JSON report: {json_file}")

    duration = (datetime.now() - start_time).total_seconds()

    return {
        'success': True,
        'run_id': run_id,
        'district_id': district_id,
        'markdown_report': str(markdown_file),
        'json_report': str(json_file),
        'duration_seconds': duration,
        'overall_success': metrics['overall_success'],
        'overall_status': metrics['overall_status']
    }

def main():
    """Main entry point"""
    # Check if input is from stdin (JSON mode) or command-line (direct mode)
    if not sys.stdin.isatty():
        # JSON mode - read from stdin
        try:
            input_data = json.load(sys.stdin)
            run_id = input_data['run_id']
            district_id = input_data['district_id']
            output_dir = input_data.get('output_dir', 'data/reports')

            result = generate_report(run_id, district_id, output_dir)

            # Output result as JSON to stdout
            print(json.dumps(result, indent=2))

            sys.exit(0 if result['success'] else 1)

        except Exception as e:
            log_error(f"Fatal error: {e}")
            error_result = {
                'success': False,
                'error': str(e)
            }
            print(json.dumps(error_result, indent=2))
            sys.exit(1)

    else:
        # Command-line mode
        parser = argparse.ArgumentParser(description='Generate migration report')
        parser.add_argument('run_id', help='Migration run ID')
        parser.add_argument('district_id', help='District ID')
        parser.add_argument('--output-dir', default='data/reports', help='Output directory')

        args = parser.parse_args()

        try:
            result = generate_report(args.run_id, args.district_id, args.output_dir)

            print(f"\n✅ Report generated successfully!")
            print(f"   - Markdown: {result['markdown_report']}")
            print(f"   - JSON: {result['json_report']}")
            print(f"   - Status: {result['overall_status']}")

            sys.exit(0)

        except Exception as e:
            log_error(f"Fatal error: {e}")
            print(f"\n⛔ Report generation failed: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()
