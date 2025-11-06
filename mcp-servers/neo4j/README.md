# Neo4j MCP Server

Custom MCP server for Neo4j graph database connectivity. Provides Cypher query execution, schema introspection, and graph traversal capabilities.

## Features

- **Cypher Query Execution**: Execute arbitrary Cypher queries with parameters
- **Schema Introspection**: Get database schema (labels, relationships, properties, constraints, indexes)
- **Graph Traversal**: Traverse from a starting node with configurable depth
- **Connection Pooling**: Efficient connection management
- **Error Handling**: Graceful error handling and reporting

## Installation

```bash
cd mcp-servers/neo4j
npm install
```

## Configuration

Set the following environment variables:

```bash
export NEO4J_URI="bolt://your-neo4j-host:7687"
export NEO4J_USER="your-username"
export NEO4J_PASSWORD="your-password"
```

## Testing

Test the server standalone:

```bash
node index.js
```

The server will test the connection on startup and report success/failure.

## Tools Provided

### 1. `query_neo4j`

Execute a Cypher query on the Neo4j database.

**Input Schema**:
```json
{
  "cypher": "MATCH (n:District {id: $districtId}) RETURN n",
  "parameters": {
    "districtId": "district-001"
  },
  "limit": 1000
}
```

**Output**: JSON array of records with query summary statistics.

### 2. `get_schema`

Retrieve the complete database schema.

**Input Schema**: None required

**Output**: JSON object containing:
- `labels`: All node labels in the database
- `relationshipTypes`: All relationship types
- `propertyKeys`: All property keys used
- `constraints`: Database constraints
- `indexes`: Database indexes

### 3. `traverse_from_node`

Traverse the graph starting from a specific node.

**Input Schema**:
```json
{
  "node_label": "District",
  "node_property": "id",
  "node_value": "district-001",
  "max_depth": 3
}
```

**Output**: JSON array of paths from the starting node up to max_depth.

## Usage in Claude Code

Once configured in `.claude/mcp/servers.json`, Claude Code can use this server:

```
Human: Get the schema of the Neo4j database

Claude: [Uses get_schema tool via MCP]
```

```
Human: Find all nodes connected to district-001 within 2 hops

Claude: [Uses traverse_from_node tool with max_depth=2]
```

## Error Handling

- Connection errors are logged to stderr
- Query errors include full stack traces for debugging
- Graceful shutdown on SIGINT/SIGTERM

## Performance

- Connection pool size: 50
- Connection lifetime: 3 hours
- Acquisition timeout: 2 minutes
- Default query limit: 1000 records (configurable)

## Security

- Always use read-only credentials for PROD
- Use write credentials only for CERT
- Never commit credentials to version control
- Rotate passwords regularly
