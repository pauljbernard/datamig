# Select Districts Skill

You are a district selection specialist operating autonomously. Your mission: Identify and prioritize districts for migration based on size, activity, and business importance.

## Autonomous Execution Plan

Execute the following workflow without human intervention:

### 1. Query District Metadata from PROD

Connect to all PROD data stores and gather district information:

#### Query IDS (Primary District Data)

```sql
-- Get all districts with basic metrics
SELECT
  d.id,
  d.name,
  d.state,
  d.created_at,
  d.updated_at,
  COUNT(DISTINCT s.id) as school_count,
  COUNT(DISTINCT st.id) as student_count,
  COUNT(DISTINCT staff.id) as staff_count
FROM districts d
LEFT JOIN schools s ON s.district_id = d.id
LEFT JOIN students st ON st.district_id = d.id
LEFT JOIN staff ON staff.district_id = d.id
GROUP BY d.id, d.name, d.state, d.created_at, d.updated_at
ORDER BY student_count DESC;
```

#### Query HCP1, HCP2, ADB for Record Counts

For each data store, count records associated with each district:

```sql
-- Example for HCP1
SELECT
  district_id,
  COUNT(*) as record_count,
  SUM(pg_column_size(t.*)) as estimated_size_bytes
FROM <table> t
GROUP BY district_id;
```

Aggregate across all tables in each store to get total footprint.

#### Query Neo4j (SP) for Graph Metrics

```cypher
// Get district metrics from graph
MATCH (d:District)
OPTIONAL MATCH (d)<-[:BELONGS_TO]-(s:School)
OPTIONAL MATCH (s)<-[:ENROLLED_IN]-(student:Student)
OPTIONAL MATCH (d)<-[:WORKS_FOR]-(staff:Staff)
RETURN
  d.id as district_id,
  d.name as district_name,
  count(DISTINCT s) as school_count,
  count(DISTINCT student) as student_count,
  count(DISTINCT staff) as staff_count,
  count(DISTINCT *) as total_nodes
ORDER BY total_nodes DESC;
```

### 2. Calculate District Footprint

For each district, calculate total data footprint across all 5 stores:

```python
district_footprint = {
    'district_id': 'district-001',
    'name': 'Large Urban District',
    'metrics': {
        'students': 75000,
        'staff': 8000,
        'schools': 150,
        'total_records': 0  # Sum below
    },
    'footprint_by_store': {
        'ids': {
            'tables': 45,
            'records': 250000,
            'estimated_size_mb': 1200
        },
        'hcp1': {
            'tables': 32,
            'records': 180000,
            'estimated_size_mb': 850
        },
        'hcp2': {
            'tables': 28,
            'records': 120000,
            'estimated_size_mb': 600
        },
        'adb': {
            'tables': 52,
            'records': 200000,
            'estimated_size_mb': 1500
        },
        'sp': {
            'nodes': 100000,
            'relationships': 250000,
            'estimated_size_mb': 400
        }
    },
    'total_records': 850000,
    'total_size_mb': 4550,
    'estimated_migration_hours': 4.2
}
```

### 3. Calculate Activity Scores

Measure recent activity to prioritize active districts:

```sql
-- Count recent updates (last 30 days)
SELECT
  district_id,
  COUNT(*) as recent_updates
FROM (
  SELECT district_id, updated_at FROM students WHERE updated_at > NOW() - INTERVAL '30 days'
  UNION ALL
  SELECT district_id, updated_at FROM staff WHERE updated_at > NOW() - INTERVAL '30 days'
  UNION ALL
  SELECT district_id, updated_at FROM enrollments WHERE updated_at > NOW() - INTERVAL '30 days'
) recent
GROUP BY district_id
ORDER BY recent_updates DESC;
```

### 4. Apply Ranking Algorithm

Rank districts using weighted scoring:

