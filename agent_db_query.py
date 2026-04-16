#!/usr/bin/env python3
"""
Database Query Tool for Agent Trading

Query wallet performance, trade history, and patterns.
"""

import asyncio
import asyncpg
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class WalletStats:
    wallet: str
    label: str
    total_trades: int
    winrate: float
    realized_pnl: float
    avg_roi: float
    avg_hold_time: str
    recent_performance: str  # improving | declining | stable


class AgentDatabase:
    def __init__(self):
        self.db: Optional[asyncpg.Connection] = None
        
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
    
    async def get_wallet_stats(self, wallet: str) -> Optional[WalletStats]:
        """Get detailed stats for a specific wallet"""
        row = await self.db.fetchrow(
            """SELECT 
                wallet_address, total_trades, winning_trades, losing_trades,
                realized_pnl, avg_roi, total_hold_time_seconds
            FROM wallet_performance 
            WHERE wallet_address = $1""",
            wallet
        )
        
        if not row:
            return None
        
        # Calculate winrate
        total = row['total_trades'] or 0
        wins = row['winning_trades'] or 0
        winrate = (wins / total * 100) if total > 0 else 0
        
        # Format hold time
        hold_secs = row['total_hold_time_seconds'] or 0
        if total > 0:
            avg_hold = hold_secs / total
            if avg_hold > 86400:
                hold_str = f"{avg_hold/86400:.1f}d"
            elif avg_hold > 3600:
                hold_str = f"{avg_hold/3600:.1f}h"
            else:
                hold_str = f"{avg_hold/60:.0f}m"
        else:
            hold_str = "N/A"
        
        # Check recent performance (last 7 days)
        recent = await self.db.fetchrow(
            """SELECT 
                COUNT(*) as trades,
                COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as wins
            FROM wallet_positions 
            WHERE wallet_address = $1 
            AND updated_at > NOW() - INTERVAL '7 days'""",
            wallet
        )
        
        recent_trades = recent['trades'] if recent else 0
        recent_wins = recent['wins'] if recent else 0
        
        if recent_trades >= 3:
            recent_wr = recent_wins / recent_trades
            if recent_wr >= 0.6:
                trend = "improving 🔥"
            elif recent_wr <= 0.3:
                trend = "declining 📉"
            else:
                trend = "stable 📊"
        else:
            trend = "insufficient data"
        
        return WalletStats(
            wallet=wallet,
            label=wallet[:8] + "...",
            total_trades=total,
            winrate=winrate,
            realized_pnl=float(row['realized_pnl'] or 0),
            avg_roi=float(row['avg_roi'] or 0),
            avg_hold_time=hold_str,
            recent_performance=trend
        )
    
    async def get_wallet_trade_history(self, wallet: str, limit: int = 10) -> List[Dict]:
        """Get recent trades for a wallet"""
        rows = await self.db.fetch(
            """SELECT 
                token_address, total_sol_invested, total_sol_returned,
                total_bought, total_sold, avg_entry_mc, first_buy_time
            FROM wallet_positions
            WHERE wallet_address = $1
            ORDER BY first_buy_time DESC
            LIMIT $2""",
            wallet, limit
        )
        
        trades = []
        for row in rows:
            pnl = float(row['total_sol_returned'] or 0) - float(row['total_sol_invested'] or 0)
            roi = (pnl / float(row['total_sol_invested'] or 1)) * 100
            
            trades.append({
                'token': row['token_address'][:8] + "...",
                'invested': float(row['total_sol_invested'] or 0),
                'returned': float(row['total_sol_returned'] or 0),
                'pnl': pnl,
                'roi': roi,
                'entry_mc': float(row['avg_entry_mc'] or 0)
            })
        
        return trades
    
    async def get_token_wallet_activity(self, token: str) -> List[Dict]:
        """Get all wallet activity for a specific token"""
        rows = await self.db.fetch(
            """SELECT 
                w.wallet_address, w.total_sol_invested, w.total_bought,
                w.total_sold, w.avg_entry_mc, p.realized_pnl, p.winrate
            FROM wallet_positions w
            LEFT JOIN wallet_performance p ON w.wallet_address = p.wallet_address
            WHERE w.token_address = $1
            ORDER BY w.total_sol_invested DESC""",
            token
        )
        
        activity = []
        for row in rows:
            activity.append({
                'wallet': row['wallet_address'][:8] + "...",
                'invested': float(row['total_sol_invested'] or 0),
                'bought': float(row['total_bought'] or 0),
                'sold': float(row['total_sold'] or 0),
                'entry_mc': float(row['avg_entry_mc'] or 0),
                'wallet_pnl': float(row['realized_pnl'] or 0),
                'wallet_winrate': float(row['winrate'] or 0)
            })
        
        return activity
    
    async def get_cluster_opportunities(self, min_wallets: int = 3) -> List[Dict]:
        """Find tokens with multiple wallet activity"""
        rows = await self.db.fetch(
            """SELECT 
                token_address,
                COUNT(*) as wallet_count,
                SUM(total_sol_invested) as total_invested,
                AVG(avg_entry_mc) as avg_entry_mc
            FROM wallet_positions
            WHERE first_buy_time > NOW() - INTERVAL '1 hour'
            GROUP BY token_address
            HAVING COUNT(*) >= $1
            ORDER BY total_invested DESC""",
            min_wallets
        )
        
        opportunities = []
        for row in rows:
            opportunities.append({
                'token': row['token_address'],
                'wallet_count': row['wallet_count'],
                'total_sol': float(row['total_invested'] or 0),
                'avg_entry_mc': float(row['avg_entry_mc'] or 0)
            })
        
        return opportunities
    
    async def generate_wallet_report(self, wallet: str) -> str:
        """Generate a text report for a wallet"""
        stats = await self.get_wallet_stats(wallet)
        if not stats:
            return f"No data for wallet {wallet[:8]}..."
        
        report = f"""📊 *WALLET ANALYSIS*

*{stats.label}*
`{wallet}`

📈 *Performance:*
• Winrate: {stats.winrate:.1f}% ({stats.total_trades} trades)
• Total PnL: {stats.realized_pnl:+.2f} SOL
• Avg ROI: {stats.avg_roi:+.1f}%
• Avg Hold: {stats.avg_hold_time}
• Trend: {stats.recent_performance}

📜 *Recent Trades:*
"""
        
        trades = await self.get_wallet_trade_history(wallet, 5)
        for t in trades:
            emoji = "🟢" if t['pnl'] >= 0 else "🔴"
            mc_str = f"${t['entry_mc']/1000:.0f}K" if t['entry_mc'] < 1000000 else f"${t['entry_mc']/1000000:.1f}M"
            report += f"• {t['token']} | {emoji} {t['pnl']:+.2f} SOL | Entry: {mc_str}\n"
        
        return report


async def main():
    import sys
    db = AgentDatabase()
    await db.connect()
    
    try:
        if len(sys.argv) > 1:
            wallet = sys.argv[1]
            report = await db.generate_wallet_report(wallet)
            print(report)
        else:
            # Show top opportunities
            print("🔍 *CURRENT CLUSTER OPPORTUNITIES*\n")
            ops = await db.get_cluster_opportunities(3)
            for op in ops:
                mc_str = f"${op['avg_entry_mc']/1000:.0f}K" if op['avg_entry_mc'] < 1000000 else f"${op['avg_entry_mc']/1000000:.1f}M"
                print(f"• {op['token'][:8]}... | {op['wallet_count']} wallets | {op['total_sol']:.2f} SOL | Avg Entry: {mc_str}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
