# Data Migration Agent - PROD to CERT Migration Framework

## Executive Summary

This project provides a Claude Code-powered framework for migrating production data from 5 data stores (1 Graph DB + 4 RDS) to CERT environment with automated extraction, anonymization, and loading capabilities. The solution implements Approach #4 (Districts Load) to extract district-specific rostering data while maintaining referential integrity.

## Problem Statement

**Challenge**: Migrate PROD-like data for major districts to CERT to enable realistic testing and debugging.

**Scope**:
- 5 data stores: IDS, HCP1, HCP2, ADB, SP (Graph DB)
- Focus: Rostering data for major districts
- Primary constraint: Maintain relationship integrity across all data stores
- Timeline: 4-5 months (targeting March completion for BTS 2026)

**Key Requirements**:
1. Extract district-specific data with relationship constraints
2. Anonymize PII and sensitive data
3. Validate data integrity and schema compliance
4. Load into CERT without disrupting existing test data
5. Fully automated and repeatable process

---

## Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Layer                        │
│  (Master Agent - Coordinates all operations)                │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Discovery  │    │  Extraction  │    │   Loading    │
│    Layer     │───▶│   Pipeline   │───▶│   Layer      │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        │            ┌──────┴──────┐           │
        │            ▼             ▼            │
        │    ┌──────────────┐ ┌──────────────┐ │
        │    │ Anonymization│ │ Validation   │ │
        │    │   Engine     │ │   Engine     │ │
        │    └──────────────┘ └──────────────┘ │
        │                                       │
        └───────────────────┬───────────────────┘
                            ▼
                ┌──────────────────────┐
                │  Monitoring & Audit  │
                └──────────────────────┘
```

---

## Detailed Skills & Agents Architecture

### 1. Data Discovery & Analysis Layer

#### **Skill: `data-store-analyzer`**
**Purpose**: Analyze schema, relationships, and data volumes across all 5 data stores

**Capabilities**:
- Connect to each data store (IDS, HCP1, HCP2, ADB, SP)
- Extract schema definitions (tables, columns, data types)
- Map foreign key relationships and constraints
- Identify primary keys and indexes
- Calculate data volumes per district
- Generate dependency graphs

**Implementation**:
```
.claude/skills/data-store-analyzer/
├── skill.md (prompt definition)
├── config.json (data store connections)
├── schema-extractor.py
├── relationship-mapper.py
└── volume-analyzer.py
```

**Required MCP Servers**:
- `mcp-database-postgres` - For RDS connectivity
- `mcp-database-neo4j` - For Graph DB connectivity
- `mcp-aws-rds` - For AWS RDS management

#### **Agent: `schema-relationship-agent`**
**Type**: Explore agent (thorough)
**Purpose**: Deep dive into cross-store relationships and identify data dependencies

**Tasks**:
- Map all foreign key relationships across stores
- Identify circular dependencies
- Find orphaned records
- Document data lineage for rostering entities
- Create relationship constraint matrix

---

### 2. District Selection & Planning Layer

#### **Skill: `district-selector`**
**Purpose**: Identify and prioritize districts for migration

**Capabilities**:
- Query district metadata from PROD
- Analyze district size (student count, staff count, schools)
- Calculate data footprint per district across all stores
- Rank districts by usage metrics
- Generate district migration manifest

**Implementation**:
```
.claude/skills/district-selector/
├── skill.md
├── district-analyzer.sql
├── footprint-calculator.py
└── priority-ranker.py
```

**Output**: `district-manifest.json`
```json
{
  "districts": [
    {
      "id": "district-123",
      "name": "Major District A",
      "priority": 1,
      "student_count": 50000,
      "staff_count": 5000,
      "estimated_records": {
        "ids": 125000,
        "hcp1": 75000,
        "hcp2": 50000,
        "adb": 100000,
        "sp": 200000
      }
    }
  ]
}
```

---

### 3. Data Extraction Pipeline

#### **Skill: `district-data-extractor`**
**Purpose**: Extract district-specific data while maintaining referential integrity

**Capabilities**:
- Perform topological sort of tables based on dependencies
- Extract data in correct dependency order
- Handle circular references (e.g., bidirectional foreign keys)
- Support incremental extraction (changed data only)
- Generate extraction logs and metadata

**Implementation**:
```
.claude/skills/district-data-extractor/
├── skill.md
├── extraction-orchestrator.py
├── dependency-resolver.py
├── extractors/
│   ├── ids-extractor.py
│   ├── hcp1-extractor.py
│   ├── hcp2-extractor.py
│   ├── adb-extractor.py
│   └── sp-extractor.py (Graph DB)
├── filters/
│   └── district-filter.sql
└── templates/
    └── extraction-query.sql.j2
