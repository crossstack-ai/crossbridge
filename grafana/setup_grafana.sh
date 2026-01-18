#!/bin/bash
# Grafana Dashboard Quick Setup Script
# Automatically configures PostgreSQL data source and imports dashboard

GRAFANA_URL="http://10.55.12.99:3000"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="admin"

PG_HOST="10.55.12.99"
PG_PORT="5432"
PG_DATABASE="udp-native-webservices-automation"
PG_USER="postgres"
PG_PASSWORD="admin"

echo "========================================="
echo "CrossBridge Grafana Dashboard Setup"
echo "========================================="
echo ""

# Step 1: Test Grafana connection
echo "Step 1: Testing Grafana connection..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" $GRAFANA_URL/api/health)
if [ "$HEALTH" = "200" ]; then
    echo "✅ Grafana is accessible at $GRAFANA_URL"
else
    echo "❌ Cannot connect to Grafana at $GRAFANA_URL"
    echo "   Please verify Grafana is running and accessible"
    exit 1
fi
echo ""

# Step 2: Create PostgreSQL data source
echo "Step 2: Creating PostgreSQL data source..."

DATA_SOURCE_JSON=$(cat <<EOF
{
  "name": "CrossBridge Coverage DB",
  "type": "postgres",
  "url": "$PG_HOST:$PG_PORT",
  "database": "$PG_DATABASE",
  "user": "$PG_USER",
  "secureJsonData": {
    "password": "$PG_PASSWORD"
  },
  "jsonData": {
    "sslmode": "disable",
    "postgresVersion": 1200,
    "timescaledb": false
  },
  "access": "proxy",
  "isDefault": true
}
EOF
)

RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -d "$DATA_SOURCE_JSON" \
  $GRAFANA_URL/api/datasources)

if echo "$RESPONSE" | grep -q '"id"'; then
    echo "✅ Data source created successfully"
    DATA_SOURCE_UID=$(echo "$RESPONSE" | grep -o '"uid":"[^"]*' | cut -d'"' -f4)
    echo "   Data Source UID: $DATA_SOURCE_UID"
else
    if echo "$RESPONSE" | grep -q "already exists"; then
        echo "⚠️  Data source already exists, using existing one"
        # Get existing data source UID
        DATA_SOURCE_UID=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
          "$GRAFANA_URL/api/datasources/name/CrossBridge%20Coverage%20DB" | \
          grep -o '"uid":"[^"]*' | cut -d'"' -f4)
    else
        echo "❌ Failed to create data source"
        echo "   Response: $RESPONSE"
        exit 1
    fi
fi
echo ""

# Step 3: Update dashboard JSON with correct data source UID
echo "Step 3: Preparing dashboard configuration..."

DASHBOARD_FILE="grafana/behavioral_coverage_dashboard.json"
if [ ! -f "$DASHBOARD_FILE" ]; then
    echo "❌ Dashboard file not found: $DASHBOARD_FILE"
    exit 1
fi

# Create temporary dashboard file with data source UID
TEMP_DASHBOARD="/tmp/crossbridge_dashboard_temp.json"

# Read the dashboard and wrap it properly for the API
cat > "$TEMP_DASHBOARD" << EOF
{
  "dashboard": $(cat "$DASHBOARD_FILE" | jq '.dashboard'),
  "overwrite": true,
  "folderId": 0,
  "message": "Imported via setup script"
}
EOF

# Update all data source references
jq --arg uid "$DATA_SOURCE_UID" \
  '.dashboard.panels[].targets[].datasource = {"type": "postgres", "uid": $uid}' \
  "$TEMP_DASHBOARD" > "${TEMP_DASHBOARD}.updated"

mv "${TEMP_DASHBOARD}.updated" "$TEMP_DASHBOARD"

echo "✅ Dashboard prepared with data source UID"
echo ""

# Step 4: Import dashboard
echo "Step 4: Importing dashboard..."

IMPORT_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -d @"$TEMP_DASHBOARD" \
  $GRAFANA_URL/api/dashboards/db)

if echo "$IMPORT_RESPONSE" | grep -q '"uid"'; then
    DASHBOARD_UID=$(echo "$IMPORT_RESPONSE" | grep -o '"uid":"[^"]*' | cut -d'"' -f4)
    DASHBOARD_URL="$GRAFANA_URL/d/$DASHBOARD_UID/crossbridge-behavioral-coverage"
    
    echo "✅ Dashboard imported successfully!"
    echo ""
    echo "========================================="
    echo "🎉 Setup Complete!"
    echo "========================================="
    echo ""
    echo "Dashboard URL:"
    echo "  $DASHBOARD_URL"
    echo ""
    echo "Data Source: CrossBridge Coverage DB"
    echo "  Host: $PG_HOST:$PG_PORT"
    echo "  Database: $PG_DATABASE"
    echo ""
    echo "Next steps:"
    echo "  1. Open dashboard in browser"
    echo "  2. Verify all panels display data"
    echo "  3. Customize time range (top-right)"
    echo "  4. Set auto-refresh interval"
    echo ""
else
    echo "❌ Failed to import dashboard"
    echo "   Response: $IMPORT_RESPONSE"
    rm -f "$TEMP_DASHBOARD"
    exit 1
fi

# Cleanup
rm -f "$TEMP_DASHBOARD"

# Step 5: Test data source connection
echo "Step 5: Testing data source connection..."
TEST_RESPONSE=$(curl -s -X GET \
  -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  "$GRAFANA_URL/api/datasources/uid/$DATA_SOURCE_UID")

if echo "$TEST_RESPONSE" | grep -q "CrossBridge Coverage DB"; then
    echo "✅ Data source connection verified"
else
    echo "⚠️  Could not verify data source connection"
fi

echo ""
echo "Setup script completed!"
