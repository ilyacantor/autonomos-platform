#!/bin/bash

# Integration script for frontend build
echo "=== Frontend Integration Script ==="

FRONTEND_BUILD="/home/runner/workspace/frontend_build.tar.gz"
STATIC_DIR="/home/runner/workspace/static"

# Check if build file exists
if [ ! -f "$FRONTEND_BUILD" ]; then
    echo "❌ Error: Frontend build file not found at $FRONTEND_BUILD"
    echo "Please upload the frontend build to this location first."
    exit 1
fi

echo "✅ Frontend build file found"

# Remove existing static directory if it exists
if [ -d "$STATIC_DIR" ]; then
    echo "🗑️  Removing existing static directory..."
    rm -rf "$STATIC_DIR"
fi

# Extract the build
echo "📦 Extracting frontend build..."
cd /home/runner/workspace
tar -xzf frontend_build.tar.gz

# Check what was extracted
if [ -d "dist" ]; then
    echo "✅ Found dist/ directory"
    mv dist static
    echo "✅ Renamed dist/ to static/"
elif [ -d "build" ]; then
    echo "✅ Found build/ directory"
    mv build static
    echo "✅ Renamed build/ to static/"
elif [ -d "static" ]; then
    echo "✅ Found static/ directory (already named correctly)"
else
    echo "❌ Error: No dist/, build/, or static/ directory found after extraction"
    echo "Contents of extracted archive:"
    ls -la
    exit 1
fi

# Verify index.html exists
if [ -f "$STATIC_DIR/index.html" ]; then
    echo "✅ index.html found in static directory"
else
    echo "⚠️  Warning: index.html not found in static directory"
    echo "Contents of static directory:"
    ls -la "$STATIC_DIR"
fi

echo ""
echo "=== Integration Complete! ==="
echo "Static files located at: $STATIC_DIR"
echo ""
echo "Next steps:"
echo "1. Restart the FastAPI server"
echo "2. Visit the public URL to see the unified app"
echo "3. API routes remain available at /api/v1/*"
