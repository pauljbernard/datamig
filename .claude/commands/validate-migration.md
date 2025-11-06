You are validating a completed migration.

**Usage**: User will type `/validate-migration <run-id>` (e.g., `/validate-migration mig-20251106-001`)

Extract the run ID from the command. If not provided, ask the user for it.

**Your autonomous workflow:**

1. **Load migration artifacts**:
   - Read `data/reports/{run_id}.json` to get district_id
   - Read `data/loads/{district_id}/load-report.json`
   - Read `data/manifests/district-manifest.json` for expected metrics

2. **Re-run validation checks on CERT**:
   - Connect to CERT databases (postgres-*-cert, neo4j-sp-cert)
   - Query for loaded district data
   - Verify record counts match expectations:
     ```sql
     SELECT COUNT(*) FROM students WHERE district_id = '{district_id}'
     ```
   - Check referential integrity on CERT:
     * All FKs should reference existing records
     * No orphaned references
   - Validate business rules on live CERT data

3. **Compare CERT data against original PROD data** (anonymization-aware):
   - Record counts should match (within 1%)
   - Relationships should be preserved
   - Data distributions should be similar
   - FK graphs should match

4. **Test data accessibility**:
   - Run sample queries on CERT
   - Verify all tables are queryable
   - Check indexes exist and work

5. **Generate validation report**:
   ```json
   {
     "validation_run_id": "val-{timestamp}",
     "migration_run_id": "{run_id}",
     "district_id": "{district_id}",
     "validated_at": "...",
     "status": "VALID" or "ISSUES_FOUND",
     "checks": {
       "record_counts": "PASSED",
       "fk_integrity": "PASSED",
       "business_rules": "PASSED",
       "data_accessibility": "PASSED",
       "data_distribution": "PASSED"
     },
     "issues": [],
     "recommendations": []
   }
   ```

6. **Report results to human**:
   ```
   ✅ Migration Validation: VALID

   Run ID: {run_id}
   District: {district_name}

   Validation Results:
   - Record Counts: ✓ Match expectations (750,000 records)
   - FK Integrity: ✓ All relationships valid
   - Business Rules: ✓ All rules satisfied
   - Data Access: ✓ All tables queryable
   - Distribution: ✓ Matches PROD patterns

   Status: MIGRATION VERIFIED SUCCESSFULLY

   CERT data for {district_name} is valid and ready for testing.
   ```

   OR if issues found:
   ```
   ⚠️ Migration Validation: ISSUES FOUND

   Run ID: {run_id}
   District: {district_name}

   Issues Detected:
   1. Record count mismatch in students table (expected: 75000, found: 74998)
   2. 3 orphaned FK references in enrollments table

   Recommendations:
   1. Review extraction logs for missing records
   2. Re-run migration with /migrate {district_id}
   3. Or investigate specific issues manually

   See full report: data/reports/validation-{timestamp}.json
   ```

**Execute autonomously.**

Use TodoWrite to track validation progress.
