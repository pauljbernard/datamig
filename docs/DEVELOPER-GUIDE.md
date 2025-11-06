# Developer Guide - Data Migration Framework

This guide is for developers who want to understand, extend, modify, or contribute to the autonomous data migration framework.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Code Organization](#code-organization)
- [Development Environment Setup](#development-environment-setup)
- [Extending the Framework](#extending-the-framework)
- [Python Scripts Development](#python-scripts-development)
- [MCP Server Development](#mcp-server-development)
- [Testing Strategies](#testing-strategies)
- [Debugging Guide](#debugging-guide)
- [Code Style and Conventions](#code-style-and-conventions)
- [Contributing Guidelines](#contributing-guidelines)
- [Release Process](#release-process)

---

## Architecture Overview

### Layered Architecture

The framework uses a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: User Interface                                │
│  - Slash commands (/migrate, /rollback, etc.)          │
│  - GitHub issue templates                               │
│  - Interactive prompts                                  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Orchestration                                 │
│  - Agent templates (orchestrator-agent.md)             │
│  - Workflow coordination                                │
│  - Decision logic (PASS/FAIL gates)                     │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Skills                                        │
│  - Reusable autonomous capabilities                     │
│  - Business logic encapsulation                         │
│  - Error handling and retry logic                       │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Execution                                     │
│  - Python scripts (extract, anonymize, validate, etc.)  │
│  - Data processing logic                                │
│  - File I/O and transformation                          │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 5: Infrastructure                                │
│  - MCP servers (database connectivity)                  │
│  - Database drivers (psycopg2, neo4j)                  │
│  - AWS SDK, file system                                 │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

**1. Autonomous-First Design**
- Each component designed for unattended execution
- Comprehensive error handling at every layer
- Self-recovery where possible, clear failure modes otherwise

**2. Declarative Configuration**
- Skills defined in markdown (`.claude/skills/*/skill.md`)
- Rules defined in YAML (`config/anonymization-rules.yaml`, `config/validation-rules.yaml`)
- Database connections defined in JSON (`.claude/mcp/servers.json`)

**3. Separation of Concerns**
- Skills = what to do (business logic)
- Python scripts = how to do it (implementation)
- MCP servers = where to do it (infrastructure)

**4. Idempotency**
- All operations can be safely re-run
- Extraction creates new directories per run
- Loading uses upsert or explicit insert strategies
- Rollback is safe to run multiple times

**5. Observability**
- TodoWrite integration for real-time progress
- Comprehensive logging to stderr and files
- Structured JSON outputs for machine parsing
- Human-readable markdown reports

---

## Code Organization

### Directory Structure

```
datamig/
├── .claude/                    # Claude Code extensions
│   ├── agents/                # Agent templates (complex workflows)
│   │   ├── discovery-agent.md
│   │   ├── extraction-agent.md
│   │   └── orchestrator-agent.md
│   ├── commands/              # Slash commands (workflow triggers)
│   │   ├── analyze-datastores.md
│   │   ├── migrate.md
│   │   ├── rollback.md
│   │   ├── select-districts.md
│   │   └── validate-migration.md
│   ├── mcp/                   # MCP server configuration
│   │   ├── servers.json       # Server definitions
│   │   └── README.md
│   └── skills/                # Autonomous capabilities
│       ├── analyze-schema/
│       ├── anonymize-pii/
│       ├── extract-district-data/
│       ├── generate-report/
│       ├── load-to-cert/
│       ├── select-districts/
│       └── validate-integrity/
│
├── scripts/                   # Python execution layer
│   ├── extractors/
│   │   └── extract_with_relationships.py
│   ├── validators/
│   │   └── validate_integrity.py
│   ├── loaders/
│   │   └── load_with_constraints.py
│   ├── github/               # GitHub Actions integration
│   │   ├── trigger-migration.py
│   │   └── trigger-rollback.py
│   ├── anonymize.py
│   ├── district-analyzer.py
│   ├── generate-report.py
│   ├── schema-analyzer.py
│   └── rollback.py
│
├── mcp-servers/              # Custom MCP server implementations
│   ├── neo4j/               # Neo4j MCP server
│   │   ├── index.js
│   │   └── package.json
│   └── etl/                 # ETL MCP server
│       ├── index.js
│       └── package.json
│
├── config/                   # Configuration files
│   ├── anonymization-rules.yaml
│   └── validation-rules.yaml
│
├── docs/                     # Documentation
│   ├── USER-GUIDE.md
│   ├── DEVELOPER-GUIDE.md
│   ├── AGENT-CAPABILITIES.md
│   ├── SETUP.md
│   ├── TROUBLESHOOTING.md
│   └── GITHUB-WORKFLOWS.md
│
├── .github/                  # GitHub integration
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│
├── data/                     # Runtime data (gitignored)
│   ├── extractions/
│   ├── anonymized/
│   ├── validations/
│   └── loads/
│
├── logs/                     # Runtime logs (gitignored)
├── reports/                  # Generated reports (gitignored)
└── README.md
```

### Component Responsibilities

**`.claude/skills/*/skill.md`**
- Define autonomous execution plans
- Specify inputs, outputs, error handling
- Invoke Python scripts or MCP servers
- Business logic in declarative form

**`scripts/*.py`**
- Implement data processing logic
- Handle file I/O, database operations
- Generate structured outputs (JSON, Parquet)
- Exit with appropriate codes (0=success, 1=failure)

**`mcp-servers/*/index.js`**
- Provide database connectivity
- Expose tools for Claude Code to invoke
- Handle authentication and connection pooling
- Return structured results

**`config/*.yaml`**
- Define rules (anonymization strategies, validation checks)
- Parameterize behavior without code changes
- Version-controlled configuration

**`.github/workflows/*.yml`**
- Define CI/CD pipelines
- Automate issue-based execution
- Handle secrets and environment variables

---

## Development Environment Setup

### Prerequisites

- **Node.js 18+**: For MCP servers
- **Python 3.11+**: For execution scripts
- **Claude Code**: Latest version
- **Git**: Version control
- **Database Access**: PROD (read-only) and CERT (read-write)

### Initial Setup

**1. Clone and Install**

```bash
git clone https://github.com/yourusername/datamig.git
cd datamig

# Install Node dependencies
npm install

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

**2. Configure Environment**

```bash
# Copy environment template
cp .env.template .env

# Edit with your credentials
vim .env
```

Required environment variables:
```bash
# PROD databases (read-only)
PROD_IDS_HOST=prod-ids.rds.amazonaws.com
PROD_IDS_PORT=5432
PROD_IDS_USER=readonly_user
PROD_IDS_PASSWORD=secure_password_here
PROD_IDS_DATABASE=ids_db

# ... repeat for HCP1, HCP2, ADB, Neo4j

# CERT databases (read-write)
CERT_IDS_HOST=cert-ids.rds.amazonaws.com
CERT_IDS_PORT=5432
CERT_IDS_USER=migration_user
CERT_IDS_PASSWORD=secure_password_here
CERT_IDS_DATABASE=ids_db

# ... repeat for CERT databases

# Anonymization
ANONYMIZATION_SALT=random_salt_for_hashing
```

**3. Enable MCP Servers**

Edit `.claude/mcp/servers.json`:
```json
{
  "mcpServers": {
    "postgres-prod-ids": {
      "disabled": false,  // Change from true to false
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "${PROD_IDS_URI}"],
      "env": {
        "PROD_IDS_URI": "postgresql://${PROD_IDS_USER}:${PROD_IDS_PASSWORD}@${PROD_IDS_HOST}:${PROD_IDS_PORT}/${PROD_IDS_DATABASE}"
      }
    }
    // ... enable other servers as needed
  }
}
```

**4. Verify Setup**

```bash
# Test Python environment
python scripts/schema-analyzer.py --help

# Test MCP servers (from Claude Code)
# In Claude Code, type:
/analyze-datastores
```

### Development Tools

**Recommended IDE: VS Code**
```bash
code .
```

**Extensions:**
- Python
- ESLint (for MCP servers)
- YAML
- Markdown All in One

**Linters:**
```bash
# Python
pip install black flake8 pylint

# Format Python code
black scripts/

# Lint Python code
flake8 scripts/ --max-line-length=120

# JavaScript (for MCP servers)
cd mcp-servers/neo4j
npm install --save-dev eslint
npm run lint
```

---

## Extending the Framework

### Adding a New Skill

Skills are the primary extension point. Here's how to add one:

**Step 1: Create Skill Directory**

```bash
mkdir -p .claude/skills/my-new-skill
```

**Step 2: Create `skill.md`**

```markdown
# Skill: my-new-skill

## Mission
[One sentence: what this skill does autonomously]

## Autonomous Execution Plan

### Step 1: [First step]
[Detailed instructions for what Claude Code should do]

### Step 2: [Second step]
[More instructions]

## Inputs
- `input_param_1` (string): Description
- `input_param_2` (integer): Description

## Outputs
- `output_file.json`: Description of output format

## Error Handling
- If [error condition], then [recovery action]
- If [critical error], STOP and report to human

## Duration
Expected: X minutes/hours
```

**Step 3: Create Supporting Python Script (if needed)**

```bash
touch scripts/my_new_operation.py
chmod +x scripts/my_new_operation.py
```

```python
#!/usr/bin/env python3
"""
Description of what this script does
"""
import sys
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description='My new operation')
    parser.add_argument('--input', required=True, help='Input parameter')
    parser.add_argument('--output', required=True, help='Output file')

    args = parser.parse_args()

    # Your logic here
    result = {
        'success': True,
        'data': 'processed data'
    }

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    return 0

if __name__ == '__main__':
    sys.exit(main())
```

**Step 4: Update Skill to Invoke Script**

In `skill.md`:
```markdown
### Step 3: Execute Processing

Run the processing script:

```bash
python3 scripts/my_new_operation.py \
  --input {input_param_1} \
  --output {output_directory}/result.json
```

Check exit code. If non-zero, operation failed.
```

**Step 5: Test the Skill**

From Claude Code:
```
Test my new skill:
- Input: test value
- Expected output: test result
```

### Adding a New Command

Commands orchestrate multiple skills into workflows.

**Step 1: Create Command File**

```bash
touch .claude/commands/my-command.md
```

**Step 2: Define Command**

```markdown
# Command: /my-command

## Purpose
[What this command does end-to-end]

## Arguments
- `<required-arg>`: Description
- `[optional-arg]`: Description (default: value)

## Autonomous Workflow

**Your mission**: Execute this workflow autonomously with minimal human intervention.

### Pre-Flight Checks
- Verify [prerequisite 1]
- Check [prerequisite 2]

### Phase 1: [First phase name]
1. Invoke `analyze-schema` skill
2. Parse results
3. Make decision based on results

### Phase 2: [Second phase name]
1. Invoke `my-new-skill` skill
2. Check for errors
3. If errors, STOP and report

### Final Report
Generate summary report for human.
```

**Step 3: Use in Claude Code**

```
/my-command required-value optional-value
```

### Adding New Validation Rules

**Edit `config/validation-rules.yaml`:**

```yaml
business_rules:
  - name: "my_new_validation"
    table: "target_table"
    condition: "field > 0 AND field < 100"
    severity: "ERROR"  # or WARNING
    message: "Field must be between 0 and 100"
```

The `validate_integrity.py` script automatically picks up new rules.

### Adding New Anonymization Rules

**Edit `config/anonymization-rules.yaml`:**

```yaml
rules:
  - name: "my_new_pii_field"
    field_pattern: ".*my_field.*"
    strategy: "faker"  # or hash, tokenize, nullify, preserve
    faker_type: "name"  # if using faker
    description: "Anonymize my new PII field"
```

---

## Python Scripts Development

### Script Template

```python
#!/usr/bin/env python3
"""
Script Name: my_script.py

Purpose:
    Brief description of what this script does

Usage:
    python3 my_script.py --arg1 value1 --arg2 value2

Inputs:
    - arg1: Description
    - arg2: Description

Outputs:
    - output_file.json: Description

Exit Codes:
    0: Success
    1: Failure
"""

import sys
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('logs/my_script.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='My script description',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--arg1', required=True, help='Argument 1')
    parser.add_argument('--arg2', required=False, default='default', help='Argument 2')
    parser.add_argument('--output', required=True, help='Output file path')

    return parser.parse_args()

def main():
    """Main execution function"""
    args = parse_arguments()

    logger.info(f"Starting script with arg1={args.arg1}, arg2={args.arg2}")

    try:
        # Your logic here
        result = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'arg1': args.arg1,
            'arg2': args.arg2
        }

        # Write output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        logger.info(f"Script completed successfully. Output: {output_path}")
        return 0

    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

### Best Practices

**1. Always Use Argparse**
- Makes scripts self-documenting
- Provides `--help` automatically
- Type checking and validation

**2. Structured Logging**
- Log to stderr (Claude Code captures this)
- Include timestamps
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)

**3. Structured Outputs**
- JSON for machine parsing
- Markdown for human reports
- Parquet for large datasets

**4. Error Handling**
```python
try:
    # Risky operation
    result = database_query()
except psycopg2.OperationalError as e:
    logger.error(f"Database connection failed: {e}")
    return 1
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return 1
```

**5. Progress Reporting**
```python
import sys

def log_progress(message):
    """Log progress to stderr for Claude Code to capture"""
    print(f"[PROGRESS] {message}", file=sys.stderr, flush=True)

# Usage
log_progress("Phase 1/5: Extraction started")
```

### Testing Python Scripts

**Unit Testing:**

Create `tests/test_my_script.py`:

```python
import unittest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from my_script import some_function

class TestMyScript(unittest.TestCase):

    def test_some_function(self):
        result = some_function(input_data)
        self.assertEqual(result, expected_output)

    def test_error_handling(self):
        with self.assertRaises(ValueError):
            some_function(invalid_input)

if __name__ == '__main__':
    unittest.main()
```

**Integration Testing:**

```bash
# Test script with sample data
python3 scripts/my_script.py \
  --arg1 test_value \
  --output /tmp/test_output.json

# Verify output
cat /tmp/test_output.json | jq .
```

---

## MCP Server Development

### MCP Server Template

Create `mcp-servers/my-server/index.js`:

```javascript
#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Initialize server
const server = new Server(
  {
    name: "my-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "my_tool",
        description: "Description of what this tool does",
        inputSchema: {
          type: "object",
          properties: {
            param1: {
              type: "string",
              description: "Parameter description",
            },
          },
          required: ["param1"],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "my_tool":
      return await handleMyTool(args);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

async function handleMyTool(args) {
  try {
    // Your implementation here
    const result = {
      success: true,
      data: "processed data",
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: false,
            error: error.message,
          }),
        },
      ],
      isError: true,
    };
  }
}

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MCP server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```

**package.json:**

```json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "bin": {
    "my-mcp-server": "./index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0"
  }
}
```

### Testing MCP Servers

**1. Test Standalone:**

```bash
cd mcp-servers/my-server
npm install
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node index.js
```

**2. Test from Claude Code:**

Add to `.claude/mcp/servers.json`:
```json
{
  "my-server": {
    "disabled": false,
    "command": "node",
    "args": ["mcp-servers/my-server/index.js"]
  }
}
```

Then in Claude Code:
```
Use the my-server MCP to test my_tool with param1="test"
```

---

## Testing Strategies

### Test Pyramid

```
                    ┌─────────────┐
                    │  End-to-End │  (Manual, via Claude Code)
                    │   Testing   │
                    └─────────────┘
                  ┌─────────────────┐
                  │   Integration   │  (Python scripts with test DBs)
                  │     Testing     │
                  └─────────────────┘
              ┌───────────────────────┐
              │    Unit Testing       │  (Pure functions, utilities)
              │  (Python unittest)    │
              └───────────────────────┘
```

### Unit Testing

Test individual functions in isolation:

```python
# tests/test_anonymize.py
import unittest
from scripts.anonymize import apply_faker_anonymization

class TestAnonymization(unittest.TestCase):
    def test_email_anonymization(self):
        result = apply_faker_anonymization('john@example.com', 'email', {})
        self.assertTrue('@' in result)
        self.assertNotEqual(result, 'john@example.com')
```

Run tests:
```bash
python -m unittest discover tests/
```

### Integration Testing

Test scripts with test databases:

```bash
# Create test database
createdb test_migration

# Run extraction against test DB
python3 scripts/extractors/extract_with_relationships.py \
  --source-config '{"store":"ids","environment":"test"}' \
  --output-dir /tmp/test_extraction

# Verify output
ls /tmp/test_extraction/
```

### End-to-End Testing

Test complete workflows via Claude Code:

```
Test the full migration workflow with test district:

1. Run /analyze-datastores (should take 2-3 minutes)
2. Run /select-districts (should identify test districts)
3. Run /migrate test-district-001
4. Verify outputs in data/extractions/
5. Verify reports in reports/
```

---

## Debugging Guide

### Debugging Skills

**1. Enable Verbose Logging**

Skills inherit Claude Code's logging. Check stderr output.

**2. Check TodoWrite Updates**

Skills should use TodoWrite to report progress:
```markdown
Update TodoWrite:
- Mark "Extraction" as in_progress
- Current step: Extracting IDS tables
```

**3. Verify Python Script Execution**

Skills invoke Python scripts. Check logs:
```bash
tail -f logs/extract_with_relationships.log
```

### Debugging Python Scripts

**1. Add Debug Logging**

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Processing table: {table_name}")
logger.debug(f"Row count: {len(df)}")
```

**2. Run Script Directly**

```bash
python3 -m pdb scripts/my_script.py --arg1 value1
```

**3. Check Exit Codes**

```bash
python3 scripts/my_script.py --arg1 value1
echo $?  # Should be 0 for success
```

### Debugging MCP Servers

**1. Test with JSON-RPC**

```bash
cd mcp-servers/neo4j
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node index.js 2>&1 | jq .
```

**2. Enable Debug Logging**

Add to MCP server:
```javascript
console.error(`[DEBUG] Received request: ${JSON.stringify(request)}`);
```

**3. Check MCP Server Logs**

Claude Code logs MCP server output to stderr.

### Common Issues

**Issue: Skill not found**
- Solution: Check `.claude/skills/skill-name/skill.md` exists
- Restart Claude Code to reload skills

**Issue: Python script not executable**
- Solution: `chmod +x scripts/my_script.py`

**Issue: MCP server not connecting**
- Solution: Check `.claude/mcp/servers.json` has `"disabled": false`
- Verify command and args are correct
- Test server standalone first

**Issue: Database connection timeout**
- Solution: Check firewall rules
- Verify credentials in `.env`
- Test connection with `psql` or `neo4j-shell`

---

## Code Style and Conventions

### Python

**Follow PEP 8:**
```bash
# Auto-format
black scripts/

# Lint
flake8 scripts/ --max-line-length=120
```

**Naming Conventions:**
- Files: `snake_case.py`
- Functions: `snake_case()`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`

**Docstrings:**
```python
def extract_table(connection, table_name, filter_criteria):
    """
    Extract data from a table with filtering.

    Args:
        connection: Database connection object
        table_name (str): Name of table to extract
        filter_criteria (dict): Filter conditions

    Returns:
        pandas.DataFrame: Extracted data

    Raises:
        psycopg2.Error: If database query fails
    """
```

### JavaScript (MCP Servers)

**Use ESLint:**
```bash
npm install --save-dev eslint
npx eslint mcp-servers/
```

**Naming Conventions:**
- Files: `camelCase.js`
- Functions: `camelCase()`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`

### Markdown (Skills, Commands, Agents)

**Structure:**
- Use H1 (`#`) for title
- Use H2 (`##`) for major sections
- Use H3 (`###`) for subsections
- Use code blocks with language tags

**Example:**
````markdown
# Skill: example-skill

## Mission
Brief description

## Autonomous Execution Plan

### Step 1: Initialize
Instructions here

```bash
command --arg value
```
````

### YAML (Configuration)

**Indentation:** 2 spaces
**Arrays:** Use `-` prefix
**Comments:** Use `#` for explanations

```yaml
# Anonymization rules for PII fields
rules:
  - name: "email_addresses"
    field_pattern: ".*email.*"
    strategy: "faker"
    faker_type: "email"
```

---

## Contributing Guidelines

### Workflow

**1. Create Feature Branch**
```bash
git checkout master
git pull origin master
git checkout -b feature/my-new-feature
```

**2. Make Changes**
- Write code
- Add tests
- Update documentation

**3. Test Locally**
```bash
# Run tests
python -m unittest discover tests/

# Test via Claude Code
/my-command test-args
```

**4. Commit**
```bash
git add .
git commit -m "Add: my new feature

- Implemented X
- Added tests for Y
- Updated docs

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**5. Push and Create PR**
```bash
git push origin feature/my-new-feature
gh pr create --title "Add my new feature" --body "Description of changes"
```

### Pull Request Checklist

- [ ] Code follows style guidelines (black, flake8, eslint)
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No secrets committed
- [ ] `IMPLEMENTATION-STATUS.md` updated if needed
- [ ] Backward compatible (or breaking changes documented)

### Code Review Process

1. Automated checks run (linting, tests, secret scanning)
2. Manual review by maintainer
3. Feedback addressed
4. Approved and merged to master

---

## Release Process

### Versioning

We use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Creating a Release

**1. Update Version**

Edit relevant files:
- `README.md` (Document Version)
- `package.json` (for MCP servers)

**2. Update CHANGELOG**

Create `CHANGELOG.md` entry:
```markdown
## [3.1.0] - 2025-01-15

### Added
- New skill: custom-validation
- Support for parallel extractions

### Fixed
- Bug in anonymization consistency mapping

### Changed
- Improved error messages in validation
```

**3. Create Git Tag**
```bash
git tag -a v3.1.0 -m "Release v3.1.0: Add custom validation support"
git push origin v3.1.0
```

**4. Create GitHub Release**
```bash
gh release create v3.1.0 \
  --title "v3.1.0: Custom Validation Support" \
  --notes-file RELEASE_NOTES.md
```

---

## Performance Optimization

### Profiling Python Scripts

**Use cProfile:**
```bash
python -m cProfile -o profile.stats scripts/extract_with_relationships.py --args

# Analyze results
python -m pstats profile.stats
> sort cumtime
> stats 20
```

### Database Query Optimization

**1. Use EXPLAIN:**
```sql
EXPLAIN ANALYZE
SELECT * FROM students WHERE district_id = 'district-001';
```

**2. Add Indexes:**
```sql
CREATE INDEX idx_students_district ON students(district_id);
```

### Parquet Optimization

**Use compression:**
```python
df.to_parquet('output.parquet', compression='snappy', index=False)
```

**Partition large datasets:**
```python
df.to_parquet('output/', partition_cols=['district_id'], compression='snappy')
```

---

## Summary

This developer guide covers:

✅ Architecture and design principles
✅ Code organization and structure
✅ Development environment setup
✅ Extending the framework (skills, commands, MCP servers)
✅ Python and JavaScript development best practices
✅ Testing strategies (unit, integration, E2E)
✅ Debugging techniques
✅ Code style and conventions
✅ Contributing guidelines
✅ Release process

**Next Steps:**
1. Set up your development environment
2. Read existing code to understand patterns
3. Start with a small contribution (new validation rule, bug fix)
4. Gradually take on larger features (new skills, MCP servers)

**Resources:**
- [User Guide](USER-GUIDE.md) - Learn how to use the framework
- [Agent Capabilities](AGENT-CAPABILITIES.md) - Understand autonomous execution
- [Troubleshooting](TROUBLESHOOTING.md) - Debug common issues
- [GitHub Workflows](GITHUB-WORKFLOWS.md) - CI/CD integration

**Questions?**
- Review existing code in `scripts/` and `.claude/skills/`
- Check GitHub issues for examples
- Create a question issue with `[QUESTION]` prefix
