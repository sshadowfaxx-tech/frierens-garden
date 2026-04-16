#!/usr/bin/env python3
"""
Agent Trading - Complete System

Combines:
- Token research (DexScreener)
- Database queries (wallet history, performance)
- Decision making (weighted conviction)
- Paper trade execution

Usage: Called by OpenClaw when alerts are received
"""

import asyncio
import asyncpg
import aiohttp
import ssl
import certifi
import os
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field

ssl_context = ssl.create_default_context(cafile=certifi.where())

# Wallet weights from performance data
WALLET_WEIGHTS = {
    'G5nxEXuFMfV74DSnsrSatqCW32F34XUnBeq3PfDS7w5E': 3.0,  # Profit
    'HYWo71Wk9PNDe5sBaRKazPnVyGnQDiwgXCFKvgAQ1ENp': 3.0,  # Moonpie?
    '8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6': 3.0,  # Cooker
    '2p2mgFLmzN82sShZeAaBGmj9zFpam4xu8g4g3wqx2ks6': 1.5,  # Shy/Coyote
    '78N177fzNJpp8pG49xDv1efYcTMSzo9tPTKEA9mAVkh2': 1.5,  # Sheep
    '215nhcAHjQQGgwpQSJQ7zR26etbjjtVdW74NLzwEgQjP': 1.5,  # OGANTD
    'GJA1HEbxGnqBhBifH9uQauzXSB53to5rhDrzmKxhSU65': 1.5,  # Latuche
}


@dataclass
class TokenResearch:
    found: bool = False
    symbol: str = "Unknown"
    name: str = "Unknown"
    price_usd: float = 0
    market_cap: float = 0
    liquidity: float = 0
    volume_24h: float = 0
    price_change_24h: float = 0
    age_hours: float = 999
    narrative: str = "Unknown"
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    description: str = ""
    score: int = 0


@dataclass
class TradeDecision:
    action: str = "WATCH"
    confidence: int = 0
    position_size: float = 0.10
    token: str = ""
    symbol: str = "Unknown"
    reasoning: List[str] = field(default_factory=list)
    research: Optional[TokenResearch] = None
    total_weight: float = 0


