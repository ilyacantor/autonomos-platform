#!/bin/bash
set -e

echo "==================================="
echo "Installing Python Dependencies"
echo "==================================="

echo ""
echo "Installing application dependencies..."
pip install --no-cache-dir -r requirements.txt

echo ""
echo "Cleaning up pip cache..."
rm -rf ~/.cache/pip
rm -rf /tmp/pip-*

echo ""
echo "==================================="
echo "Installation complete!"
echo "==================================="
