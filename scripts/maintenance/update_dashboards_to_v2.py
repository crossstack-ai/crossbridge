#!/usr/bin/env python3
"""
Update existing dashboard files to use the working v2 format
"""

import json

def update_dashboard_to_v2_format(input_file, output_file, title, uid):
    """Convert dashboard to working v2 format"""
    
    print(f"📝 Converting {input_file} to v2 format...")
    
    # Load existing dashboard
    with open(input_file, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)
    
    # Update title and uid
    dashboard['title'] = title
    dashboard['uid'] = uid
    
    # Add annotations if not present
    if 'annotations' not in dashboard or not dashboard['annotations'].get('list'):
        dashboard['annotations'] = {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {
                        "type": "grafana",
                        "uid": "-- Grafana --"
                    },
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard"
                }
            ]
        }
    
    # Add datasource template variable
    dashboard['templating'] = {
        "list": [
            {
                "current": {
                    "selected": False,
                    "text": "PostgreSQL",
                    "value": "PostgreSQL"
                },
                "hide": 0,
                "includeAll": False,
                "label": "datasource",
                "multi": False,
                "name": "DS_POSTGRESQL",
                "options": [],
                "query": "postgres",
                "refresh": 1,
                "regex": "",
                "skipUrlSync": False,
                "type": "datasource"
            }
        ]
    }
    
    # Update all panels to use the datasource variable
    for panel in dashboard.get('panels', []):
        # Update panel datasource
        panel['datasource'] = {
            "type": "postgres",
            "uid": "${DS_POSTGRESQL}"
        }
        
        # Add pluginVersion if not present
        if 'pluginVersion' not in panel:
            panel['pluginVersion'] = "10.0.0"
        
        # Update targets
        for target in panel.get('targets', []):
            target['datasource'] = {
                "type": "postgres",
                "uid": "${DS_POSTGRESQL}"
            }
            
            # Add editorMode
            if 'editorMode' not in target:
                target['editorMode'] = 'code'
            
            # Update SQL queries to add explicit type casting
            if 'rawSql' in target:
                sql = target['rawSql']
                
                # Add type casting for common aggregations
                sql = sql.replace('COUNT(*) as value', 'COUNT(*)::int as value')
                sql = sql.replace('COUNT(*) as "', 'COUNT(*)::int as "')
                sql = sql.replace('COUNT(DISTINCT test_id) as value', 'COUNT(DISTINCT test_id)::int as value')
                sql = sql.replace('AVG(duration_ms)::numeric, 2) as value', 'AVG(duration_ms)::numeric, 2)::float as value')
                sql = sql.replace('AVG(duration_ms)::numeric, 2) as "', 'AVG(duration_ms)::numeric, 2)::float as "')
                sql = sql.replace('PERCENTILE_CONT', 'PERCENTILE_CONT')  # Already returns numeric
                
                # Replace recorded_at with created_at if still present
                sql = sql.replace('recorded_at', 'created_at')
                
                target['rawSql'] = sql
    
    # Write updated dashboard
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2)
    
    print(f"   ✅ Saved to {output_file}")
    print(f"   📊 Panels: {len(dashboard.get('panels', []))}")
    print(f"   🔧 Datasource: ${{DS_POSTGRESQL}} (template variable)")
    return dashboard

# Update main dashboard
print("="*60)
print("🔄 Updating Dashboard Files to v2 Format")
print("="*60)

update_dashboard_to_v2_format(
    'grafana/performance_profiling_dashboard.json',
    'grafana/performance_profiling_dashboard.json',
    'CrossBridge - Performance Profiling',
    'crossbridge-performance-profiling'
)

print()

update_dashboard_to_v2_format(
    'grafana/performance_profiling_dashboard_simple.json',
    'grafana/performance_profiling_dashboard_simple.json',
    'CrossBridge - Performance Profiling (Simple)',
    'crossbridge-perf-simple'
)

print()
print("="*60)
print("✅ All dashboards updated!")
print("="*60)
print("""
📋 Import Instructions:
1. Go to Grafana → Dashboards → Import
2. Upload any of these JSON files:
   • performance_profiling_dashboard.json (12 panels - comprehensive)
   • performance_profiling_dashboard_simple.json (5 panels - simple)
   • performance_profiling_dashboard_v2.json (5 panels - working version)

3. Select your PostgreSQL datasource when prompted
4. Click Import
5. Set time range to 'Last 24 hours'

🔧 To edit individual panels:
1. Click panel title → Edit
2. In Query tab, you can change datasource if needed
3. All panels use the ${DS_POSTGRESQL} template variable
4. Save after making changes
""")
