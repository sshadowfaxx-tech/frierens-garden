#!/usr/bin/env python3
"""
ShadowHunter Agent Monitor - FULL ALERT VISIBILITY (FUNCTIONAL FIXES)

Fixes applied:
1. Added proper error logging (no more silent failures)
2. Fixed unbounded memory growth (deque with maxlen)
3. Added connection retry logic
4. Fixed race condition in last_check update
5. Added session cleanup on exception
"""

import asyncio
import asyncpg
import aiohttp
import ssl
import certifi
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from telegram import Bot
import logging
from collections import deque

# Ensure dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("WARNING: python-dotenv not installed. Run: pip install python-dotenv")
    print("Environment variables must be set manually.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('agent_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ssl_context = ssl.create_default_context(cafile=certifi.where())

# Wallet weights
WALLET_WEIGHTS = {
    'G5nxEXuFMfV74DSnsrSatqCW32F34XUnBeq3PfDS7w5E': 3.0,  # Profit
    'HYWo71Wk9PNDe5sBaRKazPnVyGnQDiwgXCFKvgAQ1ENp': 3.0,  # Moonpie?
    '8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6': 3.0,  # Cooker
    '2p2mgFLmzN82sShZeAaBGmj9zFpam4xu8g4g3wqx2ks6': 1.5,  # Shy/Coyote
    '78N177fzNJpp8pG49xDv1efYcTMSzo9tPTKEA9mAVkh2': 1.5,  # Sheep
    '215nhcAHjQQGgwpQSJQ7zR26etbjjtVdW74NLzwEgQjP': 1.5,  # OGANTD
    'GJA1HEbxGnqBhBifH9uQauzXSB53to5rhDrzmKxhSU65': 1.5,  # Latuche
}

WALLET_LABELS = {}

def load_wallet_labels():
    try:
        with open('wallets.txt', 'r') as f:
            for line in f:
                if '|' in line:
                    addr, label = line.strip().split('|', 1)
                    WALLET_LABELS[addr] = label
    except Exception as e:
        logger.error(f"Failed to load wallet labels: {e}")

load_wallet_labels()


class FullVisibilityAgent:
    def __init__(self):
        self.db = None
        self.session = None
        self.bot = None
        self.log_channel = os.getenv('CHANNEL_AGENT_LOGS')
        self.paper_balance = 2.0
        self.last_check = datetime.now() - timedelta(minutes=5)
        self.is_first_run = True
        # FIX: Use deque with maxlen to prevent unbounded growth
        self.processed_activity = deque(maxlen=1000)
        self.total_trades = 0
        
    async def connect(self):
        # FIX: Add retry logic for database connection
        for attempt in range(3):
            try:
                self.db = await asyncpg.connect(
                    host=os.getenv('DB_HOST', 'localhost'),
                    port=int(os.getenv('DB_PORT', 5432)),
                    database=os.getenv('DB_NAME', 'shadowhunter'),
                    user=os.getenv('DB_USER', 'postgres'),
                    password=os.getenv('DB_PASSWORD', 'sh123')
                )
                logger.info("Database connected")
                break
            except Exception as e:
                logger.error(f"DB connection attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        
        await self.load_portfolio()
        logger.info("Full-visibility agent started")
        
    async def close(self):
        if self.db: 
            try:
                await self.db.close()
            except Exception as e:
                logger.error(f"Error closing DB: {e}")
        if self.session: 
            try:
                await self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
    
    async def load_portfolio(self):
        try:
            row = await self.db.fetchrow("SELECT data FROM paper_portfolio WHERE id = 1")
            if row:
                data = json.loads(row['data'])
                self.paper_balance = data.get('sol_balance', 2.0)
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
    
    async def save_portfolio(self):
        try:
            await self.db.execute(
                "UPDATE paper_portfolio SET data = $1, updated_at = NOW() WHERE id = 1",
                json.dumps({'sol_balance': self.paper_balance, 'total_trades': self.total_trades})
            )
        except Exception as e:
            logger.error(f"Failed to save portfolio: {e}")
    
    async def get_all_recent_activity(self) -> List[Dict]:
        """Get ALL recent wallet activity - FIXED race condition"""
        
        # Store current time BEFORE query to prevent race condition
        query_start_time = datetime.now()
        
        try:
            # FIXED: Calculate winrate from winning_trades/total_trades
            trades = await self.db.fetch(
                """SELECT 
                    w.wallet_address,
                    w.token_address,
                    w.total_sol_invested,
                    w.total_bought,
                    w.avg_entry_mc,
                    w.first_buy_time,
                    CASE 
                        WHEN p.total_trades > 0 THEN (p.winning_trades::float / p.total_trades * 100)
                        ELSE 0 
                    END as wallet_winrate,
                    COALESCE(p.realized_pnl, 0) as wallet_pnl
                FROM wallet_positions w
                LEFT JOIN wallet_performance p ON w.wallet_address = p.wallet_address
                WHERE w.first_buy_time > $1
                ORDER BY w.first_buy_time DESC
                LIMIT 50""",
                self.last_check
            )
            
            # Get cluster activity
            clusters = await self.db.fetch(
                """SELECT 
                    token_address,
                    COUNT(*) as wallet_count,
                    array_agg(wallet_address) as wallets,
                    SUM(total_sol_invested) as total_sol,
                    MAX(first_buy_time) as latest
                FROM wallet_positions
                WHERE first_buy_time > $1
                GROUP BY token_address
                HAVING COUNT(*) >= 2
                ORDER BY latest DESC""",
                self.last_check
            )
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return []
        
        # Update last_check AFTER successful query to prevent missing items
        self.last_check = query_start_time
        
        activities = []
        
        # Add individual trades
        for row in trades:
            activity_id = f"trade_{row['wallet_address']}_{row['token_address']}"
            if activity_id not in self.processed_activity:
                activities.append({
                    'type': 'individual_trade',
                    'id': activity_id,
                    'wallet': row['wallet_address'],
                    'token': row['token_address'],
                    'label': WALLET_LABELS.get(row['wallet_address'], row['wallet_address'][:8]),
                    'sol_invested': float(row['total_sol_invested'] or 0),
                    'entry_mc': float(row['avg_entry_mc'] or 0),
                    'wallet_winrate': float(row['wallet_winrate'] or 0),
                    'wallet_pnl': float(row['wallet_pnl'] or 0),
                    'first_buy_time': row['first_buy_time']  # Include for proper sorting
                })
        
        # Add clusters
        for row in clusters:
            activity_id = f"cluster_{row['token_address']}"
            if activity_id not in self.processed_activity:
                wallets = row['wallets']
                total_weight = sum(WALLET_WEIGHTS.get(w, 1.0) for w in wallets)
                high_wallets = [WALLET_LABELS.get(w, w[:8]) for w in wallets if WALLET_WEIGHTS.get(w, 0) >= 1.5]
                
                activities.append({
                    'type': 'cluster',
                    'id': activity_id,
                    'token': row['token_address'],
                    'wallet_count': row['wallet_count'],
                    'wallets': wallets,
                    'total_sol': float(row['total_sol'] or 0),
                    'total_weight': total_weight,
                    'high_conviction_wallets': high_wallets,
                    'first_buy_time': row['latest']  # Include for proper sorting
                })
        
        return activities
    
    async def research_token(self, token: str) -> Dict:
        """Quick token research - FIXED session cleanup"""
        info = {'found': False, 'symbol': 'Unknown', 'market_cap': 0, 'liquidity': 0, 'age_hours': 999, 'narrative': 'Unknown'}
        
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
                        
                        created = best.get('pairCreatedAt')
                        if created:
                            info['age_hours'] = (datetime.now(timezone.utc).timestamp() * 1000 - created) / (1000 * 60 * 60)
                        
                        name = best.get('baseToken', {}).get('name', '').lower()
                        symbol = info['symbol'].lower()
                        if any(x in name or x in symbol for x in ['ai', 'gpt', 'bot']):
                            info['narrative'] = 'AI'
                        elif any(x in name or x in symbol for x in ['pepe', 'doge', 'shib', 'moon']):
                            info['narrative'] = 'Meme'
                        else:
                            info['narrative'] = 'Other'
        except Exception as e:
            logger.error(f"Token research failed for {token}: {e}")
        
        return info
    
    def calculate_decision(self, activity: Dict, token_info: Dict) -> Dict:
        """Calculate trading decision"""
        decision = {'action': 'WATCH', 'confidence': 0, 'reasoning': [], 'position_size': 0}
        
        if activity['type'] == 'cluster':
            weight = activity.get('total_weight', 0)
            
            if weight >= 8:
                decision['confidence'] = 80
                decision['action'] = 'BUY'
                decision['position_size'] = 0.20
                decision['reasoning'].append(f"High weight: {weight:.1f}x")
            elif weight >= 5:
                decision['confidence'] = 60
                decision['action'] = 'BUY'
                decision['position_size'] = 0.15
                decision['reasoning'].append(f"Good weight: {weight:.1f}x")
            elif weight >= 3:
                decision['confidence'] = 40
                decision['action'] = 'BUY'
                decision['position_size'] = 0.10
                decision['reasoning'].append(f"Moderate weight: {weight:.1f}x")
            else:
                decision['confidence'] = 20
                decision['reasoning'].append(f"Low weight: {weight:.1f}x")
            
            if activity.get('high_conviction_wallets'):
                decision['reasoning'].append(f"Key: {', '.join(activity['high_conviction_wallets'][:3])}")
        
        elif activity['type'] == 'individual_trade':
            winrate = activity.get('wallet_winrate', 0)
            pnl = activity.get('wallet_pnl', 0)
            
            if winrate >= 50 and pnl > 0:
                decision['confidence'] = 50
                decision['action'] = 'WATCH'
                decision['reasoning'].append(f"Strong: {winrate:.0f}% WR, +{pnl:.1f} SOL")
            elif pnl > 0:
                decision['confidence'] = 30
                decision['action'] = 'WATCH'
                decision['reasoning'].append(f"Profitable: +{pnl:.1f} SOL")
            else:
                decision['confidence'] = 10
                decision['reasoning'].append(f"Weak: {winrate:.0f}% WR")
        
        # Token info adjustments
        if token_info['found']:
            if token_info['narrative'] == 'AI':
                decision['confidence'] += 10
                decision['reasoning'].append("AI narrative")
            
            if token_info['age_hours'] < 1:
                decision['confidence'] += 10
                decision['reasoning'].append("Just launched")
            
            if token_info['market_cap'] < 500000:
                decision['confidence'] += 10
                decision['reasoning'].append("Low MC")
            elif token_info['market_cap'] > 10000000:
                decision['confidence'] -= 20
                decision['reasoning'].append("High MC")
            
            if token_info['liquidity'] > 50000:
                decision['confidence'] += 5
                decision['reasoning'].append("Good liq")
        
        decision['confidence'] = max(0, min(100, decision['confidence']))
        
        if decision['confidence'] < 25:
            decision['action'] = 'SKIP'
        elif decision['confidence'] < 40:
            decision['action'] = 'WATCH'
        
        return decision
    
    async def execute_paper_trade(self, decision: Dict, token: str, symbol: str) -> Optional[Dict]:
        """Execute paper trade"""
        if decision['action'] != 'BUY':
            return None
        
        amount = self.paper_balance * decision['position_size']
        amount = max(0.05, min(0.5, amount))
        
        if self.paper_balance < amount + 0.01:
            logger.warning(f"Insufficient balance: {self.paper_balance} SOL")
            return None
        
        try:
            await self.db.execute(
                """INSERT INTO paper_trades 
                (timestamp, action, token, token_symbol, amount_sol, fee, notes)
                VALUES (NOW(), 'BUY', $1, $2, $3, 0.01, $4)""",
                token, symbol, amount,
                json.dumps({'confidence': decision['confidence'], 'reasoning': decision['reasoning']})
            )
            
            self.paper_balance -= (amount + 0.01)
            self.total_trades += 1
            await self.save_portfolio()
            
            return {'amount': amount, 'balance': self.paper_balance}
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return None
    
    async def send_to_telegram(self, message: str):
        """Send message to Telegram channel"""
        if not self.bot or not self.log_channel:
            return
        
        try:
            await self.bot.send_message(
                chat_id=self.log_channel,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    def format_alert_report(self, activity: Dict, token_info: Dict, decision: Dict, trade_result: Optional[Dict]) -> str:
        """Format full alert report"""
        
        if activity['type'] == 'cluster':
            emoji = "🚨"
            header = f"{emoji} *CLUSTER ALERT* ({activity['wallet_count']} wallets)"
        else:
            emoji = "👤"
            header = f"{emoji} *INDIVIDUAL TRADE* ({activity['label']})"
        
        report = f"""{header}

*{token_info.get('symbol', 'Unknown')}*
`{activity['token']}`
"""
        
        if activity['type'] == 'cluster':
            report += f"\n📊 *Cluster Data:*"
            report += f"\n• Total SOL: {activity['total_sol']:.2f}"
            report += f"\n• Weight: {activity['total_weight']:.1f}x"
            if activity.get('high_conviction_wallets'):
                report += f"\n• Key: {', '.join(activity['high_conviction_wallets'])}"
        else:
            report += f"\n📊 *Wallet Data:*"
            report += f"\n• Invested: {activity['sol_invested']:.2f} SOL"
            report += f"\n• Winrate: {activity['wallet_winrate']:.0f}%"
            report += f"\n• PnL: {activity['wallet_pnl']:+.1f} SOL"
        
        if token_info.get('found'):
            mc_str = f"${token_info['market_cap']/1000:.0f}K" if token_info['market_cap'] < 1000000 else f"${token_info['market_cap']/1000000:.1f}M"
            report += f"\n\n📈 *Token Info:*"
            report += f"\n• Narrative: {token_info['narrative']}"
            report += f"\n• MC: {mc_str}"
            report += f"\n• Age: {token_info['age_hours']:.1f}h"
            report += f"\n• Liq: ${token_info['liquidity']/1000:.0f}K"
        
        # Decision
        action_emoji = {"BUY": "🟢", "WATCH": "👀", "SKIP": "❌"}.get(decision['action'], "⚪")
        report += f"\n\n{action_emoji} *AGENT DECISION: {decision['action']}*"
        report += f"\n• Confidence: {decision['confidence']}%"
        
        for reason in decision['reasoning'][:4]:
            report += f"\n• {reason}"
        
        if trade_result:
            report += f"\n\n💰 *Paper Trade:* {trade_result['amount']:.2f} SOL"
            report += f"\n💼 *Balance:* {trade_result['balance']:.2f} SOL"
        
        return report
    
    async def run(self):
        """Main loop - reports ALL activity"""
        await self.connect()
        
        await self.send_to_telegram("🤖 *Agent Monitor Started*\n\nMonitoring all wallet activity...")
        logger.info("Full-visibility agent started")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                activities = await self.get_all_recent_activity()
                
                # On first run, mark activities as processed and update last_check
                if self.is_first_run:
                    if activities:
                        logger.info(f"First run: Processing {len(activities)} recent activities")
                        self.last_check = datetime.now()
                        for activity in activities:
                            self.processed_activity.append(activity['id'])
                        await self.send_to_telegram(f"📊 *Startup Complete*\n\nFound {len(activities)} recent positions.\nNow monitoring for NEW activity...")
                    else:
                        await self.send_to_telegram("📊 *Startup Complete*\n\nNo recent positions found.\nWaiting for new activity...")
                    self.is_first_run = False
                    continue
                
                for activity in activities:
                    token_info = await self.research_token(activity['token'])
                    decision = self.calculate_decision(activity, token_info)
                    
                    trade_result = None
                    if decision['action'] == 'BUY':
                        trade_result = await self.execute_paper_trade(
                            decision, activity['token'], token_info.get('symbol', 'Unknown')
                        )
                    
                    report = self.format_alert_report(activity, token_info, decision, trade_result)
                    await self.send_to_telegram(report)
                    
                    logger.info(f"Processed {activity['type']}: {activity['token'][:16]}... Decision: {decision['action']}")
                    
                    self.processed_activity.append(activity['id'])
                    
                    await asyncio.sleep(1)
                
                if cycle % 40 == 0:
                    status = f"📊 *Status Update*\nBalance: {self.paper_balance:.2f} SOL | Trades: {self.total_trades}"
                    await self.send_to_telegram(status)
                    
            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
            
            await asyncio.sleep(10)


async def main():
    agent = FullVisibilityAgent()
    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.send_to_telegram("🛑 *Agent Monitor Stopped*")
        await agent.close()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
