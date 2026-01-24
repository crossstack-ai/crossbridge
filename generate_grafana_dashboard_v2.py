#!/usr/bin/env python3
"""
Generate Grafana-compatible dashboard with explicit datasource configuration
"""

import json

# This mimics the exact structure Grafana uses when you export a dashboard
dashboard = {
    "annotations": {
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
    },
    "editable": True,
    "fiscalYearStartMonth": 0,
    "graphTooltip": 0,
    "id": None,
    "links": [],
    "liveNow": False,
    "panels": [
        {
            "datasource": {
                "type": "postgres",
                "uid": "${DS_POSTGRESQL}"
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 100},
                            {"color": "red", "value": 200}
                        ]
                    },
                    "unit": "short"
                },
                "overrides": []
            },
            "gridPos": {"h": 6, "w": 6, "x": 0, "y": 0},
            "id": 1,
            "options": {
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto",
                "orientation": "auto",
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "textMode": "auto"
            },
            "pluginVersion": "10.0.0",
            "targets": [
                {
                    "datasource": {
                        "type": "postgres",
                        "uid": "${DS_POSTGRESQL}"
                    },
                    "editorMode": "code",
                    "format": "table",
                    "rawQuery": True,
                    "rawSql": "SELECT COUNT(DISTINCT test_id)::int as \"Total Tests\" FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours';",
                    "refId": "A",
                    "sql": {
                        "columns": [{"parameters": [], "type": "function"}],
                        "groupBy": [{"property": {"type": "string"}, "type": "groupBy"}],
                        "limit": 50
                    }
                }
            ],
            "title": "Total Tests (24h)",
            "type": "stat"
        },
        {
            "datasource": {
                "type": "postgres",
                "uid": "${DS_POSTGRESQL}"
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "yellow", "value": 1000},
                            {"color": "red", "value": 3000}
                        ]
                    },
                    "unit": "ms"
                },
                "overrides": []
            },
            "gridPos": {"h": 6, "w": 6, "x": 6, "y": 0},
            "id": 2,
            "options": {
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto",
                "orientation": "auto",
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "textMode": "auto"
            },
            "pluginVersion": "10.0.0",
            "targets": [
                {
                    "datasource": {
                        "type": "postgres",
                        "uid": "${DS_POSTGRESQL}"
                    },
                    "editorMode": "code",
                    "format": "table",
                    "rawQuery": True,
                    "rawSql": "SELECT ROUND(AVG(duration_ms)::numeric, 2)::float as \"Avg Duration\" FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours';",
                    "refId": "A"
                }
            ],
            "title": "Avg Test Duration (24h)",
            "type": "stat"
        },
        {
            "datasource": {
                "type": "postgres",
                "uid": "${DS_POSTGRESQL}"
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "hideFrom": {"tooltip": False, "viz": False, "legend": False}
                    },
                    "mappings": []
                },
                "overrides": []
            },
            "gridPos": {"h": 6, "w": 12, "x": 12, "y": 0},
            "id": 3,
            "options": {
                "legend": {
                    "displayMode": "table",
                    "placement": "right",
                    "showLegend": True,
                    "values": ["value", "percent"]
                },
                "pieType": "donut",
                "reduceOptions": {
                    "values": True,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "tooltip": {"mode": "single", "sort": "none"}
            },
            "targets": [
                {
                    "datasource": {
                        "type": "postgres",
                        "uid": "${DS_POSTGRESQL}"
                    },
                    "editorMode": "code",
                    "format": "table",
                    "rawQuery": True,
                    "rawSql": "SELECT framework as metric, COUNT(*)::int as value FROM crossbridge.tests WHERE created_at >= NOW() - INTERVAL '24 hours' GROUP BY framework ORDER BY value DESC;",
                    "refId": "A"
                }
            ],
            "title": "Tests by Framework (24h)",
            "type": "piechart"
        },
        {
            "datasource": {
                "type": "postgres",
                "uid": "${DS_POSTGRESQL}"
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 20,
                        "gradientMode": "none",
                        "hideFrom": {"tooltip": False, "viz": False, "legend": False},
                        "lineInterpolation": "smooth",
                        "lineWidth": 2,
                        "pointSize": 5,
                        "scaleDistribution": {"type": "linear"},
                        "showPoints": "auto",
                        "spanNulls": False,
                        "stacking": {"group": "A", "mode": "none"},
                        "thresholdsStyle": {"mode": "off"}
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [{"color": "green", "value": None}]
                    },
                    "unit": "ms"
                },
                "overrides": []
            },
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 6},
            "id": 4,
            "options": {
                "legend": {
                    "calcs": ["mean", "max", "min"],
                    "displayMode": "table",
                    "placement": "bottom",
                    "showLegend": True
                },
                "tooltip": {"mode": "multi", "sort": "desc"}
            },
            "targets": [
                {
                    "datasource": {
                        "type": "postgres",
                        "uid": "${DS_POSTGRESQL}"
                    },
                    "editorMode": "code",
                    "format": "time_series",
                    "rawQuery": True,
                    "rawSql": "SELECT\n  DATE_TRUNC('hour', created_at) AS time,\n  framework as metric,\n  ROUND(AVG(duration_ms)::numeric, 2)::float as value\nFROM crossbridge.tests\nWHERE created_at >= NOW() - INTERVAL '7 days'\nGROUP BY time, framework\nORDER BY time;",
                    "refId": "A"
                }
            ],
            "title": "Test Duration Trend by Framework (7 Days)",
            "type": "timeseries"
        },
        {
            "datasource": {
                "type": "postgres",
                "uid": "${DS_POSTGRESQL}"
            },
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "custom": {
                        "align": "auto",
                        "cellOptions": {"type": "auto"},
                        "inspect": False
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [{"color": "green", "value": None}]
                    }
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Duration (ms)"},
                        "properties": [
                            {"id": "custom.displayMode", "value": "gradient-gauge"},
                            {"id": "unit", "value": "ms"},
                            {"id": "custom.width", "value": 120}
                        ]
                    },
                    {
                        "matcher": {"id": "byName", "options": "Status"},
                        "properties": [
                            {"id": "custom.width", "value": 100}
                        ]
                    }
                ]
            },
            "gridPos": {"h": 10, "w": 24, "x": 0, "y": 14},
            "id": 5,
            "options": {
                "cellHeight": "sm",
                "footer": {
                    "countRows": False,
                    "fields": "",
                    "reducer": ["sum"],
                    "show": False
                },
                "showHeader": True,
                "sortBy": []
            },
            "pluginVersion": "10.0.0",
            "targets": [
                {
                    "datasource": {
                        "type": "postgres",
                        "uid": "${DS_POSTGRESQL}"
                    },
                    "editorMode": "code",
                    "format": "table",
                    "rawQuery": True,
                    "rawSql": "SELECT\n  test_id as \"Test Name\",\n  framework as \"Framework\",\n  status as \"Status\",\n  ROUND(duration_ms::numeric, 2)::float as \"Duration (ms)\",\n  TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as \"Time\"\nFROM crossbridge.tests\nWHERE created_at >= NOW() - INTERVAL '1 hour'\nORDER BY created_at DESC\nLIMIT 100;",
                    "refId": "A"
                }
            ],
            "title": "Recent Test Executions (Last Hour)",
            "type": "table"
        }
    ],
    "refresh": "30s",
    "schemaVersion": 38,
    "style": "dark",
    "tags": ["crossbridge", "performance", "profiling"],
    "templating": {
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
    },
    "time": {
        "from": "now-24h",
        "to": "now"
    },
    "timepicker": {},
    "timezone": "browser",
    "title": "CrossBridge - Performance Profiling v2",
    "uid": "crossbridge-perf-v2",
    "version": 0,
    "weekStart": ""
}

# Write the dashboard
output_file = "grafana/performance_profiling_dashboard_v2.json"
with open(output_file, 'w') as f:
    json.dump(dashboard, f, indent=2)

print(f"✅ Generated {output_file}")
print("\n📋 Key changes:")
print("  - Uses datasource variable: ${DS_POSTGRESQL}")
print("  - Added datasource template variable")
print("  - Explicit type casting (::int, ::float)")
print("  - Uses editorMode: 'code'")
print("  - Proper time_series format with 'metric' column")
print("\n🔧 Import Instructions:")
print("  1. Go to Grafana → Dashboards → Import")
print("  2. Upload: grafana/performance_profiling_dashboard_v2.json")
print("  3. Select your PostgreSQL datasource from dropdown")
print("  4. Click Import")
print("  5. Set time range to 'Last 24 hours'")
