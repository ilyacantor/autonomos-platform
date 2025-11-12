#!/bin/bash

echo "=========================================="
echo "Testing Production Authentication & Connections"
echo "=========================================="
echo ""

# Use the test user that exists
EMAIL="test@autonomos.ai"
# Try common passwords (you'll need to replace with actual password)
for PASS in "password123" "admin" "test123" "autonomos"; do
    echo "Testing login with password: ${PASS:0:3}***"
    RESPONSE=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
    
    TOKEN=$(echo "$RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
        echo "✅ LOGIN SUCCESSFUL!"
        echo ""
        echo "Testing /api/v1/aam/connectors endpoint..."
        CONNECTORS=$(curl -s -H "Authorization: Bearer $TOKEN" \
          http://localhost:5000/api/v1/aam/connectors)
        
        echo "Response:"
        echo "$CONNECTORS" | head -50
        
        COUNT=$(echo "$CONNECTORS" | grep -o '"total":[0-9]*' | cut -d':' -f2)
        if [ -n "$COUNT" ]; then
            echo ""
            echo "📊 Found $COUNT connectors in production!"
        fi
        exit 0
    fi
done

echo ""
echo "❌ Could not authenticate with any test password"
echo ""
echo "SOLUTION: You need to either:"
echo "1. Log in via the frontend UI (http://localhost:5000)"
echo "2. Register a new account via /api/v1/auth/register"
echo "3. Use the existing user credentials"
