#!/usr/bin/env python3
"""
Token Research Tool for Agent Trading

Quick research on tokens to inform trading decisions.
"""

import asyncio
import aiohttp
import ssl
import certifi
from datetime import datetime, timezone
from typing import Dict, Optional
import os

ssl_context = ssl.create_default_context(cafile=certifi.where())

class TokenResearcher:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def connect(self):
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def get_token_info(self, token: str) -> Dict:
        """Get comprehensive token info from DexScreener"""
        info = {
            'token': token,
            'found': False,
            'name': 'Unknown',
            'symbol': 'Unknown',
            'price_usd': 0,
            'market_cap': 0,
            'liquidity_usd': 0,
            'volume_24h': 0,
            'price_change_24h': 0,
            'links': {},
            'narrative': 'Unknown',
            'age_hours': 0
        }
        
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs:
                        info['found'] = True
                        # Get best pair by liquidity
                        best = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0) or 0)
                        
                        info['name'] = best.get('baseToken', {}).get('name', 'Unknown')
                        info['symbol'] = best.get('baseToken', {}).get('symbol', 'Unknown')
                        info['price_usd'] = float(best.get('priceUsd', 0) or 0)
                        info['market_cap'] = float(best.get('marketCap', 0) or 0)
                        info['liquidity_usd'] = float(best.get('liquidity', {}).get('usd', 0) or 0)
                        info['volume_24h'] = float(best.get('volume', {}).get('h24', 0) or 0)
                        info['price_change_24h'] = float(best.get('priceChange', {}).get('h24', 0) or 0)
                        
                        # Get social links
                        socials = best.get('info', {}).get('socials', [])
                        info['socials'] = socials
                        info['twitter'] = next((s['url'] for s in socials if s.get('type') == 'twitter'), None)
                        info['telegram'] = next((s['url'] for s in socials if s.get('type') == 'telegram'), None)
                        info['discord'] = next((s['url'] for s in socials if s.get('type') == 'discord'), None)
                        
                        # Get website
                        websites = best.get('info', {}).get('websites', [])
                        if websites:
                            info['website'] = websites[0].get('url', '')
                            
                        # Get description if available
                        info['description'] = best.get('info', {}).get('description', '')[:200]
                        
                        # Estimate age from pair creation
                        pair_created = best.get('pairCreatedAt')
                        if pair_created:
                            age_ms = datetime.now(timezone.utc).timestamp() * 1000 - pair_created
                            info['age_hours'] = age_ms / (1000 * 60 * 60)
        except Exception as e:
            print(f"Error fetching token info: {e}")
        
        return info
    
    async def quick_analysis(self, token: str) -> str:
        """Quick text analysis for agent decisions"""
        info = await self.get_token_info(token)
        
        if not info['found']:
            return f"Token {token[:8]}... not found on DexScreener"
        
        # Determine narrative type
        name_lower = info['name'].lower()
        symbol_lower = info['symbol'].lower()
        
        if any(x in name_lower or x in symbol_lower for x in ['ai', 'gpt', 'bot', 'neural', 'brain']):
            narrative = "AI"
        elif any(x in name_lower or x in symbol_lower for x in ['pepe', 'doge', 'shib', 'moon', 'wojak']):
            narrative = "Meme"
        elif any(x in name_lower or x in symbol_lower for x in ['dao', 'gov', 'vote']):
            narrative = "DAO"
        elif any(x in name_lower or x in symbol_lower for x in ['defi', 'yield', 'stake', 'farm']):
            narrative = "DeFi"
        else:
            narrative = "Other"
        
        # Liquidity quality
        liq = info['liquidity_usd']
        if liq > 100_000:
            liq_quality = "Excellent"
        elif liq > 50_000:
            liq_quality = "Good"
        elif liq > 10_000:
            liq_quality = "Okay"
        else:
            liq_quality = "Poor"
        
        # Age category
        age = info['age_hours']
        if age < 1:
            age_cat = "Just launched 🔥"
        elif age < 6:
            age_cat = "Very early"
        elif age < 24:
            age_cat = "Early"
        elif age < 72:
            age_cat = "Established"
        else:
            age_cat = "Mature"
        
        mc_str = f"${info['market_cap']/1000:.1f}K" if info['market_cap'] < 1_000_000 else f"${info['market_cap']/1_000_000:.2f}M"
        
        report = f"""📊 *TOKEN RESEARCH: {info['symbol']}*

🏷️ *Narrative:* {narrative}
⏰ *Age:* {age_cat} ({age:.1f}h)
💎 *Market Cap:* {mc_str}
💧 *Liquidity:* {liq_quality} (${liq:,.0f})
📈 *24h Change:* {info['price_change_24h']:+.1f}%
🌐 *Website:* {info.get('website', 'None')}

*Quick Assessment:*
"""
        
        # Add social links
        socials = []
        if info.get('twitter'):
            socials.append(f"[Twitter]({info['twitter']})")
        if info.get('telegram'):
            socials.append(f"[Telegram]({info['telegram']})")
        if info.get('discord'):
            socials.append(f"[Discord]({info['discord']})")
        
        if socials:
            report += f"🔗 *Socials:* {' | '.join(socials)}\n"
        
        if info.get('description'):
            report += f"📝 *Description:* {info['description'][:100]}...\n"
        
        report += f"\n*Quick Assessment:*\n"
        
        # Quick trade recommendation based on research
        signals = []
        risks = []
        
        # Narrative signal
        if narrative == "AI":
            signals.append("🤖 AI narrative (trending)")
        elif narrative == "Meme":
            if age < 1:
                risks.append("🐸 Fresh meme = high volatility")
            else:
                signals.append("🐸 Meme with some traction")
        
        # Age signal
        if age < 1:
            signals.append("🔥 Just launched (early)")
        elif age < 6:
            signals.append("⚡ Very early (sweet spot)")
        elif age > 72:
            risks.append("⏰ Old token (may be pumped)")
        
        # Liquidity signal
        if liq > 100_000:
            signals.append("💧 Excellent liquidity")
        elif liq > 50_000:
            signals.append("💧 Good liquidity")
        elif liq < 10_000:
            risks.append("❌ Low liquidity (hard exit)")
        
        # Market cap signal
        if info['market_cap'] < 500_000:
            signals.append("💎 Low MC (high upside)")
        elif info['market_cap'] > 10_000_000:
            risks.append("⚠️ High MC (limited upside)")
        
        # Social presence
        if info.get('twitter') and info.get('website'):
            signals.append("✅ Professional (web + social)")
        elif not info.get('twitter') and not info.get('website'):
            risks.append("❌ No web/social (anon)")
        
        if signals:
            report += '\n'.join(f"✅ {s}" for s in signals) + '\n'
        if risks:
            report += '\n'.join(f"⚠️ {r}" for r in risks) + '\n'
        
        # Overall recommendation
        score = len(signals) - len(risks)
        if score >= 3:
            report += "\n🟢 *STRONG BUY* - Multiple green flags"
        elif score >= 1:
            report += "\n🟡 *MODERATE BUY* - Some positives, manageable risk"
        elif score >= -1:
            report += "\n🟠 *WATCH* - Mixed signals, wait for clarity"
        else:
            report += "\n🔴 *SKIP* - Too many red flags"
        
        return report


async def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python token_research.py <token_address>")
        return
    
    token = sys.argv[1]
    researcher = TokenResearcher()
    await researcher.connect()
    
    try:
        report = await researcher.quick_analysis(token)
        print(report)
    finally:
        await researcher.close()


if __name__ == "__main__":
    asyncio.run(main())
