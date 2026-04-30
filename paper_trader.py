#!/usr/bin/env python3
"""
ShadowHunter Paper Trading Bot

Autonomous paper trading system that:
- Starts with 1 SOL paper balance
- Makes buy/sell decisions based on tracked wallet activity
- Charges 0.01 SOL fee per trade
- Sends Telegram alerts for every trade
- Tracks portfolio, PnL, winrate
"""

import asyncio
import asyncpg
import aiohttp
import ssl
import certifi
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import os
import json
from dotenv import load_dotenv
from telegram import Bot
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

@dataclass
class PaperPosition:
    token: str
    token_name: str
    token_symbol: str
    entry_price: float  # Price in USD at entry
    entry_mc: float  # Market cap at entry
    tokens_bought: float
    sol_invested: float
    sol_spent_with_fees: float
    buy_time: datetime
    current_price: float = 0
    current_mc: float = 0
    unrealized_pnl: float = 0
    unrealized_roi: float = 0
    
@dataclass
class PaperTrade:
    timestamp: datetime
    action: str  # BUY or SELL
    token: str
    token_symbol: str
    amount_sol: float
    tokens: float
    price_usd: float
    market_cap: float
    fee: float = 0.01
    realized_pnl: float = 0
    realized_roi: float = 0
    notes: str = ""

@dataclass
class PaperPortfolio:
    sol_balance: float = 1.0  # Start with 1 SOL
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_fees_paid: float = 0
    realized_pnl: float = 0
    positions: Dict[str, PaperPosition] = field(default_factory=dict)
    trade_history: List[PaperTrade] = field(default_factory=list)
    
    @property
    def winrate(self) -> float:
        if self.total_trades == 0:
            return 0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def portfolio_value(self) -> float:
        # SOL balance + value of all positions
        position_value = sum(
            pos.tokens_bought * pos.current_price / pos.sol_invested * pos.sol_invested
            for pos in self.positions.values()
        )
        return self.sol_balance + position_value


