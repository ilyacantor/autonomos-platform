#!/bin/bash
set -e

echo "==================================="
echo "Installing Python Dependencies"
echo "==================================="

# Step 1: Install CPU-only PyTorch (prevents 4-5GB CUDA dependencies)
echo ""
echo "Step 1/3: Installing CPU-only PyTorch..."
pip install --no-cache-dir -r requirements-cpu.txt

# Step 2: Install all other dependencies
echo ""
echo "Step 2/3: Installing application dependencies..."
pip install --no-cache-dir -r requirements.txt

# Step 3: Clean up pip cache
echo ""
echo "Step 3/3: Cleaning up pip cache..."
rm -rf ~/.cache/pip
rm -rf /tmp/pip-*

echo ""
echo "==================================="
echo "Installation complete!"
echo "==================================="
pip list | grep -E "torch|sentence-transformers|nvidia" || echo "No GPU packages found (good!)"
