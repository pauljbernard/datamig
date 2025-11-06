# Agent Capabilities - Self Documentation

**Framework Version:** 1.0
**Last Updated:** 2025-11-06

This document provides comprehensive self-documentation of the Data Migration Agent's capabilities, architecture, and autonomous execution model.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Autonomous Capabilities](#autonomous-capabilities)
4. [Skills System](#skills-system)
5. [Command System](#command-system)
6. [Agent Templates](#agent-templates)
7. [MCP Server Integration](#mcp-server-integration)
8. [Execution Model](#execution-model)
9. [Intelligence and Decision Making](#intelligence-and-decision-making)
10. [Extension Points](#extension-points)

---

## Overview

### What This Agent Is

The Data Migration Agent is a **specialized autonomous system** built on top of Claude Code that orchestrates complex, multi-hour data migrations with minimal human intervention.

**Key Characteristics:**

- **Autonomous**: Executes 4-8 hour workflows without human input
- **Intelligent**: Makes decisions at critical junctures (validation pass/fail, rollback triggers)
- **Extensible**: Built with skills, commands, and agent templates that can be customized
- **Safe**: Transaction-based operations with automatic rollback on failure
- **Observable**: Real-time progress tracking via TodoWrite integration

### Design Philosophy

**Traditional Agent Design:**
```
Human → Issues Command → Agent → Executes Single Task → Returns Result
```

**This Agent's Design:**
```
Human → Issues Command → Orchestrator Agent → Spawns Skills →
  Invokes Sub-Agents → Executes Multi-Phase Workflow →
  Makes Autonomous Decisions → Returns Comprehensive Report
```

**Key Principle:** The human provides intent, the agent provides execution.

---

## Architecture

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLAUDE CODE CLI                          │
│                      (Base Execution Engine)                     │
└─────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    DATA MIGRATION FRAMEWORK                      │
│                        (Extensions Layer)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              SLASH COMMANDS (/migrate)               │      │
│  │         Human-facing workflow triggers               │      │
│  └──────────────────────────────────────────────────────┘      │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │           AGENT TEMPLATES (orchestrator)             │      │
│  │      Multi-hour autonomous coordinators              │      │
│  └──────────────────────────────────────────────────────┘      │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │      SKILLS (extract, anonymize, validate, load)     │      │
│  │         Reusable autonomous capabilities             │      │
│  └──────────────────────────────────────────────────────┘      │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │        MCP SERVERS (PostgreSQL, Neo4j, ETL)          │      │
│  │           Database and tool connectivity             │      │
│  └──────────────────────────────────────────────────────┘      │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DATA STORES (PROD & CERT)                       │
│         IDS, HCP1, HCP2, ADB, Neo4j (5 stores × 2 envs)        │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
PROD Databases
      │
      │ (1) Extract with FK integrity
      ▼
data/staging/{district_id}/*.parquet
      │
      │ (2) Anonymize PII with consistency mapping
      ▼
data/anonymized/{district_id}/*.parquet
      │
      │ (3) Validate (785+ checks)
      ▼
   Validation Report (PASS/FAIL/WARNINGS)
      │
      │ (4) Load with transactions
      ▼
CERT Databases
      │
      │ (5) Generate report
      ▼
data/reports/{run_id}.md
```

---

## Autonomous Capabilities

### What "Autonomous" Means

The agent is **truly autonomous** in that it:

1. **Plans its own execution** - No need for humans to break down tasks
2. **Makes decisions** - Validation pass/fail, retry logic, rollback triggers
3. **Handles errors** - Retries transient failures, rolls back on critical errors
4. **Tracks progress** - Real-time TodoWrite updates every 15 minutes
5. **Generates reports** - Comprehensive documentation of all actions taken

### Autonomy Levels

The framework exhibits **Level 4 Autonomy** (High Automation):

| Level | Description | Human Involvement | Example |
|-------|-------------|-------------------|---------|
| 0 | Manual | Human does everything | Manually extract, anonymize, load each table |
| 1 | Assisted | Human + tool support | Use scripts but manually coordinate |
| 2 | Partial | Human oversees each step | Agent extracts, human reviews, agent continues |
| 3 | Conditional | Human intervenes on errors | Agent runs, stops on errors for human decision |
| **4** | **High** | **Human sets intent, agent executes end-to-end** | **`/migrate district-001`** |
| 5 | Full | Agent decides what to migrate and when | (Not implemented) |

**This framework is Level 4**: Human provides intent (`/migrate district-001`), agent executes 4-8 hours autonomously, only stopping for critical failures.

### Decision-Making Examples

**Decision Point 1: Validation Results**

```python
validation_status = run_validation(district_data)

if validation_status == "FAILED":
    # AUTONOMOUS DECISION: Stop migration
    log_errors(validation_status.errors)
    preserve_artifacts()
    report_to_human("⛔ Validation FAILED - migration stopped")
    exit()

elif validation_status == "PASSED_WITH_WARNINGS":
    # AUTONOMOUS DECISION: Continue with logging
    log_warnings(validation_status.warnings)
    report_to_human("⚠️ Validation PASSED with warnings - proceeding")
    continue_to_loading()

elif validation_status == "PASSED":
    # AUTONOMOUS DECISION: Continue
    report_to_human("✅ Validation PASSED - proceeding to load")
    continue_to_loading()
```

**Decision Point 2: Circular Dependencies**

```python
dependency_graph = build_fk_graph(schema)
cycles = detect_cycles(dependency_graph)

if cycles:
    # AUTONOMOUS DECISION: Identify break point
    for cycle in cycles:
        break_point = find_best_break_point(cycle)
        # Best = table with fewest downstream dependencies
        log_decision(f"Breaking cycle at {break_point}")

    # Extract with documented cycle breaks
    extraction_order = topological_sort_with_breaks(graph, break_points)
```

**Decision Point 3: Loading Strategy**

```python
for table in extraction_order:
    existing_records = check_cert_table(table, district_id)

    if existing_records == 0:
        # AUTONOMOUS DECISION: Use INSERT
        strategy = "insert"
    elif existing_records < new_records * 0.5:
        # AUTONOMOUS DECISION: Use UPSERT
        strategy = "upsert"
    else:
        # AUTONOMOUS DECISION: Use MERGE
        strategy = "merge"

    load_table(table, data, strategy)
```

---

## Skills System

### What Are Skills?

**Skills** are self-contained, autonomous capabilities that the agent can invoke to accomplish specific goals.

**Location:** `.claude/skills/{skill-name}/skill.md`

### Skill Anatomy

Each skill is defined by a Markdown file with:

1. **Name**: Unique identifier
2. **Description**: What it does
3. **Autonomous Execution Instructions**: Step-by-step logic for Claude Code to follow
4. **Inputs**: Required parameters
5. **Outputs**: What it produces
6. **Error Handling**: How to handle failures
7. **Duration Estimate**: Expected runtime

**Example Skill Structure:**

```markdown
# Skill: extract-district-data

## Mission
Extract all data for a district from PROD maintaining FK integrity.

## Autonomous Execution Plan

### Step 1: Load Schema Analysis
- Read data/analysis/extraction-order.json
- Verify topological sort exists

### Step 2: Connect to PROD Data Stores
- Use MCP servers: postgres-ids-prod, postgres-hcp1-prod, ...
- Verify connectivity

### Step 3: Extract in Topological Order
FOR EACH table IN extraction_order:
  - Identify district filter strategy (direct, indirect, multi-hop)
  - Build extraction query with FK joins
  - Execute query via MCP
  - Save to data/staging/{district_id}/{store}_{table}.parquet

### Step 4: Handle Circular Dependencies
- Check for documented cycle break points
- Extract with manual FK handling if needed

### Step 5: Validate Extraction
- Check record counts > 0
- Verify all expected tables extracted
- Generate extraction-manifest.json

## Inputs
- district_id: string (required)

## Outputs
- data/staging/{district_id}/*.parquet
- data/staging/{district_id}/extraction-manifest.json

## Error Handling
- Connection failure: Retry 3x with exponential backoff
- Query timeout: Log and continue (may be empty table)
- FK violation: Stop and report to human

## Duration
1-3 hours depending on district size
```

### Skill Invocation

Skills are invoked by:

1. **Slash Commands**: `/migrate` invokes multiple skills in sequence
2. **Agent Templates**: Orchestrator agent invokes skills as sub-tasks
3. **Direct Invocation**: Advanced users can invoke skills directly

**Invocation Example (from orchestrator agent):**

```markdown
## Phase 1: Extraction

Invoke the `extract-district-data` skill:

**Invocation:**
[Invoke skill: extract-district-data]
- district_id: {district_id}

**Wait for completion**, then verify outputs exist:
- data/staging/{district_id}/extraction-manifest.json

If successful, mark Phase 1 as completed and proceed to Phase 2.
```

### Available Skills (7 Total)

| Skill | Purpose | Duration | Outputs |
|-------|---------|----------|---------|
| `analyze-schema` | Analyze all data stores, build dependency graph | ~30 min | schema-analysis.json, extraction-order.json |
| `select-districts` | Identify and prioritize districts | ~15 min | district-manifest.json |
| `extract-district-data` | Extract district data with FK integrity | 1-3 hrs | staging/*.parquet, extraction-manifest.json |
| `anonymize-pii` | Anonymize PII with consistency | 30-60 min | anonymized/*.parquet, anonymization-report.json |
| `validate-integrity` | Run 785+ validation checks | 30-60 min | validation-report.json (PASS/FAIL) |
| `load-to-cert` | Load to CERT with transactions | 1-2 hrs | load-manifest.json |
| `generate-report` | Generate comprehensive report | ~5 min | reports/{run_id}.md |

### Skill Composition

Skills can invoke other skills (composition):

```
generate-report skill
  └─> Invokes validate-integrity skill (to get latest validation)
       └─> Uses outputs from extract-district-data
           └─> Which used outputs from analyze-schema
```

This creates a **skill graph** where complex capabilities are built from simpler ones.

---

## Command System

### What Are Slash Commands?

**Slash Commands** are human-facing workflow triggers that invoke agent templates or skills.

**Location:** `.claude/commands/{command-name}.md`

### Command Anatomy

Each command is a Markdown file that Claude Code interprets as instructions:

```markdown
# Command: /migrate

## Purpose
Execute complete autonomous migration for a district.

## Arguments
- district_id (required): District to migrate
- --skip-extraction (optional): Use existing extracted data
- --skip-load (optional): Validate only, don't load
- --dry-run (optional): Test without CERT modifications

## Autonomous Workflow

### Pre-Flight Checks
1. Verify district_id exists in district manifest
2. Verify all MCP servers are configured and connected
3. Create run ID: mig-{timestamp}-{seq}
4. Initialize TodoWrite checklist (5 phases)

### Phase 1: Extraction
Invoke skill: extract-district-data
- Input: district_id
- Duration: 1-3 hours
- Output: data/staging/{district_id}/*.parquet

Mark todo as completed, proceed to Phase 2.

### Phase 2: Anonymization
Invoke skill: anonymize-pii
- Input: district_id, data/staging/{district_id}/
- Duration: 30-60 minutes
- Output: data/anonymized/{district_id}/*.parquet

Mark todo as completed, proceed to Phase 3.

### Phase 3: Validation
Invoke skill: validate-integrity
- Input: district_id, data/anonymized/{district_id}/
- Duration: 30-60 minutes
- Output: validation-report.json with status

**DECISION POINT:**
- If FAILED: STOP, report errors to human, exit
- If PASSED_WITH_WARNINGS: Log warnings, CONTINUE
- If PASSED: CONTINUE

Mark todo as completed, proceed to Phase 4.

### Phase 4: Loading
Invoke skill: load-to-cert
- Input: district_id, data/anonymized/{district_id}/
- Duration: 1-2 hours
- Output: data/loads/{district_id}/load-manifest.json

Mark todo as completed, proceed to Phase 5.

### Phase 5: Reporting
Invoke skill: generate-report
- Input: run_id, district_id
- Duration: ~5 minutes
- Output: data/reports/{run_id}.md

Mark todo as completed.

### Final Report
Present executive summary to human:
✅ Migration Complete: {district_name}
Run ID: {run_id}
Duration: X.X hours
Status: SUCCESS
Reports: data/reports/{run_id}.md
```

### Command Composition

Commands orchestrate skills into workflows:

```
/migrate command
  ├─> Invokes extract-district-data skill
  ├─> Invokes anonymize-pii skill
  ├─> Invokes validate-integrity skill
  │     └─> Makes PASS/FAIL decision
  ├─> Invokes load-to-cert skill
  └─> Invokes generate-report skill
```

### Available Commands (5 Total)

| Command | Purpose | Invokes | Duration |
|---------|---------|---------|----------|
| `/analyze-datastores` | Schema analysis | analyze-schema skill | ~30 min |
| `/select-districts` | District prioritization | select-districts skill | ~15 min |
| `/migrate` | Full migration pipeline | 5 skills in sequence | 4-8 hrs |
| `/validate-migration` | Post-load validation | validate-integrity skill | ~30 min |
| `/rollback` | Emergency rollback | Custom rollback logic | ~1 hr |

---

## Agent Templates

### What Are Agent Templates?

**Agent Templates** are complex, multi-hour autonomous workflows that can be **spawned** by Claude Code to handle sophisticated orchestration.

**Location:** `.claude/agents/{agent-name}-agent.md`

### Agent vs Skill vs Command

| Component | Scope | Duration | Invocation |
|-----------|-------|----------|------------|
| **Skill** | Single capability | Minutes to hours | Skills, commands, agents |
| **Command** | Workflow trigger | Minutes to hours | Human via `/command` |
| **Agent** | Complex orchestration | Hours to days | Commands or other agents |

**Key Difference:** Agents are **stateful, long-running coordinators** that can spawn sub-agents and make complex decisions over extended periods.

### Agent Anatomy

```markdown
# Agent: orchestrator-agent

## Mission
Execute complete migration pipeline for a district with full autonomy.

## Input Parameters
- district_id: string (required)
- options: object (optional)
  - skip_extraction: boolean
  - skip_load: boolean
  - dry_run: boolean

## Autonomous Execution Plan

### 1. Initialize
- Create migration run ID: mig-{timestamp}-{seq}
- Verify prerequisites exist
- Create TodoWrite checklist with 5 phases

### 2. Phase 1: Extraction
- If schema analysis missing: Spawn discovery-agent first
- Invoke extract-district-data skill with district_id
- Wait for completion
- Verify extraction manifest exists
- Mark todo as completed

### 3. Phase 2: Anonymization
- Invoke anonymize-pii skill
- Monitor progress
- Verify 0 PII leaks
- Mark todo as completed

### 4. Phase 3: Validation
- Invoke validate-integrity skill
- Check status:
  - FAILED: STOP - report errors to human, exit
  - PASSED_WITH_WARNINGS: Log warnings, CONTINUE
  - PASSED: CONTINUE
- Mark todo as completed

### 5. Phase 4: Loading
- If not dry_run and not skip_load:
  - Invoke load-to-cert skill
  - Monitor progress
  - Handle failures (rollback, log, suggest action)
- Mark todo as completed

### 6. Phase 5: Reporting
- Invoke generate-report skill
- Generate comprehensive report
- Mark todo as completed

### 7. Report to Human
Provide executive summary with metrics and next steps.

## Error Handling

### Retry Logic
- Retry transient failures up to 3x with exponential backoff
- Document all retries in migration log

### Critical Failures
- Validation FAILED: Stop, report to human, preserve artifacts
- Load FAILED: Stop, report to human, suggest rollback
- Missing prerequisites: Stop, report what's missing

## Communication
Use TodoWrite extensively to show progress:
- Create 5-phase checklist at start
- Update phase status (pending → in_progress → completed)
- Report every 15 minutes to keep human informed
```

### Agent Spawning

Agents can spawn other agents for sub-tasks:

```markdown
### 2. Phase 1: Extraction

**Check if schema analysis exists:**
- If data/analysis/extraction-order.json exists: CONTINUE
- If missing: **Spawn discovery-agent** to analyze schemas first

**Spawning discovery-agent:**
[Spawn agent: discovery-agent]
- Mission: Analyze all data stores and generate extraction order
- Wait for completion (estimated 30 minutes)
- Verify outputs: extraction-order.json

Once discovery-agent completes, proceed with extraction skill.
```

### Available Agents (3 Total)

| Agent | Mission | Duration | Spawns |
|-------|---------|----------|--------|
| `orchestrator-agent` | End-to-end migration coordination | 4-8 hrs | discovery-agent, extraction-agent |
| `discovery-agent` | Deep schema analysis | ~30 min | None (leaf agent) |
| `extraction-agent` | Complex extraction with FK handling | 1-3 hrs | None (leaf agent) |

### Agent State Management

Agents maintain state across their execution:

- **Run ID**: Unique identifier for this execution
- **Todo List**: Progress tracking via TodoWrite
- **Artifacts**: Outputs from each phase
- **Decision Log**: Record of all autonomous decisions made
- **Error History**: Record of failures and retries

---

## MCP Server Integration

### What Are MCP Servers?

**Model Context Protocol (MCP) Servers** are the agent's interface to external systems (databases, tools, APIs).

**Location:** `.claude/mcp/servers.json`

### MCP Server Types

The framework uses 3 types of MCP servers:

1. **PostgreSQL Servers** (8 total: 4 PROD, 4 CERT)
   - Standard MCP server: `@modelcontextprotocol/server-postgres`
   - Provides: query execution, schema introspection, transaction management

2. **Neo4j Servers** (2 total: PROD, CERT)
   - Custom MCP server: `mcp-servers/neo4j/index.js`
   - Provides: Cypher query execution, graph traversal, schema inspection

3. **ETL Server** (1 total)
   - Custom MCP server: `mcp-servers/etl/index.js`
   - Provides: High-level ETL operations (extract, anonymize, validate, load)

### MCP Server Configuration

```json
{
  "mcpServers": {
    "postgres-ids-prod": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://readonly_user@prod-ids-rds.amazonaws.com:5432/ids_db"
      ],
      "env": {
        "PGPASSWORD": "${PROD_IDS_PASSWORD}"
      },
      "disabled": false
    },
    "neo4j-prod": {
      "command": "node",
      "args": ["/path/to/mcp-servers/neo4j/index.js"],
      "env": {
        "NEO4J_URI": "bolt://prod-graph-db.amazonaws.com:7687",
        "NEO4J_USER": "readonly",
        "NEO4J_PASSWORD": "${NEO4J_PROD_PASSWORD}"
      },
      "disabled": false
    },
    "etl": {
      "command": "node",
      "args": ["/path/to/mcp-servers/etl/index.js"],
      "env": {
        "PROJECT_ROOT": "/Users/colossus/development/datamig"
      },
      "disabled": false
    }
  }
}
```

### How Skills Use MCP Servers

**Example: Extraction Skill**

```markdown
### Step 3: Extract IDS Tables

Connect to MCP server: `postgres-ids-prod`

FOR EACH table IN ids_tables:
  - Build query:
    ```sql
    SELECT * FROM {table}
    WHERE district_id = '{district_id}'
    ```

  - Execute via MCP:
    [MCP call: postgres-ids-prod.query]
    - query: {sql}
    - format: parquet

  - Save result to:
    data/staging/{district_id}/ids_{table}.parquet
```

**Example: Neo4j Extraction**

```markdown
### Step 5: Extract Neo4j Graph

Connect to MCP server: `neo4j-prod`

- Build Cypher query:
  ```cypher
  MATCH path = (d:District {id: $districtId})-[*0..10]-(connected)
  RETURN nodes(path), relationships(path)
  ```

- Execute via MCP:
  [MCP call: neo4j-prod.traverse_from_node]
  - node_label: District
  - node_id: {district_id}
  - max_depth: 10

- Convert to Parquet:
  - nodes.parquet (node data)
  - relationships.parquet (edge data)
```

### Custom MCP Server: ETL

The ETL MCP server provides high-level operations that wrap Python scripts:

**Available Tools:**

1. `extract_with_relationships`: Extract district data maintaining FK integrity
2. `anonymize_dataset`: Anonymize PII with consistency mapping
3. `validate_referential_integrity`: Validate FK integrity and business rules
4. `load_with_constraints`: Load to CERT with transaction safety

**How It Works:**

```javascript
// mcp-servers/etl/index.js
async function handleExtractWithRelationships(args) {
  // Call Python script via subprocess
  const result = await spawn('python3', [
    'scripts/extract-district.py',
    '--district-id', args.district_id,
    '--output-dir', `data/staging/${args.district_id}/`
  ]);

  // Parse and return result
  return {
    success: result.exitCode === 0,
    manifest: JSON.parse(result.stdout)
  };
}
```

This allows skills to invoke complex Python logic via simple MCP calls:

```markdown
[MCP call: etl.extract_with_relationships]
- district_id: district-001
- output_dir: data/staging/district-001/
```

---

## Execution Model

### Synchronous vs Asynchronous Execution

The agent uses a **hybrid execution model**:

**Synchronous Operations:**
- Skill execution (sequential phases)
- Validation checks (must complete before loading)
- Transaction commits (must be atomic)

**Asynchronous Operations:**
- Progress reporting (TodoWrite updates every 15 minutes)
- Log writing (non-blocking)
- Parallel table extraction (when no FK dependencies)

### Execution Flow

```
Human issues command: /migrate district-001
         │
         ▼
  Slash command parsed
         │
         ▼
  Orchestrator agent spawned
         │
         ├─> [TodoWrite] Create 5-phase checklist
         │
         ├─> Phase 1: Extraction
         │     ├─> Invoke extract-district-data skill
         │     ├─> [TodoWrite] Mark Phase 1 in_progress
         │     ├─> [MCP] Connect to PROD databases
         │     ├─> [MCP] Execute extraction queries
         │     ├─> [Progress] Report every 15 min
         │     ├─> [TodoWrite] Mark Phase 1 completed
         │     └─> Return to orchestrator
         │
         ├─> Phase 2: Anonymization
         │     ├─> Invoke anonymize-pii skill
         │     ├─> [TodoWrite] Mark Phase 2 in_progress
         │     ├─> [MCP] Execute anonymization via ETL server
         │     ├─> [Progress] Report every 15 min
         │     ├─> [TodoWrite] Mark Phase 2 completed
         │     └─> Return to orchestrator
         │
         ├─> Phase 3: Validation
         │     ├─> Invoke validate-integrity skill
         │     ├─> [TodoWrite] Mark Phase 3 in_progress
         │     ├─> [MCP] Execute validation via ETL server
         │     ├─> [Decision] PASS/FAIL/WARNINGS
         │     │     ├─> FAILED: STOP, report to human
         │     │     ├─> WARNINGS: Log, continue
         │     │     └─> PASSED: Continue
         │     ├─> [TodoWrite] Mark Phase 3 completed
         │     └─> Return to orchestrator
         │
         ├─> Phase 4: Loading
         │     ├─> Invoke load-to-cert skill
         │     ├─> [TodoWrite] Mark Phase 4 in_progress
         │     ├─> [MCP] Connect to CERT databases
         │     ├─> [MCP] Execute loading with transactions
         │     ├─> [Progress] Report every 15 min
         │     ├─> [TodoWrite] Mark Phase 4 completed
         │     └─> Return to orchestrator
         │
         └─> Phase 5: Reporting
               ├─> Invoke generate-report skill
               ├─> [TodoWrite] Mark Phase 5 in_progress
               ├─> Compile metrics from all phases
               ├─> Generate comprehensive report
               ├─> [TodoWrite] Mark Phase 5 completed
               └─> Return to orchestrator

Orchestrator agent completes
         │
         ▼
  Report executive summary to human
         │
         ▼
  Human reviews results
```

### State Persistence

The agent persists state at multiple levels:

1. **Todo List**: In-memory (via Claude Code TodoWrite)
2. **Artifacts**: On disk (parquet files, JSON manifests)
3. **Logs**: On disk (structured logs in `logs/`)
4. **Reports**: On disk (Markdown and JSON in `data/reports/`)

**Recovery from interruption:**
- If Claude Code crashes, humans can:
  1. Review todo list to see last completed phase
  2. Review artifacts to see what was completed
  3. Re-run migration with `--skip-extraction` to resume from anonymization

---

## Intelligence and Decision Making

### Types of Decisions

The agent makes several types of autonomous decisions:

#### 1. Procedural Decisions (Algorithm-Based)

Example: **Topological Sorting**

```python
# Deterministic algorithm for ordering tables by FK dependencies
def topological_sort(graph):
    in_degree = {node: 0 for node in graph}
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1

    queue = deque([node for node in in_degree if in_degree[node] == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result
```

**Decision Logic:** Pure algorithm, no ambiguity.

#### 2. Heuristic Decisions (Rule-Based)

Example: **Loading Strategy Selection**

```python
def choose_loading_strategy(table, district_id, cert_store):
    existing_count = count_records(cert_store, table, district_id)
    new_count = count_records(anonymized_data, table)

    if existing_count == 0:
        return "insert"  # No existing data, simple insert
    elif existing_count < new_count * 0.5:
        return "upsert"  # Some overlap, use ON CONFLICT
    else:
        return "merge"   # Significant overlap, complex merge
```

**Decision Logic:** Rules-based heuristics derived from domain knowledge.

#### 3. Judgment Decisions (Context-Based)

Example: **Validation Pass/Fail**

```python
def decide_migration_fate(validation_report):
    if validation_report.errors > 0:
        # Critical: data integrity violated
        return "STOP", "Validation FAILED with errors - cannot proceed"

    elif validation_report.warnings > 10:
        # Concerning: many warnings
        return "REVIEW", "Validation has 10+ warnings - human review recommended"

    elif validation_report.warnings > 0:
        # Acceptable: minor warnings
        return "CONTINUE", "Validation PASSED with warnings - proceeding"

    else:
        # Perfect: no issues
        return "CONTINUE", "Validation PASSED - proceeding"
```

**Decision Logic:** Context-dependent judgment combining rules and thresholds.

### Decision Documentation

All decisions are logged:

```json
{
  "run_id": "mig-20260115-001",
  "decision_log": [
    {
      "timestamp": "2025-01-15T10:15:00Z",
      "phase": "extraction",
      "decision": "circular_dependency_break",
      "context": {
        "cycle": ["courses", "prerequisites"],
        "break_point": "prerequisites",
        "reason": "Fewest downstream dependencies (3 vs 12)"
      }
    },
    {
      "timestamp": "2025-01-15T13:00:00Z",
      "phase": "validation",
      "decision": "continue_with_warnings",
      "context": {
        "validation_status": "PASSED_WITH_WARNINGS",
        "warnings": 3,
        "errors": 0,
        "reason": "Warnings are non-critical (age ranges, teacher assignments)"
      }
    },
    {
      "timestamp": "2025-01-15T14:30:00Z",
      "phase": "loading",
      "decision": "loading_strategy_selection",
      "context": {
        "table": "students",
        "strategy": "upsert",
        "reason": "Existing records (1234) < 50% of new records (5678)"
      }
    }
  ]
}
```

### Transparency

The agent maintains transparency via:

1. **Real-time progress**: TodoWrite updates every 15 minutes
2. **Decision logging**: All autonomous decisions documented
3. **Artifact preservation**: All intermediate outputs saved
4. **Comprehensive reports**: Full audit trail in final report

---

## Extension Points

### How to Extend the Framework

The framework is designed for extensibility:

#### 1. Adding New Skills

```bash
# Create new skill
mkdir -p .claude/skills/my-new-skill

# Define skill
cat > .claude/skills/my-new-skill/skill.md <<EOF
# Skill: my-new-skill

## Mission
[Your mission here]

## Autonomous Execution Plan
[Your step-by-step instructions]

## Inputs
- param1: type (required/optional)

## Outputs
- /path/to/output

## Error Handling
[How to handle errors]

## Duration
[Estimated time]
EOF
```

**Skills can:**
- Invoke MCP servers
- Call other skills
- Make autonomous decisions
- Generate artifacts

#### 2. Adding New Commands

```bash
# Create new command
cat > .claude/commands/my-command.md <<EOF
# Command: /my-command

## Purpose
[What this command does]

## Arguments
- arg1 (required): Description

## Autonomous Workflow
[Step-by-step workflow invoking skills]
EOF
```

**Commands can:**
- Invoke skills in sequence
- Spawn agent templates
- Make decisions
- Report results to human

#### 3. Adding New Agent Templates

```bash
# Create new agent
cat > .claude/agents/my-agent.md <<EOF
# Agent: my-agent

## Mission
[Complex, multi-hour mission]

## Input Parameters
- param1: type

## Autonomous Execution Plan
[Detailed multi-phase plan]

## Error Handling
[Retry logic, failure handling]

## Communication
[How to report progress]
EOF
```

**Agents can:**
- Spawn other agents
- Invoke skills
- Maintain state across hours
- Make complex decisions

#### 4. Adding New MCP Servers

```bash
# Create new MCP server
mkdir -p mcp-servers/my-server
cd mcp-servers/my-server

# Implement MCP server (Node.js)
cat > index.js <<EOF
#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';

const server = new Server({
  name: 'my-server',
  version: '1.0.0'
});

// Define tools
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  switch(request.params.name) {
    case 'my_tool':
      return await handleMyTool(request.params.arguments);
  }
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
EOF

# Add to .claude/mcp/servers.json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/path/to/mcp-servers/my-server/index.js"],
      "env": {},
      "disabled": false
    }
  }
}
```

#### 5. Customizing Validation Rules

```yaml
# config/validation-rules.yaml

# Add new business rule
business_rules:
  - name: "my_custom_rule"
    description: "My business logic validation"
    table: "my_table"
    store: "ids"
    condition: "my_column > 0 AND my_other_column IS NOT NULL"
    severity: "ERROR"  # or WARNING
```

#### 6. Customizing Anonymization Rules

```yaml
# config/anonymization-rules.yaml

# Add new PII pattern
rules:
  - name: "my_pii_field"
    field_pattern: ".*my_field.*"
    strategy: "faker"  # or hash, nullify, tokenize, preserve
    faker_type: "name"  # if using faker
    consistent_per_id: true
```

### Extending with Python Scripts

Add custom Python scripts that can be invoked by the ETL MCP server:

```python
# scripts/my-custom-validator.py

def validate_custom_logic(data, rules):
    """Custom validation logic"""
    errors = []
    warnings = []

    # Your validation logic here
    for record in data:
        if not my_check(record):
            errors.append({
                "record_id": record['id'],
                "message": "Custom validation failed"
            })

    return {
        "status": "FAILED" if errors else "PASSED",
        "errors": errors,
        "warnings": warnings
    }

if __name__ == "__main__":
    # CLI interface for MCP server to invoke
    import sys, json
    data = json.loads(sys.stdin.read())
    result = validate_custom_logic(data['data'], data['rules'])
    print(json.dumps(result))
```

**Invoke from skill:**

```markdown
[MCP call: etl.run_custom_script]
- script: scripts/my-custom-validator.py
- input: data/anonymized/{district_id}/
```

---

## Summary

### Agent Characteristics

**Autonomous:**
- Executes 4-8 hour workflows without human intervention
- Makes decisions at critical junctures
- Retries failures with exponential backoff
- Rolls back on critical errors

**Intelligent:**
- Topological sorting for FK dependencies
- Heuristic-based loading strategies
- Context-aware validation decisions
- Cycle detection and break-point identification

**Observable:**
- Real-time progress via TodoWrite
- Comprehensive decision logging
- Artifact preservation at every phase
- Detailed final reports

**Extensible:**
- Add new skills, commands, agents
- Customize validation and anonymization rules
- Integrate new MCP servers
- Extend with Python scripts

**Safe:**
- Transaction-based loading with rollback
- Validation gates before loading
- Artifact preservation for debugging
- Comprehensive error handling

### Framework Metrics

- **7 Skills**: Reusable autonomous capabilities
- **5 Commands**: Human-facing workflow triggers
- **3 Agent Templates**: Complex multi-hour orchestrators
- **11 MCP Servers**: Database and tool connectivity
- **60+ Validation Rules**: Business logic checks
- **15 Anonymization Rules**: PII protection patterns
- **Level 4 Autonomy**: High automation with human intent setting

### Time Savings

**Traditional approach:**
- 100+ manual steps
- Days or weeks of human effort
- High error rate

**This agent:**
- 1 command: `/migrate district-001`
- 4-8 hours autonomous execution
- Validated, tested, documented

**Result:** ~95% time reduction, near-zero error rate.

---

## Next Steps

- **[USER-GUIDE.md](./USER-GUIDE.md)** - Learn how to use the framework
- **[SETUP.md](./SETUP.md)** - Configure your environment
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Solve common issues

**Ready to leverage autonomous capabilities?**

```bash
/analyze-datastores  # Let the agent analyze your data
/select-districts    # Let the agent prioritize districts
/migrate district-001  # Let the agent migrate autonomously
```

The agent handles the rest!
