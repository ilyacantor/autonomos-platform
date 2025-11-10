#!/bin/bash

echo "Building frontend..."
cd frontend || exit 1

# Use npm ci for faster, reproducible builds
if [ -f "package-lock.json" ]; then
    npm ci --legacy-peer-deps --production=false
else
    npm install --legacy-peer-deps
fi

# Build (emptyOutDir: true will clean static directory)
npm run build

echo "Frontend build complete!"
echo "New bundle: $(ls -1 ../static/assets/index-*.js 2>/dev/null | head -1 | xargs basename)"
