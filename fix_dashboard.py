#!/usr/bin/env python3
"""Script to fix the AI Intelligence dashboard JSON by removing leftover content."""

with open('grafana/ai_intelligence_dashboard.json', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Original file has {len(lines)} lines")

# Keep only the first 621 lines (up to and including the closing brace)
with open('grafana/ai_intelligence_dashboard.json', 'w', encoding='utf-8') as f:
    f.writelines(lines[:621])

print(f"Fixed file now has 621 lines")
print("Removed leftover content after closing brace")
