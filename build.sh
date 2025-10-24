#!/bin/bash

echo "Building frontend..."
cd frontend-backup-for-rebuild || exit 1
npm install
npm run build
echo "Copying frontend to static..."
cp -r dist/* ../static/
echo "Frontend build complete!"
