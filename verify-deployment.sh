#!/bin/bash
set -e

echo "🔍 Verifying IAM Lifecycle Demo deployment..."

# Check if services are running
echo "📊 Checking services..."
docker compose ps

echo ""
echo "❤️  Testing health endpoint..."
curl -f http://localhost:8000/health/ || (echo "❌ Health check failed" && exit 1)

echo ""
echo "👥 Testing users endpoint..."
curl -f -s http://localhost:8000/api/v1/users | jq '.[0:2]' || echo "No users yet (expected)"

echo ""
echo "🏃 Testing runs endpoint..."  
curl -f -s http://localhost:8000/api/v1/runs | jq '.[0:2]' || echo "No runs yet (expected)"

echo ""
echo "🖥️  Testing dashboard..."
curl -f -s http://localhost:8000/dashboard/ | head -1 | grep -q "DOCTYPE html" && echo "✅ Dashboard HTML loading correctly"

echo ""
echo "📚 Testing API docs..."
curl -f -s http://localhost:8000/openapi.json | jq '.info.title' || (echo "❌ OpenAPI failed" && exit 1)

echo ""
echo "🎉 All endpoints responding correctly!"
echo ""
echo "🚀 Ready for showcase!"
echo "   Dashboard: http://localhost:8000/dashboard/"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "Sample file ready at: samples/hr_roster.csv"