```

**Algorithm**:
1. Start with root entities (districts, schools)
2. Traverse dependency tree using BFS
3. Apply district filter at each level
4. Handle many-to-many relationships
5. Export to staging format (JSON/Parquet)

#### **Agent: `extraction-pipeline-agent`**
**Type**: General-purpose agent
**Purpose**: Orchestrate multi-store extraction with error handling

**Tasks**:
- Read district manifest
- Execute extractors in dependency order
- Handle extraction failures and retries
- Validate extracted record counts
- Package extraction results
- Generate extraction report

---

### 4. Data Anonymization Engine

#### **Skill: `pii-anonymizer`**
**Purpose**: Mask PII and sensitive data while preserving data utility

**Capabilities**:
- Detect PII fields automatically (names, emails, SSN, phone, addresses)
- Apply anonymization strategies:
  - Hash-based (consistent across tables for FK integrity)
  - Fake data generation (realistic but fake names/emails)
  - Tokenization (for reversible masking if needed)
  - Nullification (for highly sensitive fields)
- Preserve data format and constraints
- Generate anonymization audit trail

**Implementation**:
```
.claude/skills/pii-anonymizer/
├── skill.md
├── pii-detector.py (ML-based field detection)
├── anonymization-strategies/
│   ├── hash-anonymizer.py
│   ├── faker-anonymizer.py
│   ├── tokenizer.py
│   └── nullifier.py
├── config/
│   └── anonymization-rules.yaml
└── audit/
    └── anonymization-logger.py
```

**Anonymization Rules** (`anonymization-rules.yaml`):
```yaml
rules:
  - field_pattern: ".*email.*"
    strategy: faker
    faker_type: email
    preserve_domain: false

  - field_pattern: ".*ssn.*|.*social_security.*"
    strategy: hash
    hash_algorithm: sha256
    salt: "${ENV_SALT}"

  - field_pattern: ".*first_name.*|.*last_name.*"
    strategy: faker
    faker_type: name
    consistent_per_id: true

  - field_pattern: ".*phone.*|.*mobile.*"
    strategy: faker
    faker_type: phone_number

  - field_pattern: ".*address.*|.*street.*"
    strategy: faker
    faker_type: address
```

#### **Agent: `anonymization-agent`**
**Type**: General-purpose agent
**Purpose**: Apply anonymization rules to extracted data

**Tasks**:
- Load anonymization rules
- Scan extracted data for PII fields
- Apply appropriate anonymization strategy
- Maintain consistency map (same PROD ID → same fake value)
- Validate anonymized data integrity
- Generate anonymization report

---

### 5. Data Validation Engine

#### **Skill: `data-integrity-validator`**
**Purpose**: Ensure data quality and referential integrity

**Capabilities**:
- Schema validation (data types, constraints, nullability)
- Referential integrity checks (FK relationships valid)
- Business rule validation (rostering logic, data constraints)
- Data completeness checks (no missing required data)
- Cross-store consistency validation
- Generate validation report with errors/warnings

**Implementation**:
```
.claude/skills/data-integrity-validator/
├── skill.md
├── validators/
│   ├── schema-validator.py
│   ├── referential-validator.py
│   ├── business-rule-validator.py
│   ├── completeness-validator.py
│   └── cross-store-validator.py
├── rules/
│   └── validation-rules.yaml
└── reports/
    └── validation-reporter.py
