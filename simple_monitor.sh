#!/bin/bash
# Simple agent monitor using curl and basic tools

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-shadowhunter}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"

echo "Agent Monitor Started - $(date)"
echo "Checking for wallet activity every 15 seconds..."
echo ""

while true; do
    # Query for recent cluster activity (using psql if available, otherwise skip)
    echo "[$(date '+%H:%M:%S')] Checking database..."
    
    # Check if we can query via a simple HTTP endpoint or file
    # For now, this is a placeholder that logs activity
    
    sleep 15
done
