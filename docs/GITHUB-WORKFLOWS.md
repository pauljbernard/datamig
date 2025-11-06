# GitHub Workflows Guide

This guide explains how to use GitHub Issues and Actions to trigger autonomous migrations entirely from GitHub, without requiring local Claude Code setup.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Creating Migration Requests](#creating-migration-requests)
- [Monitoring Migrations](#monitoring-migrations)
- [Creating Rollback Requests](#creating-rollback-requests)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

---

## Overview

The GitHub integration provides a fully autonomous migration workflow:

```
User creates GitHub issue
    ↓
GitHub Actions triggered automatically
    ↓
Migration executes (4-8 hours)
    ↓
Progress updates posted to issue
    ↓
PR created with migration report
    ↓
Issue closed automatically
```

**Key Benefits:**
- No local setup required
- Fully autonomous execution
- Real-time progress updates
- Audit trail via issues and PRs
- Secure credential management

---

## Prerequisites

Before you can trigger migrations via GitHub, you need:

1. **Repository access** with permission to create issues
2. **GitHub Secrets configured** by repository admin (see [Setup](#setup))
3. **GitHub Actions enabled** on the repository

**What you DON'T need:**
- Local Claude Code installation
- Database credentials (stored in GitHub Secrets)
- Python environment
- MCP server configuration

---

## Setup

### For Repository Administrators

GitHub Secrets must be configured once before migrations can run. These secrets store database credentials securely.

#### Required Secrets

Navigate to **Settings → Secrets and variables → Actions → New repository secret** and add:

**PROD Database Credentials:**
```
PROD_IDS_PASSWORD      # PROD IDS database password
PROD_HCP1_PASSWORD     # PROD HCP1 database password
PROD_HCP2_PASSWORD     # PROD HCP2 database password
PROD_ADB_PASSWORD      # PROD ADB database password
NEO4J_PROD_PASSWORD    # PROD Neo4j (SP) database password
```

**CERT Database Credentials:**
```
CERT_IDS_PASSWORD      # CERT IDS database password
CERT_HCP1_PASSWORD     # CERT HCP1 database password
CERT_HCP2_PASSWORD     # CERT HCP2 database password
CERT_ADB_PASSWORD      # CERT ADB database password
NEO4J_CERT_PASSWORD    # CERT Neo4j (SP) database password
```

**Optional Secrets:**
```
SLACK_WEBHOOK_URL      # For Slack notifications (optional)
ANONYMIZATION_SALT     # Salt for hashing PII (if not using default)
```

#### Verification

After adding secrets, verify setup by creating a test migration issue:

```markdown
Title: [MIGRATION] Test Setup - district-test-001
Body: Fill out the issue template
```

If GitHub Actions fail immediately with authentication errors, double-check secret names.

---

## Creating Migration Requests

### Step 1: Navigate to Issues

Go to your repository and click **Issues → New Issue**

### Step 2: Choose Template

Select **Migration Request** template

### Step 3: Fill Out Form

**District ID** (required)
```
district-001
```

**Priority** (required)
- Urgent (< 24 hours)
- High (1-3 days)
- Normal (1 week)
- Low (2+ weeks)

**Migration Type** (required)
- **Full Migration** - Extract, Anonymize, Validate, Load (4-8 hours)
- **Dry Run** - Extract, Anonymize, Validate only (2-4 hours)
- **Validation Only** - Validate existing anonymized data (30 min)
- **Re-migration** - Rollback existing + migrate (5-10 hours)

**Skip Extraction** (optional)
- Check if extraction data already exists from previous run

**Skip Loading** (optional)
- Check to validate without loading to CERT

**Additional Notes** (optional)
```
Any special considerations, known issues, or context
```

### Step 4: Submit Issue

Click **Submit new issue**

### Step 5: Automatic Processing

Within 2 minutes:
1. Issue auto-labeled: `migration`, `automated`
2. GitHub Actions workflow triggered
3. Progress updates posted every phase

---

## Monitoring Migrations

### Real-Time Progress Updates

GitHub Actions posts comments to your issue at each phase:

**Phase 1: Extraction**
```markdown
📥 **Phase 1/5: Extraction**

Extracting data from PROD...

Started: 2025-01-06T14:30:00Z
```

**Phase 2: Anonymization**
```markdown
🔒 **Phase 2/5: Anonymization**

Anonymizing PII...

Started: 2025-01-06T16:15:00Z
```

**Phase 3: Validation**
```markdown
✓ **Phase 3/5: Validation**

Running 785+ validation checks...

Started: 2025-01-06T17:45:00Z
```

**Phase 4: Loading**
```markdown
📤 **Phase 4/5: Loading**

Loading to CERT...

Started: 2025-01-06T18:30:00Z
```

**Phase 5: Reporting**
```markdown
📊 **Phase 5/5: Reporting**

Generating migration report...

Started: 2025-01-06T20:15:00Z
```

### Completion

When migration completes successfully:

1. **Success comment posted**
   ```markdown
   ✅ **Migration Complete**

   District: district-001
   Run ID: mig-20250106-143000-001
   Duration: 6h 45m

   All phases completed successfully!
   ```

2. **PR created automatically**
   - Contains full migration report
   - Includes all artifacts
   - Ready for review

3. **Issue closed**
   - Labeled: `completed`
   - Linked to PR

### Monitoring Workflow Execution

**Via GitHub Actions:**
1. Navigate to **Actions** tab
2. Find workflow: "Autonomous Migration Execution"
3. Click to see live logs

**Via Issue Comments:**
- All progress updates appear as comments
- Errors appear immediately with stack traces

---

## Creating Rollback Requests

### When to Rollback

Rollback when:
- Migration loaded incorrect data
- Validation failures discovered post-load
- Need to re-run with fixes

**⚠️ WARNING:** Rollback is **DESTRUCTIVE** and **IRREVERSIBLE**. All district data will be deleted from CERT.

### Step 1: Create Rollback Issue

**Issues → New Issue → Rollback Request**

### Step 2: Fill Required Fields

**Migration Run ID** (required)
```
mig-20250106-143000-001
```
*Find in original migration issue or PR*

**District ID** (required)
```
district-001
```

**Rollback Reason** (required)
```
Data validation errors discovered in post-migration testing
```

**Critical Acknowledgments**

Check all three:
- [ ] I understand this will DELETE all data for this district from CERT
- [ ] I have verified this is the correct Run ID and District ID
- [ ] I have approval from DBA/Lead to proceed

### Step 3: Submit

Rollback executes immediately (~1 hour)

### Step 4: Monitor Progress

Similar to migration, progress updates posted to issue:

```markdown
⚠️ **Rollback Started**

Deleting all data for district district-001 from CERT...

Reason: Data validation errors discovered
```

```markdown
🗑️ Deleting data from CERT SP...
🗑️ Deleting data from CERT ADB...
🗑️ Deleting data from CERT HCP2...
🗑️ Deleting data from CERT HCP1...
🗑️ Deleting data from CERT IDS...
```

```markdown
✅ **Rollback Completed Successfully**

All data for district district-001 has been removed from CERT.
```

---

## Troubleshooting

### Migration Fails at Extraction

**Error:**
```
⛔ **Extraction Failed (IDS)**

psycopg2.OperationalError: FATAL: password authentication failed
```

**Solution:**
- Repository admin: Verify `PROD_IDS_PASSWORD` secret is correct
- Check PROD database connectivity from GitHub Actions runners
- Ensure IP whitelist includes GitHub Actions IPs

### Migration Fails at Validation

**Error:**
```
⛔ **Validation Failed**

Migration STOPPED - errors detected.

785 total checks: 12 failed
```

**Solution:**
- Download validation report from workflow artifacts
- Review specific validation failures
- Fix data issues in PROD
- Re-run migration

### GitHub Actions Timeout

**Error:**
```
The job running on runner GitHub Actions X has exceeded the maximum execution time of 600 minutes.
```

**Solution:**
- Large districts may exceed 10-hour timeout
- Split migration into phases:
  1. Run with "Skip Loading" first
  2. Validate anonymized data
  3. Run again with "Skip Extraction" to load only

### PR Not Created

**Symptoms:**
- Migration succeeds
- No PR appears

**Solution:**
- Check workflow logs for PR creation step
- Verify repository has permissions for PR creation
- Manually create PR from workflow branch

### Secrets Not Found

**Error:**
```
Error: Secret PROD_IDS_PASSWORD not found
```

**Solution:**
- Repository admin: Add missing secret
- Verify exact secret name (case-sensitive)
- Re-run workflow after adding secret

### Comment Posting Fails

**Symptoms:**
- Migration runs but no comments appear
- Workflow logs show: "Warning: Failed to post comment"

**Solution:**
- Workflow still completes successfully
- Check workflow logs for full output
- Verify `gh` CLI authentication

---

## Security Considerations

### Credential Protection

**GitHub Secrets:**
- Encrypted at rest
- Never appear in logs
- Only accessible to workflows
- Redacted in output

**Best Practices:**
1. Use least-privilege database accounts
2. Rotate credentials regularly
3. Audit secret access via GitHub audit log
4. Use environment-specific accounts (PROD ≠ CERT)

### Access Control

**Who can trigger migrations:**
- Anyone with "Write" access to repository
- Can create issues → can trigger migrations

**Recommendations:**
1. Limit repository write access
2. Enable protected branches
3. Require approvals for PRs
4. Enable branch protection on `master`

### Audit Trail

Every migration creates:
- GitHub Issue (request + approval)
- Workflow run logs (execution details)
- PR (results + report)
- Artifacts (logs, reports, manifests)

**Retention:**
- Issues: Forever
- Workflow logs: 90 days (configurable)
- Artifacts: 30-90 days (configured per workflow)

### Network Security

**GitHub Actions Runners:**
- Ephemeral VMs
- Public IPs (change frequently)
- Outbound HTTPS only

**Database Access:**
- Ensure firewall allows GitHub Actions IPs
- Use SSL/TLS for database connections
- Consider self-hosted runners for tighter control

### PII Protection

**In GitHub:**
- Anonymized data never uploaded to GitHub
- Only metadata in issues/PRs
- Reports use aggregated counts, not raw data

**In Workflow Logs:**
- Integration scripts avoid logging PII
- Python scripts write PII only to artifacts
- Artifacts stored encrypted

---

## Advanced Configuration

### Custom Workflow Timeouts

Edit `.github/workflows/migration-automation.yml`:

```yaml
jobs:
  trigger-migration:
    timeout-minutes: 600  # Change to 720 for 12 hours
```

### Slack Notifications

Add `SLACK_WEBHOOK_URL` secret, then edit workflow:

```yaml
- name: Send Slack notification
  if: always()
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
  run: |
    curl -X POST $SLACK_WEBHOOK_URL \
      -H 'Content-Type: application/json' \
      -d '{"text":"Migration ${{ steps.migration.outputs.run_id }} completed"}'
```

### Email Notifications

GitHub Actions sends email on workflow failure by default to:
- Workflow trigger (issue creator)
- Repository watchers (if configured)

Configure in **Settings → Notifications**

---

## Workflow Reference

### Migration Automation Workflow

**File:** `.github/workflows/migration-automation.yml`

**Trigger:** Issue opened/reopened with label `migration`

**Steps:**
1. Parse issue body
2. Checkout repository
3. Setup Python 3.11
4. Install dependencies
5. Configure environment from secrets
6. Execute `scripts/github/trigger-migration.py`
7. Upload artifacts
8. Create PR with report
9. Post completion comment
10. Close issue

**Artifacts:**
- `migration-logs-{run_id}` (30 days)
- `migration-report-{run_id}` (90 days)
- `extraction-manifest-{run_id}` (90 days)
- `validation-report-{run_id}` (90 days)

### Rollback Automation Workflow

**File:** `.github/workflows/rollback-automation.yml`

**Trigger:** Issue opened/reopened with label `rollback`

**Steps:**
1. Parse issue body
2. Checkout repository
3. Setup Python 3.11
4. Install dependencies
5. Configure environment from secrets
6. Execute `scripts/github/trigger-rollback.py`
7. Upload artifacts
8. Post completion comment
9. Close issue or add `needs-manual-intervention` label

**Artifacts:**
- `rollback-logs-{run_id}` (90 days)

### Issue Triage Workflow

**File:** `.github/workflows/issue-triage.yml`

**Trigger:** Issue opened

**Actions:**
- Auto-labels based on title prefix: `[MIGRATION]`, `[ROLLBACK]`, `[BUG]`, etc.
- Posts helpful comment with next steps
- Links to documentation

### PR Validation Workflow

**File:** `.github/workflows/pr-validation.yml`

**Trigger:** PR opened/synchronized on code changes

**Checks:**
- Python linting (black, flake8)
- Python syntax validation
- JavaScript linting
- YAML validation
- Secret scanning (TruffleHog)

---

## FAQ

**Q: Can I run multiple migrations in parallel?**

A: Yes, create multiple issues. Each runs independently. Be aware of:
- Database load (5 simultaneous extractions = heavy PROD load)
- GitHub Actions runner limits (default: 20 concurrent jobs)

**Q: Can I cancel a running migration?**

A: Yes:
1. Close the issue
2. Navigate to Actions → find workflow → Cancel workflow

Data already loaded will remain (rollback required to clean up).

**Q: How do I reuse extraction data?**

A: In migration issue, check "Skip Extraction" and ensure previous extraction artifacts are available.

**Q: Can I test without loading to CERT?**

A: Yes, select "Dry Run" or "Validation Only" migration type.

**Q: What if validation passes but I find issues later?**

A: Create a rollback request, fix issues, then re-run migration.

**Q: Can I see what data will be anonymized before loading?**

A: Yes, run "Validation Only" migration, download artifacts, inspect anonymized parquet files.

**Q: How long are artifacts retained?**

A:
- Migration artifacts: 90 days
- Rollback artifacts: 90 days
- Workflow logs: 90 days

Adjust in workflow YAML if longer retention needed.

**Q: Can I use this from a fork?**

A: No. Secrets are not available to fork PRs for security. Must run from main repository.

---

## Support

**Issues with GitHub Workflows:**
- Check [Troubleshooting](#troubleshooting) section above
- Review workflow logs in Actions tab
- Create bug report issue with `[BUG]` prefix

**Questions:**
- See [User Guide](USER-GUIDE.md)
- See [Troubleshooting Guide](TROUBLESHOOTING.md)
- Create issue with `[QUESTION]` prefix

**Security Concerns:**
- Do not post credentials in issues
- Contact repository admin directly
- Use private vulnerability reporting
