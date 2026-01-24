"""
Create Grafana dashboard using HTTP API to ensure proper datasource binding
"""
import requests
import json

# Grafana settings
GRAFANA_URL = "http://10.55.12.99:3000"
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = "admin"

print("Step 1: Getting datasources...")
response = requests.get(
    f"{GRAFANA_URL}/api/datasources",
    auth=(GRAFANA_USER, GRAFANA_PASSWORD)
)

if response.status_code != 200:
    print(f"ERROR: Cannot connect to Grafana: {response.status_code}")
    print(f"Response: {response.text}")
    exit(1)

datasources = response.json()
print(f"Found {len(datasources)} datasources:")

postgres_ds = None
for ds in datasources:
    print(f"  - {ds['name']} (type: {ds['type']}, uid: {ds['uid']})")
    if ds['type'] == 'postgres':
        postgres_ds = ds
        print(f"    ✓ Using this PostgreSQL datasource")

if not postgres_ds:
    print("\nERROR: No PostgreSQL datasource found!")
    print("Please create a PostgreSQL datasource in Grafana first")
    exit(1)

print(f"\nStep 2: Creating dashboard with datasource UID: {postgres_ds['uid']}")

# Create dashboard with properly bound datasource
dashboard = {
    "dashboard": {
        "title": "CrossBridge Version Tracking (API)",
        "tags": ["crossbridge", "version-tracking"],
        "timezone": "browser",
        "schemaVersion": 38,
        "version": 0,
        "refresh": "30s",
        "panels": [
            {
                "id": 1,
                "type": "stat",
                "title": "Total Tests",
                "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "table",
                        "rawSql": "SELECT COUNT(*) as value FROM test_execution_event WHERE application_version IS NOT NULL AND created_at >= NOW() - INTERVAL '10 days'",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ],
                "options": {
                    "reduceOptions": {
                        "values": False,
                        "calcs": ["lastNotNull"]
                    },
                    "graphMode": "none",
                    "textMode": "value_and_name"
                }
            },
            {
                "id": 2,
                "type": "stat",
                "title": "Active Versions",
                "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "table",
                        "rawSql": "SELECT COUNT(DISTINCT application_version) as value FROM test_execution_event WHERE application_version IS NOT NULL AND created_at >= NOW() - INTERVAL '10 days'",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ],
                "options": {
                    "reduceOptions": {
                        "values": False,
                        "calcs": ["lastNotNull"]
                    },
                    "graphMode": "none",
                    "textMode": "value_and_name"
                }
            },
            {
                "id": 3,
                "type": "stat",
                "title": "Products",
                "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "table",
                        "rawSql": "SELECT COUNT(DISTINCT product_name) as value FROM test_execution_event WHERE application_version IS NOT NULL AND created_at >= NOW() - INTERVAL '10 days'",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ],
                "options": {
                    "reduceOptions": {
                        "values": False,
                        "calcs": ["lastNotNull"]
                    },
                    "graphMode": "none",
                    "textMode": "value_and_name"
                }
            },
            {
                "id": 4,
                "type": "stat",
                "title": "Environments",
                "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "table",
                        "rawSql": "SELECT COUNT(DISTINCT environment) as value FROM test_execution_event WHERE application_version IS NOT NULL AND created_at >= NOW() - INTERVAL '10 days'",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ],
                "options": {
                    "reduceOptions": {
                        "values": False,
                        "calcs": ["lastNotNull"]
                    },
                    "graphMode": "none",
                    "textMode": "value_and_name"
                }
            },
            {
                "id": 5,
                "type": "bargauge",
                "title": "Pass Rate by Version",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "table",
                        "rawSql": "SELECT application_version as metric, ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 1) as value FROM test_execution_event WHERE application_version IS NOT NULL AND created_at >= NOW() - INTERVAL '10 days' GROUP BY application_version ORDER BY application_version",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ],
                "options": {
                    "orientation": "horizontal",
                    "displayMode": "gradient",
                    "showUnfilled": True
                },
                "fieldConfig": {
                    "defaults": {
                        "max": 100,
                        "unit": "percent",
                        "mappings": []
                    }
                }
            },
            {
                "id": 6,
                "type": "bargauge",
                "title": "Tests by Product",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "table",
                        "rawSql": "SELECT product_name as metric, COUNT(*) as value FROM test_execution_event WHERE application_version IS NOT NULL AND created_at >= NOW() - INTERVAL '10 days' GROUP BY product_name ORDER BY value DESC",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ],
                "options": {
                    "orientation": "horizontal",
                    "displayMode": "gradient",
                    "showUnfilled": True
                }
            },
            {
                "id": 7,
                "type": "table",
                "title": "Version Details",
                "gridPos": {"h": 10, "w": 24, "x": 0, "y": 12},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "table",
                        "rawSql": "SELECT application_version as \"Version\", product_name as \"Product\", environment as \"Environment\", COUNT(*) as \"Total Tests\", SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as \"Passed\", SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as \"Failed\", ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 1) as \"Pass Rate %\" FROM test_execution_event WHERE application_version IS NOT NULL AND created_at >= NOW() - INTERVAL '10 days' GROUP BY application_version, product_name, environment ORDER BY product_name, application_version",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ]
            },
            {
                "id": 8,
                "type": "timeseries",
                "title": "Test Execution Timeline by Version",
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 22},
                "datasource": {
                    "type": "postgres",
                    "uid": postgres_ds['uid']
                },
                "targets": [
                    {
                        "refId": "A",
                        "format": "time_series",
                        "rawSql": "SELECT created_at as time, COUNT(*) as value, application_version FROM test_execution_event WHERE application_version IS NOT NULL AND $__timeFilter(created_at) GROUP BY time, application_version ORDER BY time",
                        "datasource": {
                            "type": "postgres",
                            "uid": postgres_ds['uid']
                        }
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "custom": {
                            "drawStyle": "line",
                            "lineInterpolation": "smooth",
                            "fillOpacity": 10,
                            "showPoints": "auto"
                        }
                    }
                }
            }
        ]
    },
    "overwrite": True,
    "message": "Created via API with proper datasource binding"
}

print("Step 3: Posting dashboard to Grafana...")
response = requests.post(
    f"{GRAFANA_URL}/api/dashboards/db",
    auth=(GRAFANA_USER, GRAFANA_PASSWORD),
    headers={"Content-Type": "application/json"},
    data=json.dumps(dashboard)
)

if response.status_code in [200, 201]:
    result = response.json()
    print(f"\n✓ SUCCESS! Dashboard created")
    print(f"  Dashboard ID: {result.get('id')}")
    print(f"  Dashboard UID: {result.get('uid')}")
    print(f"  URL: {GRAFANA_URL}{result.get('url')}")
    print(f"\nOpen this URL in your browser:")
    print(f"  {GRAFANA_URL}{result.get('url')}?from=now-10d&to=now")
else:
    print(f"\n✗ ERROR: Failed to create dashboard")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text}")
