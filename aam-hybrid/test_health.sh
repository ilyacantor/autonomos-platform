#!/bin/bash

echo "Testing AAM Hybrid Services Health..."
echo "======================================"
echo ""

echo "1. Testing Orchestrator (Port 8001)..."
curl -s http://localhost:8001/health | jq '.'
echo ""

echo "2. Testing Auth Broker (Port 8002)..."
curl -s http://localhost:8002/health | jq '.'
echo ""

echo "3. Testing Drift Repair Agent (Port 8003)..."
curl -s http://localhost:8003/health | jq '.'
echo ""

echo "4. Testing Schema Observer (Port 8004)..."
curl -s http://localhost:8004/health | jq '.'
echo ""

echo "5. Testing RAG Engine (Port 8005)..."
curl -s http://localhost:8005/health | jq '.'
echo ""

echo "======================================"
echo "All health checks complete!"
