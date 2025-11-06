#!/usr/bin/env node

/**
 * ETL MCP Server
 *
 * Provides high-level ETL operations for data migration:
 * - Extract data with relationship resolution
 * - Anonymize datasets
 * - Validate referential integrity
 * - Load data with constraint management
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { spawn } from 'child_process';
import { promisify } from 'util';
import { readFile } from 'fs/promises';
import path from 'path';

// Get project root directory
const PROJECT_ROOT = process.env.PROJECT_ROOT || process.cwd();

// Create MCP server instance
const server = new Server(
  {
    name: 'etl-mcp-server',
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
        name: 'extract_with_relationships',
        description: 'Extract data from source with relationship resolution and topological ordering',
        inputSchema: {
          type: 'object',
          properties: {
            source_config: {
              type: 'object',
              description: 'Source database configuration',
              properties: {
                store: { type: 'string', description: 'Data store name (ids, hcp1, hcp2, adb, sp)' },
                connection: { type: 'string', description: 'Connection string or identifier' },
              },
              required: ['store'],
            },
            filter: {
              type: 'object',
              description: 'Filter criteria (e.g., district_id)',
              additionalProperties: true,
            },
            extraction_order: {
              type: 'array',
              description: 'Topologically sorted list of tables to extract',
              items: { type: 'string' },
            },
            output_dir: {
              type: 'string',
              description: 'Directory to write extracted data',
            },
          },
          required: ['source_config', 'filter', 'output_dir'],
        },
      },
      {
        name: 'anonymize_dataset',
        description: 'Anonymize PII in extracted dataset using configured rules',
        inputSchema: {
          type: 'object',
          properties: {
            input_dir: {
              type: 'string',
              description: 'Directory containing extracted data',
            },
            output_dir: {
              type: 'string',
              description: 'Directory to write anonymized data',
            },
            rules_file: {
              type: 'string',
              description: 'Path to anonymization rules YAML file',
            },
            consistency_map: {
              type: 'string',
              description: 'Path to consistency map for preserving FK relationships',
            },
          },
          required: ['input_dir', 'output_dir'],
        },
      },
      {
        name: 'validate_referential_integrity',
        description: 'Validate referential integrity and data quality of anonymized dataset',
        inputSchema: {
          type: 'object',
          properties: {
            data_dir: {
              type: 'string',
              description: 'Directory containing data to validate',
            },
            schema_file: {
              type: 'string',
              description: 'Path to schema definition file',
            },
            validation_rules: {
              type: 'string',
              description: 'Path to validation rules file',
            },
            output_report: {
              type: 'string',
              description: 'Path to write validation report',
            },
          },
          required: ['data_dir'],
        },
      },
      {
        name: 'load_with_constraints',
        description: 'Load data to target database with constraint management and transaction safety',
        inputSchema: {
          type: 'object',
          properties: {
            input_dir: {
              type: 'string',
              description: 'Directory containing data to load',
            },
            target_config: {
              type: 'object',
              description: 'Target database configuration',
              properties: {
                store: { type: 'string', description: 'Data store name (ids, hcp1, hcp2, adb, sp)' },
                connection: { type: 'string', description: 'Connection string or identifier' },
              },
              required: ['store'],
            },
            loading_order: {
              type: 'array',
              description: 'Topologically sorted list of tables to load',
              items: { type: 'string' },
            },
            strategy: {
              type: 'string',
              enum: ['insert', 'upsert', 'merge'],
              description: 'Loading strategy (default: insert)',
              default: 'insert',
            },
          },
          required: ['input_dir', 'target_config'],
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
      case 'extract_with_relationships':
        return await handleExtractWithRelationships(args);

      case 'anonymize_dataset':
        return await handleAnonymizeDataset(args);

      case 'validate_referential_integrity':
        return await handleValidateIntegrity(args);

      case 'load_with_constraints':
        return await handleLoadWithConstraints(args);

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
 * Extract data with relationship resolution
 */
async function handleExtractWithRelationships(args) {
  const { source_config, filter, extraction_order, output_dir } = args;

  // Call Python extraction script
  const scriptPath = path.join(PROJECT_ROOT, 'scripts', 'extractors', 'extract_with_relationships.py');

  const result = await runPythonScript(scriptPath, {
    source_config,
    filter,
    extraction_order,
    output_dir,
  });

  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}

/**
 * Anonymize dataset
 */
async function handleAnonymizeDataset(args) {
  const {
    input_dir,
    output_dir,
    rules_file = path.join(PROJECT_ROOT, 'config', 'anonymization-rules.yaml'),
    consistency_map = path.join(output_dir, 'consistency-map.encrypted'),
  } = args;

  // Call Python anonymization script
  const scriptPath = path.join(PROJECT_ROOT, 'scripts', 'anonymize.py');

  const result = await runPythonScript(scriptPath, {
    input_dir,
    output_dir,
    rules_file,
    consistency_map,
  });

  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}

/**
 * Validate referential integrity
 */
async function handleValidateIntegrity(args) {
  const {
    data_dir,
    schema_file = path.join(PROJECT_ROOT, 'data', 'analysis', 'schema-analysis.json'),
    validation_rules = path.join(PROJECT_ROOT, 'config', 'validation-rules.yaml'),
    output_report = path.join(data_dir, 'validation-report.json'),
  } = args;

  // Call Python validation script
  const scriptPath = path.join(PROJECT_ROOT, 'scripts', 'validators', 'validate_integrity.py');

  const result = await runPythonScript(scriptPath, {
    data_dir,
    schema_file,
    validation_rules,
    output_report,
  });

  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}

/**
 * Load data with constraints
 */
async function handleLoadWithConstraints(args) {
  const {
    input_dir,
    target_config,
    loading_order,
    strategy = 'insert',
  } = args;

  // Call Python loading script
  const scriptPath = path.join(PROJECT_ROOT, 'scripts', 'loaders', 'load_with_constraints.py');

  const result = await runPythonScript(scriptPath, {
    input_dir,
    target_config,
    loading_order,
    strategy,
  });

  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}

/**
 * Run a Python script with JSON input/output
 */
async function runPythonScript(scriptPath, inputData) {
  return new Promise((resolve, reject) => {
    const python = spawn('python3', [scriptPath], {
      cwd: PROJECT_ROOT,
    });

    let stdout = '';
    let stderr = '';

    // Send input data as JSON to stdin
    python.stdin.write(JSON.stringify(inputData));
    python.stdin.end();

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python script exited with code ${code}\nstderr: ${stderr}`));
      } else {
        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (error) {
          reject(new Error(`Failed to parse Python script output: ${error.message}\nOutput: ${stdout}`));
        }
      }
    });

    python.on('error', (error) => {
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.error('ETL MCP Server: Shutting down...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.error('ETL MCP Server: Shutting down...');
  process.exit(0);
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('ETL MCP Server: Started successfully');
}

main().catch((error) => {
  console.error('ETL MCP Server: Fatal error:', error);
  process.exit(1);
});
