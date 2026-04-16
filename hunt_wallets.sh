#!/bin/bash
# Smart Money Wallet Hunter - Quick Trigger Script
# Usage: ./hunt_wallets.sh [TOKEN_ADDRESS] [NUM_WALLETS]

TOKEN=${1:-""}
COUNT=${2:-10}
OUTPUT_DIR="/root/.openclaw/workspace/wallet_hunter_results"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate timestamped filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/hunt_results_$TIMESTAMP.json"

echo "🚀 Smart Money Wallet Hunter"
echo "============================"
echo ""

# Check for Helius API key
if [ -z "$HELIUS_API_KEY" ]; then
    echo "❌ Error: HELIUS_API_KEY not set"
    echo "   Get a free key at: https://www.helius.dev/"
    echo "   Then run: export HELIUS_API_KEY='your_key_here'"
    exit 1
fi

echo "✓ Helius API key found"
echo "✓ Output will be saved to: $OUTPUT_FILE"
echo ""

# Build command
if [ -n "$TOKEN" ]; then
    echo "🔍 Hunting wallets from token: $TOKEN"
    python3 /root/.openclaw/workspace/wallet_hunter.py \
        --seed "$TOKEN" \
        --top "$COUNT" \
        --output "$OUTPUT_FILE"
else
    echo "🔍 Running general hunt (no seed token)"
    python3 /root/.openclaw/workspace/wallet_hunter.py \
        --top "$COUNT" \
        --output "$OUTPUT_FILE"
fi

# Check if results were created
if [ -f "$OUTPUT_FILE" ]; then
    echo ""
    echo "✅ Hunt complete!"
    echo "📁 Results: $OUTPUT_FILE"
    echo ""
    
    # Show top 3 wallets
    echo "🏆 Top 3 Wallets Found:"
    python3 -c "
import json
with open('$OUTPUT_FILE') as f:
    data = json.load(f)
    wallets = data.get('profitable_wallets', [])
    for i, w in enumerate(wallets[:3], 1):
        print(f\"{i}. {w['address'][:20]}... | Win Rate: {w['win_rate']}% | Score: {w['score']}\")
"
else
    echo "❌ No results file created"
fi
