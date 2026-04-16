#!/usr/bin/env python3
"""
Agent Alert Processor - AGGRESSIVE MODE

Research-driven autonomous trading with paper money.
Position sizes: 10-25%
Max positions: 8-10
Goal: Learn fast through volume
"""

import asyncio
import asyncpg
import aiohttp
import ssl
import certifi
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os
import json
from dotenv import load_dotenv

load_dotenv()

ssl_context = ssl.create_default_context(cafile=certifi.where())

# Wallet performance weights (from corrected data)
WALLET_WEIGHTS = {
    # High conviction (3x)
    'G5nxEXuFMfV74DSnsrSatqCW32F34XUnBeq3PfDS7w5E': 3.0,  # Profit
    'HYWo71Wk9PNDe5sBaRKazPnVyGnQDiwgXCFKvgAQ1ENp': 3.0,  # Moonpie?
    '8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6': 3.0,  # Cooker
    
    # Medium conviction (1.5x)
    '2p2mgFLmzN82sShZeAaBGmj9zFpam4xu8g4g3wqx2ks6': 1.5,  # Shy/Coyote
    '78N177fzNJpp8pG49xDv1efYcTMSzo9tPTKEA9mAVkh2': 1.5,  # Sheep
    '215nhcAHjQQGgwpQSJQ7zR26etbjjtVdW74NLzwEgQjP': 1.5,  # OGANTD
    'GJA1HEbxGnqBhBifH9uQauzXSB53to5rhDrzmKxhSU65': 1.5,  # Latuche
    
    # All others default to 1.0
}


@dataclass
class TradeDecision:
    action: str  # BUY, SELL, WATCH
    confidence: int  # 0-100
    position_size: float  # 0.0-0.25 (25% max)
    reasoning: List[str]
    token: str
    token_symbol: str
    wallet_count: int
    total_weight: float


