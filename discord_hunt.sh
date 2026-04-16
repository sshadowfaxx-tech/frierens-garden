#!/bin/bash
# Discord Wallet Hunter - Quick Command Wrapper
# Usage from Discord: !hunt <PAIR_ADDRESS>

PAIR=$1

if [ -z "$PAIR" ]; then
    echo "❌ Usage: !hunt <PAIR_ADDRESS>"
    echo "Example: !hunt 58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
    exit 1
fi

# Validate Solana address format
if [ ${#PAIR} -lt 32 ] || [ ${#PAIR} -gt 44 ]; then
    echo "❌ Invalid address format. Make sure you're using a pair address (not token name)."
    exit 1
fi

echo "🔍 Running Wallet Hunter..."
echo "⏳ This may take 30-60 seconds..."
echo ""

# Run the hunter and capture output
OUTPUT=$(cd /root/.openclaw/workspace && python3 wallet_hunter_v2.py "$PAIR" --chain solana --top 10 --output /tmp/last_hunt.json 2>&1)

# Check if results exist
if [ -f /tmp/last_hunt.json ]; then
    # Parse and format for Discord
    python3 << 'EOF'
import json
import sys

try:
    with open('/tmp/last_hunt.json', 'r') as f:
        data = json.load(f)
    
    profiles = data.get('detailed_profiles', [])
    if not profiles:
        print("❌ No profitable wallets found.")
        sys.exit(0)
    
    diamond_hands = [p for p in profiles if 'diamond' in p.get('wallet_type', '').lower()]
    
    print(f"🔍 **Wallet Hunter Results**")
    print(f"```")
    print(f"Pair: {data.get('token_address', 'Unknown')[:25]}...")
    print(f"```")
    print(f"")
    print(f"📊 **Summary:** {len(data.get('early_birds', []))} Early Birds | 💎 {len(diamond_hands)} Diamond Hands | 📈 {len(profiles)} Total")
    print(f"")
    print(f"🏆 **Top 5 Wallets:**")
    print(f"```")
    
    for i, w in enumerate(profiles[:5], 1):
        wt = w.get('wallet_type', 'Unknown')
        if len(wt) > 28:
            wt = wt[:28] + "..."
        
        buys = w.get('buy_count', 0)
        sells = w.get('sell_count', 0)
        roi = w.get('roi_percentage', 0)
        pnl = w.get('realized_pnl', 0)
        addr = w.get('address', 'Unknown')[:16]
        
        emoji = "🟢" if roi > 0 else "🔴" if roi < 0 else "⚪"
        
        print(f"#{i} {emoji} {wt}")
        print(f"   {addr}...")
        print(f"   B:{buys}/S:{sells} | ROI:{roi:.1f}% | PnL:{pnl:.2f}SOL")
        print(f"")
    
    print(f"```")
    print(f"")
    print(f"💡 Diamond hands 💎 = only buys (HODLing)")
    
except Exception as e:
    print(f"❌ Error parsing results: {e}")
EOF
else
    echo "❌ Hunt failed. Pair may not be in DexCheck database."
fi
