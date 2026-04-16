#!/usr/bin/env python3
"""
Debug script to check DexCheck data structure
"""
import asyncio
import aiohttp
import os

DEXCHECK_API_KEY = os.getenv('DEXCHECK_API_KEY', 'BostDZLJBBPu44iXpiOneGprXhTpSFCg')

async def test_dexcheck():
    """Test DexCheck API to see actual data structure."""
    pair = "3KFCgJ5R3zshW8hTDbzjSrrKSRYmKvsMfhc4Vo4iddxD"
    
    url = "https://api.dexcheck.ai/api/v1/blockchain/early-birds"
    params = {"chain": "solana", "pair": pair, "limit": 100}
    headers = {"X-API-Key": DEXCHECK_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            data = await resp.json()
            
            if isinstance(data, list):
                early_birds = data
            else:
                early_birds = data.get("data", [])
            
            print(f"Total early birds: {len(early_birds)}")
            
            if early_birds:
                # Print first wallet's data structure
                first = early_birds[0]
                print("\n=== First Wallet Data ===")
                for key, value in first.items():
                    print(f"  {key}: {value}")
                
                # Check high ROI + PnL wallets
                high_roi = [b for b in early_birds if 
                            ((b.get("roi", 0) or b.get("unrealized_roi", 0) or 0) > 100) and
                            ((b.get("pnl", 0) or b.get("unrealized_pnl", 0) or 0) >= 5)]
                
                print(f"\n=== High ROI + PnL≥5 SOL: {len(high_roi)} ===")
                
                for i, w in enumerate(high_roi[:5]):
                    roi = w.get("roi", 0) or w.get("unrealized_roi", 0) or 0
                    pnl = w.get("pnl", 0) or w.get("unrealized_pnl", 0) or 0
                    buys = w.get("buy_trade_count", 0) or w.get("buyCount", 0) or 0
                    sells = w.get("sell_trade_count", 0) or w.get("sellCount", 0) or 0
                    winrate = w.get("winRate", 0) or 0
                    
                    print(f"\nWallet {i+1}: {w.get('maker', w.get('address', 'Unknown'))[:20]}...")
                    print(f"  ROI: {roi}")
                    print(f"  PnL: {pnl}")
                    print(f"  Buys: {buys}")
                    print(f"  Sells: {sells}")
                    print(f"  Winrate: {winrate}")
                    
                    # Calculate insider score manually
                    score = 0
                    if roi >= 1000: score += 30
                    elif roi >= 500: score += 25
                    elif roi >= 300: score += 20
                    elif roi >= 200: score += 15
                    elif roi >= 100: score += 10
                    elif pnl > 10: score += 10
                    elif pnl > 0: score += 5
                    
                    if buys > 0 and sells == 0: score += 25
                    elif buys > sells * 3: score += 20
                    elif buys > sells: score += 8
                    
                    print(f"  Calculated Score: {score}")

if __name__ == "__main__":
    asyncio.run(test_dexcheck())
