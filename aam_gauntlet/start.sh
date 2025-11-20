#!/bin/bash

# AAM Gauntlet Quick Start Script

echo "🚀 Starting AAM Gauntlet Demo System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Stop any existing containers
echo "🔄 Stopping any existing containers..."
docker-compose down

# Build and start the system
echo "🏗️ Building and starting containers..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check API Farm
if curl -f http://localhost:8001/admin/status &> /dev/null; then
    echo "✅ API Farm is running on port 8001"
else
    echo "❌ API Farm failed to start"
fi

# Check AAM Backend
if curl -f http://localhost:8002/health &> /dev/null; then
    echo "✅ AAM Backend is running on port 8002"
else
    echo "❌ AAM Backend failed to start"
fi

# Check Frontend
if curl -f http://localhost:3000 &> /dev/null; then
    echo "✅ Frontend is running on port 3000"
else
    echo "⚠️ Frontend may still be starting..."
fi

echo ""
echo "🎉 AAM Gauntlet is ready!"
echo ""
echo "📊 Access the UI: http://localhost:3000"
echo "🔧 API Farm Admin: http://localhost:8001/docs"
echo "🔧 AAM Backend API: http://localhost:8002/docs"
echo ""
echo "To stop the system: docker-compose down"
echo "To view logs: docker-compose logs -f"
echo ""
echo "Happy stress testing! 🚀"