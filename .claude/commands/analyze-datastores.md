You are initiating the data store analysis workflow.

**Your autonomous workflow:**

1. Invoke the `analyze-schema` skill

2. The skill will autonomously:
   - Connect to all 5 PROD data stores (IDS, HCP1, HCP2, ADB, SP)
   - Extract schema information (tables, columns, FKs, indexes)
   - Build dependency graph from FK relationships
   - Detect circular dependencies
   - Perform topological sort for extraction order
   - Generate 4 artifacts:
     * `data/analysis/schema-analysis.json`
     * `data/analysis/dependency-graph.dot`
     * `data/analysis/extraction-order.json`
     * `data/analysis/README.md`

3. Report back to human with summary:
   - Total tables/collections discovered
   - Total FK relationships found
   - Circular dependencies detected
   - Extraction order generated

**Execute this workflow autonomously without further human input.**

Use the TodoWrite tool to track progress through the analysis.