class AgentTrader:
    def __init__(self):
        self.db = None
        self.session = None
        self.paper_balance = 2.0
        
    async def connect(self):
        self.db = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Load balance
        try:
            row = await self.db.fetchrow("SELECT data FROM paper_portfolio WHERE id = 1")
            if row:
                self.paper_balance = json.loads(row['data']).get('sol_balance', 2.0)
        except:
            pass
    
    async def close(self):
        if self.db: await self.db.close()
        if self.session: await self.session.close()
    
    async def research_token(self, token: str) -> TokenResearch:
        """Research token via DexScreener"""
        r = TokenResearch(token=token)
        
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return r
                data = await resp.json()
                pairs = data.get('pairs', [])
                if not pairs:
                    return r
                
                best = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0) or 0)
                r.found = True
                r.symbol = best.get('baseToken', {}).get('symbol', 'Unknown')
                r.name = best.get('baseToken', {}).get('name', 'Unknown')
                r.price_usd = float(best.get('priceUsd', 0) or 0)
                r.market_cap = float(best.get('marketCap', 0) or 0)
                r.liquidity = float(best.get('liquidity', {}).get('usd', 0) or 0)
                r.volume_24h = float(best.get('volume', {}).get('h24', 0) or 0)
                r.price_change_24h = float(best.get('priceChange', {}).get('h24', 0) or 0)
                
                # Age
                created = best.get('pairCreatedAt')
                if created:
                    r.age_hours = (datetime.now(timezone.utc).timestamp() * 1000 - created) / (1000 * 60 * 60)
                
                # Socials
                info = best.get('info', {})
                socials = info.get('socials', [])
                r.twitter = next((s['url'] for s in socials if s.get('type') == 'twitter'), '')
                r.telegram = next((s['url'] for s in socials if s.get('type') == 'telegram'), '')
                websites = info.get('websites', [])
                if websites:
                    r.website = websites[0].get('url', '')
                r.description = info.get('description', '')[:150]
                
                # Narrative detection
                name_lower = r.name.lower()
                symbol_lower = r.symbol.lower()
                if any(x in name_lower or x in symbol_lower for x in ['ai', 'gpt', 'bot', 'neural']):
                    r.narrative = "AI"
                elif any(x in name_lower or x in symbol_lower for x in ['pepe', 'doge', 'shib', 'moon', 'wojak']):
                    r.narrative = "Meme"
                elif any(x in name_lower or x in symbol_lower for x in ['dao', 'gov']):
                    r.narrative = "DAO"
                elif any(x in name_lower or x in symbol_lower for x in ['defi', 'yield', 'stake']):
                    r.narrative = "DeFi"
                else:
                    r.narrative = "Other"
                
        except Exception as e:
            print(f"Research error: {e}")
        
        return r
    
    def calculate_research_score(self, r: TokenResearch) -> int:
        """Score token based on research"""
        score = 0
        
        # Narrative bonus
        if r.narrative == "AI": score += 15
        elif r.narrative == "Meme": score += 5
        
        # Age bonus (early = good)
        if r.age_hours < 1: score += 15
        elif r.age_hours < 6: score += 10
        elif r.age_hours < 24: score += 5
        elif r.age_hours > 72: score -= 10
        
        # Liquidity
        if r.liquidity > 100_000: score += 15
        elif r.liquidity > 50_000: score += 10
        elif r.liquidity > 10_000: score += 5
        elif r.liquidity < 5_000: score -= 15
        
        # Market cap
        if r.market_cap < 500_000: score += 15
        elif r.market_cap < 2_000_000: score += 5
        elif r.market_cap > 10_000_000: score -= 20
        
        # Social presence
        if r.twitter and r.website: score += 10
        elif not r.twitter and not r.website: score -= 10
        
        # Volume
        if r.volume_24h > r.market_cap * 0.5: score += 10  # High volume relative to MC
        
        return score
    
    def calculate_wallet_weight(self, wallets: List[str]) -> float:
        """Calculate total weighted conviction"""
        return sum(WALLET_WEIGHTS.get(w, 1.0) for w in wallets)
    
    async def make_decision(self, token: str, wallets: List[str]) -> TradeDecision:
        """Make trading decision"""
        decision = TradeDecision(token=token)
        
        # Research token
        research = await self.research_token(token)
        decision.research = research
        decision.symbol = research.symbol
        
        # Calculate scores
        research_score = self.calculate_research_score(research)
        wallet_weight = self.calculate_wallet_weight(wallets)
        
        decision.total_weight = wallet_weight
        
        # Base confidence from wallet weight
        if wallet_weight >= 8:
            decision.confidence = 85
            decision.reasoning.append(f"🎯 High wallet conviction ({wallet_weight:.1f}x)")
        elif wallet_weight >= 5:
            decision.confidence = 65
            decision.reasoning.append(f"✅ Good wallet conviction ({wallet_weight:.1f}x)")
        elif wallet_weight >= 3:
            decision.confidence = 45
            decision.reasoning.append(f"⚡ Moderate conviction ({wallet_weight:.1f}x)")
        else:
            decision.confidence = 25
            decision.reasoning.append(f"👀 Low conviction ({wallet_weight:.1f}x)")
        
        # Add high-weight wallets to reasoning
        high_wallets = [w[:8]+"..." for w in wallets if WALLET_WEIGHTS.get(w, 0) >= 1.5]
        if high_wallets:
            decision.reasoning.append(f"Key wallets: {', '.join(high_wallets[:3])}")
        
        # Research adjustments
        if not research.found:
            decision.confidence -= 30
            decision.reasoning.append("❌ Not on DexScreener")
        else:
            decision.confidence += research_score // 5
            
            if research.narrative == "AI":
                decision.reasoning.append("🤖 AI narrative")
            elif research.narrative == "Meme":
                decision.reasoning.append("🐸 Meme narrative")
            
            if research.age_hours < 1:
                decision.reasoning.append("🔥 Just launched")
            elif research.age_hours < 6:
                decision.reasoning.append("⚡ Very early")
            
            if research.liquidity > 50_000:
                decision.reasoning.append(f"💧 Good liquidity")
            
            if research.twitter:
                decision.reasoning.append("🐦 Has Twitter")
            if research.website:
                decision.reasoning.append("🌐 Has website")
        
        # Cap confidence
        decision.confidence = max(0, min(100, decision.confidence))
        
        # Determine action
        if decision.confidence >= 70:
            decision.action = "BUY"
            decision.position_size = 0.20
        elif decision.confidence >= 50:
            decision.action = "BUY"
            decision.position_size = 0.15
        elif decision.confidence >= 30:
            decision.action = "BUY"
            decision.position_size = 0.10
        elif decision.confidence >= 15:
            decision.action = "WATCH"
        else:
            decision.action = "SKIP"
        
        return decision
    
    async def execute_trade(self, decision: TradeDecision) -> Optional[Dict]:
        """Execute paper trade"""
        if decision.action != "BUY":
            return None
        
        amount = self.paper_balance * decision.position_size
        amount = max(0.05, min(0.5, amount))
        
        if self.paper_balance < amount + 0.01:
            return None
        
        # Record trade
        await self.db.execute(
            """INSERT INTO paper_trades 
            (timestamp, action, token, token_symbol, amount_sol, fee, notes)
            VALUES (NOW(), 'BUY', $1, $2, $3, 0.01, $4)""",
            decision.token,
            decision.symbol,
            amount,
            json.dumps({
                'confidence': decision.confidence,
                'weight': decision.total_weight,
                'reasoning': decision.reasoning,
                'market_cap': decision.research.market_cap if decision.research else 0
            })
        )
        
        # Update balance
        self.paper_balance -= (amount + 0.01)
        await self.db.execute(
            "UPDATE paper_portfolio SET data = $1, updated_at = NOW() WHERE id = 1",
            json.dumps({'sol_balance': self.paper_balance, 'updated': datetime.now(timezone.utc).isoformat()})
        )
        
        return {'amount': amount, 'balance': self.paper_balance}
    
    def format_report(self, decision: TradeDecision, result: Optional[Dict]) -> str:
        """Format decision as readable report"""
        emoji = {"BUY": "🟢", "WATCH": "👀", "SKIP": "❌"}.get(decision.action, "⚪")
        
        report = f"""{emoji} *AGENT DECISION: {decision.action}*

*{decision.symbol}*
`{decision.token}`

📊 *Analysis:*
"""
        for reason in decision.reasoning:
            report += f"• {reason}\n"
        
        report += f"\n🎯 *Confidence:* {decision.confidence}%"
        
        if decision.research and decision.research.found:
            r = decision.research
            mc_str = f"${r.market_cap/1000:.0f}K" if r.market_cap < 1_000_000 else f"${r.market_cap/1_000_000:.1f}M"
            report += f"\n\n📈 *Token Data:*"
            report += f"\n• Narrative: {r.narrative}"
            report += f"\n• Market Cap: {mc_str}"
            report += f"\n• Age: {r.age_hours:.1f}h"
            report += f"\n• Liquidity: ${r.liquidity/1000:.0f}K"
            if r.twitter:
                report += f"\n• [Twitter]({r.twitter})"
            if r.website:
                report += f"\n• [Website]({r.website})"
        
        if result:
            report += f"\n\n💰 *Trade:* {result['amount']:.2f} SOL"
            report += f"\n💼 *Balance:* {result['balance']:.2f} SOL"
        
        return report


# Main entry point for OpenClaw
async def process_alert(alert_text: str, wallets: List[str] = None) -> str:
    """
    Process a tracker alert and return decision report.
    Called by OpenClaw when alert received.
    """
    # Extract token if not provided
    if wallets is None:
        wallets = []
    
    match = re.search(r'`([A-HJ-NP-Za-km-z1-9]{32,44})`', alert_text)
    if not match:
        return "Could not parse token from alert"
    
    token = match.group(1)
    
    # Parse wallets from alert if provided
    if not wallets:
        # Try to extract wallet addresses from alert text
        wallets = re.findall(r'[A-HJ-NP-Za-km-z1-9]{32,44}', alert_text)
        if token in wallets:
            wallets.remove(token)
    
    agent = AgentTrader()
    await agent.connect()
    
    try:
        decision = await agent.make_decision(token, wallets)
        result = await agent.execute_trade(decision) if decision.action == "BUY" else None
        return agent.format_report(decision, result)
    finally:
        await agent.close()


if __name__ == "__main__":
    # Test
    test = """🚨 CLUSTER ALERT
`7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`

Wallets: Profit, Moonpie?, Cooker, Sheep"""
    print(asyncio.run(process_alert(test)))
