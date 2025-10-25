#!/bin/bash

echo "Building frontend..."
cd frontend-backup-for-rebuild || exit 1
npm install --legacy-peer-deps
npm run build
echo "Copying frontend to static..."
rm -rf ../static/assets/index-*.js ../static/assets/index-*.css
cp -r dist/* ../static/
echo "Frontend build complete!"
echo "New bundle: $(ls -1 dist/assets/index-*.js | head -1 | xargs basename)"
