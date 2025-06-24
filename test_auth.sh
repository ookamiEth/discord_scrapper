#!/bin/bash

echo "1. Testing backend OAuth endpoints..."
echo "====================================="

# Get OAuth login URL
echo "Getting OAuth login URL..."
curl -s http://localhost:8000/api/v1/auth/discord/login | jq .

echo -e "\n2. Generating test JWT token..."
echo "====================================="

# Generate test JWT token
TEST_URL=$(docker-compose exec -T backend python -c "
from auth import create_access_token
token = create_access_token({'sub': 'test123', 'discord_id': '123456789', 'username': 'testuser'})
print(f'http://localhost:3000/auth/callback?token={token}')
" 2>/dev/null)

echo "Test URL generated:"
echo "$TEST_URL"

echo -e "\n3. Testing direct API access with token..."
echo "====================================="

# Extract just the token
TOKEN=$(echo "$TEST_URL" | sed 's/.*token=//')
echo "Token: ${TOKEN:0:50}..."

# Test the /me endpoint with the token
echo -e "\nTesting /me endpoint with generated token:"
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me | jq .

echo -e "\n4. Instructions:"
echo "====================================="
echo "1. Open browser DevTools (F12) and go to Console tab"
echo "2. Open this URL in your browser: $TEST_URL"
echo "3. Check the console logs to see what happens"
echo "4. Also check Network tab to see API calls"
echo ""
echo "To test the real OAuth flow:"
echo "1. Restart the frontend: docker-compose restart frontend"
echo "2. Clear browser cache/localStorage"
echo "3. Try logging in again with Discord"
echo "4. Watch the browser console for debug messages"