# Data Migration Framework - User Guide

**Version:** 1.0
**Last Updated:** 2025-11-06

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Prerequisites](#prerequisites)
4. [Initial Setup](#initial-setup)
5. [Understanding the Workflow](#understanding-the-workflow)
6. [Step-by-Step Usage](#step-by-step-usage)
7. [Command Reference](#command-reference)
8. [Monitoring Progress](#monitoring-progress)
9. [Understanding Outputs](#understanding-outputs)
10. [Common Workflows](#common-workflows)
11. [Best Practices](#best-practices)
12. [FAQ](#faq)

---

## Overview

This autonomous data migration framework extends Claude Code to migrate production data from 5 data stores to CERT environment with **minimal human intervention**.

### What This Framework Does

- **Extracts** district-specific data from PROD maintaining all FK relationships
- **Anonymizes** PII while preserving referential integrity
- **Validates** data quality with 785+ integrity checks
- **Loads** safely to CERT with transaction rollback capability
- **Reports** comprehensive migration results

### The Autonomous Model

**Traditional Approach:**
- Human executes 100+ manual steps
- Days or weeks of work
- Error-prone and tedious

**This Framework:**
- Human types ONE command: `/migrate district-001`
- Claude Code executes autonomously for 4-8 hours
- Zero human intervention required

---

## Quick Start

For experienced users who want to dive right in:

```bash
# 1. Clone and configure
git clone https://github.com/pauljbernard/datamig.git
cd datamig
cp .env.example .env
# Edit .env with your credentials

# 2. Enable MCP servers in .claude/mcp/servers.json
# Change "disabled": true to "disabled": false for needed servers

# 3. Open in Claude Code
# claude-code

# 4. Run initial analysis
/analyze-datastores    # ~30 minutes autonomous
/select-districts      # ~15 minutes autonomous

# 5. Execute your first migration
/migrate district-001  # 4-8 hours autonomous
```

That's it! Claude Code handles everything autonomously.

---

## Prerequisites

### Required Access

1. **Database Credentials**
   - PROD databases: Read-only access (IDS, HCP1, HCP2, ADB, Neo4j)
   - CERT databases: Read/write access (IDS, HCP1, HCP2, ADB, Neo4j)

2. **Software Requirements**
   - Claude Code CLI installed
   - Node.js 18+ (for MCP servers)
   - Python 3.9+ (for data processing scripts)
   - PostgreSQL client tools
   - Git

3. **Disk Space**
   - Minimum 50GB free (for extracted data)
   - Recommended 100GB+ (for large districts)

4. **Network Access**
   - Connectivity to PROD databases (read-only)
   - Connectivity to CERT databases (read/write)

### Recommended Knowledge

- Basic understanding of relational databases
- Familiarity with Claude Code interface
- Understanding of data migration concepts (helpful but not required)

---

## Initial Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/pauljbernard/datamig.git
cd datamig
```

### Step 2: Install Dependencies

#### Node.js Dependencies (for MCP servers)

```bash
# Install PostgreSQL MCP server
npm install -g @modelcontextprotocol/server-postgres

# Install custom MCP servers
cd mcp-servers/neo4j
npm install
cd ../etl
npm install
cd ../..
```

#### Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install faker pandas pyarrow psycopg2-binary neo4j pyyaml
```

### Step 3: Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or your preferred editor
```

**Critical Environment Variables:**

```bash
# PROD Database Credentials (READ-ONLY)
PROD_IDS_PASSWORD=your-prod-ids-readonly-password
PROD_HCP1_PASSWORD=your-prod-hcp1-readonly-password
PROD_HCP2_PASSWORD=your-prod-hcp2-readonly-password
PROD_ADB_PASSWORD=your-prod-adb-readonly-password
NEO4J_PROD_PASSWORD=your-neo4j-prod-readonly-password

# CERT Database Credentials (READ/WRITE)
CERT_IDS_PASSWORD=your-cert-ids-admin-password
CERT_HCP1_PASSWORD=your-cert-hcp1-admin-password
CERT_HCP2_PASSWORD=your-cert-hcp2-admin-password
CERT_ADB_PASSWORD=your-cert-adb-admin-password
NEO4J_CERT_PASSWORD=your-neo4j-cert-admin-password

# Anonymization (CRITICAL - keep secret!)
ANONYMIZATION_SALT=$(openssl rand -base64 32)
```

### Step 4: Enable MCP Servers

Edit `.claude/mcp/servers.json` and change `"disabled": true` to `"disabled": false` for the servers you need:

```json
{
  "mcpServers": {
    "postgres-ids-prod": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://readonly_user@prod-ids-rds.amazonaws.com:5432/ids_db"],
      "env": {
        "PGPASSWORD": "${PROD_IDS_PASSWORD}"
      },
      "disabled": false  // ← Change this
    },
    // ... repeat for other servers
  }
}
```

**Recommended approach:** Enable servers one at a time and test connectivity.

### Step 5: Verify Setup

```bash
# Start Claude Code
claude-code

# In Claude Code, verify MCP servers loaded
# You should see connection confirmations for enabled servers
```

---

## Understanding the Workflow

### The Complete Migration Pipeline

The framework follows a 5-phase autonomous pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                     AUTONOMOUS MIGRATION PIPELINE                │
└─────────────────────────────────────────────────────────────────┘

Phase 1: EXTRACTION (~1-2 hours)
├─ Connect to all 5 PROD data stores
├─ Identify tables with district_id or FK chains to district
├─ Extract data in topologically-sorted order
├─ Handle circular dependencies
└─ Output: data/staging/{district_id}/*.parquet

Phase 2: ANONYMIZATION (~30-60 minutes)
├─ Load extracted data
├─ Apply anonymization rules (15 PII patterns)
├─ Maintain consistency mapping (same PII → same fake value)
├─ Preserve FK relationships
└─ Output: data/anonymized/{district_id}/*.parquet

Phase 3: VALIDATION (~30-60 minutes)
├─ Schema validation (data types, nullability)
├─ Referential integrity (FK validation)
├─ Business rules (45+ rules)
├─ Data completeness checks
├─ Cross-store consistency
└─ Output: validation-report.json (PASS/FAIL decision)

Phase 4: LOADING (~1-2 hours)
├─ Connect to all 5 CERT data stores
├─ Load in topologically-sorted order
├─ Use transactions for rollback safety
├─ Handle conflicts (insert/upsert/merge strategies)
└─ Output: data/loads/{district_id}/load-manifest.json

Phase 5: REPORTING (~5 minutes)
├─ Compile metrics from all phases
├─ Generate executive summary
├─ Create detailed technical report
└─ Output: data/reports/{run_id}.md
```

### Decision Points

The framework makes autonomous decisions at key points:

1. **After Validation:**
   - `PASSED` → Continue to loading
   - `PASSED_WITH_WARNINGS` → Log warnings, continue to loading
   - `FAILED` → **STOP**, report errors to human, preserve artifacts

2. **After Loading Failure:**
   - Automatic rollback via PostgreSQL transactions
   - Preserve error logs for troubleshooting
   - Report failure to human with recommendations

3. **Circular Dependency Detection:**
   - Identify cycles in FK graph
   - Suggest break points
   - Document in extraction manifest

---

## Step-by-Step Usage

### Phase 0: Initial Discovery

Before migrating any districts, run the discovery commands:

#### Command 1: Analyze Data Stores

```bash
/analyze-datastores
```

**What it does:**
- Connects to all 5 PROD data stores
- Extracts complete schemas (tables, columns, data types, constraints)
- Builds FK dependency graph
- Performs topological sort to determine extraction order
- Detects circular dependencies

**Duration:** ~30 minutes (autonomous)

**Outputs:**
- `data/analysis/schema-analysis.json` - Complete schema metadata
- `data/analysis/dependency-graph.dot` - Visual FK graph
- `data/analysis/extraction-order.json` - Topologically sorted table list
- `data/analysis/README.md` - Human-readable summary

**What to do:** Review the outputs to understand your data landscape.

#### Command 2: Select Districts

```bash
/select-districts
```

**What it does:**
- Analyzes all districts across data stores
- Scores each district on 4 dimensions:
  - Size (40% weight): Total records
  - Activity (30% weight): Recent updates
  - Completeness (20% weight): Data quality
  - Business Priority (10% weight): Importance flag
- Ranks districts by score
- Recommends 3 pilot districts (1 large, 1 medium, 1 small)

**Duration:** ~15 minutes (autonomous)

**Outputs:**
- `data/manifests/district-manifest.json` - Top 15 districts with scores
- Console output with pilot recommendations

**What to do:** Review the recommendations and select your first migration target.

### Phase 1: Execute Your First Migration

#### Command: Migrate a District

```bash
/migrate district-001
```

**What it does:** Executes the complete 5-phase pipeline autonomously.

**Duration:** 4-8 hours depending on district size

**Parameters:**
- `district-001` - Required: The district ID to migrate

**Optional flags (for advanced users):**
```bash
/migrate district-001 --skip-extraction  # Use existing extracted data
/migrate district-001 --skip-load        # Validate only, don't load
/migrate district-001 --dry-run          # Test without CERT modifications
```

**Progress Tracking:**

Claude Code will show a todo checklist with real-time updates:

```
✓ Phase 1: Extraction - Completed (1.2 hours)
✓ Phase 2: Anonymization - Completed (45 minutes)
✓ Phase 3: Validation - Completed (30 minutes)
⏳ Phase 4: Loading - In Progress (35% complete)
⏸ Phase 5: Reporting - Pending
```

**Human Involvement:** ZERO (except approval gates if configured)

You can check in anytime to see progress, but no action is required.

### Phase 2: Validate the Migration

After migration completes, validate the CERT data:

```bash
/validate-migration mig-20260115-001
```

**What it does:**
- Re-runs all validation checks on CERT databases
- Compares CERT data to anonymized data
- Verifies FK integrity in CERT
- Checks for data loss or corruption

**Duration:** ~30 minutes (autonomous)

**Outputs:**
- `data/reports/{run_id}-validation.json` - Validation results

### Phase 3: Rollback (if needed)

If a migration fails or produces bad data:

```bash
/rollback mig-20260115-001
```

**What it does:**
- Confirms with user (destructive operation)
- Deletes all data for the district from CERT
- Processes in REVERSE dependency order (children before parents)
- Preserves logs and artifacts

**IMPORTANT:** This is destructive! You will be prompted to confirm.

---

## Command Reference

### `/analyze-datastores`

**Purpose:** Discover and analyze all PROD data store schemas

**Usage:**
```bash
/analyze-datastores
```

**Duration:** ~30 minutes (autonomous)

**Prerequisites:**
- PROD MCP servers enabled and configured
- Read access to all PROD databases

**Outputs:**
- `data/analysis/schema-analysis.json`
- `data/analysis/dependency-graph.dot`
- `data/analysis/extraction-order.json`
- `data/analysis/README.md`

**When to use:**
- First time setup
- When database schemas change
- Quarterly to keep analysis fresh

---

### `/select-districts`

**Purpose:** Identify and prioritize districts for migration

**Usage:**
```bash
/select-districts
```

**Duration:** ~15 minutes (autonomous)

**Prerequisites:**
- PROD MCP servers enabled
- `/analyze-datastores` completed

**Outputs:**
- `data/manifests/district-manifest.json`
- Console recommendations

**When to use:**
- After schema analysis
- When planning migration batches
- To find good pilot candidates

---

### `/migrate <district-id>`

**Purpose:** Execute complete autonomous migration for a district

**Usage:**
```bash
/migrate district-001                    # Standard migration
/migrate district-001 --skip-extraction  # Use existing data
/migrate district-001 --skip-load        # Validate only
/migrate district-001 --dry-run          # Test run
```

**Duration:** 4-8 hours (autonomous)

**Prerequisites:**
- All MCP servers enabled (PROD + CERT)
- Anonymization rules configured
- Validation rules configured
- `/analyze-datastores` completed

**Outputs:**
- `data/staging/{district_id}/` - Extracted data
- `data/anonymized/{district_id}/` - Anonymized data
- `data/loads/{district_id}/` - Load manifest
- `data/reports/{run_id}.md` - Final report

**When to use:**
- After planning your migration schedule
- For production migrations
- For testing migrations (with `--dry-run`)

**Error Handling:**
- Validation FAILED → Stops before loading
- Load failure → Automatic rollback via transactions
- All errors → Detailed logs preserved

---

### `/validate-migration <run-id>`

**Purpose:** Validate migration results in CERT

**Usage:**
```bash
/validate-migration mig-20260115-001
```

**Duration:** ~30 minutes (autonomous)

**Prerequisites:**
- CERT MCP servers enabled
- Migration completed
- Run ID from migration report

**Outputs:**
- `data/reports/{run_id}-validation.json`

**When to use:**
- After every migration (recommended)
- Before QA testing begins
- To verify data quality

---

### `/rollback <run-id>`

**Purpose:** Rollback a failed or problematic migration

**Usage:**
```bash
/rollback mig-20260115-001
```

**Duration:** ~1 hour (autonomous)

**Prerequisites:**
- CERT MCP servers enabled
- Run ID from migration report
- User confirmation (you'll be prompted)

**What it does:**
- Deletes all district data from CERT
- Processes in REVERSE dependency order
- Preserves all logs and artifacts

**IMPORTANT:** This is destructive and irreversible!

**When to use:**
- Migration validation failed
- Incorrect data loaded
- Need to re-migrate with fixes

---

## Monitoring Progress

### Real-Time Progress Tracking

Claude Code uses the TodoWrite system to show real-time progress:

```
Todo List:
✓ Initialize migration (Run ID: mig-20260115-001)
✓ Phase 1: Extraction - Completed
✓ Phase 2: Anonymization - Completed
⏳ Phase 3: Validation - In Progress
   └─ Running business rules validation (45 of 785 checks complete)
⏸ Phase 4: Loading - Pending
⏸ Phase 5: Reporting - Pending
```

### Progress Updates

Claude Code reports progress every 15 minutes:

```
[2025-01-15 14:30:00] Phase 3: Validation - 35% complete
- Schema validation: PASSED (312 checks)
- Referential integrity: PASSED (187 FKs)
- Business rules: IN PROGRESS (12 of 45 complete)
```

### Checking In

You can check progress anytime:
- Review the todo list in Claude Code
- Check output logs in `logs/mig-{run_id}.log`
- View intermediate artifacts in `data/` directories

### What to Watch For

**Normal progress indicators:**
- Todo items moving from "Pending" → "In Progress" → "Completed"
- Regular progress updates every 15 minutes
- Checkpoint messages after each phase

**Warning signs:**
- No progress updates for >30 minutes
- Error messages in logs
- Validation warnings (may be OK, but review them)

**Critical issues:**
- "Validation FAILED" message → Migration stops, review errors
- "Load FAILED" message → Rollback triggered, review logs
- Connection errors → Check network/credentials

---

## Understanding Outputs

### Directory Structure

After migrations, your directory structure looks like:

```
datamig/
├── data/
│   ├── staging/              # Extracted PROD data (not anonymized!)
│   │   └── district-001/
│   │       ├── ids_students.parquet
│   │       ├── ids_schools.parquet
│   │       └── extraction-manifest.json
│   │
│   ├── anonymized/           # Anonymized data (safe for CERT)
│   │   └── district-001/
│   │       ├── ids_students.parquet
│   │       ├── ids_schools.parquet
│   │       ├── anonymization-report.json
│   │       └── consistency-map.json.encrypted
│   │
│   ├── loads/                # Load manifests
│   │   └── district-001/
│   │       └── load-manifest.json
│   │
│   ├── reports/              # Final reports
│   │   ├── mig-20260115-001.md
│   │   └── mig-20260115-001.json
│   │
│   ├── analysis/             # Schema analysis
│   │   ├── schema-analysis.json
│   │   ├── dependency-graph.dot
│   │   └── extraction-order.json
│   │
│   └── manifests/            # District manifests
│       └── district-manifest.json
│
└── logs/                     # Execution logs
    └── mig-20260115-001.log
```

### Key Output Files

#### Extraction Manifest

**Location:** `data/staging/{district_id}/extraction-manifest.json`

**Contents:**
```json
{
  "run_id": "mig-20260115-001",
  "district_id": "district-001",
  "extraction_timestamp": "2025-01-15T10:00:00Z",
  "tables_extracted": 47,
  "total_records": 543210,
  "extraction_order": ["schools", "students", "enrollments", ...],
  "circular_dependencies": [
    {
      "tables": ["courses", "prerequisites"],
      "break_point": "prerequisites",
      "reason": "Fewest downstream dependencies"
    }
  ],
  "store_breakdown": {
    "ids": {"tables": 15, "records": 123456},
    "hcp1": {"tables": 12, "records": 234567},
    "hcp2": {"tables": 10, "records": 123456},
    "adb": {"tables": 8, "records": 45678},
    "sp": {"nodes": 15000, "relationships": 23400}
  }
}
```

#### Anonymization Report

**Location:** `data/anonymized/{district_id}/anonymization-report.json`

**Contents:**
```json
{
  "run_id": "mig-20260115-001",
  "district_id": "district-001",
  "anonymization_timestamp": "2025-01-15T11:30:00Z",
  "rules_applied": [
    {
      "rule": "email_addresses",
      "fields_matched": 12,
      "records_anonymized": 15234,
      "strategy": "faker"
    },
    {
      "rule": "ssn",
      "fields_matched": 2,
      "records_anonymized": 3456,
      "strategy": "hash"
    }
  ],
  "pii_fields_anonymized": 67,
  "total_records_processed": 543210,
  "consistency_map_entries": 45678,
  "pii_leak_check": "PASSED (0 leaks detected)"
}
```

#### Validation Report

**Location:** `data/reports/{run_id}-validation.json` (or embedded in final report)

**Contents:**
```json
{
  "run_id": "mig-20260115-001",
  "district_id": "district-001",
  "validation_timestamp": "2025-01-15T13:00:00Z",
  "overall_status": "PASSED_WITH_WARNINGS",
  "checks": {
    "schema_validation": {
      "status": "PASSED",
      "checks_run": 312,
      "checks_passed": 312,
      "checks_failed": 0
    },
    "referential_integrity": {
      "status": "PASSED",
      "fk_checks": 187,
      "fk_passed": 187,
      "fk_failed": 0
    },
    "business_rules": {
      "status": "PASSED_WITH_WARNINGS",
      "rules_checked": 45,
      "passed": 42,
      "warnings": 3,
      "errors": 0
    }
  },
  "warnings": [
    {
      "rule": "student_age_range",
      "severity": "WARNING",
      "count": 12,
      "message": "12 students have age outside 5-22 range (may be adult learners)"
    }
  ],
  "errors": []
}
```

#### Final Migration Report

**Location:** `data/reports/{run_id}.md`

**Contents:** (Markdown format, ~50KB)

```markdown
# Migration Report: district-001

**Run ID:** mig-20260115-001
**Status:** ✅ SUCCESS
**Duration:** 5.2 hours
**Timestamp:** 2025-01-15 10:00:00 - 15:12:34

## Executive Summary

Successfully migrated district "Springfield Public Schools" from PROD to CERT.

- **Records Extracted:** 543,210
- **PII Fields Anonymized:** 67
- **Validation Status:** PASSED (3 warnings)
- **Records Loaded to CERT:** 543,210

CERT environment is ready for testing.

## Phase Breakdown

### Phase 1: Extraction (1.2 hours)
- Connected to 5 PROD data stores
- Extracted 47 tables in topologically-sorted order
- Handled 2 circular dependencies
...

### Phase 2: Anonymization (0.8 hours)
- Applied 15 PII detection rules
- Anonymized 67 fields across 543,210 records
- 0 PII leaks detected
...

### Phase 3: Validation (0.5 hours)
- Ran 785 validation checks
- Status: PASSED_WITH_WARNINGS
- 3 warnings (see details below)
...

### Phase 4: Loading (2.5 hours)
- Loaded to 5 CERT data stores
- All transactions committed successfully
- 0 rollbacks required
...

### Phase 5: Reporting (0.2 hours)
- Generated comprehensive report
- Saved artifacts to data/reports/
...

## Warnings

1. **student_age_range**: 12 students have age outside 5-22 range
   - Likely adult learners, not a data quality issue
   - Recommendation: Accept and proceed

2. **teacher_has_classes**: 5 teachers not assigned to any classes
   - May be administrative staff or on leave
   - Recommendation: Verify with district roster

3. **attendance_in_school_year**: 23 attendance records outside school year
   - Summer school or extended year programs
   - Recommendation: Accept and proceed

## Recommendations

1. ✅ CERT is ready for QA testing
2. Review the 3 warnings above (non-blocking)
3. Run `/validate-migration mig-20260115-001` for post-load validation
4. Begin QA test plan execution

## Artifacts

- Extracted Data: data/staging/district-001/
- Anonymized Data: data/anonymized/district-001/
- Load Manifest: data/loads/district-001/load-manifest.json
- Logs: logs/mig-20260115-001.log
```

---

## Common Workflows

### Workflow 1: First-Time Setup

```bash
# 1. Clone and configure
git clone https://github.com/pauljbernard/datamig.git
cd datamig
cp .env.example .env
# Edit .env with credentials

# 2. Install dependencies
npm install -g @modelcontextprotocol/server-postgres
cd mcp-servers/neo4j && npm install && cd ../..
cd mcp-servers/etl && npm install && cd ../..
python3 -m venv venv && source venv/bin/activate
pip install faker pandas pyarrow psycopg2-binary neo4j pyyaml

# 3. Enable MCP servers
# Edit .claude/mcp/servers.json, set disabled: false

# 4. Open in Claude Code
claude-code

# 5. Verify setup
# Check that MCP servers loaded successfully
```

### Workflow 2: Planning Your Migrations

```bash
# 1. Analyze data stores (one-time or when schemas change)
/analyze-datastores  # ~30 min

# 2. Select districts (refresh when needed)
/select-districts    # ~15 min

# 3. Review recommendations
cat data/manifests/district-manifest.json | jq '.districts[] | select(.pilot_recommendation != null)'

# 4. Plan your batch
# Start with 3 pilot districts (1 large, 1 medium, 1 small)
# Then proceed to production migrations
```

### Workflow 3: Pilot Migration (Testing)

```bash
# 1. Select a small pilot district
/select-districts  # Note the small pilot recommendation

# 2. Run dry-run migration (no CERT changes)
/migrate district-small-001 --dry-run  # ~2-3 hours

# 3. Review dry-run results
cat data/reports/mig-{run_id}.md

# 4. If successful, run real migration
/migrate district-small-001  # ~2-3 hours

# 5. Validate results
/validate-migration mig-{run_id}  # ~30 min

# 6. QA testing in CERT
# Work with QA team to test data quality

# 7. If issues found, rollback and fix
/rollback mig-{run_id}  # ~30 min
```

### Workflow 4: Production Migration Batch

```bash
# Migrate multiple districts in sequence
# (Run each migration after previous completes)

/migrate district-001  # ~4-6 hours
/validate-migration mig-{run_id_1}

/migrate district-002  # ~4-6 hours
/validate-migration mig-{run_id_2}

/migrate district-003  # ~4-6 hours
/validate-migration mig-{run_id_3}

# Review all results
cat data/reports/mig-*.md | grep "Status:"
```

### Workflow 5: Handling Failed Migrations

```bash
# 1. Migration fails during validation
/migrate district-001
# Output: "⛔ Validation FAILED - see errors below"

# 2. Review errors
cat data/reports/mig-{run_id}.md
# Look at the "Errors" section

# 3. Common issues and fixes:

# Issue: Referential integrity violation
# Fix: Check extraction order, may need to update schema analysis
/analyze-datastores  # Re-run if schemas changed

# Issue: Business rule violation
# Fix: Update config/validation-rules.yaml if rule is incorrect
# OR: Accept and override (advanced)

# 4. Rollback if needed
/rollback mig-{run_id}

# 5. Re-run migration after fixes
/migrate district-001
```

### Workflow 6: Refreshing CERT Data

```bash
# When you need to refresh a district already in CERT

# 1. Rollback existing data
/rollback mig-{old_run_id}  # ~1 hour

# 2. Re-migrate with fresh data
/migrate district-001  # ~4-8 hours

# 3. Validate
/validate-migration mig-{new_run_id}
```

---

## Best Practices

### Security Best Practices

1. **Credentials Management**
   - NEVER commit `.env` to git (it's in .gitignore)
   - Use AWS Secrets Manager or similar in production
   - Rotate credentials regularly (quarterly recommended)
   - Use read-only credentials for PROD (strictly enforce)

2. **Data Protection**
   - Keep `ANONYMIZATION_SALT` secret and consistent
   - Never expose `data/staging/` (contains real PII)
   - Regularly purge old staging data: `rm -rf data/staging/*`
   - Only share `data/anonymized/` if necessary

3. **Access Control**
   - Limit CERT credentials to migration user only
   - Use separate accounts for each environment
   - Enable audit logging on all databases
   - Monitor for suspicious activity

### Operational Best Practices

1. **Start Small**
   - Begin with 3 pilot districts (small, medium, large)
   - Validate each pilot thoroughly
   - Learn from issues before scaling

2. **Batch Planning**
   - Migrate 3-5 districts per batch
   - Allow time for QA validation between batches
   - Don't rush - data quality matters more than speed

3. **Monitoring**
   - Check in on long-running migrations every 2-3 hours
   - Monitor disk space (can grow large for big districts)
   - Watch for validation warnings (may indicate data quality issues)

4. **Rollback Strategy**
   - Test rollback with pilot districts
   - Keep migration artifacts for 30 days minimum
   - Document rollback decision criteria

5. **Documentation**
   - Keep notes on each migration
   - Document any manual interventions
   - Track validation warnings and resolutions

### Data Quality Best Practices

1. **Validation Rules**
   - Review `config/validation-rules.yaml` quarterly
   - Add new rules as you discover edge cases
   - Adjust severity levels based on experience

2. **Anonymization Rules**
   - Review `config/anonymization-rules.yaml` before first use
   - Test anonymization with pilot districts
   - Ensure consistency mapping works correctly

3. **Schema Changes**
   - Re-run `/analyze-datastores` when PROD schemas change
   - Update extraction order if new FKs added
   - Test with pilot district after schema changes

### Performance Best Practices

1. **Disk Management**
   - Provision adequate disk space (100GB+ recommended)
   - Purge old migrations: `rm -rf data/staging/district-* data/anonymized/district-*`
   - Keep reports and manifests, delete raw data

2. **Network Optimization**
   - Run migrations during off-peak hours if possible
   - Ensure stable network connectivity
   - Consider VPN or direct connections for large districts

3. **Resource Monitoring**
   - Monitor CPU/memory during migrations
   - Parquet operations can be memory-intensive
   - Close other applications during large migrations

---

## FAQ

### General Questions

**Q: How long does a migration take?**
A: 4-8 hours depending on district size:
- Small district (<100K records): 2-3 hours
- Medium district (100K-500K records): 4-6 hours
- Large district (>500K records): 6-8 hours

**Q: Can I run multiple migrations in parallel?**
A: Not recommended. Run migrations sequentially to avoid resource conflicts and ensure data integrity.

**Q: What if my migration fails halfway through?**
A: The framework automatically rolls back any database changes using transactions. Your data is safe. Review the error logs and re-run after fixing issues.

**Q: Can I pause a migration?**
A: Not directly, but you can let the current phase complete and use `--skip-extraction` on retry to avoid re-extracting data.

### Technical Questions

**Q: What database versions are supported?**
A: PostgreSQL 11+, Neo4j 4.0+. Tested on PostgreSQL 13 and Neo4j 4.4.

**Q: Can I customize anonymization rules?**
A: Yes! Edit `config/anonymization-rules.yaml`. Changes take effect immediately.

**Q: Can I customize validation rules?**
A: Yes! Edit `config/validation-rules.yaml`. Changes take effect immediately.

**Q: What format is the extracted data?**
A: Apache Parquet (columnar format). Efficient, compressed, preserves data types.

**Q: Can I inspect extracted data before anonymization?**
A: Yes, but BE CAREFUL - `data/staging/` contains real PII. Use Parquet tools:
```bash
pip install parquet-tools
parquet-tools show data/staging/district-001/ids_students.parquet
```

### Troubleshooting Questions

**Q: My MCP servers won't connect. What's wrong?**
A: Check these common issues:
1. Verify credentials in `.env`
2. Check network connectivity to databases
3. Ensure MCP servers are enabled in `.claude/mcp/servers.json`
4. Check firewall rules
5. Verify database hosts/ports are correct

**Q: Validation is failing with FK violations. Why?**
A: Common causes:
1. Circular dependencies not handled correctly
2. Extraction order is incorrect (re-run `/analyze-datastores`)
3. Data quality issues in PROD (orphaned FKs)

**Q: Anonymization is too slow. How can I speed it up?**
A: The consistency mapping can slow down with large datasets. Strategies:
1. Use `hash` strategy instead of `faker` where possible (faster)
2. Ensure adequate RAM (8GB+ recommended)
3. Close other applications

**Q: I'm seeing "PII leak detected" errors. What does this mean?**
A: The framework detected PII that wasn't anonymized. Check:
1. Are your anonymization rules comprehensive?
2. Did you add new PII fields to PROD?
3. Review the leak report for specific fields

**Q: Can I recover from a failed rollback?**
A: Rollback uses DELETE operations in reverse dependency order. If it fails midway:
1. Review the rollback log
2. Manually delete remaining records using district_id filter
3. Contact your DBA if needed

### Planning Questions

**Q: How many districts can I migrate per week?**
A: Conservatively, 3-5 per week assuming:
- 6-8 hours per migration
- 1 day for QA validation
- 1 day buffer for issues

**Q: Should I migrate all districts or just active ones?**
A: Start with active districts. Inactive districts can be migrated later or excluded.

**Q: What's the recommended pilot approach?**
A: The framework recommends 3 pilots:
1. One SMALL district (quick validation)
2. One MEDIUM district (typical use case)
3. One LARGE district (stress test)

**Q: When should I refresh schema analysis?**
A: Run `/analyze-datastores` when:
- First time setup
- PROD schema changes (new tables, FKs, columns)
- Quarterly maintenance
- After major PROD releases

**Q: How do I handle schema changes mid-migration?**
A: If PROD schemas change during active migrations:
1. Complete in-flight migrations with old schema
2. Re-run `/analyze-datastores`
3. Use new schema for subsequent migrations
4. Consider re-migrating already-completed districts if schema changes are significant

### Advanced Questions

**Q: Can I add custom validation logic?**
A: Yes! Create custom validation functions in `scripts/validators/custom_validations.py` and reference them in `config/validation-rules.yaml`.

**Q: Can I change the anonymization strategy for a specific table?**
A: Not per-table, but per-field-pattern. Edit `config/anonymization-rules.yaml` to add more specific patterns.

**Q: Can I migrate a subset of a district (e.g., one school)?**
A: Not directly with current commands. You would need to:
1. Extract the full district
2. Manually filter to desired school
3. Use custom loading scripts

**Q: Can I use this framework for other data migrations (non-district)?**
A: The framework is designed for district-based migrations, but the skills and agents can be adapted. You'd need to:
1. Modify extraction logic for your entity type
2. Update validation rules
3. Adjust anonymization rules
4. Create new skills/commands

**Q: What if I have custom database schemas not in the standard 5 stores?**
A: Add new MCP servers to `.claude/mcp/servers.json` and update the skills to handle the new stores.

---

## Getting Help

### Documentation

- **Main README**: `/README.md` - Architecture and overview
- **Agent Capabilities**: `/docs/AGENT-CAPABILITIES.md` - Self-documentation
- **Setup Guide**: `/docs/SETUP.md` - Detailed configuration
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md` - Common issues and fixes

### Logs and Artifacts

All logs and artifacts are preserved for troubleshooting:

- **Execution Logs**: `logs/mig-{run_id}.log`
- **Validation Reports**: `data/reports/{run_id}-validation.json`
- **Migration Reports**: `data/reports/{run_id}.md`
- **Extraction Manifests**: `data/staging/{district_id}/extraction-manifest.json`

### Support Channels

1. **GitHub Issues**: https://github.com/pauljbernard/datamig/issues
2. **Project Documentation**: Review all docs in `/docs/`
3. **Code Review**: Inspect skills, commands, and agents for details

---

## Next Steps

Now that you understand the framework, proceed to:

1. **[SETUP.md](./SETUP.md)** - Detailed configuration walkthrough
2. **[AGENT-CAPABILITIES.md](./AGENT-CAPABILITIES.md)** - Deep dive into agent capabilities
3. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Solutions to common problems

**Ready to migrate?**

```bash
/analyze-datastores
/select-districts
/migrate <your-first-district>
```

Happy migrating!
