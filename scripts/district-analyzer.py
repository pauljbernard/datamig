#!/usr/bin/env python3
"""
District Analyzer

Analyzes districts, calculates footprints, and generates priority rankings
for migration selection.

Input: JSON from stdin with district data from all stores
Output: JSON to stdout with ranked districts and recommendations
"""

import json
import sys
from datetime import datetime
from typing import Dict, List

def calculate_priority_score(district: Dict) -> float:
    """
    Calculate priority score for district migration.

    Factors:
    - Size (40%): Larger districts = higher priority
    - Activity (30%): More active = higher priority
    - Completeness (20%): More complete data = higher priority
    - Business Priority (10%): Manual override if provided
    """
    total_records = district['metrics']['total_records']
    recent_updates = district['metrics'].get('recent_updates_30d', 0)
    completeness = district['metrics'].get('data_completeness_pct', 100)
    business_priority = district.get('business_priority', 50)

    # Normalize to 0-100 scale
    size_score = min(100, (total_records / 1000000) * 100)
    activity_score = min(100, (recent_updates / 10000) * 100)
    completeness_score = completeness
    business_score = business_priority

    weighted_score = (
        size_score * 0.40 +
        activity_score * 0.30 +
        completeness_score * 0.20 +
        business_score * 0.10
    )

    return round(weighted_score, 2)


def estimate_migration_time(total_records: int) -> float:
    """
    Estimate migration time based on historical performance.

    Assumptions:
    - Extraction: 50,000 records/minute
    - Anonymization: 100,000 records/minute
    - Validation: 200,000 records/minute
    - Loading: 30,000 records/minute (bottleneck)
    """
    extraction_min = total_records / 50000
    anonymization_min = total_records / 100000
    validation_min = total_records / 200000
    loading_min = total_records / 30000

    # Add 10% overhead for setup, monitoring, reporting
    total_min = (extraction_min + anonymization_min + validation_min + loading_min) * 1.1

    return round(total_min / 60, 1)  # Convert to hours


def categorize_district_size(total_records: int) -> str:
    """Categorize district by size."""
    if total_records >= 700000:
        return 'large'
    elif total_records >= 300000:
        return 'medium'
    else:
        return 'small'


def select_pilot_districts(ranked_districts: List[Dict]) -> List[str]:
    """
    Select 3 districts for pilot phase.

    Strategy: 1 large, 1 medium, 1 small for comprehensive testing
    """
    large = None
    medium = None
    small = None

    for district in ranked_districts:
        size = categorize_district_size(district['metrics']['total_records'])
        if size == 'large' and large is None:
            large = district['id']
        elif size == 'medium' and medium is None:
            medium = district['id']
        elif size == 'small' and small is None:
            small = district['id']

        if large and medium and small:
            break

    return [d for d in [large, medium, small] if d]


def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Get criteria from input or use defaults
        criteria = input_data.get('selection_criteria', {
            'min_students': 5000,
            'min_schools': 10,
            'min_total_records': 50000,
            'max_total_records': 2000000,
            'min_completeness_pct': 85
        })

        # Process districts
        districts = []
        for district_data in input_data.get('districts', []):
            # Apply filtering criteria
            metrics = district_data['metrics']
            if metrics['students'] < criteria['min_students']:
                continue
            if metrics.get('schools', 0) < criteria['min_schools']:
                continue
            if metrics['total_records'] < criteria['min_total_records']:
                continue
            if metrics['total_records'] > criteria['max_total_records']:
                continue
            if metrics.get('data_completeness_pct', 100) < criteria['min_completeness_pct']:
                continue

            # Calculate priority score
            priority_score = calculate_priority_score(district_data)

            # Estimate migration time
            migration_hours = estimate_migration_time(metrics['total_records'])

            # Build district entry
            district = {
                'id': district_data['id'],
                'name': district_data['name'],
                'state': district_data.get('state', 'Unknown'),
                'priority_score': priority_score,
                'metrics': metrics,
                'footprint_by_store': district_data.get('footprint_by_store', {}),
                'estimated_migration_hours': migration_hours,
                'size_category': categorize_district_size(metrics['total_records'])
            }

            districts.append(district)

        # Sort by priority score (descending)
        ranked_districts = sorted(districts, key=lambda d: d['priority_score'], reverse=True)

        # Assign priority rank
        for idx, district in enumerate(ranked_districts, start=1):
            district['priority'] = idx

        # Select top N (default 15)
        top_n = input_data.get('top_n', 15)
        recommended_districts = ranked_districts[:top_n]

        # Mark pilot recommendations
        pilot_districts = select_pilot_districts(recommended_districts)
        for district in recommended_districts:
            district['recommended_for_pilot'] = district['id'] in pilot_districts

        # Calculate summary statistics
        summary = {
            'total_students': sum(d['metrics']['students'] for d in recommended_districts),
            'total_staff': sum(d['metrics'].get('staff', 0) for d in recommended_districts),
            'total_schools': sum(d['metrics'].get('schools', 0) for d in recommended_districts),
            'total_records': sum(d['metrics']['total_records'] for d in recommended_districts),
            'estimated_total_migration_hours': sum(d['estimated_migration_hours'] for d in recommended_districts),
            'districts_by_size': {
                'large': sum(1 for d in recommended_districts if d['size_category'] == 'large'),
                'medium': sum(1 for d in recommended_districts if d['size_category'] == 'medium'),
                'small': sum(1 for d in recommended_districts if d['size_category'] == 'small'),
            },
            'pilot_recommended': pilot_districts
        }

        # Build output
        result = {
            'success': True,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'total_districts_analyzed': len(input_data.get('districts', [])),
            'recommended_districts': len(recommended_districts),
            'selection_criteria': criteria,
            'districts': recommended_districts,
            'summary': summary
        }

        # Write output to stdout
        json.dump(result, sys.stdout, indent=2)
        sys.exit(0)

    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
        json.dump(error_result, sys.stdout, indent=2)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