```

**Validation Checks**:
1. **Schema Validation**: Data types match target schema
2. **Referential Integrity**: All FKs point to existing records
3. **Uniqueness**: Primary keys and unique constraints satisfied
4. **Nullability**: Required fields are not null
5. **Data Ranges**: Values within expected ranges
6. **Rostering Logic**: Student-teacher-school relationships valid
7. **Temporal Consistency**: Dates/timestamps logical

#### **Agent: `pre-load-validation-agent`**
**Type**: General-purpose agent
**Purpose**: Validate data before loading to CERT

---

### 6. Data Loading Layer

#### **Skill: `cert-data-loader`**
**Purpose**: Load anonymized data into CERT environment

**Capabilities**:
- Connect to CERT data stores
- Load data in dependency order (respects FK constraints)
- Handle constraint violations gracefully
- Support transaction rollback on errors
- Generate load statistics and logs
- Verify loaded data matches source

**Implementation**:
```
.claude/skills/cert-data-loader/
├── skill.md
├── loaders/
│   ├── ids-loader.py
│   ├── hcp1-loader.py
│   ├── hcp2-loader.py
│   ├── adb-loader.py
│   └── sp-loader.py
├── strategies/
│   ├── insert-loader.py (new records)
│   ├── upsert-loader.py (update or insert)
│   └── merge-loader.py (complex merging)
└── rollback/
    └── rollback-manager.py
```

**Loading Strategy**:
1. Create backup/snapshot of CERT before load
2. Disable FK constraints temporarily (if supported)
3. Load data in topological order
4. Re-enable FK constraints
5. Validate loaded data
6. Commit or rollback based on validation

#### **Agent: `load-orchestration-agent`**
**Type**: General-purpose agent
**Purpose**: Manage the loading process with error recovery

---

### 7. Orchestration & Monitoring

#### **Agent: `master-migration-orchestrator`**
**Type**: General-purpose agent
**Purpose**: Coordinate the entire migration pipeline end-to-end

**Workflow**:
```
1. Initialize Migration
   ├─ Load configuration
   ├─ Validate environment connectivity
   └─ Create migration run ID

2. Discovery Phase
   ├─ Analyze data stores (schema-relationship-agent)
   ├─ Select districts (district-selector skill)
   └─ Generate migration plan

3. Extraction Phase
   ├─ Extract district data (extraction-pipeline-agent)
   └─ Validate extraction completeness

4. Anonymization Phase
   ├─ Apply PII anonymization (anonymization-agent)
   └─ Validate anonymization quality

5. Validation Phase
   ├─ Schema validation
   ├─ Referential integrity checks
   └─ Business rule validation

6. Loading Phase
   ├─ Backup CERT (optional)
   ├─ Load data (load-orchestration-agent)
   └─ Validate loaded data

7. Finalization
   ├─ Generate migration report
   ├─ Update audit trail
   └─ Notify stakeholders
```

#### **Skill: `migration-monitor`**
**Purpose**: Real-time monitoring and reporting

**Capabilities**:
- Track progress of each phase
- Monitor resource utilization (CPU, memory, network)
- Detect anomalies and errors
- Generate real-time dashboards
- Send notifications on failures
- Maintain audit log

**Implementation**:
```
.claude/skills/migration-monitor/
├── skill.md
├── monitors/
│   ├── progress-tracker.py
│   ├── resource-monitor.py
│   └── error-detector.py
├── reporters/
│   ├── dashboard-generator.py
│   └── notification-sender.py
└── audit/
    └── audit-logger.py
```

---

## Supporting Infrastructure

### MCP Servers Required

1. **Database Connectivity**
   - `mcp-database-postgres` - PostgreSQL/RDS connectivity
   - `mcp-database-neo4j` - Graph database connectivity
   - `mcp-aws-rds` - AWS RDS management and operations

2. **Cloud Services**
   - `mcp-aws-s3` - Staging data storage
   - `mcp-aws-secrets-manager` - Secure credential management
   - `mcp-aws-cloudwatch` - Logging and monitoring

3. **Data Processing**
   - `mcp-pandas` - Data manipulation and transformation
   - `mcp-pyspark` - Large-scale data processing (if needed)

4. **Utilities**
   - `mcp-filesystem` - Local file operations
   - `mcp-git` - Version control for configs and scripts

### Configuration Management

**Directory Structure**:
```
/Users/colossus/development/datamig/
├── .claude/
│   ├── skills/
│   │   ├── data-store-analyzer/
│   │   ├── district-selector/
│   │   ├── district-data-extractor/
│   │   ├── pii-anonymizer/
│   │   ├── data-integrity-validator/
│   │   ├── cert-data-loader/
│   │   └── migration-monitor/
│   ├── agents/
│   │   ├── schema-relationship-agent.md
│   │   ├── extraction-pipeline-agent.md
│   │   ├── anonymization-agent.md
│   │   ├── pre-load-validation-agent.md
│   │   ├── load-orchestration-agent.md
│   │   └── master-migration-orchestrator.md
│   └── mcp/
│       └── servers.json
├── config/
│   ├── environments.yaml (PROD/CERT connection strings)
│   ├── districts.yaml (district selection criteria)
│   ├── anonymization-rules.yaml
│   ├── validation-rules.yaml
│   └── pipeline-config.yaml
├── scripts/
│   ├── extractors/
│   ├── loaders/
│   ├── validators/
│   └── utilities/
├── data/
│   ├── staging/ (extracted data)
│   ├── anonymized/ (anonymized data)
│   └── reports/ (validation reports)
├── logs/
│   └── migrations/ (audit logs by run)
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
    ├── architecture.md
    ├── runbook.md
    └── troubleshooting.md
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up project structure and repository
- [ ] Install required MCP servers
- [ ] Configure PROD/CERT connectivity (read-only PROD)
- [ ] Create configuration management framework
- [ ] Develop `data-store-analyzer` skill
- [ ] Implement `schema-relationship-agent`
- [ ] Document data store schemas and relationships

