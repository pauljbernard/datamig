# Documentation Index

Welcome to the Data Migration Framework documentation. This page helps you find the right guide for your needs.

## Quick Navigation

### 👤 I'm a User (I want to run migrations)
→ Start with **[User Guide](USER-GUIDE.md)**

### 💻 I'm a Developer (I want to extend/modify the framework)
→ Start with **[Developer Guide](DEVELOPER-GUIDE.md)**

### 🔧 I'm Setting Up (First time configuration)
→ Start with **[Setup Guide](SETUP.md)**

### 🐛 Something Went Wrong (Troubleshooting)
→ Start with **[Troubleshooting Guide](TROUBLESHOOTING.md)**

### 🤖 I Want to Use GitHub (Issue-based execution)
→ Start with **[GitHub Workflows Guide](GITHUB-WORKFLOWS.md)**

### 🧠 I Want to Understand How It Works (Architecture deep dive)
→ Start with **[Agent Capabilities](AGENT-CAPABILITIES.md)**

---

## Documentation Structure

### Core Guides

| Guide | Audience | When to Use | Length |
|-------|----------|-------------|--------|
| **[User Guide](USER-GUIDE.md)** | End users, operators | Running migrations, monitoring progress, understanding workflows | ~1,200 lines |
| **[Developer Guide](DEVELOPER-GUIDE.md)** | Developers, contributors | Extending framework, writing code, debugging | ~1,000 lines |
| **[Setup Guide](SETUP.md)** | Everyone | Initial configuration, environment setup, verification | ~1,200 lines |

### Specialized Guides

| Guide | Audience | When to Use | Length |
|-------|----------|-------------|--------|
| **[GitHub Workflows](GITHUB-WORKFLOWS.md)** | Users, DevOps | Executing migrations via GitHub issues, CI/CD setup | ~640 lines |
| **[Troubleshooting](TROUBLESHOOTING.md)** | Everyone | Debugging issues, error resolution, recovery procedures | ~1,240 lines |
| **[Agent Capabilities](AGENT-CAPABILITIES.md)** | Advanced users, developers | Understanding architecture, extending capabilities | ~1,260 lines |

---

## Documentation by Task

### Getting Started

