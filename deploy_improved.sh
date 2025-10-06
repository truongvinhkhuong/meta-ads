#!/bin/bash

# Improved deployment script for Heroku with connection testing

echo "=== DEPLOYING TO HEROKU WITH IMPROVEMENTS ==="

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run from the project root directory."
    exit 1
fi

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Error: Heroku CLI not found. Please install it first."
    exit 1
fi

# Set Heroku environment variables for better performance
echo "🔧 Setting Heroku environment variables..."

heroku config:set REQUEST_TIMEOUT=60
heroku config:set MAX_RETRIES=5
heroku config:set BACKOFF_FACTOR=0.5
heroku config:set SKIP_INSIGHTS=false
heroku config:set WEB_CONCURRENCY=2
heroku config:set WORKER_CONNECTIONS=1000

# Deploy to Heroku
echo "🚀 Deploying to Heroku..."
git add .
git commit -m "Improve connection handling and error management for Heroku production"
git push heroku main

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
sleep 10

# Test the deployment
echo "🧪 Testing deployment..."

# Test health endpoint
echo "Testing health endpoint..."
curl -f https://your-app-name.herokuapp.com/api/health || {
    echo "❌ Health check failed"
    exit 1
}

# Test connection
echo "Testing Facebook API connection..."
python test_heroku_connection.py || {
    echo "❌ Connection test failed"
    exit 1
}

echo "✅ Deployment completed successfully!"
echo "🌐 Your app is running at: https://your-app-name.herokuapp.com"

# Show logs
echo "📋 Recent logs:"
heroku logs --tail --num=50
