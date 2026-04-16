#!/usr/bin/env python3
"""
Agent Monitor - Background process to watch for alerts

Polls database for new wallet activity and triggers trading decisions.
"""

import asyncio
import asyncpg
import os
import json
from datetime import datetime, timezone
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the trading logic
import sys
sys.path.insert(0, '/root/.openclaw/workspace')
from agent_trading import AgentTrader, process_alert

class AgentMonitor:
    def __init__(self):
        self.db = None
        self.last_check = datetime.now(timezone.utc)
        self.processed_tokens = set()
        
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
    
    async def get_new_activity(self) -> List[Dict]:
        """Get token activity since last check"""
        rows = await self.db.fetch(
            """SELECT 
                token_address,
                COUNT(*) as wallet_count,
                array_agg(wallet_address) as wallets,
                MAX(first_buy_time) as latest_activity
            FROM wallet_positions
            WHERE first_buy_time > $1
            GROUP BY token_address
            HAVING COUNT(*) >= 2
            ORDER BY latest_activity DESC""",
            self.last_check
        )
        
        self.last_check = datetime.now(timezone.utc)
        
        return [
            {
                'token': row['token_address'],
                'wallet_count': row['wallet_count'],
                'wallets': row['wallets']
            }
            for row in rows
            if row['token_address'] not in self.processed_tokens
        ]
    
    async def run(self):
        """Main monitoring loop"""
        await self.connect()
        logger.info("Agent monitor started - watching for alerts")
        
        cycle = 0
        while True:
            try:
                # Check for new activity
                activities = await self.get_new_activity()
                
                for activity in activities:
                    token = activity['token']
                    wallets = activity['wallets']
                    
                    logger.info(f"New activity: {token[:8]}... with {len(wallets)} wallets")
                    
                    # Process through trading logic
                    alert_text = f"🚨 CLUSTER: {len(wallets)} wallets on token\n`{token}`\n\nWallets: {', '.join(w[:8] for w in wallets[:5])}"
                    
                    result = await process_alert(alert_text, wallets)
                    
                    # Log the decision
                    logger.info(f"Decision for {token[:8]}: {result[:100]}...")
                    
                    # Mark as processed
                    self.processed_tokens.add(token)
                    
                    # Keep set from growing too large
                    if len(self.processed_tokens) > 1000:
                        self.processed_tokens = set(list(self.processed_tokens)[-500:])
                
                cycle += 1
                if cycle % 10 == 0:
                    logger.info(f"Monitor cycle {cycle} - watching...")
                    
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds


async def main():
    monitor = AgentMonitor()
    try:
        await monitor.run()
    except KeyboardInterrupt:
        logger.info("Monitor stopped")
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
