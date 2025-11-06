# Agent Templates

This directory contains templates for spawning specialized subagents using the Task tool.

## Available Agents

### 1. Discovery Agent (`discovery-agent.md`)
- **Purpose**: Analyze data stores and map schemas/relationships
- **When to use**: Before first migration or when schema changes
- **Duration**: ~30 minutes
- **Usage**:
  ```
  Use Task tool with subagent_type="Explore" and prompt from discovery-agent.md
  ```

### 2. Extraction Agent (`extraction-agent.md`)
- **Purpose**: Extract district data maintaining FK integrity
- **When to use**: During extraction phase of migration
- **Duration**: 1-3 hours per district
- **Usage**:
  ```
  Use Task tool with subagent_type="general-purpose" and prompt from extraction-agent.md
  ```

### 3. Orchestrator Agent (`orchestrator-agent.md`)
- **Purpose**: Coordinate entire end-to-end migration pipeline
- **When to use**: For full autonomous migrations
- **Duration**: 4-8 hours per district
- **Usage**:
  ```
  Spawned automatically by /migrate command
  ```

## How Agents Work

Agents are autonomous subprocesses that:
1. Receive a detailed mission/prompt
2. Execute independently using available tools (MCP servers, skills, scripts)
3. Report back results when complete
4. Cannot be interrupted mid-execution

## Agent Communication

- **Parent → Agent**: Via Task tool prompt (one-way, at spawn time)
- **Agent → Parent**: Via final report (one-way, at completion)
- **No real-time interaction**: Agents execute autonomously

## Best Practices

1. **Detailed Prompts**: Agents need comprehensive instructions upfront
2. **Clear Success Criteria**: Define what "done" looks like
3. **Error Handling**: Agents should handle errors gracefully
4. **Progress Tracking**: Use TodoWrite within agent for visibility
5. **Resource Limits**: Consider timeout and resource constraints

## When to Use Agents vs Skills

**Use Skills**: For discrete, reusable operations (anonymize, validate, etc.)
**Use Agents**: For complex workflows requiring decision-making and orchestration

## Template Structure

Each agent template contains:
- Mission statement
- Input parameters
- Autonomous execution plan
- Tools available
- Success criteria
- Error handling instructions
- Expected duration