**Deliverables**:
- Complete schema documentation for all 5 data stores
- Relationship dependency graph
- Data volume analysis per store

### Phase 2: District Selection (Week 3)
- [ ] Develop `district-selector` skill
- [ ] Analyze top 20 districts by size and activity
- [ ] Generate district prioritization list
- [ ] Create district migration manifest
- [ ] Get stakeholder approval on district list

**Deliverables**:
- District manifest JSON with top 10-15 districts
- Data footprint analysis per district

### Phase 3: Extraction Pipeline (Weeks 4-7)
- [ ] Develop `district-data-extractor` skill
- [ ] Implement extractors for each data store (IDS, HCP1, HCP2, ADB, SP)
- [ ] Build dependency resolver algorithm
- [ ] Create `extraction-pipeline-agent`
- [ ] Test extraction with 1 small district
- [ ] Optimize extraction performance
- [ ] Add error handling and retry logic

**Deliverables**:
- Working extraction pipeline for all 5 stores
- Extraction validation report
- Performance benchmarks

### Phase 4: Anonymization (Weeks 8-10)
- [ ] Develop `pii-anonymizer` skill
- [ ] Implement PII detection logic
- [ ] Build anonymization strategies (hash, faker, tokenization)
- [ ] Create anonymization rules configuration
- [ ] Implement `anonymization-agent`
- [ ] Test anonymization on extracted data
- [ ] Validate anonymization quality

**Deliverables**:
- Complete anonymization engine
- Anonymization audit reports
- Sample anonymized datasets

### Phase 5: Validation Framework (Weeks 11-12)
- [ ] Develop `data-integrity-validator` skill
- [ ] Implement schema validator
- [ ] Build referential integrity checker
- [ ] Create business rule validators (rostering logic)
- [ ] Develop `pre-load-validation-agent`
- [ ] Test validation on anonymized data

**Deliverables**:
- Comprehensive validation framework
- Validation reports with pass/fail status

### Phase 6: Loading Pipeline (Weeks 13-15)
- [ ] Develop `cert-data-loader` skill
- [ ] Implement loaders for each CERT data store
- [ ] Build dependency-aware loading logic
- [ ] Create rollback mechanism
- [ ] Implement `load-orchestration-agent`
- [ ] Test loading with 1 small district on CERT
- [ ] Validate loaded data in CERT

**Deliverables**:
- Working load pipeline
- Load validation reports
- Rollback procedure documentation

### Phase 7: Orchestration & Automation (Weeks 16-17)
- [ ] Develop `master-migration-orchestrator` agent
- [ ] Implement `migration-monitor` skill
- [ ] Build end-to-end pipeline automation
- [ ] Create monitoring dashboards
- [ ] Add notification system
- [ ] Develop audit logging

**Deliverables**:
- Fully automated migration pipeline
- Real-time monitoring dashboard
- Audit trail system

### Phase 8: Testing & Validation (Weeks 18-19)
- [ ] Perform end-to-end test with 3 districts
- [ ] Validate rostering flows on CERT with migrated data
- [ ] Performance testing and optimization
- [ ] Security and compliance review
- [ ] User acceptance testing with QE teams
- [ ] Fix identified issues

**Deliverables**:
- Test results and validation reports
- Performance optimization recommendations
- Security audit clearance

