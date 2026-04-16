#!/bin/bash
# ShadowHunter Auto-Hunter Launcher
# Starts continuous momentum monitoring with auto-scan

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              🤖 SHADOWHUNTER AUTO-HUNTER                        ║"
echo "║        Continuous Momentum Detection + Auto-Scan                ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if running in Docker or locally
if [ -f /.dockerenv ]; then
    echo "📦 Running inside Docker container"
    IN_DOCKER=true
else
    echo "🖥️  Running locally"
    IN_DOCKER=false
fi

# Configuration
INTERVAL=${1:-5}  # Default 5 minutes
THRESHOLD=${2:-60}  # Default momentum score 60

echo "⚙️  Configuration:"
echo "   • Check interval: ${INTERVAL} minutes"
echo "   • Momentum threshold: ${THRESHOLD} score"
echo ""

# Check environment
echo "🔍 Checking environment..."

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "   ⚠️  TELEGRAM_BOT_TOKEN not set - alerts will log to console only"
else
    echo "   ✅ Telegram bot configured"
fi

if [ -z "$DEXCHECK_API_KEY" ]; then
    echo "   ⚠️  DEXCHECK_API_KEY not set - using default"
else
    echo "   ✅ DexCheck API configured"
fi

if [ -z "$HELIUS_API_KEY" ]; then
    echo "   ⚠️  HELIUS_API_KEY not set - hidden exit detection disabled"
else
    echo "   ✅ Helius API configured"
fi

echo ""
echo "🚀 Starting Auto-Hunter..."
echo "   Press Ctrl+C to stop"
echo ""

# Run the hunter
exec python3 auto_hunter.py --interval $INTERVAL --threshold $THRESHOLD
