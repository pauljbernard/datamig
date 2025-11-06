# Generate Report Skill

You are a reporting specialist operating autonomously. Your mission: Generate comprehensive migration reports by aggregating artifacts from all migration phases.

## Input Parameters

- `run_id`: Migration run identifier
- `district_id`: District that was migrated
- `output_formats`: Report formats to generate (default: ["json", "markdown", "html"])

## Autonomous Execution Plan

### 1. Collect All Artifacts

Gather outputs from each migration phase:

```python
def collect_artifacts(district_id, run_id):
    """
    Collect all artifacts from migration run.
    """
    artifacts = {
        'extraction': read_json(f'data/staging/{district_id}/extraction-manifest.json'),
        'anonymization': read_json(f'data/anonymized/{district_id}/anonymization-report.json'),
        'validation': read_json(f'data/anonymized/{district_id}/validation-report.json'),
        'loading': read_json(f'data/loads/{district_id}/load-report.json'),
        'district_info': get_district_from_manifest(district_id),
        'run_metadata': {
            'run_id': run_id,
            'district_id': district_id,
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }
    }

    return artifacts
```

### 2. Calculate Summary Metrics

```python
def calculate_summary(artifacts):
    """
    Calculate overall migration metrics.
    """
    extraction = artifacts['extraction']
    anonymization = artifacts['anonymization']
    validation = artifacts['validation']
    loading = artifacts['loading']

    # Timing
    start_time = parse_iso(extraction['started_at'])
    end_time = parse_iso(loading['completed_at'])
    total_duration = (end_time - start_time).total_seconds() / 60  # minutes

    # Phase durations
    phase_durations = {
        'extraction': extraction['duration_minutes'],
        'anonymization': anonymization['duration_minutes'],
        'validation': validation['duration_minutes'],
        'loading': loading['duration_minutes']
    }

    # Records
    total_records_extracted = extraction['totals']['records']
    total_records_anonymized = anonymization['totals']['records_processed']
    total_records_loaded = loading['totals']['records_loaded']

    # Status
    overall_status = determine_overall_status(artifacts)

    return {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'total_duration_minutes': round(total_duration, 1),
        'total_duration_hours': round(total_duration / 60, 2),
        'phase_durations': phase_durations,
        'total_records_extracted': total_records_extracted,
        'total_records_anonymized': total_records_anonymized,
        'total_records_loaded': total_records_loaded,
        'data_loss_pct': ((total_records_extracted - total_records_loaded) / total_records_extracted * 100),
        'overall_status': overall_status
    }
```

### 3. Analyze Phase Performance

```python
def analyze_phases(artifacts):
    """
    Detailed analysis of each migration phase.
    """
    phases = {
        'extraction': {
            'status': artifacts['extraction']['status'],
            'duration_minutes': artifacts['extraction']['duration_minutes'],
            'records_extracted': artifacts['extraction']['totals']['records'],
            'tables_extracted': artifacts['extraction']['totals']['tables'],
            'size_mb': artifacts['extraction']['totals']['size_mb'],
            'throughput_records_per_minute': artifacts['extraction']['totals']['records'] / artifacts['extraction']['duration_minutes'],
            'stores': artifacts['extraction']['stores']
        },
        'anonymization': {
            'status': artifacts['anonymization']['status'],
            'duration_minutes': artifacts['anonymization']['duration_minutes'],
            'pii_fields_anonymized': artifacts['anonymization']['totals']['pii_fields_anonymized'],
            'records_processed': artifacts['anonymization']['totals']['records_processed'],
            'unique_values_mapped': artifacts['anonymization']['totals']['unique_values_mapped'],
            'throughput_records_per_minute': artifacts['anonymization']['totals']['records_processed'] / artifacts['anonymization']['duration_minutes'],
            'pii_leak_status': artifacts['anonymization']['validation']['pii_leak_scan']
        },
        'validation': {
            'status': artifacts['validation']['overall_status'],
            'duration_minutes': artifacts['validation']['duration_minutes'],
            'checks_run': artifacts['validation']['checks_run'],
            'errors': artifacts['validation']['summary']['total_errors'],
            'warnings': artifacts['validation']['summary']['total_warnings'],
            'validation_results': artifacts['validation']['validation_results']
        },
        'loading': {
            'status': artifacts['loading']['overall_status'],
            'duration_minutes': artifacts['loading']['duration_minutes'],
            'records_loaded': artifacts['loading']['totals']['records_loaded'],
            'tables_loaded': artifacts['loading']['totals']['tables_loaded'],
            'throughput_records_per_minute': artifacts['loading']['totals']['records_loaded'] / artifacts['loading']['duration_minutes'],
            'stores': artifacts['loading']['stores']
        }
    }

    return phases
```

### 4. Generate JSON Report

Create `data/reports/{run_id}.json`:

