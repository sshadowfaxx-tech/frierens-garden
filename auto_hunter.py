#!/usr/bin/env python3
"""
ShadowHunter Auto-Scan Bot
Continuously monitors for high-momentum tokens and auto-scans them

This runs the full workflow:
1. Check momentum every X minutes
2. Detect high-momentum tokens (score > 60)
3. Automatically scan for early buyers
4. Send alerts to Telegram
5. Save results

Usage:
    python3 auto_hunter.py --interval 5 --threshold 60
"""

import asyncio
import aiohttp
import argparse
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | 🤖 AUTO-HUNTER | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger('AutoHunter')

# Config
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ALERTS = os.getenv('CHANNEL_ALERTS') or os.getenv('CHANNEL_SCANNER')
DEXCHECK_API_KEY = os.getenv('DEXCHECK_API_KEY', 'BostDZLJBBPu44iXpiOneGprXhTpSFCg')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')

# Tracked tokens (to avoid duplicates)
tracked_tokens: Dict[str, datetime] = {}
signals_generated: List[Dict] = []


class AutoHunter:
    """Automated momentum detection + auto-scan"""
    
    def __init__(self, interval_minutes: int = 5, threshold: float = 60.0):
        self.interval = interval_minutes
        self.threshold = threshold
        self.scan_count = 0
        self.hits = 0
        
    async def run(self):
        """Main hunting loop"""
        logger.info("="*70)
        logger.info("🤖 SHADOWHUNTER AUTO-HUNTER STARTED")
        logger.info(f"⏰ Interval: {self.interval} minutes")
        logger.info(f"🎯 Threshold: {self.threshold} momentum score")
        logger.info(f"📡 Alerts: {CHANNEL_ALERTS or 'Console only'}")
        logger.info("="*70)
        
        while True:
            try:
                await self.hunt_cycle()
                logger.info(f"⏳ Sleeping {self.interval} minutes...")
                await asyncio.sleep(self.interval * 60)
            except Exception as e:
                logger.error(f"❌ Hunt cycle error: {e}")
                await asyncio.sleep(60)  # Wait 1 min on error
    
    async def hunt_cycle(self):
        """Single hunting cycle"""
        self.scan_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info("")
        logger.info("="*70)
        logger.info(f"🔍 HUNT CYCLE #{self.scan_count} | {timestamp}")
        logger.info("="*70)
        
        # Phase 1: Find high-momentum tokens
        high_momentum = await self.find_momentum_tokens()
        
        if not high_momentum:
            logger.info("😴 No high-momentum tokens detected")
            return
        
        logger.info(f"🎯 Found {len(high_momentum)} tokens above threshold")
        
        # Phase 2: Filter new tokens (not recently tracked)
        new_tokens = self.filter_new_tokens(high_momentum)
        
        if not new_tokens:
            logger.info("📋 All high-momentum tokens already tracked")
            return
        
        logger.info(f"✨ {len(new_tokens)} NEW tokens to analyze")
        
        # Phase 3: Auto-scan each new token
        for token in new_tokens:
            await self.analyze_token(token)
            # Small delay between scans
            await asyncio.sleep(2)
    
    async def find_momentum_tokens(self) -> List[Dict]:
        """Scan ecosystem for high-momentum tokens"""
        logger.info("📊 Scanning DexScreener for momentum...")
        
        tokens = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.dexscreener.com/latest/dex/search?q=SOL"
                
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        logger.error(f"DexScreener error: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    pairs = data.get('pairs', [])
                    
                    logger.info(f"  Total pairs: {len(pairs)}")
                    
                    for pair in pairs:
                        if pair.get('chainId') != 'solana':
                            continue
                        
                        liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                        if liquidity < 10000:  # Min $10K
                            continue
                        
                        price_change_1h = float(pair.get('priceChange', {}).get('h1', 0) or 0)
                        volume_24h = float(pair.get('volume', {}).get('h24', 0) or 0)
                        
                        # Momentum score
                        score = min(abs(price_change_1h) * 2, 50) + min(volume_24h / 10000, 50)
                        
                        if score >= self.threshold:
                            tokens.append({
                                'symbol': pair.get('baseToken', {}).get('symbol', '???'),
                                'name': pair.get('baseToken', {}).get('name', 'Unknown'),
                                'address': pair.get('baseToken', {}).get('address', ''),
                                'pair': pair.get('pairAddress', ''),
                                'price': pair.get('priceUsd', 0),
                                'change_1h': price_change_1h,
                                'change_5m': float(pair.get('priceChange', {}).get('m5', 0) or 0),
                                'volume': volume_24h,
                                'liquidity': liquidity,
                                'market_cap': float(pair.get('marketCap', 0) or 0),
                                'score': score,
                                'created_at': pair.get('pairCreatedAt')
                            })
                    
                    # Sort by score
                    tokens.sort(key=lambda x: x['score'], reverse=True)
                    
        except Exception as e:
            logger.error(f"Error finding momentum: {e}")
        
        return tokens
    
    def filter_new_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Filter out recently tracked tokens"""
        new_tokens = []
        now = datetime.now()
        
        for token in tokens:
            pair = token['pair']
            
            # Check if recently tracked (within 4 hours)
            if pair in tracked_tokens:
                last_tracked = tracked_tokens[pair]
                if now - last_tracked < timedelta(hours=4):
                    continue  # Skip recently tracked
            
            new_tokens.append(token)
            # Mark as tracked
            tracked_tokens[pair] = now
        
        # Cleanup old tracked tokens (>24h)
        old_pairs = [p for p, t in tracked_tokens.items() if now - t > timedelta(hours=24)]
        for p in old_pairs:
            del tracked_tokens[p]
        
        return new_tokens
    
    async def analyze_token(self, token: Dict):
        """Full analysis of a token - momentum + early buyers"""
        self.hits += 1
        
        logger.info("")
        logger.info(f"🎯 ANALYZING: {token['symbol']} | Score: {token['score']:.1f}")
        logger.info(f"   Pair: {token['pair'][:40]}...")
        
        # Build alert message
        alert = self.build_momentum_alert(token)
        
        # Send momentum alert
        await self.send_telegram_alert(alert)
        
        # Auto-scan for early buyers
        early_birds = await self.scan_early_buyers(token)
        
        if early_birds:
            scan_report = self.build_scan_report(token, early_birds)
            await self.send_telegram_alert(scan_report)
        
        # Save signal
        signals_generated.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': token['symbol'],
            'pair': token['pair'],
            'score': token['score'],
            'early_birds': len(early_birds),
            'price_change': token['change_1h']
        })
        
        logger.info(f"✅ Analysis complete for {token['symbol']}")
    
    async def scan_early_buyers(self, token: Dict) -> List[Dict]:
        """Scan for early buyers using DexCheck"""
        logger.info(f"   🔍 Fetching early buyers from DexCheck...")
        
        early_birds = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.dexcheck.ai/api/v1/blockchain/early-birds"
                params = {"chain": "solana", "pair": token['pair'], "limit": 50}
                headers = {"X-API-Key": DEXCHECK_API_KEY}
                
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data if isinstance(data, list) else data.get("data", [])
                        
                        # Filter high-quality early birds
                        for item in items:
                            roi = float(item.get("roi", 0) or 0)
                            pnl = float(item.get("pnl", 0) or 0)
                            
                            if roi > 100 and pnl >= 20:  # Quality filter
                                early_birds.append({
                                    'wallet': item.get("maker") or item.get("address"),
                                    'roi': roi,
                                    'pnl': pnl,
                                    'buys': int(item.get("buy_trade_count", 0) or 0),
                                    'sells': int(item.get("sell_trade_count", 0) or 0)
                                })
                        
                        logger.info(f"   ✅ Found {len(early_birds)} high-quality early birds")
                    else:
                        logger.warning(f"   ⚠️ DexCheck error: {resp.status}")
        
        except Exception as e:
            logger.error(f"   ❌ Error scanning early buyers: {e}")
        
        return early_birds[:10]  # Top 10
    
    def build_momentum_alert(self, token: Dict) -> str:
        """Build momentum detection alert"""
        mc_str = f"${token['market_cap']/1_000_000:.2f}M" if token['market_cap'] >= 1_000_000 else f"${token['market_cap']/1000:.1f}K"
        
        age_str = "Unknown"
        if token['created_at']:
            age_hours = (datetime.now().timestamp() - token['created_at']/1000) / 3600
            if age_hours < 1:
                age_str = f"{int(age_hours*60)} minutes"
            elif age_hours < 24:
                age_str = f"{int(age_hours)} hours"
            else:
                age_str = f"{int(age_hours/24)} days"
        
        return f"""🚨 *HIGH-MOMENTUM TOKEN DETECTED!*

🎯 *{token['symbol']}* | Score: {token['score']:.1f}/100
💰 Price: `${float(token['price']):.10f}`
📈 1h Change: `{token['change_1h']:+.2f}%`
📊 5m Change: `{token['change_5m']:+.2f}%`
💎 Market Cap: `{mc_str}`
💧 Liquidity: `${token['liquidity']:,.0f}`
📊 Volume 24h: `${token['volume']:,.0f}`
⏰ Age: `{age_str}`

🔗 Pair: `{token['pair']}`

🔍 *Auto-scanning for early buyers...*"""
    
    def build_scan_report(self, token: Dict, early_birds: List[Dict]) -> str:
        """Build early buyer scan report"""
        if not early_birds:
            return f"⚠️ *{token['symbol']}* - No high-quality early birds found"
        
        report = f"""🔎 *EARLY BUYER ANALYSIS: {token['symbol']}*

📊 Found {len(early_birds)} high-quality early buyers
Filters: ROI > 100% | PnL ≥ $20 USD

🐣 *TOP EARLY BIRDS:*

"""
        
        for i, bird in enumerate(early_birds[:5], 1):
            emoji = "🚀" if bird['roi'] >= 500 else "📈" if bird['roi'] >= 200 else "✅"
            pattern = "💎 HOLDING" if bird['sells'] == 0 else f"🔄 {bird['buys']}B/{bird['sells']}S"
            
            report += f"""{emoji} *#{i}* `{bird['wallet'][:20]}...`
   💰 PnL: `${bird['pnl']:.2f}` | ROI: `{bird['roi']:.1f}%`
   📊 {pattern}

"""
        
        report += f"💡 *Use `/scan {token['pair']}` for full analysis*"
        
        return report
    
    async def send_telegram_alert(self, message: str):
        """Send alert to Telegram"""
        if not TELEGRAM_BOT_TOKEN or not CHANNEL_ALERTS:
            logger.info("📤 Would send Telegram alert (console mode):")
            logger.info(message[:200] + "..." if len(message) > 200 else message)
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                
                payload = {
                    'chat_id': CHANNEL_ALERTS,
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
                
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info("   📤 Telegram alert sent")
                    else:
                        logger.warning(f"   ⚠️ Telegram error: {resp.status}")
        
        except Exception as e:
            logger.error(f"   ❌ Telegram send error: {e}")
    
    def save_report(self):
        """Save hunt results to file"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_scans': self.scan_count,
            'total_hits': self.hits,
            'signals': signals_generated[-50:]  # Last 50
        }
        
        filename = f"auto_hunt_report_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📄 Report saved: {filename}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")


def main():
    parser = argparse.ArgumentParser(description='ShadowHunter Auto-Hunter')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Minutes between scans')
    parser.add_argument('--threshold', '-t', type=float, default=60.0, help='Momentum score threshold')
    parser.add_argument('--once', '-o', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    hunter = AutoHunter(interval_minutes=args.interval, threshold=args.threshold)
    
    if args.once:
        # Run single cycle
        asyncio.run(hunter.hunt_cycle())
        hunter.save_report()
    else:
        # Run continuous
        try:
            asyncio.run(hunter.run())
        except KeyboardInterrupt:
            logger.info("\n👋 Stopping auto-hunter...")
            hunter.save_report()


if __name__ == "__main__":
    main()
