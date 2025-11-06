#!/usr/bin/env node

/**
 * Neo4j MCP Server
 *
 * Provides Model Context Protocol interface for Neo4j graph database.
 * Supports Cypher query execution and graph traversal operations.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import neo4j from 'neo4j-driver';

// Validate required environment variables
const requiredEnvVars = ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD'];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    console.error(`Error: ${envVar} environment variable is required`);
    process.exit(1);
  }
}

// Initialize Neo4j driver
const driver = neo4j.driver(
  process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASSWORD),
  {
    maxConnectionLifetime: 3 * 60 * 60 * 1000, // 3 hours
    maxConnectionPoolSize: 50,
    connectionAcquisitionTimeout: 2 * 60 * 1000, // 2 minutes
  }
);

// Test connection on startup
async function testConnection() {
  const session = driver.session();
  try {
    const result = await session.run('RETURN 1 AS test');
    console.error('Neo4j MCP Server: Connection successful');
    return true;
  } catch (error) {
    console.error('Neo4j MCP Server: Connection failed:', error.message);
    return false;
  } finally {
    await session.close();
  }
}

// Create MCP server instance
const server = new Server(
  {
    name: 'neo4j-mcp-server',
    version: '1.0.0',
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
        name: 'query_neo4j',
        description: 'Execute a Cypher query on the Neo4j graph database',
        inputSchema: {
          type: 'object',
          properties: {
            cypher: {
              type: 'string',
              description: 'The Cypher query to execute',
            },
            parameters: {
              type: 'object',
              description: 'Parameters for the Cypher query (optional)',
              additionalProperties: true,
            },
            limit: {
              type: 'number',
              description: 'Maximum number of records to return (default: 1000)',
              default: 1000,
            },
          },
          required: ['cypher'],
        },
      },
      {
        name: 'get_schema',
        description: 'Get the Neo4j database schema (node labels, relationship types, properties)',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'traverse_from_node',
        description: 'Traverse the graph starting from a specific node',
        inputSchema: {
          type: 'object',
          properties: {
            node_label: {
              type: 'string',
              description: 'The label of the starting node (e.g., "District")',
            },
            node_property: {
              type: 'string',
              description: 'Property to match (e.g., "id")',
            },
            node_value: {
              type: 'string',
              description: 'Value of the property to match',
            },
            max_depth: {
              type: 'number',
              description: 'Maximum depth to traverse (default: 3)',
              default: 3,
            },
          },
          required: ['node_label', 'node_property', 'node_value'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'query_neo4j':
        return await handleQueryNeo4j(args);

      case 'get_schema':
        return await handleGetSchema();

      case 'traverse_from_node':
        return await handleTraverseFromNode(args);

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}\nStack: ${error.stack}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Execute a Cypher query
 */
async function handleQueryNeo4j(args) {
  const { cypher, parameters = {}, limit = 1000 } = args;

  const session = driver.session();
  try {
    // Add LIMIT if not present in query
    const finalQuery = cypher.toUpperCase().includes('LIMIT')
      ? cypher
      : `${cypher} LIMIT ${limit}`;

    const result = await session.run(finalQuery, parameters);

    const records = result.records.map((record) => {
      const obj = {};
      record.keys.forEach((key) => {
        const value = record.get(key);
        // Convert Neo4j types to plain JavaScript objects
        obj[key] = convertNeo4jValue(value);
      });
      return obj;
    });

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            records,
            summary: {
              query: finalQuery,
              parameters,
              recordCount: records.length,
              availableAfter: result.summary.resultAvailableAfter?.toNumber() || 0,
              consumedAfter: result.summary.resultConsumedAfter?.toNumber() || 0,
            },
          }, null, 2),
        },
      ],
    };
  } finally {
    await session.close();
  }
}

/**
 * Get database schema
 */
async function handleGetSchema() {
  const session = driver.session();
  try {
    // Get node labels
    const labelsResult = await session.run('CALL db.labels()');
    const labels = labelsResult.records.map(r => r.get('label'));

    // Get relationship types
    const relsResult = await session.run('CALL db.relationshipTypes()');
    const relationshipTypes = relsResult.records.map(r => r.get('relationshipType'));

    // Get property keys
    const propsResult = await session.run('CALL db.propertyKeys()');
    const propertyKeys = propsResult.records.map(r => r.get('propertyKey'));

    // Get constraints
    const constraintsResult = await session.run('SHOW CONSTRAINTS');
    const constraints = constraintsResult.records.map(r => convertNeo4jValue(r.toObject()));

    // Get indexes
    const indexesResult = await session.run('SHOW INDEXES');
    const indexes = indexesResult.records.map(r => convertNeo4jValue(r.toObject()));

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            labels,
            relationshipTypes,
            propertyKeys,
            constraints,
            indexes,
          }, null, 2),
        },
      ],
    };
  } finally {
    await session.close();
  }
}

/**
 * Traverse graph from a starting node
 */
async function handleTraverseFromNode(args) {
  const { node_label, node_property, node_value, max_depth = 3 } = args;

  const session = driver.session();
  try {
    const query = `
      MATCH path = (start:${node_label} {${node_property}: $value})-[*1..${max_depth}]-(connected)
      RETURN start, connected, relationships(path) as rels, length(path) as depth
      LIMIT 1000
    `;

    const result = await session.run(query, { value: node_value });

    const paths = result.records.map((record) => ({
      start: convertNeo4jValue(record.get('start')),
      connected: convertNeo4jValue(record.get('connected')),
      relationships: convertNeo4jValue(record.get('rels')),
      depth: record.get('depth').toNumber(),
    }));

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            startNode: {
              label: node_label,
              property: node_property,
              value: node_value,
            },
            maxDepth: max_depth,
            pathsFound: paths.length,
            paths,
          }, null, 2),
        },
      ],
    };
  } finally {
    await session.close();
  }
}

/**
 * Convert Neo4j values to plain JavaScript objects
 */
function convertNeo4jValue(value) {
  if (value === null || value === undefined) {
    return null;
  }

  // Handle Neo4j Integer
  if (neo4j.isInt(value)) {
    return value.toNumber();
  }

  // Handle Neo4j Node
  if (value.labels !== undefined) {
    return {
      id: value.identity.toNumber(),
      labels: value.labels,
      properties: value.properties,
    };
  }

  // Handle Neo4j Relationship
  if (value.type !== undefined && value.start !== undefined) {
    return {
      id: value.identity.toNumber(),
      type: value.type,
      start: value.start.toNumber(),
      end: value.end.toNumber(),
      properties: value.properties,
    };
  }

  // Handle Arrays
  if (Array.isArray(value)) {
    return value.map(convertNeo4jValue);
  }

  // Handle Objects
  if (typeof value === 'object') {
    const converted = {};
    for (const [key, val] of Object.entries(value)) {
      converted[key] = convertNeo4jValue(val);
    }
    return converted;
  }

  return value;
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.error('Neo4j MCP Server: Shutting down...');
  await driver.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.error('Neo4j MCP Server: Shutting down...');
  await driver.close();
  process.exit(0);
});

// Start server
async function main() {
  const connected = await testConnection();
  if (!connected) {
    console.error('Neo4j MCP Server: Failed to connect to Neo4j. Exiting.');
    process.exit(1);
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Neo4j MCP Server: Started successfully');
}

main().catch((error) => {
  console.error('Neo4j MCP Server: Fatal error:', error);
  process.exit(1);
});
