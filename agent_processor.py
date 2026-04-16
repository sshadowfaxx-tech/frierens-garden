#!/usr/bin/env python3
"""
Agent Alert Processor - For OpenClaw Integration

This script allows the AI agent to receive tracker alerts
and make autonomous trading decisions.

Setup:
1. Configure tracker to send alerts to a specific Telegram channel
2. Set CHANNEL_AGENT_ALERTS in .env
3. The AI will receive alerts via OpenClaw and process them

The AI will:
- Receive cluster alerts
- Make buy/sell decisions  
- Execute paper trades
- Log decisions to memory
"""

import asyncio
import asyncpg
import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AlertSignal:
    token: str
    token_symbol: str
    market_cap: float
    wallet_count: int
    holding_count: int
    total_sol_invested: float
    trigger_wallet: str
    alert_type: str  # 'cluster' | 'buy' | 'sell'
    timestamp: datetime


class AgentProcessor:
    """Processes tracker alerts and makes trading decisions"""
    
    def __init__(self):
        self.db: Optional[asyncpg.Connection] = None
        self.decision_log = []
        
    async def connect(self):
        self.db = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        
    async def close(self):
        if self.db:
            await self.db.close()
    
    def parse_alert(self, alert_text: str) -> Optional[AlertSignal]:
        """Parse a tracker alert message into structured data"""
        try:
            # Extract token address (44-45 char base58)
            import re
            token_match = re.search(r'`([A-HJ-NP-Za-km-z1-9]{32,44})`', alert_text)
            if not token_match:
                return None
            token = token_match.group(1)
            
            # Extract token symbol/name
            symbol_match = re.search(r'\*([A-Z]+)\*', alert_text)
            symbol = symbol_match.group(1) if symbol_match else "Unknown"
            
            # Extract market cap
            mc_match = re.search(r'Market Cap:\s*`\$?([\d.]+)([KM]?)`', alert_text)
            market_cap = 0
            if mc_match:
                value = float(mc_match.group(1))
                unit = mc_match.group(2)
                if unit == 'M':
                    market_cap = value * 1_000_000
                elif unit == 'K':
                    market_cap = value * 1_000
                else:
                    market_cap = value
            
            # Extract wallet counts
            wallet_match = re.search(r'(\d+)\s+Total Wallets', alert_text)
            wallet_count = int(wallet_match.group(1)) if wallet_match else 0
            
            holding_match = re.search(r'(\d+)\s+Holding', alert_text)
            holding_count = int(holding_match.group(1)) if holding_match else 0
            
            # Extract SOL invested
            sol_match = re.search(r'Total SOL.*?`([\d.]+)`', alert_text)
            sol_invested = float(sol_match.group(1)) if sol_match else 0
            
            # Determine alert type
            if 'CLUSTER' in alert_text:
                alert_type = 'cluster'
            elif 'BUY' in alert_text:
                alert_type = 'buy'
            elif 'SELL' in alert_text:
                alert_type = 'sell'
            else:
                alert_type = 'unknown'
            
            return AlertSignal(
                token=token,
                token_symbol=symbol,
                market_cap=market_cap,
                wallet_count=wallet_count,
                holding_count=holding_count,
                total_sol_invested=sol_invested,
                trigger_wallet="",
                alert_type=alert_type,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Failed to parse alert: {e}")
            return None
    
    def make_decision(self, signal: AlertSignal) -> Dict:
        """
        Make trading decision based on signal
        Returns decision dict with action and reasoning
        """
        decision = {
            'action': 'WATCH',  # WATCH | BUY | SELL
            'confidence': 0,
            'position_size': 0,
            'reasoning': [],
            'signal': {
                'token': signal.token,
                'symbol': signal.token_symbol,
                'market_cap': signal.market_cap,
                'wallet_count': signal.wallet_count
            }
        }
        
        # Skip if market cap too high
        if signal.market_cap > 10_000_000:
            decision['reasoning'].append(f"Market cap too high (${signal.market_cap/1_000_000:.1f}M)")
            return decision
        
        # Evaluate signal strength
        if signal.wallet_count >= 10:
            decision['confidence'] = 90
            decision['action'] = 'BUY'
            decision['position_size'] = 0.15  # 15%
            decision['reasoning'].append(f"Strong signal: {signal.wallet_count} wallets")
        elif signal.wallet_count >= 6:
            decision['confidence'] = 70
            decision['action'] = 'BUY'
            decision['position_size'] = 0.10  # 10%
            decision['reasoning'].append(f"Medium signal: {signal.wallet_count} wallets")
        elif signal.wallet_count >= 4:
            decision['confidence'] = 50
            decision['action'] = 'BUY'
            decision['position_size'] = 0.05  # 5%
            decision['reasoning'].append(f"Weak signal: {signal.wallet_count} wallets")
        else:
            decision['reasoning'].append(f"Insufficient signal: {signal.wallet_count} wallets")
        
        # Check market cap quality
        if signal.market_cap < 1_000_000:
            decision['confidence'] += 10
            decision['reasoning'].append("Early entry (<$1M MC)")
        elif signal.market_cap < 5_000_000:
            decision['confidence'] += 5
            decision['reasoning'].append("Good entry (<$5M MC)")
        
        return decision
    
    async def log_decision(self, decision: Dict):
        """Log decision to memory file for learning"""
        import os
        memory_path = os.path.expanduser('~/.openclaw/workspace/memory/agent_decisions.jsonl')
        
        # Append to JSONL file
        with open(memory_path, 'a') as f:
            f.write(json.dumps(decision) + '\n')
    
    async def execute_paper_trade(self, decision: Dict, signal: AlertSignal):
        """Execute a paper trade based on decision"""
        if decision['action'] != 'BUY':
            return
        
        # Get current portfolio
        row = await self.db.fetchrow(
            "SELECT data FROM paper_portfolio WHERE id = 1"
        )
        
        if not row:
            logger.error("No portfolio found")
            return
        
        portfolio = json.loads(row['data'])
        sol_balance = portfolio.get('sol_balance', 1.0)
        
        # Calculate trade size
        position_size = decision['position_size']
        sol_amount = sol_balance * position_size
        
        # Min/max limits
        sol_amount = max(0.05, min(0.5, sol_amount))
        
        # Check if we have enough
        if sol_balance < sol_amount + 0.01:
            logger.info(f"Insufficient balance: {sol_balance:.2f} SOL")
            return
        
        # Record paper trade
        await self.db.execute(
            """INSERT INTO paper_trades 
            (timestamp, action, token, token_symbol, amount_sol, fee, notes)
            VALUES (NOW(), 'BUY', $1, $2, $3, 0.01, $4)""",
            signal.token,
            signal.token_symbol,
            sol_amount,
            json.dumps(decision['reasoning'])
        )
        
        # Update portfolio
        new_balance = sol_balance - sol_amount - 0.01
        portfolio['sol_balance'] = new_balance
        portfolio['total_trades'] = portfolio.get('total_trades', 0) + 1
        
        await self.db.execute(
            "UPDATE paper_portfolio SET data = $1, updated_at = NOW() WHERE id = 1",
            json.dumps(portfolio)
        )
        
        logger.info(f"Paper BUY: {signal.token_symbol} | {sol_amount:.2f} SOL | Confidence: {decision['confidence']}%")
        
        return {
            'action': 'BUY',
            'token': signal.token_symbol,
            'amount': sol_amount,
            'confidence': decision['confidence']
        }
    
    async def process_alert(self, alert_text: str) -> Optional[Dict]:
        """Main entry point: process an alert and take action"""
        await self.connect()
        
        try:
            # Parse the alert
            signal = self.parse_alert(alert_text)
            if not signal:
                return None
            
            # Make decision
            decision = self.make_decision(signal)
            
            # Log decision
            await self.log_decision(decision)
            
            # Execute if BUY
            if decision['action'] == 'BUY':
                result = await self.execute_paper_trade(decision, signal)
                return result
            
            return decision
            
        finally:
            await self.close()


# This function will be called by OpenClaw when I receive tracker alerts
async def process_tracker_alert(alert_text: str) -> str:
    """
    Entry point for OpenClaw integration.
    Call this when I receive a tracker alert message.
    
    Returns: Human-readable response with decision
    """
    processor = AgentProcessor()
    result = await processor.process_alert(alert_text)
    
    if not result:
        return "Could not parse alert"
    
    if result.get('action') == 'BUY':
        return f"🟢 **PAPER BUY EXECUTED**\n\n" \
               f"Token: {result['token']}\n" \
               f"Amount: {result['amount']:.2f} SOL\n" \
               f"Confidence: {result['confidence']}%"
    elif result.get('action') == 'WATCH':
        return f"👀 **WATCHING**\n\nSignal not strong enough to enter"
    else:
        return f"⚪ **NO ACTION**\n\n{result.get('reasoning', ['Unknown'])[0]}"


if __name__ == "__main__":
    # Test with sample alert
    test_alert = """🚨 *WALLET CLUSTER UPDATE* 🚨

*CAPTCHA* (Captcha)
`FtSRgyCEhKTc1PPgEAXvuHN3NyiP6LS9uyB28KCN3CAP`
💰 *Market Cap:* `$250.5K`
📈 *Price:* `$0.00001234`
💵 *Total SOL in Cluster:* `15.50 SOL`

🟢 *Triggered by:* LeBron (BUY)

👥 *7 Total Wallets | 💎 5 Holding | 💨 2 Sold*

🏆 LeBron | 💎 HOLDING 
  💰 2.50 SOL | ⏱ 2h 📍$25.8K

[📊 DexScreener] | [⚡ Photon]"""
    
    result = asyncio.run(process_tracker_alert(test_alert))
    print(result)
