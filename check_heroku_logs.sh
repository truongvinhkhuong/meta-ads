#!/bin/bash

# Script to check Heroku logs and diagnose connection issues

echo "=== HEROKU LOGS DIAGNOSTIC ==="

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Error: Heroku CLI not found. Please install it first."
    exit 1
fi

# Check if we're in a Heroku app directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run from the project root directory."
    exit 1
fi

echo "🔍 Checking Heroku app status..."
heroku ps

echo -e "\n🔍 Checking recent errors..."
heroku logs --tail --num=100 | grep -i "error\|exception\|timeout\|connection\|failed" | tail -20

echo -e "\n🔍 Checking refresh-related logs..."
heroku logs --tail --num=200 | grep -i "refresh\|facebook\|api" | tail -20

echo -e "\n🔍 Checking app health..."
curl -s https://your-app-name.herokuapp.com/api/health || echo "❌ Health check failed"

echo -e "\n🔍 Checking environment variables..."
heroku config | grep -E "(TOKEN|TIMEOUT|RETRY|CONCURRENCY)"

echo -e "\n🔍 Running connection test..."
heroku run python test_heroku_connection.py

echo -e "\n✅ Diagnostic complete!"
echo "📋 For more detailed logs, run: heroku logs --tail"
