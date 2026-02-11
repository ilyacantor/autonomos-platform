#!/bin/bash
set -e

echo "=========================================="
echo "AutonomOS Deployment Build"
echo "=========================================="

# Step 1: Install Python dependencies
echo ""
echo "Step 1/3: Installing Python dependencies..."
bash install-dependencies.sh

# Step 2: Build frontend
echo ""
echo "Step 2/3: Building frontend..."
cd frontend || exit 1

if [ -f "package-lock.json" ]; then
    npm ci --legacy-peer-deps --production=false
else
    npm install --legacy-peer-deps
fi

npm run build

cd ..

# Step 3: Clean up caches and temporary files
echo ""
echo "Step 3/3: Cleaning up build artifacts..."
rm -rf ~/.cache/pip
rm -rf /tmp/pip-*
rm -rf frontend/.vite
rm -rf frontend/node_modules/.cache

echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo "Frontend bundle: $(ls -1 static/assets/index-*.js 2>/dev/null | head -1 | xargs basename)"
echo "Python packages: $(pip list 2>/dev/null | wc -l) installed"