```json
{
  "migration_report": {
    "run_id": "mig-20251106-001",
    "district_id": "district-001",
    "district_name": "Large Urban District A",
    "generated_at": "2025-11-06T22:00:00Z",
    "report_version": "1.0",
    "summary": {
      "overall_status": "SUCCESS",
      "start_time": "2025-11-06T14:00:00Z",
      "end_time": "2025-11-06T21:45:00Z",
      "total_duration_hours": 7.75,
      "phase_durations_minutes": {
        "extraction": 135,
        "anonymization": 28,
        "validation": 12,
        "loading": 105
      },
      "records": {
        "extracted": 750000,
        "anonymized": 750000,
        "loaded": 750000,
        "data_loss_pct": 0.0
      }
    },
    "phases": { /* detailed phase analysis */ },
    "stores": {
      "ids": { /* IDS metrics */ },
      "hcp1": { /* HCP1 metrics */ },
      "hcp2": { /* HCP2 metrics */ },
      "adb": { /* ADB metrics */ },
      "sp": { /* SP metrics */ }
    },
    "validation_summary": {
      "overall_status": "PASSED_WITH_WARNINGS",
      "total_checks": 487,
      "errors": 0,
      "warnings": 3
    },
    "recommendations": [
      "Migration completed successfully",
      "Data is ready for QE testing on CERT",
      "3 business rule warnings found - review recommended",
      "Monitor CERT for any rostering issues during testing"
    ]
  }
}
```

### 5. Generate Markdown Report

Create `data/reports/{run_id}.md`:

```markdown
# Migration Report: district-001

**Migration Run**: mig-20251106-001
**District**: Large Urban District A (district-001)
**Status**: ✅ SUCCESS
**Date**: 2025-11-06
**Duration**: 7.75 hours

---

## Executive Summary

Successfully migrated **750,000 records** across **5 data stores** from PROD to CERT environment.

### Key Metrics

| Metric | Value |
|--------|-------|
| Total Records | 750,000 |
| Data Stores | 5 (IDS, HCP1, HCP2, ADB, SP) |
| Tables Migrated | 157 |
| PII Fields Anonymized | 353 |
| Validation Checks | 487 (PASSED) |
| Data Loss | 0.0% |
| Total Duration | 7.75 hours |

---

## Phase Breakdown

### 1. Extraction Phase ✅
**Duration**: 2.25 hours (135 minutes)
**Status**: SUCCESS

- **Records Extracted**: 750,000
- **Tables**: 157
- **Data Size**: 4.5 GB
- **Throughput**: 5,555 records/minute

#### By Data Store

| Store | Tables | Records | Size |
|-------|--------|---------|------|
| IDS | 45 | 250,000 | 1.2 GB |
| HCP1 | 32 | 180,000 | 850 MB |
| HCP2 | 28 | 120,000 | 600 MB |
| ADB | 52 | 200,000 | 1.5 GB |
| SP (Graph) | 100K nodes | 250K rels | 400 MB |

### 2. Anonymization Phase ✅
**Duration**: 28 minutes
**Status**: SUCCESS

- **PII Fields Detected**: 353
- **Records Anonymized**: 750,000
- **Unique Values Mapped**: 42,500
- **Throughput**: 26,785 records/minute
- **PII Leak Scan**: ✅ PASSED (0 leaks)

#### PII Categories

- Names: 187 fields
- Emails: 45 fields
- Phones: 38 fields
- Addresses: 52 fields
- SSNs: 18 fields

### 3. Validation Phase ✅
**Duration**: 12 minutes
**Status**: PASSED WITH WARNINGS

- **Checks Run**: 487
- **Errors**: 0 ❌
- **Warnings**: 3 ⚠️

#### Validation Results

| Check | Status | Details |
|-------|--------|---------|
| Schema Validation | ✅ PASSED | 785 checks |
| Referential Integrity | ✅ PASSED | 312 FK relationships |
| Uniqueness | ✅ PASSED | 157 checks |
| Business Rules | ⚠️ WARNINGS | 3 warnings |
| Completeness | ✅ PASSED | 157 tables |

#### Warnings

1. **student_age_range**: 3 students with age > 22 (likely adult learners)
2. [Additional warnings...]

### 4. Loading Phase ✅
**Duration**: 1.75 hours (105 minutes)
**Status**: SUCCESS

- **Records Loaded**: 750,000
- **Tables Loaded**: 157
- **Throughput**: 7,142 records/minute
- **Transactions**: All COMMITTED ✅

#### By Data Store

| Store | Status | Records | Duration |
|-------|--------|---------|----------|
| IDS | ✅ COMMITTED | 250,000 | 32 min |
| HCP1 | ✅ COMMITTED | 180,000 | 24 min |
| HCP2 | ✅ COMMITTED | 120,000 | 18 min |
| ADB | ✅ COMMITTED | 200,000 | 28 min |
| SP | ✅ COMMITTED | 350,000 | 3 min |

---

## Performance Analysis

### Throughput by Phase

| Phase | Records/Minute | Efficiency |
|-------|----------------|------------|
| Extraction | 5,555 | Baseline |
| Anonymization | 26,785 | 4.8x faster |
| Validation | 62,500 | 11.2x faster |
| Loading | 7,142 | 1.3x |

**Bottleneck**: Loading phase (slowest at 7,142 records/min)

### Timeline

```
14:00 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Extraction (135 min)
16:15 ━━━━━━ Anonymization (28 min)
16:43 ━━ Validation (12 min)
16:55 ━━━━━━━━━━━━━━━━━━━━ Loading (105 min)
18:40 ✅ Complete
```

---

## Recommendations

1. ✅ **Migration Successful** - Data is ready for QE testing on CERT
2. 📋 **Review Warnings** - 3 business rule warnings found (non-blocking)
3. 🧪 **Begin Testing** - Validate rostering flows with migrated data
4. 📊 **Monitor CERT** - Watch for any issues during initial testing
5. 🔄 **Schedule Refreshes** - Plan monthly data refresh cycle

---

## Next Steps

1. Notify QE team that CERT is ready with district-001 data
2. Begin rostering flow testing
3. Monitor for any data quality issues
4. Proceed with next district migration if successful

---

## Artifacts

- **Extraction Manifest**: `data/staging/district-001/extraction-manifest.json`
- **Anonymization Report**: `data/anonymized/district-001/anonymization-report.json`
- **Validation Report**: `data/anonymized/district-001/validation-report.json`
- **Load Report**: `data/loads/district-001/load-report.json`
- **This Report**: `data/reports/mig-20251106-001.md`

---

**Generated**: 2025-11-06 22:00:00 UTC
**Report Version**: 1.0
**Claude Code Migration Framework**: v1.0
```

