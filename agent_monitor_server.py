#!/usr/bin/env python3
"""
ShadowHunter Agent Monitor
Runs on user's FX 6300 server to watch for trading opportunities.

Features:
- Polls database for new wallet cluster activity
- Researches tokens via DexScreener
- Makes weighted trading decisions
- Executes paper trades
- Logs all activity to file and console
"""

import asyncio
import asyncpg
import aiohttp
import ssl
import certifi
import os
import json
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('agent_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SSL context for Windows
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
    market_cap: float = 0
    liquidity: float = 0
    age_hours: float = 999
    narrative: str = "Unknown"
    website: str = ""
    twitter: str = ""


@dataclass
class TradeDecision:
    action: str = "WATCH"
    confidence: int = 0
    position_size: float = 0.10
    token: str = ""
    symbol: str = "Unknown"
    reasoning: List[str] = field(default_factory=list)
    total_weight: float = 0


class AgentMonitor:
    def __init__(self):
        self.db: Optional[asyncpg.Connection] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.paper_balance = 2.0
        self.last_check = datetime.now(timezone.utc) - timedelta(minutes=5)
        self.processed_tokens = set()
        self.total_trades = 0
        
    async def connect(self):
        """Connect to database and create HTTP session"""
        self.db = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'sh123')
        )
        
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Load paper portfolio
        await self.load_portfolio()
        logger.info(f"Agent connected. Paper balance: {self.paper_balance:.2f} SOL")
        
    async def close(self):
        if self.db:
            await self.db.close()
        if self.session:
            await self.session.close()
    
    async def load_portfolio(self):
        """Load paper portfolio state"""
        try:
            row = await self.db.fetchrow("SELECT data FROM paper_portfolio WHERE id = 1")
            if row:
                data = json.loads(row['data'])
                self.paper_balance = data.get('sol_balance', 2.0)
                self.total_trades = data.get('total_trades', 0)
        except Exception as e:
            logger.warning(f"Could not load portfolio: {e}")
    
    async def save_portfolio(self):
        """Save paper portfolio state"""
        try:
            await self.db.execute(
                """INSERT INTO paper_portfolio (id, data, updated_at) 
                VALUES (1, $1, NOW())
                ON CONFLICT (id) DO UPDATE SET data = $1, updated_at = NOW()""",
                json.dumps({
                    'sol_balance': self.paper_balance,
                    'total_trades': self.total_trades,
                    'updated': datetime.now(timezone.utc).isoformat()
                })
            )
        except Exception as e:
            logger.error(f"Could not save portfolio: {e}")
    
    async def research_token(self, token: str) -> TokenResearch:
        """Research token via DexScreener"""
        r = TokenResearch()
        
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
                r.market_cap = float(best.get('marketCap', 0) or 0)
                r.liquidity = float(best.get('liquidity', {}).get('usd', 0) or 0)
                
                # Age
                created = best.get('pairCreatedAt')
                if created:
                    r.age_hours = (datetime.now(timezone.utc).timestamp() * 1000 - created) / (1000 * 60 * 60)
                
                # Socials
                info = best.get('info', {})
                socials = info.get('socials', [])
                r.twitter = next((s['url'] for s in socials if s.get('type') == 'twitter'), '')
                websites = info.get('websites', [])
                if websites:
                    r.website = websites[0].get('url', '')
                
                # Narrative detection
                name = best.get('baseToken', {}).get('name', '').lower()
                symbol = r.symbol.lower()
                if any(x in name or x in symbol for x in ['ai', 'gpt', 'bot']):
                    r.narrative = "AI"
                elif any(x in name or x in symbol for x in ['pepe', 'doge', 'shib', 'moon']):
                    r.narrative = "Meme"
                elif any(x in name or x in symbol for x in ['dao']):
                    r.narrative = "DAO"
                else:
                    r.narrative = "Other"
                    
        except Exception as e:
            logger.error(f"Research error for {token[:8]}: {e}")
        
        return r
    
    def calculate_weight(self, wallets: List[str]) -> float:
        """Calculate weighted conviction"""
        return sum(WALLET_WEIGHTS.get(w, 1.0) for w in wallets)
    
    async def make_decision(self, token: str, wallets: List[str]) -> TradeDecision:
        """Make trading decision"""
        decision = TradeDecision(token=token)
        
        # Research token
        research = await self.research_token(token)
        decision.symbol = research.symbol
        
        # Calculate weight
        weight = self.calculate_weight(wallets)
        decision.total_weight = weight
        
        # Base confidence from weight
        if weight >= 8:
            decision.confidence = 80
            decision.reasoning.append(f"High conviction: {weight:.1f}x weight")
        elif weight >= 5:
            decision.confidence = 60
            decision.reasoning.append(f"Good conviction: {weight:.1f}x weight")
        elif weight >= 3:
            decision.confidence = 40
            decision.reasoning.append(f"Moderate: {weight:.1f}x weight")
        else:
            decision.confidence = 20
            decision.reasoning.append(f"Low: {weight:.1f}x weight")
        
        # High weight wallets
        high = [w[:8] for w in wallets if WALLET_WEIGHTS.get(w, 0) >= 1.5]
        if high:
            decision.reasoning.append(f"Key: {', '.join(high[:3])}")
        
        # Research adjustments
        if research.found:
            if research.narrative == "AI":
                decision.confidence += 10
                decision.reasoning.append("AI narrative")
            
            if research.age_hours < 1:
                decision.confidence += 10
                decision.reasoning.append("Just launched")
            elif research.age_hours < 6:
                decision.confidence += 5
                decision.reasoning.append("Early")
            
            if research.market_cap < 500000:
                decision.confidence += 10
                decision.reasoning.append("Low MC")
            elif research.market_cap > 10000000:
                decision.confidence -= 20
                decision.reasoning.append("High MC")
            
            if research.liquidity > 50000:
                decision.confidence += 5
                decision.reasoning.append("Good liq")
        
        decision.confidence = max(0, min(100, decision.confidence))
        
        # Action
        if decision.confidence >= 60:
            decision.action = "BUY"
            decision.position_size = 0.20
        elif decision.confidence >= 40:
            decision.action = "BUY"
            decision.position_size = 0.15
        elif decision.confidence >= 25:
            decision.action = "BUY"
            decision.position_size = 0.10
        elif decision.confidence >= 10:
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
            logger.warning("Insufficient balance")
            return None
        
        # Record trade
        try:
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
                    'reasoning': decision.reasoning
                })
            )
            
            self.paper_balance -= (amount + 0.01)
            self.total_trades += 1
            await self.save_portfolio()
            
            return {'amount': amount, 'balance': self.paper_balance}
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return None
    
    def format_decision(self, decision: TradeDecision, result: Optional[Dict], wallets: List[str]) -> str:
        """Format decision for display"""
        emoji = {"BUY": "🟢", "WATCH": "👀", "SKIP": "❌"}.get(decision.action, "⚪")
        
        lines = [
            f"{emoji} AGENT DECISION: {decision.action}",
            "",
            f"{decision.symbol}",
            f"{decision.token}",
            "",
            "Analysis:",
        ]
        
        for reason in decision.reasoning:
            lines.append(f"• {reason}")
        
        lines.append(f"")
        lines.append(f"Confidence: {decision.confidence}%")
        lines.append(f"Wallets: {len(wallets)}")
        
        if result:
            lines.append(f"")
            lines.append(f"Trade: {result['amount']:.2f} SOL")
            lines.append(f"Balance: {result['balance']:.2f} SOL")
        
        return "\n".join(lines)
    
    async def check_new_activity(self) -> List[Dict]:
        """Check for new wallet cluster activity"""
        rows = await self.db.fetch(
            """SELECT 
                token_address,
                COUNT(*) as wallet_count,
                array_agg(wallet_address) as wallets,
                MAX(first_buy_time) as latest
            FROM wallet_positions
            WHERE first_buy_time > $1
            GROUP BY token_address
            HAVING COUNT(*) >= 2
            ORDER BY latest DESC""",
            self.last_check
        )
        
        self.last_check = datetime.now(timezone.utc)
        
        return [
            {
                'token': row['token_address'],
                'count': row['wallet_count'],
                'wallets': row['wallets']
            }
            for row in rows
            if row['token_address'] not in self.processed_tokens
        ]
    
    async def run(self):
        """Main monitoring loop"""
        await self.connect()
        logger.info("=" * 50)
        logger.info("AGENT MONITOR STARTED")
        logger.info("=" * 50)
        logger.info(f"Paper Balance: {self.paper_balance:.2f} SOL")
        logger.info(f"Monitoring {len(WALLET_WEIGHTS)} weighted wallets")
        logger.info("")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                # Check for new activity
                activities = await self.check_new_activity()
                
                for activity in activities:
                    token = activity['token']
                    wallets = activity['wallets']
                    
                    logger.info(f"🔔 NEW ACTIVITY: {token[:16]}... with {len(wallets)} wallets")
                    
                    # Make decision
                    decision = await self.make_decision(token, wallets)
                    
                    # Execute if BUY
                    result = None
                    if decision.action == "BUY":
                        result = await self.execute_trade(decision)
                    
                    # Log decision
                    report = self.format_decision(decision, result, wallets)
                    for line in report.split('\n'):
                        logger.info(line)
                    
                    logger.info("-" * 40)
                    
                    # Mark processed
                    self.processed_tokens.add(token)
                    if len(self.processed_tokens) > 500:
                        self.processed_tokens = set(list(self.processed_tokens)[-250:])
                
                if cycle % 20 == 0:
                    logger.info(f"[Cycle {cycle}] Watching... Balance: {self.paper_balance:.2f} SOL | Trades: {self.total_trades}")
                    
            except Exception as e:
                logger.error(f"Error in cycle {cycle}: {e}")
            
            await asyncio.sleep(15)  # Check every 15 seconds


async def main():
    monitor = AgentMonitor()
    try:
        await monitor.run()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
