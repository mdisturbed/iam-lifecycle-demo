#!/bin/bash

# Development server startup script
# Uses SQLite database for local development

echo "Starting IAM Lifecycle Demo development server..."
echo "Using SQLite database for local development"

# Set environment variables for local development
export POSTGRES_URL="sqlite:///./test.db"
export REDIS_URL="redis://localhost:6379/0"
export CONNECTOR_MODE="MOCK"

# Activate virtual environment and start server
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
