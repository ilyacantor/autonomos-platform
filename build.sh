#!/bin/bash

echo "Building frontend..."
cd frontend || exit 1
npm install --legacy-peer-deps
echo "Cleaning old assets..."
rm -f ../static/assets/index-*.js ../static/assets/index-*.css
npm run build
echo "Frontend build complete!"
echo "New bundle: $(ls -1 ../static/assets/index-*.js 2>/dev/null | head -1 | xargs basename)"
