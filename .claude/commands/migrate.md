You are initiating a FULL AUTONOMOUS MIGRATION for a district.

**Usage**: User will type `/migrate <district-id>` (e.g., `/migrate district-001`)

Extract the district ID from the command. If not provided, ask the user for it.

**Your autonomous workflow:**

1. **Pre-flight checks**:
   - Verify district exists in `data/manifests/district-manifest.json`
   - Check all MCP servers are configured (note: they may be disabled, document this)
   - Verify required files exist (schema-analysis.json, extraction-order.json)
   - Create migration run ID: `mig-{timestamp}-{counter}`
   - Use TodoWrite to create migration checklist

2. **Phase 1: Extraction**
   - Invoke `extract-district-data` skill with district_id parameter
   - Log progress: "Extracting from IDS... X records"
   - Wait for completion
   - Verify extraction-manifest.json was generated

3. **Phase 2: Anonymization**
   - Invoke `anonymize-pii` skill with district_id parameter
   - Monitor anonymization progress
   - Wait for completion
   - Verify anonymization-report.json was generated
   - Verify 0 PII leaks detected

4. **Phase 3: Validation**
   - Invoke `validate-integrity` skill with district_id parameter
   - Wait for validation completion
   - Check validation-report.json status:
     * If FAILED: STOP - report errors to human, do NOT proceed
     * If PASSED_WITH_WARNINGS: Log warnings, CONTINUE
     * If PASSED: CONTINUE

5. **Phase 4: Loading** (only if validation passed)
   - Invoke `load-to-cert` skill with district_id parameter
   - Monitor loading progress
   - Wait for completion
   - Check load-report.json status:
     * If FAILED: Report failure, suggest /rollback
     * If SUCCESS: CONTINUE

6. **Phase 5: Reporting**
   - Invoke `generate-report` skill with run_id and district_id
   - Generate comprehensive migration report
   - (Optional) Send notifications if configured

7. **Report final status to human**:
   ```
   ✅ Migration Complete for {district_name}

   Run ID: {run_id}
   Duration: X.X hours
   Status: SUCCESS

   Summary:
   - Extracted: XXX,XXX records
   - Anonymized: XXX,XXX records (XXX PII fields)
   - Validated: PASSED (X warnings)
   - Loaded: XXX,XXX records to CERT

   Reports:
   - Full Report: data/reports/{run_id}.md
   - JSON Report: data/reports/{run_id}.json

   Next Steps:
   1. Review warnings (if any)
   2. Begin QE testing on CERT
   3. Monitor for any issues

   CERT is ready for testing! 🎉
   ```

**IMPORTANT**: Execute this entire workflow autonomously. Only stop for human intervention if:
- Critical errors occur that cannot be auto-resolved
- Validation fails with ERRORS (not warnings)
- You need credentials/configuration that aren't available
- Load phase fails

Otherwise, execute end-to-end without human input.

**Use TodoWrite extensively** to show progress:
- Create initial checklist with all 5 phases
- Mark phases as in_progress when starting
- Mark phases as completed when done
- Update human on progress every 10-15 minutes

**Expected duration**: 4-8 hours for typical district (750K records)

**Error Recovery**:
- Retry transient failures up to 3 times
- If a phase fails critically, stop and report
- Preserve all artifacts even on failure for troubleshooting
