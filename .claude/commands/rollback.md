You are rolling back a failed or problematic migration.

**Usage**: User will type `/rollback <run-id>` (e.g., `/rollback mig-20251106-001`)

Extract the run ID from the command. If not provided, ask the user for it.

**IMPORTANT**: This is a destructive operation. Confirm with the user before proceeding:

```
⚠️  ROLLBACK CONFIRMATION REQUIRED

You are about to rollback migration: {run_id}
District: {district_name} ({district_id})

This will DELETE all data loaded for this district from CERT databases.

Are you sure you want to proceed? (yes/no)
```

Wait for user confirmation. Only proceed if user types "yes" (case-insensitive).

**Your autonomous workflow (after confirmation):**

1. **Load migration artifacts**:
   - Read `data/reports/{run_id}.json` to get district_id
   - Read `data/loads/{district_id}/load-report.json` to see what was loaded
   - Identify all tables that had data loaded

2. **Build deletion plan**:
   - Determine deletion order (reverse of loading order)
   - Identify FK constraints that must be handled
   - Calculate estimated rows to delete

3. **Execute rollback** (in REVERSE dependency order):
   - Connect to CERT databases
   - For each store in reverse order [sp, adb, hcp2, hcp1, ids]:
     * For each table in reverse loading order:
       ```sql
       DELETE FROM {table} WHERE district_id = '{district_id}'
       ```
     * Log rows deleted
     * Verify deletion successful

4. **Handle Neo4j rollback**:
   ```cypher
   MATCH (n {district_id: '{district_id}'})
   DETACH DELETE n
   ```

5. **Verify rollback**:
   - Query each CERT database
   - Confirm 0 records remain for district_id
   - Check FK integrity not violated

6. **Generate rollback report**:
   ```json
   {
     "rollback_run_id": "rb-{timestamp}",
     "migration_run_id": "{run_id}",
     "district_id": "{district_id}",
     "rolled_back_at": "...",
     "status": "SUCCESS" or "PARTIAL" or "FAILED",
     "deletions": {
       "ids": {
         "tables": 45,
         "rows_deleted": 250000
       },
       ...
     },
     "total_rows_deleted": 750000,
     "verification": "PASSED"
   }
   ```

7. **Clean up staging/anonymized data** (optional):
   - Ask user: "Delete staging and anonymized data for this district? (yes/no)"
   - If yes:
     ```bash
     rm -rf data/staging/{district_id}
     rm -rf data/anonymized/{district_id}
     rm -rf data/loads/{district_id}
     ```

8. **Report completion to human**:
   ```
   ✅ Rollback Complete

   Run ID: {run_id}
   District: {district_name}

   Rollback Summary:
   - Tables Processed: 157
   - Rows Deleted: 750,000
   - Stores Cleaned: 5 (IDS, HCP1, HCP2, ADB, SP)

   Verification: PASSED
   - CERT databases verified clean
   - No {district_id} records remain
   - FK integrity maintained

   CERT is ready for fresh migration attempt.

   Next Steps:
   1. Investigate root cause of original failure
   2. Fix any issues
   3. Re-run migration: /migrate {district_id}

   Rollback report: data/reports/rollback-{timestamp}.json
   ```

   OR if rollback had issues:
   ```
   ⚠️  Rollback Incomplete

   Run ID: {run_id}
   District: {district_name}

   Issues Encountered:
   1. Could not delete X records from table Y (FK constraint violation)
   2. [Other issues...]

   Status: PARTIAL ROLLBACK

   Manual intervention required:
   - Review rollback report: data/reports/rollback-{timestamp}.json
   - Check CERT databases manually
   - Contact DBA if needed

   Some data may remain in CERT for district {district_id}.
   ```

**Error Handling**:
- Use transactions where possible
- If deletion fails, log error but continue with other tables
- Generate detailed report of what was/wasn't deleted
- Do NOT fail silently - report all issues

**Safety Checks**:
- NEVER delete data without district_id filter
- ALWAYS verify district_id in WHERE clause
- ALWAYS use transactions for PostgreSQL
- ALWAYS verify deletions after execution

**Execute autonomously after user confirmation.**

Use TodoWrite to track rollback progress through each store.