**First time user?**
1. Read [Setup Guide](SETUP.md) - Configure your environment
2. Read [User Guide - Quick Start](USER-GUIDE.md#quick-start) - Run your first migration
3. Read [User Guide - Monitoring](USER-GUIDE.md#monitoring-progress) - Track progress

**First time developer?**
1. Read [Developer Guide - Setup](DEVELOPER-GUIDE.md#development-environment-setup) - Set up dev environment
2. Read [Developer Guide - Code Organization](DEVELOPER-GUIDE.md#code-organization) - Understand structure
3. Read [Developer Guide - Extending](DEVELOPER-GUIDE.md#extending-the-framework) - Add your first feature

### Common Tasks

**Running Migrations**
- **Via Claude Code**: [User Guide - Step-by-Step Usage](USER-GUIDE.md#step-by-step-usage)
- **Via GitHub**: [GitHub Workflows - Creating Requests](GITHUB-WORKFLOWS.md#creating-migration-requests)

**Monitoring & Validation**
- **Real-time progress**: [User Guide - Monitoring Progress](USER-GUIDE.md#monitoring-progress)
- **Reviewing outputs**: [User Guide - Understanding Outputs](USER-GUIDE.md#understanding-outputs)
- **Validating results**: [User Guide - Phase 2: Validate](USER-GUIDE.md#phase-2-validate-the-migration)

**Troubleshooting**
- **Connection issues**: [Troubleshooting - Connection Issues](TROUBLESHOOTING.md#connection-issues)
- **Extraction failures**: [Troubleshooting - Extraction Issues](TROUBLESHOOTING.md#extraction-issues)
- **Validation errors**: [Troubleshooting - Validation Issues](TROUBLESHOOTING.md#validation-issues)
- **Performance problems**: [Troubleshooting - Performance Issues](TROUBLESHOOTING.md#performance-issues)

**Extending the Framework**
- **Adding skills**: [Developer Guide - Adding New Skill](DEVELOPER-GUIDE.md#adding-a-new-skill)
- **Adding commands**: [Developer Guide - Adding New Command](DEVELOPER-GUIDE.md#adding-a-new-command)
- **Adding validation rules**: [Developer Guide - Validation Rules](DEVELOPER-GUIDE.md#adding-new-validation-rules)
- **Adding MCP servers**: [Developer Guide - MCP Server Development](DEVELOPER-GUIDE.md#mcp-server-development)

---

## Documentation by Role

### End User / Operator

**What you need to know:**
1. How to run migrations
2. How to monitor progress
3. How to interpret results
4. What to do if something fails

**Your reading path:**
1. [Setup Guide](SETUP.md) - One time: Configure environment
2. [User Guide](USER-GUIDE.md) - Essential: Learn all workflows
3. [Troubleshooting Guide](TROUBLESHOOTING.md) - Reference: When issues occur
4. [GitHub Workflows Guide](GITHUB-WORKFLOWS.md) - Optional: If using GitHub integration

**Estimated reading time:** 2-3 hours

### Developer / Contributor

**What you need to know:**
1. Architecture and design patterns
2. Code organization
3. How to extend the framework
4. Testing and debugging strategies
5. Contributing process

**Your reading path:**
1. [Setup Guide](SETUP.md) - One time: Dev environment setup
2. [Developer Guide](DEVELOPER-GUIDE.md) - Essential: Architecture, extending, testing
3. [Agent Capabilities](AGENT-CAPABILITIES.md) - Deep dive: How autonomous execution works
4. [User Guide](USER-GUIDE.md) - Reference: Understand user workflows
5. [Troubleshooting Guide](TROUBLESHOOTING.md) - Reference: Debugging

**Estimated reading time:** 4-6 hours

### DevOps / Platform Engineer

**What you need to know:**
1. CI/CD integration
2. GitHub Actions workflows
3. Secret management
4. Infrastructure requirements
5. Monitoring and alerting

**Your reading path:**
1. [Setup Guide](SETUP.md) - Infrastructure requirements
2. [GitHub Workflows Guide](GITHUB-WORKFLOWS.md) - Essential: CI/CD setup
3. [User Guide](USER-GUIDE.md) - Understanding workflows
4. [Troubleshooting Guide](TROUBLESHOOTING.md) - Operations issues

**Estimated reading time:** 2-3 hours

### Architect / Technical Lead

**What you need to know:**
1. System architecture
2. Design decisions
3. Scalability considerations
4. Integration points
5. Extension capabilities

**Your reading path:**
1. [Agent Capabilities](AGENT-CAPABILITIES.md) - Essential: Architecture deep dive
2. [Developer Guide](DEVELOPER-GUIDE.md) - Technical details
3. [User Guide](USER-GUIDE.md) - Operational workflows
4. [GitHub Workflows Guide](GITHUB-WORKFLOWS.md) - Automation capabilities

**Estimated reading time:** 3-4 hours

---

## Reference Documentation

### Configuration Files

| File | Purpose | Documentation |
|------|---------|---------------|
| `.env` | Database credentials, secrets | [Setup Guide - Environment Variables](SETUP.md#step-3-configure-environment-variables) |
| `config/anonymization-rules.yaml` | PII anonymization rules | [Developer Guide - Anonymization Rules](DEVELOPER-GUIDE.md#adding-new-anonymization-rules) |
| `config/validation-rules.yaml` | Data validation rules | [Developer Guide - Validation Rules](DEVELOPER-GUIDE.md#adding-new-validation-rules) |
| `.claude/mcp/servers.json` | MCP server connections | [Setup Guide - MCP Servers](SETUP.md#step-4-enable-mcp-servers) |

### Extension Points

| Extension | Location | Documentation |
|-----------|----------|---------------|
| Skills | `.claude/skills/*/skill.md` | [Developer Guide - Adding Skills](DEVELOPER-GUIDE.md#adding-a-new-skill) |
| Commands | `.claude/commands/*.md` | [Developer Guide - Adding Commands](DEVELOPER-GUIDE.md#adding-a-new-command) |
| Agents | `.claude/agents/*.md` | [Agent Capabilities - Agent Templates](AGENT-CAPABILITIES.md#agent-templates) |
| MCP Servers | `mcp-servers/*/index.js` | [Developer Guide - MCP Servers](DEVELOPER-GUIDE.md#mcp-server-development) |
| Python Scripts | `scripts/*.py` | [Developer Guide - Python Development](DEVELOPER-GUIDE.md#python-scripts-development) |

### Command Reference

| Command | Purpose | Documentation |
|---------|---------|---------------|
| `/analyze-datastores` | Analyze PROD schema | [User Guide - Command Reference](USER-GUIDE.md#analyze-datastores) |
| `/select-districts` | Choose districts to migrate | [User Guide - Command Reference](USER-GUIDE.md#select-districts) |
| `/migrate <district>` | Execute autonomous migration | [User Guide - Command Reference](USER-GUIDE.md#migrate-district-id) |
| `/validate-migration <run-id>` | Validate completed migration | [User Guide - Command Reference](USER-GUIDE.md#validate-migration-run-id) |
| `/rollback <run-id>` | Rollback migration | [User Guide - Command Reference](USER-GUIDE.md#rollback-run-id) |

---

## Learning Paths

### Path 1: "I Just Want to Run Migrations"

**Time: ~1 hour**

1. [Setup Guide - Quick Start](SETUP.md#quick-start) (15 min)
2. [User Guide - Quick Start](USER-GUIDE.md#quick-start) (10 min)
3. [User Guide - Step-by-Step Usage](USER-GUIDE.md#step-by-step-usage) (20 min)
4. [User Guide - Monitoring Progress](USER-GUIDE.md#monitoring-progress) (15 min)

**Outcome:** Can successfully run and monitor migrations

### Path 2: "I Want to Understand Everything"

**Time: ~3 hours**

1. [Agent Capabilities - Overview](AGENT-CAPABILITIES.md#overview) (20 min)
2. [Agent Capabilities - Architecture](AGENT-CAPABILITIES.md#architecture) (30 min)
3. [Agent Capabilities - Autonomous Capabilities](AGENT-CAPABILITIES.md#autonomous-capabilities) (30 min)
4. [User Guide - Complete](USER-GUIDE.md) (60 min)
5. [Developer Guide - Architecture](DEVELOPER-GUIDE.md#architecture-overview) (30 min)

**Outcome:** Deep understanding of how autonomous execution works

### Path 3: "I Want to Extend the Framework"

**Time: ~2 hours**

1. [Developer Guide - Code Organization](DEVELOPER-GUIDE.md#code-organization) (20 min)
2. [Developer Guide - Development Setup](DEVELOPER-GUIDE.md#development-environment-setup) (30 min)
3. [Developer Guide - Extending Framework](DEVELOPER-GUIDE.md#extending-the-framework) (40 min)
4. [Agent Capabilities - Extension Points](AGENT-CAPABILITIES.md#extension-points) (30 min)

**Outcome:** Can add new skills, commands, and validation rules

### Path 4: "I'm Troubleshooting an Issue"

**Time: ~30 min**

1. [Troubleshooting - Find your issue category](TROUBLESHOOTING.md) (10 min)
2. [Troubleshooting - Follow resolution steps](TROUBLESHOOTING.md) (15 min)
3. [User Guide - Understanding Outputs](USER-GUIDE.md#understanding-outputs) (5 min - to review logs)

**Outcome:** Issue resolved or clear escalation path

---

## FAQ About Documentation

**Q: Where do I start if I'm completely new?**

A: Start with [User Guide - Quick Start](USER-GUIDE.md#quick-start). It's a 10-minute intro that gets you running your first migration.

**Q: I'm a developer. Which docs are essential?**

A: [Developer Guide](DEVELOPER-GUIDE.md) is essential. [Agent Capabilities](AGENT-CAPABILITIES.md) is highly recommended for understanding architecture.

**Q: How do I find documentation for a specific error?**

A: Use the [Troubleshooting Guide](TROUBLESHOOTING.md). It's organized by error category (connection, extraction, validation, etc.).

**Q: Is there a cheat sheet or quick reference?**

A: Yes, see [User Guide - Command Reference](USER-GUIDE.md#command-reference) for all commands and [User Guide - Common Workflows](USER-GUIDE.md#common-workflows) for step-by-step recipes.

**Q: Where are configuration file formats documented?**

A: See the [Reference Documentation](#reference-documentation) section above or [Setup Guide - Configuration](SETUP.md#step-3-configure-environment-variables).

**Q: How do I contribute to documentation?**

A: See [Developer Guide - Contributing Guidelines](DEVELOPER-GUIDE.md#contributing-guidelines). Documentation changes follow the same PR process as code.

**Q: Are there code examples?**

A: Yes, throughout the docs. See especially [Developer Guide - Script Template](DEVELOPER-GUIDE.md#script-template) and [Developer Guide - MCP Server Template](DEVELOPER-GUIDE.md#mcp-server-template).

**Q: Where's the API reference?**

A: Python scripts use argparse (see `--help` for each script). MCP servers expose tools (see [Agent Capabilities - MCP Integration](AGENT-CAPABILITIES.md#mcp-server-integration)).

---

## Documentation Conventions

### Notation

- `code blocks`: File paths, commands, code
- **Bold**: Important concepts, emphasis
- *Italics*: Placeholders (e.g., *your-district-id*)
- → Arrow: "Go to" or "Start with"
- ✅ Checkmark: Completed items
- ⚠️ Warning: Important cautions
- 📝 Note: Additional information

### Code Block Languages

````markdown
```bash
# Shell commands
```

```python
# Python code
```

```javascript
# JavaScript code
```

```yaml
# YAML configuration
```

```json
# JSON configuration
```
````

### Cross-References

Links to other docs use relative paths:
- `[Setup Guide](SETUP.md)`
- `[User Guide - Section](USER-GUIDE.md#section)`

---

## Getting Help

### Documentation Issues

**Found an error or gap in documentation?**

1. Create a GitHub issue with `[DOCS]` prefix
2. Include: Which doc, which section, what's wrong/missing
3. We'll update it

### Questions Not Answered in Docs

**Have a question not covered here?**

1. Search existing GitHub issues
2. Check [User Guide - FAQ](USER-GUIDE.md#faq)
3. Create issue with `[QUESTION]` prefix

### Contributing to Documentation

**Want to improve these docs?**

1. Read [Developer Guide - Contributing](DEVELOPER-GUIDE.md#contributing-guidelines)
2. Make your changes
3. Submit PR with clear description
4. Docs follow same review process as code

---

## Document Status

| Document | Last Updated | Status | Lines |
|----------|--------------|--------|-------|
| User Guide | 2025-01-06 | ✅ Complete | 1,238 |
| Developer Guide | 2025-01-06 | ✅ Complete | ~1,000 |
| Setup Guide | 2025-01-06 | ✅ Complete | 1,179 |
| Troubleshooting | 2025-01-06 | ✅ Complete | 1,239 |
| GitHub Workflows | 2025-01-06 | ✅ Complete | 642 |
| Agent Capabilities | 2025-01-06 | ✅ Complete | 1,262 |
| This Index | 2025-01-06 | ✅ Complete | - |

**Total Documentation:** ~6,560 lines across 6 comprehensive guides

---

## Summary

This documentation suite covers:

✅ **User workflows** - From setup to production migrations
✅ **Developer workflows** - From code to contributions
✅ **Architecture** - Deep dive into autonomous execution
✅ **Operations** - GitHub integration, CI/CD, monitoring
✅ **Troubleshooting** - Comprehensive problem resolution
✅ **Reference** - Commands, configs, APIs

**Everything you need to successfully use, extend, and maintain the autonomous data migration framework.**

**Start reading:** Choose your role above and follow the recommended path!
