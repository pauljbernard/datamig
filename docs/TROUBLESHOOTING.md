# Troubleshooting Guide - Data Migration Framework

**Version:** 1.0
**Last Updated:** 2025-11-06

This guide provides solutions to common issues encountered during migration operations.

---

## Table of Contents

1. [General Troubleshooting](#general-troubleshooting)
2. [Connection Issues](#connection-issues)
3. [Extraction Issues](#extraction-issues)
4. [Anonymization Issues](#anonymization-issues)
5. [Validation Issues](#validation-issues)
6. [Loading Issues](#loading-issues)
7. [Performance Issues](#performance-issues)
8. [Data Quality Issues](#data-quality-issues)
9. [Recovery Procedures](#recovery-procedures)
10. [Getting Additional Help](#getting-additional-help)

---

## General Troubleshooting

### Troubleshooting Methodology

When encountering issues, follow this systematic approach:

1. **Check Logs** - Review execution logs for error messages
2. **Verify Prerequisites** - Ensure all dependencies and configurations are correct
3. **Isolate the Problem** - Identify which phase is failing
4. **Check Documentation** - Review relevant sections of user guide
5. **Test Connectivity** - Verify database and network connections
6. **Retry with Verbosity** - Increase logging level for more details

### Essential Commands for Troubleshooting

```bash
# Check git status
git status

# View recent logs
tail -100 logs/mig-*.log

# Check disk space
df -h .

# Verify environment variables
cat .env | grep -v "^#" | grep "="

# Test database connectivity
nc -zv prod-ids-rds.amazonaws.com 5432

# Check Python environment
source venv/bin/activate && python3 --version

# Verify MCP servers
ls .claude/mcp/servers.json
```

### Log Locations

| Log Type | Location | Contents |
|----------|----------|----------|
| Execution Logs | `logs/mig-{run_id}.log` | Complete migration execution log |
| Error Logs | `logs/error-{run_id}.log` | Error-specific logs |
| MCP Logs | `~/.claude/mcp/logs/` | MCP server connection logs |
| Validation Logs | `data/reports/{run_id}-validation.json` | Detailed validation results |

---

## Connection Issues

### Issue: Cannot Connect to PROD Databases

**Symptoms:**
```
Error: connect ECONNREFUSED prod-ids-rds.amazonaws.com:5432
Error: Connection timeout
Error: FATAL: password authentication failed
```

**Diagnosis:**

```bash
# Test network connectivity
ping prod-ids-rds.amazonaws.com

# Test port connectivity
nc -zv prod-ids-rds.amazonaws.com 5432

# Test PostgreSQL authentication
PGPASSWORD="${PROD_IDS_PASSWORD}" psql \
  -h prod-ids-rds.amazonaws.com \
  -U readonly_user \
  -d ids_db \
  -c "SELECT version();"
```

**Solutions:**

1. **Network Issues:**
   ```bash
   # Check VPN connection
   # Verify you're on the correct network
   # Check firewall rules
   ```

2. **Authentication Issues:**
   ```bash
   # Verify password in .env
   cat .env | grep PROD_IDS_PASSWORD

   # Test with correct password
   PGPASSWORD="correct-password" psql -h prod-ids-rds.amazonaws.com -U readonly_user -d ids_db -c "SELECT 1;"
   ```

3. **Security Group Issues:**
   - Contact your DBA to whitelist your IP address
   - Verify your IP: `curl ifconfig.me`
   - Provide your IP to DBA for whitelisting

4. **Hostname Issues:**
   ```bash
   # Verify hostname resolution
   nslookup prod-ids-rds.amazonaws.com

   # Update .claude/mcp/servers.json with correct hostname
   ```

### Issue: Cannot Connect to Neo4j

**Symptoms:**
```
Error: ServiceUnavailable: Connection refused
Error: AuthenticationError: Invalid username or password
```

**Diagnosis:**

```bash
# Test Bolt protocol connectivity
nc -zv prod-graph-db.amazonaws.com 7687

# Test with Cypher-shell (if installed)
cypher-shell -a bolt://prod-graph-db.amazonaws.com:7687 \
  -u readonly \
  -p "${NEO4J_PROD_PASSWORD}" \
  "RETURN 1;"
```

**Solutions:**

1. **Connection Issues:**
   ```bash
   # Verify Neo4j URI format
   # Should be: bolt://hostname:7687 (not https://)

   # Check .env
   cat .env | grep NEO4J_PROD
   ```

2. **Authentication Issues:**
   ```bash
   # Verify credentials
   # Neo4j uses username + password (not connection string auth)

   # Update mcp-servers/neo4j/.env if using local config
   ```

3. **Protocol Issues:**
   - Ensure you're using Bolt protocol (port 7687)
   - Not HTTP (7474) or HTTPS (7473)

### Issue: MCP Server Won't Start

**Symptoms:**
```
Error: MCP server 'postgres-ids-prod' failed to start
Error: Cannot find module '@modelcontextprotocol/server-postgres'
```

**Diagnosis:**

```bash
# Check if MCP server is installed
npm list -g @modelcontextprotocol/server-postgres

# Check if custom MCP servers have dependencies
cd mcp-servers/neo4j && npm list
cd mcp-servers/etl && npm list
```

**Solutions:**

1. **Missing Global MCP Server:**
   ```bash
   npm install -g @modelcontextprotocol/server-postgres
   ```

2. **Missing Custom MCP Server Dependencies:**
   ```bash
   cd mcp-servers/neo4j
   npm install
   cd ../etl
   npm install
   cd ../..
   ```

3. **Path Issues in MCP Configuration:**
   ```bash
   # Update .claude/mcp/servers.json with absolute paths
   # Use: pwd to get current directory
   # Then update all paths in servers.json
   ```

---

## Extraction Issues

### Issue: Extraction Failing with FK Violations

**Symptoms:**
```
Error: Foreign key violation during extraction
Error: Referenced record not found
Extracted 0 records for table 'enrollments' (expected > 0)
```

**Diagnosis:**

```bash
# Review extraction manifest
cat data/staging/{district_id}/extraction-manifest.json | jq '.circular_dependencies'

# Check extraction order
cat data/analysis/extraction-order.json | jq '.extraction_order'

# Manually query the database
PGPASSWORD="${PROD_IDS_PASSWORD}" psql \
  -h prod-ids-rds.amazonaws.com \
  -U readonly_user \
  -d ids_db \
  -c "SELECT COUNT(*) FROM enrollments WHERE district_id = 'district-001';"
```

**Solutions:**

1. **Re-run Schema Analysis:**
   ```bash
   # Schema may have changed
   /analyze-datastores

   # Check if new FKs were added
   diff data/analysis/schema-analysis.json data/analysis/schema-analysis.json.backup
   ```

2. **Handle Circular Dependencies:**
   ```bash
   # Review circular dependency break points
   cat data/staging/{district_id}/extraction-manifest.json | jq '.circular_dependencies'

   # Manually extract problematic tables
   # (Advanced - contact support)
   ```

3. **Check for Orphaned FKs in PROD:**
   ```sql
   -- Run this query in PROD to find orphaned records
   SELECT COUNT(*)
   FROM enrollments e
   LEFT JOIN students s ON e.student_id = s.id
   WHERE e.district_id = 'district-001'
     AND s.id IS NULL;
   ```

   If count > 0, you have data quality issues in PROD that need fixing.

### Issue: Extraction Timeout

**Symptoms:**
```
Error: Query timeout after 600 seconds
Error: ETIMEDOUT
```

**Diagnosis:**

```bash
# Check district size
jq '.districts[] | select(.district_id == "district-001") | .total_records' \
  data/manifests/district-manifest.json
```

**Solutions:**

1. **Increase Timeout:**
   ```bash
   # Edit extraction skill
   # Update timeout in skill.md (search for "timeout")
   ```

2. **Extract in Batches:**
   ```bash
   # For very large districts, extract specific stores first
   # (Advanced - requires custom scripting)
   ```

3. **Check Database Performance:**
   - Contact DBA about slow queries
   - Check if indexes exist on district_id columns
   - Run EXPLAIN ANALYZE on slow queries

### Issue: No Records Extracted

**Symptoms:**
```
Warning: Extracted 0 records for district-001
Extraction manifest shows 0 total_records
```

**Diagnosis:**

```bash
# Verify district exists
PGPASSWORD="${PROD_IDS_PASSWORD}" psql \
  -h prod-ids-rds.amazonaws.com \
  -U readonly_user \
  -d ids_db \
  -c "SELECT id, name FROM districts WHERE id = 'district-001';"

# Check if district has students
PGPASSWORD="${PROD_IDS_PASSWORD}" psql \
  -h prod-ids-rds.amazonaws.com \
  -U readonly_user \
  -d ids_db \
  -c "SELECT COUNT(*) FROM students WHERE district_id = 'district-001';"
```

**Solutions:**

1. **Wrong District ID:**
   ```bash
   # Review district manifest for correct IDs
   jq '.districts[] | .district_id' data/manifests/district-manifest.json

   # Use correct ID from manifest
   ```

2. **District Has No Data:**
   - District may be inactive
   - Select a different district from manifest

3. **Column Name Mismatch:**
   ```bash
   # Verify district_id column name
   # May be: district_id, district_key, districtId, etc.

   # Update extraction logic if needed
   ```

---

## Anonymization Issues

### Issue: PII Leak Detected

**Symptoms:**
```
Error: PII leak detected in anonymized data
Fields with potential PII: ['email', 'ssn']
Anonymization FAILED
```

**Diagnosis:**

```bash
# Review anonymization report
cat data/anonymized/{district_id}/anonymization-report.json | jq '.pii_leak_check'

# Check which fields leaked
cat data/anonymized/{district_id}/anonymization-report.json | jq '.leaked_fields'
```

**Solutions:**

1. **Add Missing Anonymization Rules:**
   ```yaml
   # Edit config/anonymization-rules.yaml

   # Add rule for leaked field
   rules:
     - name: "leaked_field_name"
       field_pattern: ".*leaked_field.*"
       strategy: "faker"  # or hash, nullify
       faker_type: "name"
   ```

2. **Verify Pattern Matching:**
   ```bash
   # Check if field pattern is matching
   # Field: "user_email" vs Pattern: ".*email.*" (should match)
   # Field: "mail" vs Pattern: ".*email.*" (won't match!)

   # Update pattern to be more inclusive:
   field_pattern: ".*email.*|.*mail.*|.*e_mail.*"
   ```

3. **Re-run Anonymization:**
   ```bash
   # After fixing rules
   /migrate district-001 --skip-extraction
   # This will re-anonymize using existing extracted data
   ```

### Issue: Anonymization Too Slow

**Symptoms:**
```
Anonymization phase running for > 2 hours
Progress stuck at 45%
```

**Diagnosis:**

```bash
# Check dataset size
du -sh data/staging/{district_id}/

# Check memory usage
top -o MEM

# Check consistency map size
ls -lh data/anonymized/{district_id}/consistency-map.json.encrypted
```

**Solutions:**

1. **Use Faster Strategies:**
   ```yaml
   # config/anonymization-rules.yaml

   # Change from faker to hash for better performance
   - name: "ssn"
     strategy: "hash"  # Faster than faker
     hash_algorithm: "sha256"
   ```

2. **Increase Memory:**
   ```bash
   # Close other applications
   # Increase system swap space
   # Use a machine with more RAM
   ```

3. **Batch Processing:**
   ```bash
   # For very large districts, process tables in batches
   # (Advanced - requires code modifications)
   ```

### Issue: Inconsistent Anonymization

**Symptoms:**
```
Same email in different tables anonymized differently
FK relationships broken after anonymization
```

**Diagnosis:**

```bash
# Check if consistent_per_id is enabled
cat config/anonymization-rules.yaml | grep -A5 "email" | grep consistent_per_id
```

**Solutions:**

1. **Enable Consistency Mapping:**
   ```yaml
   # config/anonymization-rules.yaml

   rules:
     - name: "email_addresses"
       field_pattern: ".*email.*"
       strategy: "faker"
       faker_type: "email"
       consistent_per_id: true  # ← Ensure this is true
   ```

2. **Preserve Consistency Map:**
   ```bash
   # Don't delete consistency-map.json between runs
   # If you need to re-run anonymization, use same map

   # Keep: data/anonymized/{district_id}/consistency-map.json.encrypted
   ```

---

## Validation Issues

### Issue: Validation Failing with Errors

**Symptoms:**
```
⛔ Validation FAILED
Errors: 23
Status: MIGRATION STOPPED
```

**Diagnosis:**

```bash
# Review validation report
cat data/reports/{run_id}-validation.json | jq '.errors'

# Check error types
cat data/reports/{run_id}-validation.json | jq '.errors | group_by(.rule) | map({rule: .[0].rule, count: length})'
```

**Solutions:**

**Error Type: Referential Integrity Violations**

```json
{
  "rule": "referential_integrity",
  "message": "FK violation: students.school_id references non-existent school",
  "count": 15
}
```

Solution:
```bash
# Check if extraction order was correct
cat data/staging/{district_id}/extraction-manifest.json | jq '.extraction_order'

# Verify schools were extracted before students
# If not, re-run extraction
/migrate district-001 --skip-anonymization --skip-load
```

**Error Type: Business Rule Violations**

```json
{
  "rule": "enrollment_date_logical",
  "message": "enrollment_date >= graduation_date",
  "count": 8,
  "severity": "ERROR"
}
```

Solution:
```yaml
# If rule is too strict, adjust severity
# config/validation-rules.yaml

business_rules:
  - name: "enrollment_date_logical"
    severity: "WARNING"  # Change from ERROR to WARNING
```

**Error Type: Schema Violations**

```json
{
  "rule": "schema_validation",
  "message": "Column 'age' has NULL values (expected NOT NULL)",
  "count": 12
}
```

Solution:
```bash
# Data quality issue in PROD
# Options:
# 1. Fix data in PROD and re-extract
# 2. Add default value during anonymization
# 3. Adjust schema expectations
```

### Issue: Too Many Warnings

**Symptoms:**
```
⚠️ Validation PASSED with 47 warnings
Warning threshold exceeded (max: 10)
```

**Diagnosis:**

```bash
# Review warnings
cat data/reports/{run_id}-validation.json | jq '.warnings'

# Group warnings by type
cat data/reports/{run_id}-validation.json | jq '.warnings | group_by(.rule) | map({rule: .[0].rule, count: length})'
```

**Solutions:**

1. **Adjust Warning Threshold:**
   ```yaml
   # config/validation-rules.yaml

   settings:
     max_warnings_allowed: 50  # Increase from 10 to 50
   ```

2. **Suppress Known Warnings:**
   ```yaml
   # If certain warnings are expected, change to INFO
   business_rules:
     - name: "student_age_range"
       severity: "INFO"  # Change from WARNING
   ```

3. **Fix Data Quality:**
   - Address root causes in PROD
   - Clean up data before extraction

---

## Loading Issues

### Issue: Loading Fails with Unique Constraint Violation

**Symptoms:**
```
Error: duplicate key value violates unique constraint "students_pkey"
DETAIL: Key (id)=(12345) already exists.
```

**Diagnosis:**

```bash
# Check if data already exists in CERT
PGPASSWORD="${CERT_IDS_PASSWORD}" psql \
  -h cert-ids-rds.amazonaws.com \
  -U admin_user \
  -d ids_db \
  -c "SELECT COUNT(*) FROM students WHERE district_id = 'district-001';"
```

**Solutions:**

1. **Rollback and Re-migrate:**
   ```bash
   # Remove existing data
   /rollback mig-{old_run_id}

   # Re-migrate
   /migrate district-001
   ```

2. **Use Upsert Strategy:**
   ```bash
   # Edit load-to-cert skill
   # Change strategy from "insert" to "upsert"
   # (Advanced - requires skill modification)
   ```

3. **Merge Strategy:**
   ```bash
   # For complex scenarios, use merge
   # (Advanced - requires skill modification)
   ```

### Issue: Loading Timeout

**Symptoms:**
```
Error: CERT loading timeout after 3600 seconds
Transaction rolled back
```

**Diagnosis:**

```bash
# Check dataset size
du -sh data/anonymized/{district_id}/

# Check CERT database performance
PGPASSWORD="${CERT_IDS_PASSWORD}" psql \
  -h cert-ids-rds.amazonaws.com \
  -U admin_user \
  -d ids_db \
  -c "SELECT pg_database_size('ids_db');"
```

**Solutions:**

1. **Increase Timeout:**
   ```bash
   # Edit load-to-cert skill
   # Increase timeout value
   ```

2. **Load in Batches:**
   ```bash
   # For very large districts
   # (Advanced - requires code modification)
   ```

3. **Optimize CERT Database:**
   - Contact DBA to add indexes
   - Vacuum and analyze CERT database
   - Increase CERT database resources

### Issue: Rollback Fails

**Symptoms:**
```
Error during rollback: Cannot delete students (FK constraint)
Rollback incomplete
```

**Diagnosis:**

```bash
# Check rollback log
tail -100 logs/rollback-{run_id}.log

# Identify which table deletion failed
```

**Solutions:**

1. **Manual Cleanup:**
   ```sql
   -- Connect to CERT
   -- Delete in reverse dependency order

   -- 1. Delete child tables first
   DELETE FROM enrollments WHERE district_id = 'district-001';
   DELETE FROM attendance WHERE district_id = 'district-001';

   -- 2. Then parent tables
   DELETE FROM students WHERE district_id = 'district-001';
   DELETE FROM schools WHERE district_id = 'district-001';
   ```

2. **Disable FK Checks (Temporary):**
   ```sql
   -- DANGEROUS - use with caution
   SET session_replication_role = 'replica';  -- Disables FK checks

   -- Delete all tables
   DELETE FROM students WHERE district_id = 'district-001';
   DELETE FROM schools WHERE district_id = 'district-001';
   -- ... etc

   SET session_replication_role = 'origin';  -- Re-enable FK checks
   ```

3. **Contact DBA:**
   - For complex FK graphs
   - If manual cleanup is risky

---

## Performance Issues

### Issue: Migration Taking Too Long

**Symptoms:**
```
Migration running for > 12 hours (expected 4-8 hours)
Progress appears stuck
```

**Diagnosis:**

```bash
# Check current phase
# Review todo list in Claude Code

# Check disk I/O
iostat -x 5

# Check CPU usage
top -o CPU

# Check network utilization
nload
```

**Solutions:**

1. **Disk I/O Bottleneck:**
   ```bash
   # Move to faster disk (SSD)
   # Reduce concurrent operations
   ```

2. **Network Bottleneck:**
   ```bash
   # Use wired connection (not WiFi)
   # Check bandwidth: speedtest-cli
   # Consider running closer to databases (cloud VM)
   ```

3. **Database Performance:**
   ```bash
   # Contact DBA about:
   # - Missing indexes on district_id
   # - Database resource constraints
   # - Slow queries (check EXPLAIN ANALYZE)
   ```

### Issue: Out of Memory

**Symptoms:**
```
Error: Cannot allocate memory
Process killed (OOM)
Python process terminated
```

**Diagnosis:**

```bash
# Check memory usage
free -h  # Linux
vm_stat  # macOS

# Check Python process memory
ps aux | grep python | awk '{print $6}'
```

**Solutions:**

1. **Increase Available Memory:**
   ```bash
   # Close other applications
   # Increase swap space
   # Use machine with more RAM
   ```

2. **Process in Smaller Batches:**
   ```bash
   # Reduce record_sample_size in config/validation-rules.yaml
   settings:
     record_sample_size: 500  # Reduce from 1000
   ```

3. **Optimize Python Scripts:**
   ```python
   # Use generators instead of loading all data
   # Process tables one at a time
   # Use Parquet read in chunks
   ```

### Issue: Disk Space Exhausted

**Symptoms:**
```
Error: No space left on device
Error: ENOSPC: no space left on device
```

**Diagnosis:**

```bash
# Check disk usage
df -h .

# Check data directory sizes
du -sh data/*/
```

**Solutions:**

1. **Clean Up Old Migrations:**
   ```bash
   # Remove old staging data (CAUTION: Contains PII)
   rm -rf data/staging/district-*

   # Remove old anonymized data
   rm -rf data/anonymized/district-*

   # Keep reports and manifests (small)
   ```

2. **Move to Larger Disk:**
   ```bash
   # Move project to larger volume
   mv /Users/colossus/development/datamig /Volumes/LargerDisk/

   # Update PROJECT_ROOT in .env
   ```

3. **Compress Old Files:**
   ```bash
   # Compress old Parquet files
   find data/staging -name "*.parquet" -mtime +7 -exec gzip {} \;
   ```

---

## Data Quality Issues

### Issue: Inconsistent Data Across Stores

**Symptoms:**
```
Warning: Student count mismatch between IDS and HCP1
IDS: 5,432 students
HCP1: 5,387 students
Difference: 45 students (0.8%)
```

**Diagnosis:**

```bash
# Review cross-store validation
cat data/reports/{run_id}-validation.json | jq '.cross_store_rules'

# Manually verify counts
PGPASSWORD="${PROD_IDS_PASSWORD}" psql -h prod-ids-rds.amazonaws.com -U readonly_user -d ids_db \
  -c "SELECT COUNT(*) FROM students WHERE district_id = 'district-001';"

PGPASSWORD="${PROD_HCP1_PASSWORD}" psql -h prod-hcp1-rds.amazonaws.com -U readonly_user -d hcp1_db \
  -c "SELECT COUNT(*) FROM students WHERE district_id = 'district-001';"
```

**Solutions:**

1. **Acceptable Variance:**
   ```yaml
   # If variance is within acceptable limits, increase tolerance
   # config/validation-rules.yaml

   cross_store_rules:
     - name: "student_count_consistency"
       tolerance: 0.10  # Increase from 0.05 (5%) to 0.10 (10%)
   ```

2. **Investigate Discrepancy:**
   ```sql
   -- Find students in IDS but not in HCP1
   SELECT s.id, s.first_name, s.last_name
   FROM ids.students s
   LEFT JOIN hcp1.students h ON s.id = h.id
   WHERE s.district_id = 'district-001'
     AND h.id IS NULL;
   ```

3. **Accept and Document:**
   - Some variance is expected (data sync delays, archival, etc.)
   - Document in migration report
   - Proceed if variance is acceptable

### Issue: Invalid Data Values

**Symptoms:**
```
Warning: 23 students have age = 0
Warning: 15 students have future enrollment dates
```

**Diagnosis:**

```bash
# Review data quality warnings
cat data/reports/{run_id}-validation.json | jq '.warnings[] | select(.rule | contains("age"))'
```

**Solutions:**

1. **Fix in PROD (Preferred):**
   ```sql
   -- Update invalid values in PROD
   UPDATE students
   SET age = NULL  -- or calculate from birth_date
   WHERE age = 0 AND district_id = 'district-001';
   ```

2. **Fix During Anonymization:**
   ```python
   # Add data cleaning to anonymization step
   # (Advanced - requires code modification)

   def clean_age(age):
       if age == 0 or age > 100:
           return None  # Set to NULL
       return age
   ```

3. **Accept with Warning:**
   ```yaml
   # Change severity to INFO if expected
   # config/validation-rules.yaml

   business_rules:
     - name: "student_age_range"
       severity: "INFO"  # Accept any age, just log it
   ```

---

## Recovery Procedures

### Recovering from Failed Migration

**Scenario:** Migration failed during loading phase.

**Steps:**

1. **Review Error Logs:**
   ```bash
   tail -100 logs/mig-{run_id}.log | grep -i error
   ```

2. **Check What Was Loaded:**
   ```bash
   # Review load manifest
   cat data/loads/{district_id}/load-manifest.json | jq '.tables_loaded'
   ```

3. **Rollback:**
   ```bash
   /rollback mig-{run_id}
   ```

4. **Fix Root Cause:**
   - Address validation errors
   - Fix connectivity issues
   - Resolve data quality problems

5. **Retry Migration:**
   ```bash
   # If extraction and anonymization succeeded, skip them
   /migrate district-001 --skip-extraction

   # Otherwise, start fresh
   /migrate district-001
   ```

### Recovering from Corrupted Artifacts

**Scenario:** Parquet files corrupted or incomplete.

**Steps:**

1. **Identify Corrupted Files:**
   ```bash
   # Try to read each Parquet file
   python3 << EOF
   import pandas as pd
   import glob

   for file in glob.glob('data/anonymized/district-001/*.parquet'):
       try:
           df = pd.read_parquet(file)
           print(f"✓ {file}: {len(df)} records")
       except Exception as e:
           print(f"✗ {file}: {e}")
   EOF
   ```

2. **Re-extract Corrupted Tables:**
   ```bash
   # Delete corrupted files
   rm data/staging/district-001/corrupted_table.parquet
   rm data/anonymized/district-001/corrupted_table.parquet

   # Re-run extraction (will re-extract all)
   /migrate district-001 --skip-load
   ```

3. **Verify Integrity:**
   ```bash
   # Check file sizes
   ls -lh data/anonymized/district-001/

   # Check record counts
   python3 << EOF
   import pandas as pd
   import glob

   for file in glob.glob('data/anonymized/district-001/*.parquet'):
       df = pd.read_parquet(file)
       print(f"{file}: {len(df)} records")
   EOF
   ```

### Recovering from Partial Rollback

**Scenario:** Rollback failed midway.

**Steps:**

1. **Identify What Was Deleted:**
   ```bash
   # Review rollback log
   cat logs/rollback-{run_id}.log | grep "DELETE FROM"
   ```

2. **Complete Manual Cleanup:**
   ```sql
   -- Connect to CERT
   -- Delete remaining tables manually

   -- Check what's left
   SELECT 'students' AS table_name, COUNT(*) AS count
   FROM students WHERE district_id = 'district-001'
   UNION ALL
   SELECT 'schools', COUNT(*)
   FROM schools WHERE district_id = 'district-001';

   -- Delete remaining records
   DELETE FROM students WHERE district_id = 'district-001';
   DELETE FROM schools WHERE district_id = 'district-001';
   -- etc.
   ```

3. **Verify Cleanup:**
   ```sql
   -- Verify all district data is gone
   SELECT 'students' AS table_name, COUNT(*) AS remaining
   FROM students WHERE district_id = 'district-001'
   UNION ALL
   SELECT 'schools', COUNT(*)
   FROM schools WHERE district_id = 'district-001';
   -- All counts should be 0
   ```

---

## Getting Additional Help

### Before Requesting Help

Gather this information:

1. **Run ID:** `mig-20260115-001`
2. **District ID:** `district-001`
3. **Phase:** Which phase failed (extraction, anonymization, validation, loading)
4. **Error Message:** Full error message from logs
5. **Environment:** OS, Claude Code version, Python version
6. **Logs:** Relevant sections from `logs/mig-{run_id}.log`

### Diagnostic Report

Generate a diagnostic report:

```bash
#!/bin/bash
# Save as: generate-diagnostic-report.sh

RUN_ID="mig-20260115-001"
DISTRICT_ID="district-001"

echo "=== Diagnostic Report ===" > diagnostic-report.txt
echo "Run ID: $RUN_ID" >> diagnostic-report.txt
echo "District ID: $DISTRICT_ID" >> diagnostic-report.txt
echo "Timestamp: $(date)" >> diagnostic-report.txt
echo "" >> diagnostic-report.txt

echo "=== System Info ===" >> diagnostic-report.txt
uname -a >> diagnostic-report.txt
python3 --version >> diagnostic-report.txt
node --version >> diagnostic-report.txt
echo "" >> diagnostic-report.txt

echo "=== Disk Space ===" >> diagnostic-report.txt
df -h . >> diagnostic-report.txt
echo "" >> diagnostic-report.txt

echo "=== Environment Variables (sanitized) ===" >> diagnostic-report.txt
cat .env | grep -v "PASSWORD" | grep -v "SALT" >> diagnostic-report.txt
echo "" >> diagnostic-report.txt

echo "=== Recent Errors ===" >> diagnostic-report.txt
tail -100 logs/${RUN_ID}.log | grep -i error >> diagnostic-report.txt
echo "" >> diagnostic-report.txt

echo "=== Artifacts ===" >> diagnostic-report.txt
ls -lh data/staging/${DISTRICT_ID}/ >> diagnostic-report.txt
ls -lh data/anonymized/${DISTRICT_ID}/ >> diagnostic-report.txt
echo "" >> diagnostic-report.txt

echo "Report saved to: diagnostic-report.txt"
```

Run:
```bash
chmod +x generate-diagnostic-report.sh
./generate-diagnostic-report.sh
```

### Support Channels

1. **GitHub Issues:**
   - Repository: https://github.com/pauljbernard/datamig/issues
   - Include diagnostic report
   - Include run ID and district ID

2. **Documentation:**
   - [USER-GUIDE.md](./USER-GUIDE.md) - Usage instructions
   - [SETUP.md](./SETUP.md) - Configuration help
   - [AGENT-CAPABILITIES.md](./AGENT-CAPABILITIES.md) - Understanding the agent

3. **Internal Support:**
   - Contact your DBA for database issues
   - Contact IT for network/infrastructure issues
   - Contact project lead for process questions

---

## Appendix: Common Error Messages

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| `ECONNREFUSED` | Database not reachable | Check network, VPN, firewall |
| `password authentication failed` | Wrong credentials | Verify .env passwords |
| `No space left on device` | Disk full | Clean up old migrations, free space |
| `Cannot allocate memory` | Out of RAM | Close apps, increase swap, use bigger machine |
| `Foreign key violation` | Extraction order wrong | Re-run schema analysis |
| `duplicate key value` | Data already exists in CERT | Rollback and retry |
| `PII leak detected` | Missing anonymization rule | Add rule to anonymization-rules.yaml |
| `Validation FAILED` | Data integrity issue | Review validation errors, fix data |
| `Query timeout` | Query too slow | Add indexes, optimize query, contact DBA |
| `Connection timeout` | Network issue | Check VPN, bandwidth, latency |

---

## Next Steps

- **[USER-GUIDE.md](./USER-GUIDE.md)** - Return to user guide
- **[SETUP.md](./SETUP.md)** - Review setup instructions
- **[AGENT-CAPABILITIES.md](./AGENT-CAPABILITIES.md)** - Understand agent capabilities

**Still having issues?** Open a GitHub issue with your diagnostic report.
