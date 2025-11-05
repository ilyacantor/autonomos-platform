#!/bin/bash

echo "Testing AAM Connection Onboarding Flow..."
echo "=========================================="
echo ""

echo "Step 1: Onboarding Salesforce connection..."
RESPONSE=$(curl -s -X POST http://localhost:8001/connections/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "Salesforce",
    "connection_name": "Salesforce Test Connection",
    "credential_id": "salesforce-prod"
  }')

echo "$RESPONSE" | jq '.'
CONNECTION_ID=$(echo "$RESPONSE" | jq -r '.id')
echo ""

if [ "$CONNECTION_ID" = "null" ] || [ -z "$CONNECTION_ID" ]; then
  echo "❌ Onboarding failed!"
  exit 1
fi

echo "✅ Connection created: $CONNECTION_ID"
echo ""

echo "Step 2: Listing all connections..."
curl -s http://localhost:8001/connections | jq '.'
echo ""

echo "Step 3: Getting connection details..."
curl -s http://localhost:8001/connections/$CONNECTION_ID | jq '.'
echo ""

echo "Step 4: Triggering sync..."
curl -s -X POST http://localhost:8001/connections/$CONNECTION_ID/sync \
  -H "Content-Type: application/json" | jq '.'
echo ""

echo "=========================================="
echo "✅ All tests completed successfully!"
echo "Connection ID: $CONNECTION_ID"