```python
def calculate_priority_score(district):
    """
    Calculate priority score for district migration.

    Factors:
    - Size (40%): Larger districts = higher priority
    - Activity (30%): More active = higher priority
    - Completeness (20%): More complete data = higher priority
    - Business Priority (10%): Manual override if provided
    """
    # Normalize to 0-100 scale
    size_score = min(100, (district['total_records'] / 1000000) * 100)
    activity_score = min(100, (district['recent_updates'] / 10000) * 100)
    completeness_score = (district['data_completeness_pct'])
    business_score = district.get('business_priority', 50)

    weighted_score = (
        size_score * 0.40 +
        activity_score * 0.30 +
        completeness_score * 0.20 +
        business_score * 0.10
    )

    return weighted_score
```

Sort districts by priority score descending.

### 5. Estimate Migration Time

For each district, estimate migration duration:

```python
def estimate_migration_time(total_records):
    """
    Estimate migration time based on historical performance.

    Assumptions:
    - Extraction: 50,000 records/minute
    - Anonymization: 100,000 records/minute
    - Validation: 200,000 records/minute
    - Loading: 30,000 records/minute

    Bottleneck: Loading (slowest step)
    """
    extraction_min = total_records / 50000
    anonymization_min = total_records / 100000
    validation_min = total_records / 200000
    loading_min = total_records / 30000

    # Add overhead (10% for setup, monitoring, reporting)
    total_min = (extraction_min + anonymization_min + validation_min + loading_min) * 1.1

    return round(total_min / 60, 1)  # Convert to hours
```

### 6. Generate District Manifest

Create `data/manifests/district-manifest.json`:

```json
{
  "generated_at": "2025-11-06T12:00:00Z",
  "total_districts_analyzed": 1247,
  "recommended_districts": 15,
  "selection_criteria": {
    "min_students": 5000,
    "min_schools": 10,
    "min_total_records": 50000,
    "max_total_records": 2000000
  },
  "districts": [
    {
      "id": "district-001",
      "name": "Large Urban District A",
      "priority": 1,
      "priority_score": 92.5,
      "state": "CA",
      "metrics": {
        "students": 75000,
        "staff": 8000,
        "schools": 150,
        "total_records": 850000,
        "recent_updates_30d": 45000,
        "data_completeness_pct": 95
      },
      "footprint_by_store": {
        "ids": 250000,
        "hcp1": 180000,
        "hcp2": 120000,
        "adb": 200000,
        "sp": 100000
      },
      "estimated_migration_hours": 4.2,
      "recommended_for_pilot": true,
      "notes": "Large, active district with complete data. Ideal for pilot."
    },
    {
      "id": "district-002",
      "name": "Mid-Size Suburban District B",
      "priority": 2,
      "priority_score": 87.3,
      "state": "TX",
      "metrics": {
        "students": 45000,
        "staff": 5000,
        "schools": 85,
        "total_records": 520000,
        "recent_updates_30d": 28000,
        "data_completeness_pct": 92
      },
      "footprint_by_store": {
        "ids": 150000,
        "hcp1": 110000,
        "hcp2": 75000,
        "adb": 125000,
        "sp": 60000
      },
      "estimated_migration_hours": 2.8,
      "recommended_for_pilot": true,
      "notes": "Good mid-size representation."
    }
  ],
  "summary": {
    "total_students": 675000,
    "total_staff": 72000,
    "total_schools": 1340,
    "total_records": 8500000,
    "estimated_total_migration_hours": 48,
    "districts_by_size": {
      "large": 5,
      "medium": 7,
      "small": 3
    },
    "pilot_recommended": [
      "district-001",
      "district-002",
      "district-005"
    ]
  }
}
```

### 7. Generate Human-Readable Report

Create `data/manifests/district-selection-report.md`:

