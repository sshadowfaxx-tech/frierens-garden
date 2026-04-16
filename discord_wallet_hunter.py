#!/usr/bin/env python3
"""
Discord Wallet Hunter Bot
Simple command handler for running wallet hunter from Discord
"""

import os
import sys
import json
import subprocess
import asyncio
from datetime import datetime

# Add workspace to path
sys.path.insert(0, '/root/.openclaw/workspace')

async def run_wallet_hunter(pair_address: str, chain: str = "solana") -> dict:
    """Run wallet hunter and return results."""
    
    output_file = f"/tmp/wallet_hunt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Run the hunter
    cmd = [
        "python3", 
        "/root/.openclaw/workspace/wallet_hunter_v2.py",
        pair_address,
        "--chain", chain,
        "--top", "10",
        "--output", output_file
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        
        # Read results
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                data = json.load(f)
            os.remove(output_file)  # Clean up
            return data
        else:
            return {"error": "No results file created", "stderr": result.stderr}
            
    except subprocess.TimeoutExpired:
        return {"error": "Wallet hunter timed out (120s)"}
    except Exception as e:
        return {"error": str(e)}


def format_discord_response(data: dict) -> str:
    """Format results for Discord message."""
    
    if "error" in data:
        return f"❌ **Error:** {data['error']}"
    
    profiles = data.get("detailed_profiles", [])
    if not profiles:
        return "❌ No profitable wallets found for this pair."
    
    # Count diamond hands
    diamond_hands = [p for p in profiles if 'diamond' in p.get('wallet_type', '').lower()]
    
    # Build response
    lines = [
        f"🔍 **Wallet Hunter Results**",
        f"Pair: `{data.get('token_address', 'Unknown')[:20]}...`",
        f"",
        f"📊 **Summary:**",
        f"• Early Birds: {len(data.get('early_birds', []))}",
        f"• Diamond Hands: {len(diamond_hands)}",
        f"• Quality Wallets: {len(profiles)}",
        f"",
        f"🏆 **Top Wallets:**",
        f"```"
    ]
    
    # Top 5 wallets
    for i, wallet in enumerate(profiles[:5], 1):
        wallet_type = wallet.get('wallet_type', 'Unknown')
        buys = wallet.get('buy_count', 0)
        sells = wallet.get('sell_count', 0)
        roi = wallet.get('roi_percentage', 0)
        pnl = wallet.get('realized_pnl', 0)
        balance = wallet.get('sol_balance', 0)
        address = wallet.get('address', 'Unknown')[:12]
        
        # Emoji based on performance
        if roi > 0:
            emoji = "🟢"
        elif roi < 0:
            emoji = "🔴"
        else:
            emoji = "⚪"
        
        lines.append(f"#{i} {emoji} {wallet_type[:20]}")
        lines.append(f"   {address}...")
        lines.append(f"   Buys: {buys} | Sells: {sells} | ROI: {roi:.1f}%")
        lines.append(f"   PnL: {pnl:.2f} SOL | Balance: {balance:.2f} SOL")
        lines.append("")
    
    lines.append("```")
    lines.append("")
    lines.append("💡 **Tip:** Diamond hands 💎 = buys only (HODLing)")
    
    return "\n".join(lines)


# Main execution for Discord integration
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("pair", help="Pair address")
    parser.add_argument("--chain", default="solana", help="Chain")
    args = parser.parse_args()
    
    result = asyncio.run(run_wallet_hunter(args.pair, args.chain))
    print(format_discord_response(result))
