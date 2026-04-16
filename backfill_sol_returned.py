#!/usr/bin/env python3
"""
Backfill script v3 - Improved SOL returned detection
"""

import asyncio
import asyncpg
import aiohttp
import ssl
import certifi
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

RPC_URLS = [
    HELIUS_RPC_URL,
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com"
]

DEX_PROGRAMS = {
    'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4',
    '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
    '5quB7PxxgfP86MCT74D29itB5RFzZPn6Y4zvGJY6Vj6S',  # Raydium CLMM
    'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc',
    'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo',
    '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
    '39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJmw',
    '7OjPdbU7RjUoJzUpK1wZsWkdtWPS5bDrPmfxnzMT3JFR',
    'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK',  # Raydium CLMM
    'MoonCVVNZFSYkqNXP6bxHLPL6QQxAvKm4Mj6aEwapqq',
    'TSWAPa5r5W7X25VmhV2H6HBS4zrHYtrD7Tq5w1H7yqF',
}


class SolReturnedBackfill:
    def __init__(self):
        self.db = None
        self.session = None
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.connector = aiohttp.TCPConnector(ssl=ssl_context, limit=50)
        self.processed = 0
        self.updated = 0

    async def connect(self):
        self.db = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(connector=self.connector, timeout=timeout)

    async def close(self):
        if self.db:
            await self.db.close()
        if self.session:
            await self.session.close()

    async def get_positions(self) -> List[Dict]:
        rows = await self.db.fetch(
            """SELECT wallet_address, token_address, total_sold, total_bought, 
                total_sol_invested, first_buy_time
            FROM wallet_positions
            WHERE total_sold > 0.0001
            AND (total_sol_returned IS NULL OR total_sol_returned = 0)
            ORDER BY first_buy_time DESC
            LIMIT 500"""
        )
        return [dict(r) for r in rows]

    async def fetch_txs(self, wallet: str, before: str = None) -> List[Dict]:
        params = {"limit": 100, "commitment": "confirmed"}
        if before:
            params["before"] = before

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, params]
        }

        for url in RPC_URLS:
            try:
                async with self.session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('result', [])
                    if resp.status == 429:
                        await asyncio.sleep(1)
            except Exception as e:
                continue
        return []

    async def fetch_tx_details(self, sig: str) -> Optional[Dict]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [sig, {"commitment": "confirmed", "maxSupportedTransactionVersion": 0}]
        }
        for url in RPC_URLS:
            try:
                async with self.session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('result')
            except:
                continue
        return None

    def get_account_keys(self, tx: Dict) -> List[str]:
        if not tx or 'transaction' not in tx:
            return []
        msg = tx['transaction'].get('message', {})
        keys = msg.get('accountKeys', [])
        if not keys and 'staticAccountKeys' in msg:
            keys = msg['staticAccountKeys']
        return keys

    def is_dex_tx(self, tx: Dict) -> bool:
        if not tx or 'transaction' not in tx:
            return False
        
        keys = self.get_account_keys(tx)
        msg = tx['transaction'].get('message', {})
        
        # Check instructions
        for ix in msg.get('instructions', []):
            pid = ix.get('programId', '')
            if pid in DEX_PROGRAMS:
                return True
            if 'programIdIndex' in ix:
                idx = ix['programIdIndex']
                if idx < len(keys) and keys[idx] in DEX_PROGRAMS:
                    return True
        
        # Check inner instructions
        meta = tx.get('meta', {})
        for inner in meta.get('innerInstructions', []):
            for ix in inner.get('instructions', []):
                if 'programIdIndex' in ix:
                    idx = ix['programIdIndex']
                    if idx < len(keys) and keys[idx] in DEX_PROGRAMS:
                        return True
        return False

    def get_token_balance_changes(self, tx: Dict, wallet: str, keys: List[str]) -> Dict[str, float]:
        """Get all token balance changes for a wallet in this tx"""
        wallet_idx = -1
        for i, k in enumerate(keys):
            if k == wallet:
                wallet_idx = i
                break
        if wallet_idx == -1:
            return {}
        
        meta = tx.get('meta', {})
        pre = meta.get('preTokenBalances', [])
        post = meta.get('postTokenBalances', [])
        
        # Build balance maps
        pre_balances = {}
        for p in pre:
            if p.get('accountIndex') == wallet_idx:
                mint = p.get('mint', '')
                amt = float(p.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                pre_balances[mint] = amt
        
        post_balances = {}
        for p in post:
            if p.get('accountIndex') == wallet_idx:
                mint = p.get('mint', '')
                amt = float(p.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                post_balances[mint] = amt
        
        # Calculate changes
        all_mints = set(pre_balances.keys()) | set(post_balances.keys())
        changes = {}
        for mint in all_mints:
            before = pre_balances.get(mint, 0)
            after = post_balances.get(mint, 0)
            changes[mint] = after - before
        
        return changes

    def get_sol_change(self, tx: Dict, wallet: str, keys: List[str]) -> float:
        """Get SOL balance change for wallet"""
        wallet_idx = -1
        for i, k in enumerate(keys):
            if k == wallet:
                wallet_idx = i
                break
        if wallet_idx == -1:
            return 0
        
        meta = tx.get('meta', {})
        pre = meta.get('preBalances', [])
        post = meta.get('postBalances', [])
        
        if wallet_idx < len(pre) and wallet_idx < len(post):
            return (post[wallet_idx] - pre[wallet_idx]) / 1e9
        return 0

    async def backfill_position(self, pos: Dict) -> Tuple[float, int]:
        wallet = pos['wallet_address']
        token = pos['token_address']
        first_buy = pos['first_buy_time']
        
        logger.info(f"Processing {wallet[:10]}... / {token[:10]}...")
        
        # Fetch all tx signatures
        all_sigs = []
        before = None
        for _ in range(10):  # Max 1000 transactions
            sigs = await self.fetch_txs(wallet, before)
            if not sigs:
                break
            all_sigs.extend(sigs)
            if len(sigs) < 100:
                break
            before = sigs[-1].get('signature')
            await asyncio.sleep(0.1)
        
        logger.info(f"  Found {len(all_sigs)} transactions")
        
        total_sol = 0.0
        sell_count = 0
        
        for sig_info in all_sigs:
            sig = sig_info.get('signature')
            if not sig:
                continue
            
            tx = await self.fetch_tx_details(sig)
            if not tx:
                continue
            
            keys = self.get_account_keys(tx)
            
            # Check if this tx involves our token
            token_changes = self.get_token_balance_changes(tx, wallet, keys)
            if token not in token_changes:
                continue
            
            token_change = token_changes[token]
            sol_change = self.get_sol_change(tx, wallet, keys)
            
            # For sells: token decreases, SOL might increase or just decrease less
            # A pure sell should have token_change < 0
            # SOL change could be positive (received SOL) or small negative (fees only)
            if token_change < -0.0001:
                # This is a sell - calculate SOL received
                # For Pump.fun, sometimes SOL change is just slightly negative (fees)
                # but token went out
                is_dex = self.is_dex_tx(tx)
                
                if is_dex or abs(token_change) > 100:  # Significant token movement
                    # Estimate SOL from token value if SOL change is just fees
                    if sol_change > 0.01:  # Clear SOL received
                        total_sol += sol_change
                        sell_count += 1
                        logger.debug(f"    Sell: {token_change:.2f} tokens, +{sol_change:.4f} SOL")
                    elif sol_change > -0.1:  # Small fee, still a sell
                        # Can't determine exact SOL without price data
                        # Mark as sell but with 0 SOL (will need manual check)
                        sell_count += 1
                        logger.debug(f"    Sell (fees only): {token_change:.2f} tokens, {sol_change:.4f} SOL")
            
            await asyncio.sleep(0.03)
        
        logger.info(f"  Found {sell_count} sells, {total_sol:.4f} SOL")
        return total_sol, sell_count

    async def run(self, limit: int = 500):
        await self.connect()
        
        try:
            positions = await self.get_positions()
            logger.info(f"Found {len(positions)} positions to backfill")
            
            if limit:
                positions = positions[:limit]
            
            to_update = []
            
            for i, pos in enumerate(positions, 1):
                logger.info(f"\n[{i}/{len(positions)}]")
                sol, count = await self.backfill_position(pos)
                self.processed += 1
                
                if sol > 0 or count > 0:
                    to_update.append({
                        'wallet': pos['wallet_address'],
                        'token': pos['token_address'],
                        'sol': sol
                    })
                    self.updated += 1
                
                if i % 10 == 0:
                    logger.info(f"Progress: {i} processed, {self.updated} with SOL")
            
            # Update DB
            logger.info(f"\nUpdating {len(to_update)} positions...")
            for item in to_update:
                await self.db.execute(
                    "UPDATE wallet_positions SET total_sol_returned = $1 WHERE wallet_address = $2 AND token_address = $3",
                    item['sol'], item['wallet'], item['token']
                )
            
            logger.info(f"Done. Processed: {self.processed}, Updated: {self.updated}")
            
        finally:
            await self.close()


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=500)
    args = parser.parse_args()
    
    bf = SolReturnedBackfill()
    await bf.run(limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