### Phase 9: Production Rollout (Week 20)
- [ ] Migrate remaining districts (phased approach)
- [ ] Monitor migration health
- [ ] Support QE teams with CERT testing
- [ ] Document lessons learned
- [ ] Create maintenance runbook

**Deliverables**:
- All major districts migrated to CERT
- Operational runbook
- Maintenance schedule

### Phase 10: Post-Migration Support (Ongoing)
- [ ] Monitor data quality on CERT
- [ ] Handle refresh requests
- [ ] Implement incremental update capability
- [ ] Optimize pipeline based on feedback
- [ ] Extend to additional districts as needed

---

## Success Metrics

1. **Coverage**: Top 15 districts migrated (representing 70%+ of PROD usage)
2. **Data Quality**: >99% referential integrity maintained
3. **Performance**: Full migration completes in <4 hours per district
4. **Anonymization**: 100% PII fields masked, 0 data leaks
5. **Testing Impact**: QE teams report 50%+ improvement in bug detection
6. **Automation**: Pipeline runs with <5% manual intervention
7. **Repeatability**: Refresh pipeline executable monthly with <1 day effort

---

## Risk Mitigation

### Technical Risks
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Complex FK relationships cause extraction failures | High | Implement robust dependency resolver with circular reference handling |
| Large data volumes exceed memory limits | High | Use streaming/chunking approach, leverage Spark for large datasets |
| Anonymization breaks referential integrity | Critical | Use consistent hashing, maintain ID mapping tables |
| CERT load failures corrupt environment | High | Always create backup, implement atomic transactions with rollback |
| Graph DB extraction complexity | High | Engage SP domain experts early, use Cypher query optimization |

### Operational Risks
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Insufficient data domain expertise | High | Assign POCs from each domain as required, schedule weekly syncs |
| Timeline slippage due to complexity | Medium | Use agile sprints, have contingency buffer, prioritize critical path |
| PROD access restrictions | Medium | Work with security team early, use read-only replicas |
| Compliance and security concerns | Critical | Engage security/compliance teams from start, document everything |

---

## Team Requirements

### Core Team (Dedicated)
- **1 Data Architect / Tech Lead** - Overall architecture and coordination
- **2-3 Data Engineers** - ETL pipeline development
- **1 QE/Automation Engineer** - Testing and validation framework
- **1 DevOps Engineer** - Infrastructure, deployment, monitoring

### Supporting Resources (Part-time)
- **Domain POCs** (1 per data store): IDS, HCP1, HCP2, ADB, SP
- **Security/Compliance Advisor** - Anonymization and compliance guidance
- **Cloud Architect** - AWS infrastructure and optimization
- **QE Team Representatives** - UAT and feedback

---

## Next Steps

1. **Immediate Actions** (This Week):
   - [ ] Get stakeholder approval on this plan
   - [ ] Secure dedicated team assignments
   - [ ] Request PROD read-only access for data analysis
   - [ ] Set up development environment and repository
   - [ ] Schedule kickoff meeting with domain POCs

2. **Week 1 Deliverables**:
   - [ ] Complete project setup
   - [ ] Install MCP servers and validate connectivity
   - [ ] Begin Phase 1: Data store analysis
   - [ ] Document schemas for IDS and HCP1

3. **Sprint Planning**:
   - 2-week sprints aligned with phases
   - Weekly status updates to stakeholders
   - Bi-weekly demos to QE teams
   - Monthly steering committee reviews

---

## Appendix

### A. Technology Stack
- **Languages**: Python 3.11+, SQL, Cypher (Graph DB)
- **Frameworks**: Pandas, SQLAlchemy, Neo4j Driver, Faker
- **Cloud**: AWS (RDS, S3, Secrets Manager, CloudWatch)
- **Orchestration**: Claude Code Agents
- **Testing**: pytest, Great Expectations
- **Monitoring**: CloudWatch, custom dashboards

### B. Compliance Considerations
- All PII fields must be anonymized per GDPR/FERPA requirements
- Audit trail maintained for all data access and transformations
- Data encryption in transit and at rest
- Access controls and authentication enforced
- Regular security reviews and penetration testing

### C. References
- BTS 2026 Timeline and Requirements
- Data Store Documentation (IDS, HCP, ADB, SP)
- CERT Environment Specifications
- Security and Compliance Guidelines
- AWS Best Practices for Data Migration

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Owner**: Data Migration Team
**Status**: Planning
