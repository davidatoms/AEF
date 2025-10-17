#!/usr/bin/env python3
"""Example usage of the structured search results."""

import json
from pathlib import Path

# Load consolidated data
consolidated_file = Path(__file__).parent / "search_results_consolidated.json"
with consolidated_file.open() as f:
    all_searches = json.load(f)

# Example 1: Get all series IDs for a specific query
print("=== Example 1: All unemployment series IDs ===")
unemployment_data = all_searches.get("unemployment", {})
for result in unemployment_data.get("results", []):
    print(f"{result['series_id']}: {result['title']}")

print("\n=== Example 2: Filter by frequency ===")
# Get only monthly series across all queries
for query, data in all_searches.items():
    monthly_series = [
        r for r in data.get("results", [])
        if r.get("frequency", "").startswith("Monthly")
    ]
    if monthly_series:
        print(f"\n{query.upper()} - Monthly series:")
        for series in monthly_series[:3]:  # Just show first 3
            print(f"  {series['series_id']}: {series['title']}")

print("\n=== Example 3: Create lookup dictionary ===")
# Create a series_id -> info lookup
series_lookup = {}
for query, data in all_searches.items():
    for result in data.get("results", []):
        series_lookup[result["series_id"]] = {
            "title": result["title"],
            "frequency": result["frequency"],
            "units": result["units"],
            "query_category": query,
        }

# Look up a specific series
series_id = "UNRATE"
if series_id in series_lookup:
    info = series_lookup[series_id]
    print(f"\nSeries {series_id}:")
    print(f"  Title: {info['title']}")
    print(f"  Frequency: {info['frequency']}")
    print(f"  Units: {info['units']}")
    print(f"  Category: {info['query_category']}")

print("\n=== Example 4: Load individual JSON ===")
# Or load a specific query's JSON file
industry_file = Path(__file__).parent / "search_results" / "industry.json"
with industry_file.open() as f:
    industry_data = json.load(f)

print(f"\nIndustry query returned {industry_data['result_count']} results")
print(f"First result: {industry_data['results'][0]['series_id']}")
