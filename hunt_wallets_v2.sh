#!/bin/bash
# Smart Money Wallet Hunter v2 - Quick Trigger
# Usage: ./hunt_wallets_v2.sh <PAIR_ADDRESS> [CHAIN]
# 
# IMPORTANT: This script requires POOL/PAIR addresses, NOT token addresses!
# To find pair addresses:
#   1. Go to https://dexscreener.com/solana
#   2. Search for your token
#   3. Click on the pair (e.g., "TOKEN/SOL")
#   4. The URL shows: dexscreener.com/solana/<THIS_IS_THE_PAIR_ADDRESS>
#
# Example pair addresses:
#   - SOL-USDC Raydium: 58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2

PAIR=$1
CHAIN=${2:-"solana"}
OUTPUT_DIR="/root/.openclaw/workspace/wallet_hunter_results"

# Check arguments
if [ -z "$PAIR" ]; then
    echo "❌ Error: Please provide a PAIR address (not token address)"
    echo ""
    echo "Usage: ./hunt_wallets_v2.sh <PAIR_ADDRESS> [CHAIN]"
    echo ""
    echo "⚠️  IMPORTANT: Use POOL/PAIR addresses, NOT token mint addresses!"
    echo ""
    echo "How to find pair addresses:"
    echo "  1. Go to https://dexscreener.com/solana"
    echo "  2. Search for your token"
    echo "  3. Click on the pair (e.g., 'TOKEN/SOL')"
    echo "  4. Copy the address from the URL"
    echo ""
    echo "Example:"
    echo "  ./hunt_wallets_v2.sh 58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
    exit 1
fi

# Validate address length (Solana addresses are 32-44 chars)
if [ ${#PAIR} -lt 32 ] || [ ${#PAIR} -gt 44 ]; then
    echo "⚠️  Warning: Address length (${#PAIR}) doesn't look like a Solana address"
    echo "   Make sure you're using a pair/pool address, not a token name"
    echo ""
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate timestamped filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/hunt_results_${TIMESTAMP}.json"

echo "🚀 Smart Money Wallet Hunter v2"
echo "==============================="
echo ""
echo "🔍 Pair Address: $PAIR"
echo "⛓️  Chain: $CHAIN"
echo "📁 Output: $OUTPUT_FILE"
echo ""
echo "💡 Filtering: Ignoring wallets with sells-only (dumpers)"
echo "💡 Highlighting: Diamond hands (buys only, no sells)"
echo ""

# Run the hunter
python3 /root/.openclaw/workspace/wallet_hunter_v2.py \
    "$PAIR" \
    --chain "$CHAIN" \
    --top 20 \
    --output "$OUTPUT_FILE"

# Check if results were created
if [ -f "$OUTPUT_FILE" ]; then
    echo ""
    echo "✅ Hunt complete!"
    
    # Extract and display summary
    echo ""
    python3 -c "
import json
with open('$OUTPUT_FILE') as f:
    data = json.load(f)
    wallets = data.get('detailed_profiles', [])
    diamond_hands = [w for w in wallets if 'diamond' in w['wallet_type'].lower()]
    
    print(f'💎 Diamond Hands: {len(diamond_hands)}')
    print(f'📊 Total Quality Wallets: {len(wallets)}')
    print()
    print('🏆 Top 5 Wallets:')
    print('-' * 60)
    for i, w in enumerate(wallets[:5], 1):
        emoji = '💎' if 'diamond' in w['wallet_type'].lower() else '  '
        print(f\"{emoji} #{i} {w['wallet_type'][:30]}\")
        print(f\"      {w['address'][:25]}...\")
        print(f\"      Buys: {w['buy_count']} | Sells: {w['sell_count']} | Score: {w['dexcheck_score']:.1f}\")
        print()
" 
fi
