#!/bin/bash

# Complete development environment startup script
# Starts Redis, web server, and Celery worker

echo "🚀 Starting IAM Lifecycle Demo development environment..."

# Set environment variables for local development
export POSTGRES_URL="sqlite:///./test.db"
export REDIS_URL="redis://localhost:6379/0"
export CONNECTOR_MODE="MOCK"

echo "📦 Starting Redis server..."
brew services start redis

echo "⚙️  Activating Python virtual environment..."
source venv/bin/activate

echo "🔄 Starting Celery worker in background..."
celery -A app.workers.tasks worker --loglevel=info &
CELERY_PID=$!

echo "🌐 Starting web server..."
echo "Dashboard will be available at: http://localhost:8000/dashboard/"
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo "🛑 Stopping services..."
    kill $CELERY_PID 2>/dev/null
    pkill -f uvicorn
    echo "✅ All services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT

# Start web server in foreground
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