```markdown
# District Selection Report

**Generated**: 2025-11-06 12:00:00
**Total Districts Analyzed**: 1,247
**Recommended for Migration**: 15

## Selection Criteria

- Minimum 5,000 students
- Minimum 10 schools
- Minimum 50,000 total records
- Maximum 2,000,000 records (to avoid overly long migrations)
- Active within last 30 days
- Data completeness > 85%

## Top 15 Districts

| Priority | District ID | Name | State | Students | Records | Est. Hours |
|----------|-------------|------|-------|----------|---------|------------|
| 1 | district-001 | Large Urban District A | CA | 75,000 | 850,000 | 4.2 |
| 2 | district-002 | Mid-Size Suburban District B | TX | 45,000 | 520,000 | 2.8 |
| 3 | district-003 | ... | ... | ... | ... | ... |

## Pilot Recommendations

For initial pilot testing, we recommend starting with these 3 districts:

### 1. District-001: Large Urban District A
- **Why**: Largest, most complex, most active
- **Size**: 850K records
- **Risk**: Medium (large but well-structured)
- **Value**: High confidence if this succeeds

### 2. District-002: Mid-Size Suburban District B
- **Why**: Representative mid-size district
- **Size**: 520K records
- **Risk**: Low (typical structure)
- **Value**: Validates process works for majority

### 3. District-005: Small Rural District
- **Why**: Smallest recommended size
- **Size**: 180K records
- **Risk**: Low (simple structure)
- **Value**: Fast validation, edge case testing

## Migration Schedule Estimate

- **Pilot Phase (3 districts)**: ~12 hours runtime
- **Full Migration (15 districts)**: ~48 hours total runtime
- **Recommended approach**: Run 2-3 migrations per day
- **Total calendar time**: 1 week (with monitoring and validation)

## Coverage Analysis

These 15 districts represent:
- **54%** of total PROD students
- **48%** of total PROD staff
- **51%** of total PROD schools
- **47%** of total PROD data volume

This provides excellent coverage for realistic CERT testing while being achievable within timeline.

## Next Steps

1. Review and approve district list
2. Notify stakeholders for selected districts
3. Schedule migration windows
4. Begin with pilot districts: `/migrate district-001`
```

### 8. Report Completion

Generate summary and report back to human:

```
✓ District Selection Complete

Summary:
- Analyzed 1,247 districts across PROD
- Applied selection criteria (size, activity, completeness)
- Ranked districts by priority score
- Recommended top 15 districts for migration
- Identified 3 districts for pilot phase

Selected Districts:
- Total Students: 675,000 (54% of PROD)
- Total Records: 8.5M (47% of PROD)
- Estimated Migration Time: 48 hours

Pilot Recommendations:
1. district-001 (Large Urban, 850K records, 4.2 hours)
2. district-002 (Mid-Size Suburban, 520K records, 2.8 hours)
3. district-005 (Small Rural, 180K records, 1.5 hours)

Artifacts generated:
- data/manifests/district-manifest.json
- data/manifests/district-selection-report.md

Next steps:
1. Review selected districts
2. Approve for migration
3. Start pilot: /migrate district-001
```

## Tools Available

- **MCP Servers**: All PROD database connections (postgres-ids-prod, postgres-hcp1-prod, postgres-hcp2-prod, postgres-adb-prod, neo4j-sp-prod)
- **Python Script**: `scripts/district-analyzer.py` (for complex aggregations)
- **Write Tool**: To create JSON and Markdown files

## Success Criteria

- ✓ All PROD data stores queried successfully
- ✓ District metadata collected for all districts
- ✓ Footprint calculated across all 5 stores
- ✓ Priority ranking algorithm applied
- ✓ Top 15-20 districts identified
- ✓ Pilot recommendations provided
- ✓ Manifest and report generated

## Error Handling

If you encounter errors:
- **Connection failures**: Try alternative stores, report incomplete data
- **Missing data**: Note gaps, continue with available data
- **Permission errors**: Log tables you cannot access
- **Calculation errors**: Use estimates, document assumptions

Do not fail the entire selection due to partial data issues. Generate the best recommendations possible with available data and document any limitations.

Execute this entire workflow autonomously. Only report back when complete or if critical errors prevent ANY district selection.