### 6. Generate HTML Dashboard (Optional)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Migration Report: district-001</title>
    <style>
        /* Responsive dashboard styling */
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>Migration Report</h1>
        <div class="status success">✅ SUCCESS</div>

        <!-- Summary cards -->
        <div class="metrics">
            <div class="card">
                <h3>750,000</h3>
                <p>Records Migrated</p>
            </div>
            <!-- More cards -->
        </div>

        <!-- Phase timeline -->
        <div class="timeline">
            <!-- Visual timeline -->
        </div>

        <!-- Detailed tables -->
        <!-- Charts (if visualization library available) -->
    </div>
</body>
</html>
```

### 7. Send Notifications (Optional)

```python
def send_notifications(report, config):
    """
    Send migration completion notifications.
    """
    if config.get('email_enabled'):
        send_email(
            to=config['stakeholder_emails'],
            subject=f"Migration Complete: {report['district_name']}",
            body=generate_email_body(report)
        )

    if config.get('slack_enabled'):
        post_to_slack(
            webhook=config['slack_webhook'],
            message=generate_slack_message(report)
        )
```

### 8. Archive Artifacts

```python
def archive_artifacts(run_id, district_id):
    """
    Archive all migration artifacts for audit trail.
    """
    archive_dir = f"data/archive/{run_id}"

    # Copy all artifacts
    shutil.copytree(f"data/staging/{district_id}", f"{archive_dir}/staging")
    shutil.copytree(f"data/anonymized/{district_id}", f"{archive_dir}/anonymized")
    shutil.copytree(f"data/loads/{district_id}", f"{archive_dir}/loads")

    # Create archive tarball
    shutil.make_archive(f"{archive_dir}", 'gztar', archive_dir)

    log_info(f"Artifacts archived to: {archive_dir}.tar.gz")
```

### 9. Report Completion

```
✓ Migration Report Generated

Run ID: mig-20251106-001
District: district-001 (Large Urban District A)
Status: SUCCESS

Reports Generated:
- JSON: data/reports/mig-20251106-001.json
- Markdown: data/reports/mig-20251106-001.md
- HTML: data/reports/mig-20251106-001.html

Summary:
- Duration: 7.75 hours
- Records: 750,000 (100% success)
- Status: ✅ ALL PHASES SUCCESSFUL
- Warnings: 3 (non-blocking)

Recommendations:
1. Data ready for QE testing on CERT
2. Review 3 business rule warnings
3. Monitor CERT during initial testing

Artifacts archived to: data/archive/mig-20251106-001.tar.gz

Migration Complete! 🎉
```

## Tools Available

- **Python Libraries**: pandas, json, jinja2 (for templates)
- **Report Templates**: `templates/report-template.md`, `templates/report-template.html`

## Success Criteria

- ✓ All artifacts collected successfully
- ✓ Reports generated in requested formats
- ✓ Summary metrics calculated
- ✓ Recommendations provided
- ✓ Artifacts archived

## Error Handling

- **Missing artifacts**: Note in report, continue with available data
- **Calculation errors**: Use safe defaults, document assumptions

Always generate report even if migration had failures.
Report should clearly indicate status and provide troubleshooting guidance.

Execute autonomously.
