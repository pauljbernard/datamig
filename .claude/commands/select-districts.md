You are initiating the district selection workflow.

**Your autonomous workflow:**

1. Invoke the `select-districts` skill

2. The skill will autonomously:
   - Query all PROD data stores for district metadata
   - Calculate district footprint across all 5 stores
   - Measure activity scores (30-day updates)
   - Apply weighted priority ranking algorithm
   - Estimate migration time per district
   - Select top 15-20 districts
   - Recommend 3 districts for pilot (1 large, 1 medium, 1 small)
   - Generate 2 artifacts:
     * `data/manifests/district-manifest.json`
     * `data/manifests/district-selection-report.md`

3. Report back to human with:
   - List of top 15 districts with metrics
   - Pilot recommendations
   - Estimated total migration time
   - Coverage analysis (% of PROD data)

**Execute this workflow autonomously without further human input.**

Use the TodoWrite tool to track progress through the selection process.
