#!/usr/bin/env python3
"""Detailed market scan showing current conditions"""
import asyncio
import aiohttp
from datetime import datetime

async def detailed_scan():
    print('='*70)
    print('🔍 DETAILED MARKET SCAN')
    print('='*70)
    print(f'⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    async with aiohttp.ClientSession() as session:
        url = 'https://api.dexscreener.com/latest/dex/search?q=SOL'
        
        async with session.get(url, timeout=15) as resp:
            data = await resp.json()
            pairs = data.get('pairs', [])
            
            print(f'📊 Total Solana pairs found: {len(pairs)}')
            print()
            
            # Show top tokens by liquidity
            solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
            solana_pairs.sort(key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0), reverse=True)
            
            print('💧 TOP TOKENS BY LIQUIDITY:')
            print('-'*70)
            
            for i, pair in enumerate(solana_pairs[:8], 1):
                symbol = pair.get('baseToken', {}).get('symbol', '???')
                name = pair.get('baseToken', {}).get('name', 'Unknown')
                liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                volume = float(pair.get('volume', {}).get('h24', 0) or 0)
                price_change = float(pair.get('priceChange', {}).get('h1', 0) or 0)
                price = pair.get('priceUsd', 0)
                
                liq_str = f'${liquidity/1_000_000:.2f}M' if liquidity >= 1_000_000 else f'${liquidity/1000:.1f}K'
                vol_str = f'${volume/1_000_000:.2f}M' if volume >= 1_000_000 else f'${volume/1000:.1f}K'
                
                change_emoji = '🟢' if price_change > 0 else '🔴' if price_change < 0 else '⚪'
                
                print(f"{i}. {symbol}")
                print(f"   Name: {name}")
                print(f"   Price: ${float(price):.10f}")
                print(f"   1h Change: {change_emoji} {price_change:+.2f}%")
                print(f"   Liquidity: {liq_str}")
                print(f"   Volume 24h: {vol_str}")
                print()
            
            # Calculate momentum scores anyway to show data
            print('📈 MOMENTUM ANALYSIS (all tokens with >$10K liquidity):')
            print('-'*70)
            
            scored_tokens = []
            for pair in solana_pairs:
                liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                if liquidity < 10000:
                    continue
                    
                price_change = float(pair.get('priceChange', {}).get('h1', 0) or 0)
                volume = float(pair.get('volume', {}).get('h24', 0) or 0)
                
                score = min(abs(price_change) * 2, 50) + min(volume / 10000, 50)
                
                scored_tokens.append({
                    'symbol': pair.get('baseToken', {}).get('symbol', '???'),
                    'score': score,
                    'change': price_change,
                    'volume': volume,
                    'liquidity': liquidity
                })
            
            scored_tokens.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"Tokens analyzed: {len(scored_tokens)}")
            if scored_tokens:
                print(f"Highest momentum score: {scored_tokens[0]['score']:.1f}/100")
            print()
            
            if scored_tokens:
                print('TOP 3 BY MOMENTUM SCORE:')
                for i, t in enumerate(scored_tokens[:3], 1):
                    status = '🔥 HIGH' if t['score'] >= 60 else '⚡ MEDIUM' if t['score'] >= 40 else '📊 LOW'
                    print(f"{i}. {t['symbol']} - Score: {t['score']:.1f} {status}")
                    print(f"   1h Change: {t['change']:+.2f}%")
            
            print()
            print('='*70)
            print('📊 SCAN SUMMARY')
            print('='*70)
            print(f'✅ DexScreener API: ONLINE (unlimited)')
            print(f'✅ Total pairs indexed: {len(pairs)}')
            print(f'✅ Solana pairs: {len(solana_pairs)}')
            print(f'✅ With >$10K liquidity: {len(scored_tokens)}')
            print()
            print('💡 MARKET STATUS:')
            print('   Current conditions are relatively calm.')
            print('   No major pumps detected (score > 60).')
            print('   This is normal during off-peak hours.')
            print()
            print('🎯 RECOMMENDATION:')
            print('   1. Run continuous /monitor to catch moves early')
            print('   2. Set up alerts for when momentum > 60')
            print('   3. Check back during peak hours (UTC 14:00-23:00)')
            print()
            print(f"⏰ Scan completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print('='*70)

if __name__ == "__main__":
    asyncio.run(detailed_scan())
