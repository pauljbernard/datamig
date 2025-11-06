# MCP Server Configuration

This directory contains the Model Context Protocol (MCP) server configuration for the data migration project.

## Overview

The migration project uses 11 MCP servers:
- **4 PostgreSQL servers for PROD** (IDS, HCP1, HCP2, ADB) - Read-only access
- **4 PostgreSQL servers for CERT** (IDS, HCP1, HCP2, ADB) - Read/Write access
- **1 Neo4j server for PROD** (SP Graph DB) - Read-only access
- **1 Neo4j server for CERT** (SP Graph DB) - Read/Write access
- **1 Custom ETL server** - Data processing operations

## Setup Instructions

### 1. Install PostgreSQL MCP Server

```bash
npm install -g @modelcontextprotocol/server-postgres
```

### 2. Set Environment Variables

Create a `.env` file in the project root with your database credentials:

```bash
# PROD Database Passwords (Read-Only)
export PROD_IDS_PASSWORD="your-prod-ids-password"
export PROD_HCP1_PASSWORD="your-prod-hcp1-password"
export PROD_HCP2_PASSWORD="your-prod-hcp2-password"
export PROD_ADB_PASSWORD="your-prod-adb-password"
export NEO4J_PROD_PASSWORD="your-neo4j-prod-password"

# CERT Database Passwords (Read/Write)
export CERT_IDS_PASSWORD="your-cert-ids-password"
export CERT_HCP1_PASSWORD="your-cert-hcp1-password"
export CERT_HCP2_PASSWORD="your-cert-hcp2-password"
export CERT_ADB_PASSWORD="your-cert-adb-password"
export NEO4J_CERT_PASSWORD="your-neo4j-cert-password"
```

### 3. Update Connection Strings

Edit `servers.json` and replace the placeholder connection strings with your actual:
- RDS endpoints
- Database names
- Usernames

### 4. Build Custom MCP Servers

```bash
# Build Neo4j MCP server
cd mcp-servers/neo4j
npm install
npm run build

# Build ETL MCP server
cd ../etl
npm install
npm run build
```

### 5. Enable Servers

Once configured, change `"disabled": true` to `"disabled": false` for the servers you want to enable.

### 6. Test Connection

Restart Claude Code and verify MCP servers are connected:
```bash
claude
> [Check that MCP tools are available]
```

## Security Notes

- **NEVER commit `.env` file or credentials to git**
- Use read-only credentials for PROD databases
- Ensure PROD credentials cannot write/modify data
- Use AWS Secrets Manager for production deployments
- Rotate credentials regularly

## Troubleshooting

### MCP Server Not Connecting

1. Check environment variables are set: `echo $PROD_IDS_PASSWORD`
2. Verify database is accessible from your network
3. Check Claude Code logs: `~/.claude/logs/`
4. Test connection manually: `psql -h prod-ids-rds.amazonaws.com -U readonly_user -d ids_db`

### Permission Errors

- Ensure PROD users have SELECT permission only
- Ensure CERT users have INSERT/UPDATE/DELETE permissions
- Check database firewall rules allow your IP

## MCP Server Status

| Server | Type | Purpose | Status |
|--------|------|---------|--------|
| postgres-ids-prod | PostgreSQL | PROD IDS data store | ⏸️ Disabled |
| postgres-hcp1-prod | PostgreSQL | PROD HCP1 data store | ⏸️ Disabled |
| postgres-hcp2-prod | PostgreSQL | PROD HCP2 data store | ⏸️ Disabled |
| postgres-adb-prod | PostgreSQL | PROD ADB data store | ⏸️ Disabled |
| neo4j-sp-prod | Neo4j | PROD SP graph database | ⏸️ Disabled |
| postgres-ids-cert | PostgreSQL | CERT IDS data store | ⏸️ Disabled |
| postgres-hcp1-cert | PostgreSQL | CERT HCP1 data store | ⏸️ Disabled |
| postgres-hcp2-cert | PostgreSQL | CERT HCP2 data store | ⏸️ Disabled |
| postgres-adb-cert | PostgreSQL | CERT ADB data store | ⏸️ Disabled |
| neo4j-sp-cert | Neo4j | CERT SP graph database | ⏸️ Disabled |
| etl-server | Custom | ETL operations | ⏸️ Disabled |

Update this table as servers are configured and enabled.
