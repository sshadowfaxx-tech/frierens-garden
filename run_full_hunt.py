#!/usr/bin/env python3
"""ShadowHunter Full Workflow Execution"""
import asyncio
import aiohttp
from datetime import datetime

async def full_hunt():
    print('='*70)
    print('🎯 SHADOWHUNTER FULL WORKFLOW EXECUTION')
    print('='*70)
    print(f'⏰ Start time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # Phase 1: Momentum Scan
    print('🔍 PHASE 1: Scanning ecosystem for momentum...')
    print('-'*70)
    
    async with aiohttp.ClientSession() as session:
        url = 'https://api.dexscreener.com/latest/dex/search?q=SOL'
        
        try:
            async with session.get(url, timeout=15) as resp:
                data = await resp.json()
                pairs = data.get('pairs', [])
                
                print(f'📊 Total pairs found: {len(pairs)}')
                
                # Filter and score
                high_momentum = []
                for pair in pairs:
                    if pair.get('chainId') != 'solana':
                        continue
                    
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                    if liquidity < 10000:  # Min $10K
                        continue
                    
                    price_change_1h = float(pair.get('priceChange', {}).get('h1', 0) or 0)
                    price_change_5m = float(pair.get('priceChange', {}).get('m5', 0) or 0)
                    volume_24h = float(pair.get('volume', {}).get('h24', 0) or 0)
                    market_cap = float(pair.get('marketCap', 0) or 0)
                    
                    # Momentum score
                    score = min(abs(price_change_1h) * 2, 50) + min(volume_24h / 10000, 50)
                    
                    if score >= 40:  # Lower threshold for demo
                        high_momentum.append({
                            'symbol': pair.get('baseToken', {}).get('symbol', '???'),
                            'name': pair.get('baseToken', {}).get('name', 'Unknown'),
                            'address': pair.get('baseToken', {}).get('address', ''),
                            'pair': pair.get('pairAddress', ''),
                            'price': pair.get('priceUsd', 0),
                            'change_1h': price_change_1h,
                            'change_5m': price_change_5m,
                            'volume': volume_24h,
                            'liquidity': liquidity,
                            'market_cap': market_cap,
                            'score': score,
                            'created_at': pair.get('pairCreatedAt')
                        })
                
                # Sort by score
                high_momentum.sort(key=lambda x: x['score'], reverse=True)
                
                print(f'🎯 High-momentum tokens (score >= 40): {len(high_momentum)}')
                print()
                
                if not high_momentum:
                    print('😴 No significant momentum detected')
                    print('Current market conditions are slow.')
                    return
                
                # Phase 2: Display Results
                print('🔥 PHASE 2: Top Momentum Tokens')
                print('-'*70)
                
                for i, token in enumerate(high_momentum[:5], 1):
                    age_str = 'Unknown'
                    if token['created_at']:
                        age_ms = token['created_at']
                        age_hours = (datetime.now().timestamp() - age_ms/1000) / 3600
                        if age_hours < 1:
                            age_str = f'{int(age_hours*60)}m'
                        elif age_hours < 24:
                            age_str = f'{int(age_hours)}h'
                        else:
                            age_str = f'{int(age_hours/24)}d'
                    
                    mc = token['market_cap']
                    mc_str = f'${mc/1_000_000:.2f}M' if mc >= 1_000_000 else f'${mc/1000:.1f}K'
                    
                    print(f"{i}. 🎯 {token['symbol']} | Score: {token['score']:.1f}/100")
                    print(f"   Name: {token['name']}")
                    print(f"   Price: ${float(token['price']):.10f}")
                    print(f"   1h Change: {token['change_1h']:+.2f}%")
                    print(f"   5m Change: {token['change_5m']:+.2f}%")
                    print(f"   Volume 24h: ${token['volume']:,.0f}")
                    print(f"   Liquidity: ${token['liquidity']:,.0f}")
                    print(f"   Market Cap: {mc_str}")
                    print(f"   Age: {age_str}")
                    print(f"   Address: {token['address'][:20]}...")
                    print()
                
                # Phase 3: Alpha Wallet Summary
                print('='*70)
                print('👑 PHASE 3: Stealth Hunt 2.0 - Top Alpha Wallets')
                print('='*70)
                
                wallets = [
                    {'name': 'LeBron', 'address': 'G5nxEXuFMfV74DSnsrSatqCW32F34XUnBeq3PfDS7w5E', 'profits': '$17.6M+', 'tier': 'LEGENDARY'},
                    {'name': 'Nansen Smart Trader', 'address': '4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6', 'profits': '$44.24M', 'tier': 'LEGENDARY'},
                    {'name': 'E6Y Sandwich Bot', 'address': 'E6YoRP3adE5XYneSseLee15wJshDxCsmyD2WtLvAmfLi', 'profits': '$300K/day', 'tier': 'MEV_LEGENDARY'},
                    {'name': 'FARTCOIN Whale', 'address': 'HWdeCUjBvPP1HJ5oCJt7aNsvMWpWoDgiejUWvfFX6T7R', 'profits': '$4.38M', 'tier': 'TIER_1'},
                    {'name': 'TRUMP Millionaire', 'address': '9HCTuTPEiQvkUtLmTZvK6uch4E3pDynwJTbNw6jLhp9z', 'profits': '$4.8M', 'tier': 'TIER_1'},
                ]
                
                for w in wallets:
                    tier_emoji = {'LEGENDARY': '👑', 'MEV_LEGENDARY': '🤖👑', 'TIER_1': '💎'}
                    print(f"{tier_emoji.get(w['tier'], '📌')} {w['name']}")
                    print(f"   Profits: {w['profits']}")
                    print(f"   Address: {w['address']}")
                    print()
                
                # Summary
                print('='*70)
                print('📊 HUNT SUMMARY')
                print('='*70)
                print(f'Tokens scanned: {len(pairs)}')
                print(f'High-momentum found: {len(high_momentum)}')
                print(f'Alpha wallets available: 7')
                print()
                print('💡 RECOMMENDATIONS:')
                print('1. Monitor top 3 tokens for entry points')
                print('2. Add alpha wallets to tracking list')
                print('3. Set price alerts on high-momentum tokens')
                print()
                print(f"⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print('='*70)
                
        except Exception as e:
            print(f'❌ Error: {e}')

if __name__ == "__main__":
    asyncio.run(full_hunt())