class PaperTrader:
    def __init__(self):
        self.db: Optional[asyncpg.Connection] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.bot: Optional[Bot] = None
        self.channel_id = os.getenv('CHANNEL_PAPER_TRADES')
        self.portfolio = PaperPortfolio()
        self.running = False
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Trading parameters
        self.max_positions = 5  # Max concurrent positions
        self.min_signal_strength = 3  # Min wallet cluster size to trigger
        self.take_profit_levels = [2.0, 5.0, 10.0]  # 2x, 5x, 10x
        self.stop_loss = -0.50  # -50% stop loss
        
    async def connect(self):
        """Connect to database and Telegram"""
        self.db = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        
        # Load existing portfolio if any
        await self.load_portfolio()
        logger.info(f"Paper trader initialized. Balance: {self.portfolio.sol_balance:.2f} SOL")
        
    async def close(self):
        if self.db:
            await self.db.close()
        if self.session:
            await self.session.close()
            
    async def load_portfolio(self):
        """Load portfolio state from database"""
        try:
            row = await self.db.fetchrow(
                "SELECT data FROM paper_portfolio WHERE id = 1"
            )
            if row:
                data = json.loads(row['data'])
                self.portfolio.sol_balance = data.get('sol_balance', 1.0)
                self.portfolio.total_trades = data.get('total_trades', 0)
                self.portfolio.winning_trades = data.get('winning_trades', 0)
                self.portfolio.losing_trades = data.get('losing_trades', 0)
                self.portfolio.total_fees_paid = data.get('total_fees_paid', 0)
                self.portfolio.realized_pnl = data.get('realized_pnl', 0)
                logger.info(f"Loaded portfolio: {self.portfolio.sol_balance:.2f} SOL")
        except Exception as e:
            logger.info(f"No existing portfolio found, starting fresh: {e}")
            
    async def save_portfolio(self):
        """Save portfolio state to database"""
        try:
            data = {
                'sol_balance': self.portfolio.sol_balance,
                'total_trades': self.portfolio.total_trades,
                'winning_trades': self.portfolio.winning_trades,
                'losing_trades': self.portfolio.losing_trades,
                'total_fees_paid': self.portfolio.total_fees_paid,
                'realized_pnl': self.portfolio.realized_pnl,
                'positions_count': len(self.portfolio.positions),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.execute(
                """INSERT INTO paper_portfolio (id, data, updated_at) 
                VALUES (1, $1, NOW())
                ON CONFLICT (id) DO UPDATE 
                SET data = $1, updated_at = NOW()""",
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Failed to save portfolio: {e}")
            
    async def get_token_price(self, token: str) -> Optional[Dict]:
        """Get token price from DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get('pairs', [])
                    if pairs:
                        best = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0) or 0)
                        return {
                            'price': float(best.get('priceUsd', 0) or 0),
                            'market_cap': float(best.get('marketCap', 0) or 0),
                            'ticker': best.get('baseToken', {}).get('symbol', 'Unknown'),
                            'name': best.get('baseToken', {}).get('name', 'Unknown')
                        }
        except Exception as e:
            logger.error(f"Failed to get price for {token}: {e}")
        return None
        
    async def evaluate_buy_signal(self, token: str, cluster_wallets: List[Dict]) -> tuple[bool, str]:
        """Evaluate if we should buy based on cluster signal"""
        if len(cluster_wallets) < self.min_signal_strength:
            return False, f"Insufficient signal strength ({len(cluster_wallets)} wallets)"
            
        if token in self.portfolio.positions:
            return False, "Already holding this token"
            
        if len(self.portfolio.positions) >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})"
            
        if self.portfolio.sol_balance < 0.1:
            return False, f"Insufficient SOL balance ({self.portfolio.sol_balance:.2f})"
        
        # Calculate average entry MC of cluster
        avg_entry_mc = sum(w.get('avg_entry_mc', 0) for w in cluster_wallets) / len(cluster_wallets)
        
        # Get current token info
        token_info = await self.get_token_price(token)
        if not token_info:
            return False, "Could not get token price"
            
        current_mc = token_info['market_cap']
        
        # Don't buy if MC is too high (already pumped)
        if current_mc > 10_000_000:  # $10M MC
            return False, f"Market cap too high (${current_mc/1_000_000:.1f}M)"
            
        # Calculate how much SOL to invest (1-20% of balance based on conviction)
        conviction = min(len(cluster_wallets) / 10, 1.0)  # 3 wallets = 30%, 10+ = 100%
        investment_pct = 0.01 + (conviction * 0.19)  # 1% to 20%
        sol_to_invest = self.portfolio.sol_balance * investment_pct
        
        # Minimum 0.05 SOL, maximum 0.5 SOL per trade
        sol_to_invest = max(0.05, min(0.5, sol_to_invest))
        
        return True, f"Buy signal: {len(cluster_wallets)} wallets, investing {sol_to_invest:.2f} SOL"
        
    async def execute_buy(self, token: str, cluster_wallets: List[Dict]):
        """Execute a paper buy"""
        should_buy, reason = await self.evaluate_buy_signal(token, cluster_wallets)
        
        if not should_buy:
            logger.info(f"Buy rejected for {token[:8]}: {reason}")
            return
            
        token_info = await self.get_token_price(token)
        if not token_info:
            return
            
        # Calculate investment amount
        conviction = min(len(cluster_wallets) / 10, 1.0)
        investment_pct = 0.01 + (conviction * 0.19)
        sol_to_invest = self.portfolio.sol_balance * investment_pct
        sol_to_invest = max(0.05, min(0.5, sol_to_invest))
        
        # Deduct SOL + fee
        total_cost = sol_to_invest + 0.01
        self.portfolio.sol_balance -= total_cost
        self.portfolio.total_fees_paid += 0.01
        
        # Calculate tokens received
        price_sol = token_info['price'] / 150  # Approximate SOL price $150
        tokens_received = sol_to_invest / price_sol
        
        # Create position
        position = PaperPosition(
            token=token,
            token_name=token_info['name'],
            token_symbol=token_info['ticker'],
            entry_price=token_info['price'],
            entry_mc=token_info['market_cap'],
            tokens_bought=tokens_received,
            sol_invested=sol_to_invest,
            sol_spent_with_fees=total_cost,
            buy_time=datetime.now(timezone.utc),
            current_price=token_info['price'],
            current_mc=token_info['market_cap']
        )
        
        self.portfolio.positions[token] = position
        self.portfolio.total_trades += 1
        
        # Record trade
        trade = PaperTrade(
            timestamp=datetime.now(timezone.utc),
            action="BUY",
            token=token,
            token_symbol=token_info['ticker'],
            amount_sol=sol_to_invest,
            tokens=tokens_received,
            price_usd=token_info['price'],
            market_cap=token_info['market_cap'],
            fee=0.01,
            notes=f"Cluster of {len(cluster_wallets)} wallets"
        )
        self.portfolio.trade_history.append(trade)
        
        # Save and notify
        await self.save_portfolio()
        await self.send_trade_alert(trade, position)
        
        logger.info(f"BUY: {token_info['ticker']} | {sol_to_invest:.2f} SOL | {tokens_received:.2f} tokens")
        
    async def evaluate_sell_signal(self, token: str, current_price: float, current_mc: float) -> tuple[bool, str]:
        """Evaluate if we should sell based on PnL"""
        if token not in self.portfolio.positions:
            return False, "Not holding this token"
            
        position = self.portfolio.positions[token]
        
        # Calculate ROI
        roi = (current_price - position.entry_price) / position.entry_price
        
        # Take profit levels
        for level in self.take_profit_levels:
            if roi >= level:
                return True, f"Take profit at {roi*100:.0f}% ROI (target: {level*100:.0f}%)"
                
        # Stop loss
        if roi <= self.stop_loss:
            return True, f"Stop loss triggered at {roi*100:.0f}% ROI"
            
        return False, f"Holding: {roi*100:.1f}% ROI"
        
    async def execute_sell(self, token: str, reason: str = "Signal"):
        """Execute a paper sell"""
        if token not in self.portfolio.positions:
            return
            
        position = self.portfolio.positions[token]
        
        # Get current price
        token_info = await self.get_token_price(token)
        if token_info:
            current_price = token_info['price']
            current_mc = token_info['market_cap']
        else:
            current_price = position.current_price
            current_mc = position.current_mc
            
        # Calculate proceeds
        price_sol = current_price / 150
        sol_received = position.tokens_bought * price_sol
        
        # Deduct fee
        sol_after_fees = sol_received - 0.01
        self.portfolio.total_fees_paid += 0.01
        
        # Calculate PnL
        realized_pnl = sol_after_fees - position.sol_invested
        realized_roi = (realized_pnl / position.sol_invested) * 100
        
        # Update portfolio
        self.portfolio.sol_balance += sol_after_fees
        self.portfolio.realized_pnl += realized_pnl
        self.portfolio.total_trades += 1
        
        if realized_pnl > 0:
            self.portfolio.winning_trades += 1
        else:
            self.portfolio.losing_trades += 1
            
        # Record trade
        trade = PaperTrade(
            timestamp=datetime.now(timezone.utc),
            action="SELL",
            token=token,
            token_symbol=position.token_symbol,
            amount_sol=sol_received,
            tokens=position.tokens_bought,
            price_usd=current_price,
            market_cap=current_mc,
            fee=0.01,
            realized_pnl=realized_pnl,
            realized_roi=realized_roi,
            notes=reason
        )
        self.portfolio.trade_history.append(trade)
        
        # Remove position
        del self.portfolio.positions[token]
        
        # Save and notify
        await self.save_portfolio()
        await self.send_trade_alert(trade, None)
        
        logger.info(f"SELL: {position.token_symbol} | PnL: {realized_pnl:+.2f} SOL ({realized_roi:+.1f}%)")
        
    async def send_trade_alert(self, trade: PaperTrade, position: Optional[PaperPosition]):
        """Send Telegram alert for trade"""
        if not self.bot or not self.channel_id:
            return
            
        try:
            emoji = "🟢" if trade.action == "BUY" else "🔴"
            pnl_line = ""
            
            if trade.action == "SELL" and trade.realized_pnl != 0:
                pnl_emoji = "🟢" if trade.realized_pnl > 0 else "🔴"
                pnl_line = f"\n{pnl_emoji} Realized PnL: `{trade.realized_pnl:+.2f}` SOL ({trade.realized_roi:+.1f}%)"
            
            mc_str = f"${trade.market_cap/1000:.1f}K" if trade.market_cap < 1_000_000 else f"${trade.market_cap/1_000_000:.2f}M"
            
            message = f"""{emoji} *PAPER TRADE: {trade.action}*

*{trade.token_symbol}*
`{trade.token}`

💰 Amount: `{trade.amount_sol:.2f}` SOL
🪙 Tokens: `{trade.tokens:.2f}`
📊 Price: `${trade.price_usd:.8f}`
💎 Market Cap: `{mc_str}`
💸 Fee: `0.01` SOL
📝 {trade.notes}{pnl_line}

💼 Portfolio: `{self.portfolio.sol_balance:.2f}` SOL
📈 Winrate: `{self.portfolio.winrate:.1f}%` ({self.portfolio.winning_trades}W/{self.portfolio.losing_trades}L)
📊 Total PnL: `{self.portfolio.realized_pnl:+.2f}` SOL

[📊 DexScreener](https://dexscreener.com/solana/{trade.token})
[⚡ Photon](https://photon-sol.tinyastro.io/en/lp/{trade.token})"""

            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send trade alert: {e}")
            
    async def update_positions(self):
        """Update current prices and check for sell signals"""
        for token, position in list(self.portfolio.positions.items()):
            try:
                token_info = await self.get_token_price(token)
                if not token_info:
                    continue
                    
                position.current_price = token_info['price']
                position.current_mc = token_info['market_cap']
                
                # Calculate unrealized PnL
                price_change = (position.current_price - position.entry_price) / position.entry_price
                position.unrealized_roi = price_change * 100
                position.unrealized_pnl = position.sol_invested * price_change
                
                # Check sell signal
                should_sell, reason = await self.evaluate_sell_signal(
                    token, position.current_price, position.current_mc
                )
                
                if should_sell:
                    await self.execute_sell(token, reason)
                    
            except Exception as e:
                logger.error(f"Error updating position {token[:8]}: {e}")
                
    async def check_for_opportunities(self):
        """Monitor database for new cluster signals"""
        try:
            # Find tokens with recent cluster activity
            rows = await self.db.fetch(
                """SELECT DISTINCT token_address, COUNT(*) as wallet_count,
                   MAX(last_buy_time) as latest_activity
                FROM wallet_positions
                WHERE first_buy_time > NOW() - INTERVAL '5 minutes'
                GROUP BY token_address
                HAVING COUNT(*) >= $1
                ORDER BY latest_activity DESC""",
                self.min_signal_strength
            )
            
            for row in rows:
                token = row['token_address']
                
                # Skip if already holding
                if token in self.portfolio.positions:
                    continue
                    
                # Get cluster details
                wallet_rows = await self.db.fetch(
                    """SELECT wallet_address, total_sol_invested, avg_entry_mc
                    FROM wallet_positions
                    WHERE token_address = $1""",
                    token
                )
                
                cluster_wallets = [
                    {
                        'wallet': w['wallet_address'],
                        'sol_invested': float(w['total_sol_invested'] or 0),
                        'avg_entry_mc': float(w['avg_entry_mc'] or 0)
                    }
                    for w in wallet_rows
                ]
                
                # Evaluate buy
                await self.execute_buy(token, cluster_wallets)
                
        except Exception as e:
            logger.error(f"Error checking opportunities: {e}")
            
    async def send_portfolio_summary(self):
        """Send daily portfolio summary"""
        if not self.bot or not self.channel_id:
            return
            
        try:
            message = f"""📊 *PAPER TRADING SUMMARY*

💰 SOL Balance: `{self.portfolio.sol_balance:.2f}` SOL
📈 Total Trades: `{self.portfolio.total_trades}`
✅ Winrate: `{self.portfolio.winrate:.1f}%`
🟢 Wins: `{self.portfolio.winning_trades}`
🔴 Losses: `{self.portfolio.losing_trades}`
💎 Realized PnL: `{self.portfolio.realized_pnl:+.2f}` SOL
💸 Total Fees: `{self.portfolio.total_fees_paid:.2f}` SOL
📦 Open Positions: `{len(self.portfolio.positions)}`
"""
            if self.portfolio.positions:
                message += "\n*Open Positions:*\n"
                for token, pos in self.portfolio.positions.items():
                    emoji = "🟢" if pos.unrealized_pnl >= 0 else "🔴"
                    message += f"• {pos.token_symbol}: {emoji} {pos.unrealized_pnl:+.2f} SOL ({pos.unrealized_roi:+.1f}%)\n"
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send summary: {e}")
            
    async def run(self):
        """Main loop"""
        await self.connect()
        self.running = True
        
        logger.info("Paper trader started")
        await self.send_portfolio_summary()
        
        cycle = 0
        while self.running:
            try:
                # Check for new buy opportunities
                await self.check_for_opportunities()
                
                # Update positions and check sells
                await self.update_positions()
                
                # Save state
                await self.save_portfolio()
                
                # Send summary every 10 cycles (approx 5 minutes)
                cycle += 1
                if cycle % 10 == 0:
                    await self.send_portfolio_summary()
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
            await asyncio.sleep(30)  # Check every 30 seconds
            
        await self.close()


async def main():
    trader = PaperTrader()
    try:
        await trader.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        trader.running = False
        await trader.close()


if __name__ == "__main__":
    asyncio.run(main())
