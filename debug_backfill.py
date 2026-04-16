#!/usr/bin/env python3
"""
Debug script to diagnose why SOL returned isn't being found.
Run this on a specific wallet/token pair to see detailed transaction analysis.
"""

import asyncio
import asyncpg
import aiohttp
import ssl
import certifi
from datetime import datetime
import os
from dotenv import load_dotenv
import json

load_dotenv()

HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

DEX_PROGRAMS = {
    'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4',
    '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
    'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc',
    'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo',
    '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
    '39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJmw',
    '7OjPdbU7RjUoJzUpK1wZsWkdtWPS5bDrPmfxnzMT3JFR',
    'MoonCVVNZFSYkqNXP6bxHLPL6QQxAvKm4Mj6aEwapqq',
    'TSWAPa5r5W7X25VmhV2H6HBS4zrHYtrD7Tq5w1H7yqF',
}


class DebugBackfill:
    def __init__(self):
        self.db = None
        self.session = None
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.connector = aiohttp.TCPConnector(ssl=ssl_context)

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

    async def get_tx_details(self, signature: str):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [signature, {"commitment": "confirmed", "maxSupportedTransactionVersion": 0}]
        }
        async with self.session.post(HELIUS_RPC_URL, json=payload) as resp:
            data = await resp.json()
            return data.get('result')

    def get_account_keys(self, tx):
        if not tx or 'transaction' not in tx:
            return []
        message = tx['transaction'].get('message', {})
        keys = message.get('accountKeys', [])
        if not keys and 'staticAccountKeys' in message:
            keys = message['staticAccountKeys']
        return keys

    def find_dex_programs(self, tx):
        """Find all DEX programs involved in transaction"""
        found = []
        if not tx or 'transaction' not in tx:
            return found
        
        account_keys = self.get_account_keys(tx)
        message = tx['transaction'].get('message', {})
        
        # Check main instructions
        for ix in message.get('instructions', []):
            pid = ix.get('programId', '')
            if pid in DEX_PROGRAMS:
                found.append(pid[:16])
            if 'programIdIndex' in ix:
                idx = ix['programIdIndex']
                if idx < len(account_keys):
                    if account_keys[idx] in DEX_PROGRAMS:
                        found.append(account_keys[idx][:16])
        
        # Check inner instructions
        meta = tx.get('meta', {})
        for inner in meta.get('innerInstructions', []):
            for ix in inner.get('instructions', []):
                if 'programIdIndex' in ix:
                    idx = ix['programIdIndex']
                    if idx < len(account_keys):
                        if account_keys[idx] in DEX_PROGRAMS:
                            found.append(account_keys[idx][:16])
        
        return list(set(found))

    def calculate_changes(self, tx, wallet, token, account_keys):
        """Calculate SOL and token changes"""
        if not tx or 'meta' not in tx:
            return None, None
        
        wallet_idx = -1
        for i, key in enumerate(account_keys):
            if key == wallet:
                wallet_idx = i
                break
        
        if wallet_idx == -1:
            return None, None
        
        meta = tx.get('meta', {})
        
        # SOL change
        pre_sol = meta.get('preBalances', [])
        post_sol = meta.get('postBalances', [])
        sol_change = 0
        if wallet_idx < len(pre_sol) and wallet_idx < len(post_sol):
            sol_change = (post_sol[wallet_idx] - pre_sol[wallet_idx]) / 1e9
        
        # Token change
        pre_tokens = meta.get('preTokenBalances', [])
        post_tokens = meta.get('postTokenBalances', [])
        
        pre_amount = 0
        for p in pre_tokens:
            if p.get('accountIndex') == wallet_idx and p.get('mint') == token:
                pre_amount = float(p.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
        
        post_amount = 0
        for p in post_tokens:
            if p.get('accountIndex') == wallet_idx and p.get('mint') == token:
                post_amount = float(p.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
        
        token_change = post_amount - pre_amount
        
        return token_change, sol_change

    async def debug_wallet_token(self, wallet: str, token: str):
        """Debug a specific wallet/token pair"""
        print(f"\n{'='*60}")
        print(f"DEBUG: {wallet[:16]}... / {token[:16]}...")
        print(f"{'='*60}\n")
        
        # Get position from DB
        row = await self.db.fetchrow(
            "SELECT total_sold, total_bought, total_sol_invested FROM wallet_positions WHERE wallet_address=$1 AND token_address=$2",
            wallet, token
        )
        if row:
            print(f"DB Record:")
            print(f"  Total Bought: {float(row['total_bought'] or 0):.4f}")
            print(f"  Total Sold: {float(row['total_sold'] or 0):.4f}")
            print(f"  SOL Invested: {float(row['total_sol_invested'] or 0):.4f}")
        print()
        
        # Fetch signatures
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": 100}]
        }
        async with self.session.post(HELIUS_RPC_URL, json=payload) as resp:
            data = await resp.json()
            signatures = data.get('result', [])
        
        print(f"Found {len(signatures)} transactions\n")
        
        found_sells = 0
        total_sol_returned = 0
        
        for i, sig_info in enumerate(signatures[:20]):  # Check first 20
            sig = sig_info.get('signature')
            if not sig:
                continue
            
            # Fetch tx
            tx = await self.get_tx_details(sig)
            if not tx:
                continue
            
            account_keys = self.get_account_keys(tx)
            dex_programs = self.find_dex_programs(tx)
            token_change, sol_change = self.calculate_changes(tx, wallet, token, account_keys)
            
            # Check if this involves our token
            meta = tx.get('meta', {})
            involves_token = False
            for p in meta.get('preTokenBalances', []) + meta.get('postTokenBalances', []):
                if p.get('mint') == token:
                    involves_token = True
                    break
            
            if involves_token or (token_change and abs(token_change) > 0.0001):
                print(f"\n--- TX {i+1}: {sig[:20]}... ---")
                print(f"DEX Programs: {dex_programs if dex_programs else 'None'}")
                print(f"Token Change: {token_change:.6f}")
                print(f"SOL Change: {sol_change:.6f}")
                
                if token_change and token_change < -0.0001 and sol_change > 0.0001:
                    print(f"*** SELL DETECTED: {sol_change:.4f} SOL ***")
                    found_sells += 1
                    total_sol_returned += sol_change

        print(f"\n{'='*60}")
        print(f"SUMMARY: Found {found_sells} sells, {total_sol_returned:.4f} SOL")
        print(f"{'='*60}\n")
        
        return found_sells, total_sol_returned


async def main():
    # Example: Use one of the wallet/token pairs from your logs
    # You can change these to any wallet/token you want to debug
    
    # From your logs: mW4PZB45... / GAnGPNLF... (sold: 5222350.1030)
    # These are truncated addresses - you need full addresses
    
    print("Debug Backfill Script")
    print("="*60)
    print("\nEnter full wallet address (or press Enter for example):")
    wallet = input().strip()
    
    if not wallet:
        # Example from your log - replace with actual full addresses
        print("\nUsing example addresses from database...")
        debugger = DebugBackfill()
        await debugger.connect()
        
        # Get first position needing backfill
        row = await debugger.db.fetchrow(
            """SELECT wallet_address, token_address FROM wallet_positions 
            WHERE total_sold > 0.0001 AND (total_sol_returned IS NULL OR total_sol_returned = 0)
            LIMIT 1"""
        )
        
        if row:
            wallet = row['wallet_address']
            token = row['token_address']
            print(f"\nDebug position: {wallet[:16]}... / {token[:16]}...")
            await debugger.debug_wallet_token(wallet, token)
        else:
            print("No positions found needing backfill")
        
        await debugger.close()
    else:
        print("\nEnter full token address:")
        token = input().strip()
        
        debugger = DebugBackfill()
        await debugger.connect()
        await debugger.debug_wallet_token(wallet, token)
        await debugger.close()


if __name__ == "__main__":
    asyncio.run(main())
