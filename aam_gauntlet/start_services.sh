#!/bin/bash

echo "🚀 Starting AAM Gauntlet Services..."

# Install Python dependencies for API Farm
echo "📦 Installing API Farm dependencies..."
cd aam_gauntlet/api_farm
pip install -q -r requirements.txt

# Install Python dependencies for AAM Backend
echo "📦 Installing AAM Backend dependencies..."
cd ../aam
pip install -q -r requirements.txt

# Install Node dependencies for UI
echo "📦 Installing UI dependencies..."
cd ../ui
npm install --silent

# Start API Farm (port 8001)
echo "🚀 Starting API Farm on port 8001..."
cd ../api_farm
python main.py &
API_FARM_PID=$!
sleep 2

# Start AAM Backend (port 8002)
echo "🚀 Starting AAM Backend on port 8002..."
cd ../aam
python api.py &
AAM_PID=$!
sleep 2

# Start UI (port 3001)
echo "🚀 Starting UI on port 3001..."
cd ../ui
npm run dev &
UI_PID=$!

echo "✅ AAM Gauntlet services started!"
echo "   - API Farm: http://localhost:8001 (PID: $API_FARM_PID)"
echo "   - AAM Backend: http://localhost:8002 (PID: $AAM_PID)"
echo "   - UI: http://localhost:3001 (PID: $UI_PID)"
echo ""
echo "To stop services: kill $API_FARM_PID $AAM_PID $UI_PID"

# Keep the script running
wait