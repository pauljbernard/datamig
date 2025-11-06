# Setup Guide - Data Migration Framework

**Version:** 1.0
**Last Updated:** 2025-11-06

This guide provides detailed step-by-step instructions for setting up the Data Migration Framework from scratch.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Requirements](#system-requirements)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [MCP Server Setup](#mcp-server-setup)
6. [Verification](#verification)
7. [First Run](#first-run)
8. [Troubleshooting Setup Issues](#troubleshooting-setup-issues)

---

## Prerequisites

### Required Access

Before beginning setup, ensure you have:

#### Database Credentials

**PROD Environment (Read-Only Access):**
- IDS PostgreSQL database
- HCP1 PostgreSQL database
- HCP2 PostgreSQL database
- ADB PostgreSQL database
- Neo4j graph database (SP)

**CERT Environment (Read/Write Access):**
- IDS PostgreSQL database
- HCP1 PostgreSQL database
- HCP2 PostgreSQL database
- ADB PostgreSQL database
- Neo4j graph database (SP)

#### Account Requirements

- **GitHub account**: To clone the repository
- **Claude Code CLI**: Installed and configured
- **AWS/Cloud access** (if databases are in cloud): VPN or direct connect configured

### Required Software

| Software | Minimum Version | Recommended Version | Purpose |
|----------|----------------|---------------------|---------|
| Node.js | 18.0 | 20.x LTS | MCP server runtime |
| Python | 3.9 | 3.11+ | Data processing scripts |
| Git | 2.30 | Latest | Version control |
| PostgreSQL Client | 13 | 15+ | Database connectivity |
| Claude Code CLI | Latest | Latest | Agent execution |

### System Resources

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| RAM | 8 GB | 16 GB | For large district processing |
| Disk Space | 50 GB free | 100 GB free | Parquet files can be large |
| CPU | 4 cores | 8 cores | Faster processing |
| Network | 10 Mbps | 100 Mbps | Database connectivity |

---

## System Requirements

### Operating System

**Supported:**
- macOS 12+ (Monterey or later)
- Linux (Ubuntu 20.04+, RHEL 8+, Debian 11+)
- Windows 11 with WSL2

**Recommended:** macOS or Linux for best performance

### Network Requirements

**Connectivity:**
- Outbound HTTPS (443) for GitHub
- Database ports open to PROD and CERT:
  - PostgreSQL: 5432
  - Neo4j: 7687 (Bolt protocol)

**Bandwidth:**
- Minimum: 10 Mbps download, 5 Mbps upload
- Recommended: 100 Mbps+ for large migrations

**Latency:**
- Ideally < 50ms to database servers
- VPN or direct connect recommended for cloud databases

---

## Installation Steps

### Step 1: Install System Dependencies

#### macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Node.js
brew install node

# Install Python 3
brew install python@3.11

# Install PostgreSQL client tools
brew install postgresql@15

# Install Git (if not already installed)
brew install git
```

#### Linux (Ubuntu/Debian)

```bash
# Update package lists
sudo apt update

# Install Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL client
sudo apt install -y postgresql-client

# Install Git
sudo apt install -y git
```

#### Linux (RHEL/CentOS)

```bash
# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

# Install Python 3
sudo yum install -y python3.11 python3-pip

# Install PostgreSQL client
sudo yum install -y postgresql

# Install Git
sudo yum install -y git
```

#### Windows (WSL2)

```powershell
# Install WSL2 (if not already installed)
wsl --install -d Ubuntu-22.04

# Then follow Linux (Ubuntu/Debian) instructions inside WSL
```

### Step 2: Verify Installations

```bash
# Verify Node.js
node --version
# Expected: v20.x.x or later

# Verify npm
npm --version
# Expected: v10.x.x or later

# Verify Python
python3 --version
# Expected: Python 3.9+ (3.11+ recommended)

# Verify pip
pip3 --version
# Expected: pip 23.x or later

# Verify PostgreSQL client
psql --version
# Expected: psql (PostgreSQL) 13.x or later

# Verify Git
git --version
# Expected: git version 2.30 or later
```

### Step 3: Install Claude Code CLI

```bash
# Install Claude Code CLI globally
npm install -g @anthropic-ai/claude-code

# Verify installation
claude-code --version
# Expected: version number (e.g., 1.2.0)

# Configure Claude Code (first-time setup)
claude-code config
# Follow prompts to authenticate with Anthropic account
```

### Step 4: Clone the Repository

```bash
# Navigate to your development directory
cd ~/development  # or wherever you keep projects

# Clone the repository
git clone https://github.com/pauljbernard/datamig.git

# Navigate into the project
cd datamig

# Verify repository structure
ls -la
# Expected: README.md, .claude/, config/, scripts/, etc.
```

### Step 5: Install Node.js Dependencies

```bash
# Install PostgreSQL MCP server globally
npm install -g @modelcontextprotocol/server-postgres

# Verify installation
npx @modelcontextprotocol/server-postgres --version

# Install dependencies for custom Neo4j MCP server
cd mcp-servers/neo4j
npm install
cd ../..

# Install dependencies for custom ETL MCP server
cd mcp-servers/etl
npm install
cd ../..
```

### Step 6: Install Python Dependencies

```bash
# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows (WSL):
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install \
  faker \
  pandas \
  pyarrow \
  psycopg2-binary \
  neo4j \
  pyyaml \
  python-dotenv

# Verify installations
pip list | grep -E "(faker|pandas|pyarrow|psycopg2|neo4j|pyyaml|dotenv)"

# Create requirements.txt for future reference
pip freeze > requirements.txt
```

**Note:** Keep the virtual environment activated for all subsequent Python operations.

---

## Configuration

### Step 1: Environment Variables

#### Create .env File

```bash
# Copy template
cp .env.example .env

# Open for editing
nano .env  # or vim, code, etc.
```

#### Configure PROD Credentials (Read-Only)

```bash
# IDS - PROD
PROD_IDS_PASSWORD=your-prod-ids-readonly-password-here
PROD_IDS_HOST=prod-ids-rds.amazonaws.com  # Optional: uncomment if custom
PROD_IDS_PORT=5432                         # Optional: uncomment if custom
PROD_IDS_DATABASE=ids_db                   # Optional: uncomment if custom
PROD_IDS_USER=readonly_user                # Optional: uncomment if custom

# HCP1 - PROD
PROD_HCP1_PASSWORD=your-prod-hcp1-readonly-password-here
# ... (similar for HCP1)

# HCP2 - PROD
PROD_HCP2_PASSWORD=your-prod-hcp2-readonly-password-here
# ... (similar for HCP2)

# ADB - PROD
PROD_ADB_PASSWORD=your-prod-adb-readonly-password-here
# ... (similar for ADB)

# Neo4j - PROD
NEO4J_PROD_PASSWORD=your-neo4j-prod-readonly-password-here
NEO4J_PROD_URI=bolt://prod-graph-db.amazonaws.com:7687  # Optional: uncomment if custom
NEO4J_PROD_USER=readonly                                # Optional: uncomment if custom
```

#### Configure CERT Credentials (Read/Write)

```bash
# IDS - CERT
CERT_IDS_PASSWORD=your-cert-ids-admin-password-here
CERT_IDS_HOST=cert-ids-rds.amazonaws.com  # Optional: uncomment if custom
CERT_IDS_PORT=5432                         # Optional: uncomment if custom
CERT_IDS_DATABASE=ids_db                   # Optional: uncomment if custom
CERT_IDS_USER=admin_user                   # Optional: uncomment if custom

# HCP1 - CERT
CERT_HCP1_PASSWORD=your-cert-hcp1-admin-password-here
# ... (similar for HCP1)

# HCP2 - CERT
CERT_HCP2_PASSWORD=your-cert-hcp2-admin-password-here
# ... (similar for HCP2)

# ADB - CERT
CERT_ADB_PASSWORD=your-cert-adb-admin-password-here
# ... (similar for ADB)

# Neo4j - CERT
NEO4J_CERT_PASSWORD=your-neo4j-cert-admin-password-here
NEO4J_CERT_URI=bolt://cert-graph-db.amazonaws.com:7687  # Optional: uncomment if custom
NEO4J_CERT_USER=admin                                   # Optional: uncomment if custom
```

#### Configure Anonymization Settings

```bash
# Generate a secure random salt (CRITICAL - keep this secret!)
ANONYMIZATION_SALT=$(openssl rand -base64 32)

# Or manually generate and paste:
# openssl rand -base64 32
# Then copy output and paste as value:
ANONYMIZATION_SALT=your-random-salt-string-here-keep-this-secret
```

**IMPORTANT:**
- Keep the same `ANONYMIZATION_SALT` for all runs to ensure consistency
- Never commit `.env` to version control (it's in `.gitignore`)
- Store the salt securely (e.g., password manager, secrets vault)

#### Optional Settings

```bash
# Enable CERT backup before loading (requires significant disk space)
ENABLE_CERT_BACKUP=false  # Set to true if you want backups

# Project root directory (auto-detected if not set)
PROJECT_ROOT=/Users/colossus/development/datamig

# Notification settings (optional)
EMAIL_ENABLED=false
STAKEHOLDER_EMAILS=team@example.com,qa@example.com

SLACK_ENABLED=false
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### Verify .env File

```bash
# Verify all passwords are set (should show "set")
cat .env | grep -E "PASSWORD=" | grep -v "^#" | awk -F= '{print $1 ": " ($2 ? "set" : "NOT SET")}'

# Verify salt is set
cat .env | grep ANONYMIZATION_SALT | grep -v "^#"
# Should show a long random string, NOT "your-random-salt-string-here-keep-this-secret"
```

### Step 2: Configure MCP Servers

MCP servers connect Claude Code to databases. Configuration is in `.claude/mcp/servers.json`.

#### Edit MCP Configuration

```bash
# Open MCP configuration
nano .claude/mcp/servers.json  # or your preferred editor
```

#### Configure PostgreSQL MCP Servers

**IMPORTANT:** Update connection strings with your actual database hosts.

```json
{
  "mcpServers": {
    "postgres-ids-prod": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://readonly_user@prod-ids-rds.amazonaws.com:5432/ids_db"
        // ^^^^^^^^^^^^ UPDATE THIS HOST ^^^^^^^^^^^^
      ],
      "env": {
        "PGPASSWORD": "${PROD_IDS_PASSWORD}"
      },
      "disabled": false  // ← Change from true to false to enable
    },

    "postgres-hcp1-prod": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://readonly_user@prod-hcp1-rds.amazonaws.com:5432/hcp1_db"
        // ^^^^^^^^^^^^ UPDATE THIS HOST ^^^^^^^^^^^^
      ],
      "env": {
        "PGPASSWORD": "${PROD_HCP1_PASSWORD}"
      },
      "disabled": false
    },

    // ... repeat for all 8 PostgreSQL servers
  }
}
```

**Steps:**
1. Replace `prod-ids-rds.amazonaws.com` with your actual PROD IDS host
2. Replace `cert-ids-rds.amazonaws.com` with your actual CERT IDS host
3. Repeat for HCP1, HCP2, ADB (both PROD and CERT)
4. Change `"disabled": true` to `"disabled": false` for each server
5. Verify usernames match your setup (default: `readonly_user` for PROD, `admin_user` for CERT)

#### Configure Neo4j MCP Servers

```json
{
  "mcpServers": {
    "neo4j-prod": {
      "command": "node",
      "args": ["/Users/colossus/development/datamig/mcp-servers/neo4j/index.js"],
      // ^^^^^^^ UPDATE THIS PATH TO ABSOLUTE PATH ^^^^^^^
      "env": {
        "NEO4J_URI": "bolt://prod-graph-db.amazonaws.com:7687",
        // ^^^^^^^^^^^^^ UPDATE THIS HOST ^^^^^^^^^^^^^
        "NEO4J_USER": "readonly",
        "NEO4J_PASSWORD": "${NEO4J_PROD_PASSWORD}"
      },
      "disabled": false
    },

    "neo4j-cert": {
      "command": "node",
      "args": ["/Users/colossus/development/datamig/mcp-servers/neo4j/index.js"],
      // ^^^^^^^ UPDATE THIS PATH TO ABSOLUTE PATH ^^^^^^^
      "env": {
        "NEO4J_URI": "bolt://cert-graph-db.amazonaws.com:7687",
        // ^^^^^^^^^^^^^ UPDATE THIS HOST ^^^^^^^^^^^^^
        "NEO4J_USER": "admin",
        "NEO4J_PASSWORD": "${NEO4J_CERT_PASSWORD}"
      },
      "disabled": false
    }
  }
}
```

**Steps:**
1. Replace `/Users/colossus/development/datamig/` with YOUR actual project path
   - Get it with: `pwd` (in the project directory)
2. Replace `prod-graph-db.amazonaws.com` with your actual Neo4j host
3. Change `"disabled": true` to `"disabled": false`

#### Configure ETL MCP Server

```json
{
  "mcpServers": {
    "etl": {
      "command": "node",
      "args": ["/Users/colossus/development/datamig/mcp-servers/etl/index.js"],
      // ^^^^^^^ UPDATE THIS PATH TO ABSOLUTE PATH ^^^^^^^
      "env": {
        "PROJECT_ROOT": "/Users/colossus/development/datamig",
        // ^^^^^^^ UPDATE THIS PATH ^^^^^^^
        "PYTHON_BIN": "/Users/colossus/development/datamig/venv/bin/python3"
        // ^^^^^^^ UPDATE THIS PATH TO YOUR VENV PYTHON ^^^^^^^
      },
      "disabled": false
    }
  }
}
```

**Steps:**
1. Replace project paths with YOUR actual paths
2. Verify Python binary path points to your virtualenv
   - Get it with: `which python3` (with venv activated)
3. Change `"disabled": true` to `"disabled": false`

#### Progressive Enablement Strategy

**Recommended Approach:** Enable servers progressively and test each one.

**Day 1: Enable PROD IDS only**
```json
{
  "mcpServers": {
    "postgres-ids-prod": { "disabled": false },
    // All others: "disabled": true
  }
}
```

Test connectivity (see Verification section below).

**Day 2: Enable all PROD servers**
```json
{
  "mcpServers": {
    "postgres-ids-prod": { "disabled": false },
    "postgres-hcp1-prod": { "disabled": false },
    "postgres-hcp2-prod": { "disabled": false },
    "postgres-adb-prod": { "disabled": false },
    "neo4j-prod": { "disabled": false },
    // CERT servers still disabled
  }
}
```

Test schema analysis.

**Day 3: Enable CERT servers**
```json
{
  "mcpServers": {
    // All PROD: "disabled": false
    "postgres-ids-cert": { "disabled": false },
    "postgres-hcp1-cert": { "disabled": false },
    "postgres-hcp2-cert": { "disabled": false },
    "postgres-adb-cert": { "disabled": false },
    "neo4j-cert": { "disabled": false }
  }
}
```

**Day 4: Enable ETL server**
```json
{
  "mcpServers": {
    // All database servers: "disabled": false
    "etl": { "disabled": false }
  }
}
```

Ready for full migrations!

### Step 3: Configure Validation Rules

Review and customize business validation rules:

```bash
# Open validation rules
nano config/validation-rules.yaml
```

**Review sections:**
1. `business_rules`: Domain-specific logic (e.g., student age ranges)
2. `completeness_rules`: Required field checks
3. `cross_store_rules`: Multi-database consistency
4. `data_quality_rules`: General data quality

**Customization:**
- Adjust severity levels: `ERROR` (blocks migration) vs `WARNING` (logs only)
- Modify conditions to match your business rules
- Add new rules as needed

**Example customization:**

```yaml
business_rules:
  - name: "student_age_range"
    description: "Students must be between 5 and 22 years old"
    table: "students"
    store: "ids"
    condition: "age >= 5 AND age <= 22"
    severity: "WARNING"  # Change to ERROR if strict enforcement needed
```

### Step 4: Configure Anonymization Rules

Review and customize PII anonymization rules:

```bash
# Open anonymization rules
nano config/anonymization-rules.yaml
```

**Review sections:**
1. Field patterns (regex to match PII columns)
2. Anonymization strategies (faker, hash, nullify, tokenize, preserve)
3. Consistency settings

**Customization:**
- Add new field patterns if you have custom PII fields
- Adjust strategies (e.g., use `hash` instead of `faker` for better performance)
- Set `consistent_per_id: true` for fields that need consistency

**Example customization:**

```yaml
rules:
  # Add a custom PII field
  - name: "employee_ids"
    field_pattern: ".*employee_id.*|.*emp_id.*"
    strategy: "hash"  # Use hash for better performance
    hash_algorithm: "sha256"
    salt: "${ANONYMIZATION_SALT}"
    examples: ["employee_id", "emp_id"]
```

### Step 5: Create Directory Structure

Ensure all required directories exist:

```bash
# Create data directories
mkdir -p data/staging
mkdir -p data/anonymized
mkdir -p data/loads
mkdir -p data/archive
mkdir -p data/analysis
mkdir -p data/manifests
mkdir -p data/reports

# Create logs directory
mkdir -p logs

# Create .gitkeep files to preserve empty directories
touch data/staging/.gitkeep
touch data/anonymized/.gitkeep
touch data/loads/.gitkeep
touch data/archive/.gitkeep
touch logs/.gitkeep

# Verify structure
tree data logs
```

---

## MCP Server Setup

### Testing Individual MCP Servers

Before running full migrations, test each MCP server independently.

#### Test PostgreSQL MCP Server

```bash
# Test PROD IDS connection
npx @modelcontextprotocol/server-postgres \
  "postgresql://readonly_user@prod-ids-rds.amazonaws.com:5432/ids_db" \
  --test

# If using custom credentials
PGPASSWORD="your-password" npx @modelcontextprotocol/server-postgres \
  "postgresql://readonly_user@prod-ids-rds.amazonaws.com:5432/ids_db" \
  --test
```

**Expected output:**
```
✓ Connected to PostgreSQL
✓ Database: ids_db
✓ User: readonly_user
✓ Schema introspection successful
✓ Test query executed successfully
```

**Repeat for all 8 PostgreSQL servers.**

#### Test Neo4j MCP Server

```bash
# Navigate to Neo4j MCP server directory
cd mcp-servers/neo4j

# Set environment variables
export NEO4J_URI="bolt://prod-graph-db.amazonaws.com:7687"
export NEO4J_USER="readonly"
export NEO4J_PASSWORD="your-neo4j-password"

# Run test
node index.js --test

# Expected output:
# ✓ Connected to Neo4j
# ✓ Database: neo4j
# ✓ Schema introspection successful
# ✓ Test query executed successfully
```

#### Test ETL MCP Server

```bash
# Navigate to ETL MCP server directory
cd mcp-servers/etl

# Set environment variables
export PROJECT_ROOT="/Users/colossus/development/datamig"
export PYTHON_BIN="/Users/colossus/development/datamig/venv/bin/python3"

# Run test
node index.js --test

# Expected output:
# ✓ ETL MCP Server initialized
# ✓ Python environment verified
# ✓ Project root verified
# ✓ Test script executed successfully
```

### Troubleshooting MCP Server Issues

**Problem: "Connection refused"**

```bash
# Check if database host is reachable
ping prod-ids-rds.amazonaws.com

# Check if port is open
nc -zv prod-ids-rds.amazonaws.com 5432

# Check firewall rules (if on VPN)
# Ensure your IP is whitelisted in database security groups
```

**Problem: "Authentication failed"**

```bash
# Verify credentials
cat .env | grep PROD_IDS_PASSWORD

# Test credentials directly with psql
PGPASSWORD="your-password" psql \
  -h prod-ids-rds.amazonaws.com \
  -U readonly_user \
  -d ids_db \
  -c "SELECT 1;"

# Expected: "1" returned
```

**Problem: "MCP server not found"**

```bash
# Verify global install
npm list -g @modelcontextprotocol/server-postgres

# Reinstall if missing
npm install -g @modelcontextprotocol/server-postgres
```

---

## Verification

### Step 1: Verify Environment

```bash
# Check all environment variables are set
source venv/bin/activate
python3 << EOF
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    'PROD_IDS_PASSWORD',
    'PROD_HCP1_PASSWORD',
    'PROD_HCP2_PASSWORD',
    'PROD_ADB_PASSWORD',
    'NEO4J_PROD_PASSWORD',
    'CERT_IDS_PASSWORD',
    'CERT_HCP1_PASSWORD',
    'CERT_HCP2_PASSWORD',
    'CERT_ADB_PASSWORD',
    'NEO4J_CERT_PASSWORD',
    'ANONYMIZATION_SALT'
]

missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print("❌ Missing environment variables:")
    for var in missing:
        print(f"   - {var}")
else:
    print("✅ All required environment variables are set")
EOF
```

### Step 2: Verify MCP Servers

```bash
# Start Claude Code
claude-code

# In Claude Code, check MCP server status
# You should see connection messages for each enabled server
```

**Expected output in Claude Code:**
```
✓ Connected to postgres-ids-prod
✓ Connected to postgres-hcp1-prod
✓ Connected to postgres-hcp2-prod
✓ Connected to postgres-adb-prod
✓ Connected to postgres-ids-cert
✓ Connected to postgres-hcp1-cert
✓ Connected to postgres-hcp2-cert
✓ Connected to postgres-adb-cert
✓ Connected to neo4j-prod
✓ Connected to neo4j-cert
✓ Connected to etl
```

### Step 3: Verify Skills and Commands

```bash
# List available skills
ls -1 .claude/skills/
# Expected: 7 skill directories

# List available commands
ls -1 .claude/commands/
# Expected: 5 command files

# List available agents
ls -1 .claude/agents/
# Expected: 4 files (3 agents + README)
```

### Step 4: Verify Python Scripts

```bash
# Activate venv
source venv/bin/activate

# Test schema analyzer
python3 scripts/schema-analyzer.py --help
# Should show usage information

# Test district analyzer
python3 scripts/district-analyzer.py --help
# Should show usage information
```

---

## First Run

### Test with Read-Only Operations

Start with safe, read-only operations to verify setup.

#### Test 1: Schema Analysis

```bash
# Start Claude Code
claude-code

# In Claude Code, run:
/analyze-datastores
```

**Expected behavior:**
- Connects to all PROD databases (read-only)
- Extracts schemas for all tables
- Builds FK dependency graph
- Generates extraction order
- Duration: ~30 minutes

**Expected outputs:**
- `data/analysis/schema-analysis.json`
- `data/analysis/dependency-graph.dot`
- `data/analysis/extraction-order.json`
- `data/analysis/README.md`

**Verification:**
```bash
# Check outputs exist
ls -lh data/analysis/

# Review schema analysis
cat data/analysis/README.md

# Count tables discovered
jq '.stores | map(.tables | length) | add' data/analysis/schema-analysis.json
# Should show total table count across all stores
```

#### Test 2: District Selection

```bash
# In Claude Code:
/select-districts
```

**Expected behavior:**
- Analyzes all districts in PROD
- Scores by size, activity, completeness, priority
- Recommends 3 pilot districts
- Duration: ~15 minutes

**Expected outputs:**
- `data/manifests/district-manifest.json`

**Verification:**
```bash
# Review manifest
cat data/manifests/district-manifest.json | jq '.districts[] | select(.pilot_recommendation != null)'

# Should show 3 pilot recommendations:
# - 1 small district
# - 1 medium district
# - 1 large district
```

#### Test 3: Dry-Run Migration (No CERT Changes)

```bash
# In Claude Code, run dry-run migration (no CERT writes):
/migrate district-small-001 --dry-run
```

**Expected behavior:**
- Extracts data from PROD (read-only)
- Anonymizes PII
- Validates data
- **SKIPS** loading to CERT
- Generates report
- Duration: ~2-3 hours for small district

**Expected outputs:**
- `data/staging/district-small-001/*.parquet`
- `data/anonymized/district-small-001/*.parquet`
- `data/reports/mig-{run_id}.md`

**Verification:**
```bash
# Check extraction worked
ls -lh data/staging/district-small-001/

# Check anonymization worked
ls -lh data/anonymized/district-small-001/

# Review report
cat data/reports/mig-*.md | head -50
```

### First Real Migration

Once dry-run succeeds, try a real migration with a small pilot district.

```bash
# In Claude Code:
/migrate district-small-001
```

**Expected behavior:**
- Full 5-phase pipeline
- Loads data to CERT
- Duration: ~2-3 hours

**Post-migration verification:**

```bash
# In Claude Code:
/validate-migration mig-{run_id}

# Then manually check CERT database
PGPASSWORD="${CERT_IDS_PASSWORD}" psql \
  -h cert-ids-rds.amazonaws.com \
  -U admin_user \
  -d ids_db \
  -c "SELECT COUNT(*) FROM students WHERE district_id = 'district-small-001';"

# Should return a count > 0
```

---

## Troubleshooting Setup Issues

### Issue: MCP servers won't connect

**Symptoms:**
- "Connection refused" errors
- Timeout errors
- Authentication failures

**Solutions:**

1. **Check network connectivity:**
```bash
ping prod-ids-rds.amazonaws.com
nc -zv prod-ids-rds.amazonaws.com 5432
```

2. **Verify credentials:**
```bash
# Test with psql directly
PGPASSWORD="your-password" psql -h prod-ids-rds.amazonaws.com -U readonly_user -d ids_db -c "SELECT 1;"
```

3. **Check firewall/security groups:**
- Ensure your IP is whitelisted
- Verify VPN is connected (if required)

4. **Verify MCP configuration:**
```bash
# Check for typos in .claude/mcp/servers.json
cat .claude/mcp/servers.json | jq '.mcpServers | keys'
```

### Issue: Python dependencies failing

**Symptoms:**
- `ModuleNotFoundError: No module named 'faker'`
- Import errors

**Solutions:**

1. **Ensure venv is activated:**
```bash
which python3
# Should show: /Users/colossus/development/datamig/venv/bin/python3
```

2. **Reinstall dependencies:**
```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Check Python version:**
```bash
python3 --version
# Must be 3.9 or later
```

### Issue: Disk space errors

**Symptoms:**
- "No space left on device"
- Parquet write failures

**Solutions:**

1. **Check disk space:**
```bash
df -h .
# Ensure at least 50GB free
```

2. **Clean up old migrations:**
```bash
# Remove old staging data (contains PII - be careful!)
rm -rf data/staging/district-*

# Remove old anonymized data
rm -rf data/anonymized/district-*

# Keep reports and manifests
```

3. **Move to larger disk:**
```bash
# Move project to disk with more space
mv /Users/colossus/development/datamig /Volumes/LargerDisk/datamig
cd /Volumes/LargerDisk/datamig
```

### Issue: Claude Code not finding skills/commands

**Symptoms:**
- "Command not found: /migrate"
- Skills not loading

**Solutions:**

1. **Verify directory structure:**
```bash
ls -la .claude/
# Should show: commands/, skills/, agents/, mcp/
```

2. **Check file permissions:**
```bash
chmod -R u+r .claude/
```

3. **Restart Claude Code:**
```bash
# Exit and restart
claude-code
```

### Issue: Permission denied errors

**Symptoms:**
- "Permission denied" when creating files
- "EACCES" errors

**Solutions:**

1. **Check directory ownership:**
```bash
ls -ld data/
# Should be owned by your user
```

2. **Fix permissions:**
```bash
sudo chown -R $USER:$USER data/ logs/
chmod -R u+rw data/ logs/
```

---

## Next Steps

Setup complete! Proceed to:

1. **[USER-GUIDE.md](./USER-GUIDE.md)** - Learn how to use the framework
2. **[AGENT-CAPABILITIES.md](./AGENT-CAPABILITIES.md)** - Understand agent capabilities
3. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Solve runtime issues

**Ready to begin migrations!**

```bash
claude-code

# Inside Claude Code:
/analyze-datastores
/select-districts
/migrate district-001
```