class AggressiveAgent:
    def __init__(self):
        self.db: Optional[asyncpg.Connection] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.paper_balance = 2.0
        self.open_positions = 0
        
    async def connect(self):
        self.db = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Load current portfolio
        await self.load_portfolio()
        
    async def close(self):
        if self.db:
            await self.db.close()
        if self.session:
            await self.session.close()
    
    async def load_portfolio(self):
        """Load current paper portfolio"""
        try:
            row = await self.db.fetchrow("SELECT data FROM paper_portfolio WHERE id = 1")
            if row:
                data = json.loads(row['data'])
                self.paper_balance = data.get('sol_balance', 2.0)
        except:
            pass
    
    async def get_token_info(self, token: str) -> Dict:
        """Quick token research"""
        info = {
            'found': False,
            'symbol': 'Unknown',
            'market_cap': 0,
            'liquidity': 0,
            'age_hours': 999,
            'narrative': 'Unknown'
        }
        
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get('pairs', [])
                    if pairs:
                        best = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0) or 0)
                        info['found'] = True
                        info['symbol'] = best.get('baseToken', {}).get('symbol', 'Unknown')
                        info['market_cap'] = float(best.get('marketCap', 0) or 0)
                        info['liquidity'] = float(best.get('liquidity', {}).get('usd', 0) or 0)
                        
                        # Estimate age
                        created = best.get('pairCreatedAt')
                        if created:
                            age_ms = datetime.now(timezone.utc).timestamp() * 1000 - created
                            info['age_hours'] = age_ms / (1000 * 60 * 60)
                        
                        # Detect narrative
                        name = best.get('baseToken', {}).get('name', '').lower()
                        symbol = info['symbol'].lower()
                        if any(x in name or x in symbol for x in ['ai', 'gpt', 'bot']):
                            info['narrative'] = 'AI'
                        elif any(x in name or x in symbol for x in ['pepe', 'doge', 'shib', 'moon']):
                            info['narrative'] = 'Meme'
                        elif any(x in name or x in symbol for x in ['dao']):
                            info['narrative'] = 'DAO'
                        else:
                            info['narrative'] = 'Other'
        except:
            pass
        
        return info
    
    def calculate_cluster_weight(self, wallets: List[str]) -> tuple[float, List[str]]:
        """Calculate weighted conviction from wallet list"""
        total_weight = 0
        weighted_wallets = []
        
        for wallet in wallets:
            weight = WALLET_WEIGHTS.get(wallet, 1.0)  # Default 1.0
            total_weight += weight
            if weight >= 1.5:
                weighted_wallets.append(f"{wallet[:8]}...({weight}x)")
        
        return total_weight, weighted_wallets
    
    async def make_decision(self, token: str, wallets: List[str], alert_type: str = 'cluster') -> TradeDecision:
        """
        Make aggressive trading decision based on research
        """
        decision = TradeDecision(
            action='WATCH',
            confidence=0,
            position_size=0,
            reasoning=[],
            token=token,
            token_symbol='Unknown',
            wallet_count=len(wallets),
            total_weight=0
        )
        
        # Get token info
        token_info = await self.get_token_info(token)
        decision.token_symbol = token_info['symbol']
        
        # Calculate weighted conviction
        total_weight, high_conviction_wallets = self.calculate_cluster_weight(wallets)
        decision.total_weight = total_weight
        
        # Base confidence from weight
        if total_weight >= 8:  # e.g., Profit(3) + Moonpie(3) + Cooker(3) = 9
            decision.confidence = 90
            decision.reasoning.append(f"Very high conviction: {total_weight:.1f} weight")
        elif total_weight >= 5:
            decision.confidence = 70
            decision.reasoning.append(f"High conviction: {total_weight:.1f} weight")
        elif total_weight >= 3:
            decision.confidence = 50
            decision.reasoning.append(f"Medium conviction: {total_weight:.1f} weight")
        else:
            decision.reasoning.append(f"Low conviction: {total_weight:.1f} weight")
        
        # Adjust for high conviction wallets
        if high_conviction_wallets:
            decision.confidence += 10
            decision.reasoning.append(f"Top wallets: {', '.join(high_conviction_wallets[:3])}")
        
        # Token research adjustments
        if not token_info['found']:
            decision.reasoning.append("❌ Not on DexScreener")
            decision.confidence -= 30
        else:
            # Market cap
            mc = token_info['market_cap']
            if mc < 500_000:
                decision.confidence += 15
                decision.reasoning.append(f"✅ Early entry: ${mc/1000:.0f}K MC")
            elif mc < 2_000_000:
                decision.confidence += 5
                decision.reasoning.append(f"🟡 Okay MC: ${mc/1_000_000:.1f}M")
            else:
                decision.confidence -= 20
                decision.reasoning.append(f"⚠️ High MC: ${mc/1_000_000:.1f}M")
            
            # Liquidity
            liq = token_info['liquidity']
            if liq > 50_000:
                decision.confidence += 10
                decision.reasoning.append(f"✅ Good liquidity: ${liq/1000:.0f}K")
            elif liq < 10_000:
                decision.confidence -= 15
                decision.reasoning.append(f"❌ Low liquidity: ${liq/1000:.0f}K")
            
            # Age
            age = token_info['age_hours']
            if age < 1:
                decision.confidence += 5
                decision.reasoning.append("🔥 Just launched")
            elif age > 72:
                decision.confidence -= 10
                decision.reasoning.append("⚠️ Old token")
            
            # Narrative
            narrative = token_info['narrative']
            if narrative == 'AI':
                decision.confidence += 10
                decision.reasoning.append("🤖 AI narrative")
            elif narrative == 'Meme':
                decision.reasoning.append("🐸 Meme coin")
        
        # Cap confidence
        decision.confidence = max(0, min(100, decision.confidence))
        
        # Determine action and position size
        if decision.confidence >= 70:
            decision.action = 'BUY'
            decision.position_size = 0.20  # 20%
        elif decision.confidence >= 50:
            decision.action = 'BUY'
            decision.position_size = 0.15  # 15%
        elif decision.confidence >= 30:
            decision.action = 'BUY'
            decision.position_size = 0.10  # 10%
        elif decision.confidence >= 15:
            decision.action = 'WATCH'
            decision.reasoning.append("👀 Below threshold - watching")
        else:
            decision.action = 'SKIP'
            decision.reasoning.append("❌ Too low confidence")
        
        # Check limits
        if self.open_positions >= 10:
            decision.action = 'SKIP'
            decision.reasoning.append("❌ Max positions (10) reached")
        
        if self.paper_balance < 0.2:
            decision.action = 'SKIP'
            decision.reasoning.append("❌ Low balance")
        
        return decision
    
    async def execute_paper_trade(self, decision: TradeDecision):
        """Execute paper trade and return report"""
        if decision.action != 'BUY':
            return None
        
        sol_amount = self.paper_balance * decision.position_size
        sol_amount = max(0.05, min(0.5, sol_amount))  # Min 0.05, max 0.5
        
        # Deduct with fee
        total_cost = sol_amount + 0.01
        self.paper_balance -= total_cost
        
        # Record trade
        await self.db.execute(
            """INSERT INTO paper_trades 
            (timestamp, action, token, token_symbol, amount_sol, fee, notes)
            VALUES (NOW(), 'BUY', $1, $2, $3, 0.01, $4)""",
            decision.token,
            decision.token_symbol,
            sol_amount,
            json.dumps({
                'confidence': decision.confidence,
                'reasoning': decision.reasoning,
                'wallets': decision.wallet_count,
                'weight': decision.total_weight
            })
        )
        
        self.open_positions += 1
        
        # Update portfolio
        await self.db.execute(
            "UPDATE paper_portfolio SET data = $1, updated_at = NOW() WHERE id = 1",
            json.dumps({
                'sol_balance': self.paper_balance,
                'open_positions': self.open_positions
            })
        )
        
        return {
            'token': decision.token_symbol,
            'amount': sol_amount,
            'confidence': decision.confidence,
            'balance': self.paper_balance
        }
    
    async def process_alert(self, alert_text: str, wallets: List[str] = None) -> str:
        """Process alert and return decision report"""
        await self.connect()
        
        try:
            # Extract token from alert if not provided
            if not wallets:
                import re
                token_match = re.search(r'`([A-HJ-NP-Za-km-z1-9]{32,44})`', alert_text)
                if not token_match:
                    return "Could not parse token from alert"
                token = token_match.group(1)
                wallets = []  # Would need to parse from alert text
            else:
                token = wallets[0] if wallets else None
            
            if not token:
                return "No token found"
            
            # Make decision
            decision = await self.make_decision(token, wallets or [])
            
            # Execute if BUY
            result = None
            if decision.action == 'BUY':
                result = await self.execute_paper_trade(decision)
            
            # Format report
            emoji = "🟢" if decision.action == 'BUY' else "👀" if decision.action == 'WATCH' else "❌"
            
            report = f"""{emoji} *AGENT DECISION: {decision.action}*

*{decision.token_symbol}*
`{token}`

📊 *Analysis:*
"""
            for reason in decision.reasoning:
                report += f"• {reason}\n"
            
            report += f"\n🎯 *Confidence:* {decision.confidence}%"
            
            if result:
                report += f"\n💰 *Position:* {result['amount']:.2f} SOL ({decision.position_size*100:.0f}%)"
                report += f"\n💼 *Balance:* {result['balance']:.2f} SOL remaining"
            
            return report
            
        finally:
            await self.close()


# Entry point for OpenClaw
async def process_alert(alert_text: str) -> str:
    agent = AggressiveAgent()
    return await agent.process_alert(alert_text)


if __name__ == "__main__":
    # Test
    test_alert = """🚨 CLUSTER: 4 wallets on TOKEN
`FtSRgyCEhKTc1PPgEAXvuHN3NyiP6LS9uyB28KCN3CAP`

Wallets: Profit, Moonpie?, Cooker, Sheep"""
    
    result = asyncio.run(process_alert(test_alert))
    print(result)
