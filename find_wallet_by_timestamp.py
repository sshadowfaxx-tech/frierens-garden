#!/usr/bin/env python3
"""
Find wallet by token and transaction timestamps.

This script searches for wallets that traded a specific token
around the given timestamps.

Usage:
    python find_wallet_by_timestamp.py
"""

import asyncio
import aiohttp
import ssl
import certifi
from datetime import datetime
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Token to search
TOKEN = "FtSRgyCEhKTc1PPgEAXvuHN3NyiP6LS9uyB28KCN3CAP"

# Target timestamps (Mar 24, 2026 - Central Daylight Time CDT = UTC-5)
# Converting CDT to UTC Unix timestamps for year 2026
TARGET_TIMES = [
    ("Mar 24, 10:04 PM CDT", 1774407840),  # Mar 25, 3:04 AM UTC
    ("Mar 24, 10:03 PM CDT", 1774407780),  # Mar 25, 3:03 AM UTC
    ("Mar 24, 8:37 PM CDT",  1774402620),  # Mar 25, 1:37 AM UTC
    ("Mar 24, 8:26 PM CDT",  1774401960),  # Mar 25, 1:26 AM UTC
    ("Mar 24, 5:08 PM CDT",  1774390080),  # Mar 24, 10:08 PM UTC
    ("Mar 24, 1:45 PM CDT",  1774377900),  # Mar 24, 6:45 PM UTC
]

# Time window (±10 minutes to account for clock differences and block times)
TIME_WINDOW = 600  # 10 minutes in seconds


class WalletFinder:
    def __init__(self):
        self.session = None
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.connector = aiohttp.TCPConnector(ssl=ssl_context)

    async def connect(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(connector=self.connector, timeout=timeout)

    async def close(self):
        if self.session:
            await self.session.close()

    async def get_token_transactions(self, token: str, before: str = None) -> List[Dict]:
        """Fetch transactions for a token address"""
        params = {
            "limit": 100,
            "commitment": "confirmed"
        }
        if before:
            params["before"] = before

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [token, params]
        }

        try:
            async with self.session.post(HELIUS_RPC_URL, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('result', [])
        except Exception as e:
            print(f"Error fetching signatures: {e}")
        
        return []

    async def get_transaction_details(self, signature: str) -> Optional[Dict]:
        """Get full transaction details"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"commitment": "confirmed", "maxSupportedTransactionVersion": 0}
            ]
        }

        try:
            async with self.session.post(HELIUS_RPC_URL, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('result')
        except Exception as e:
            print(f"Error fetching tx: {e}")
        
        return None

    def get_account_keys(self, tx: Dict) -> List[str]:
        """Extract account keys from transaction"""
        if not tx or 'transaction' not in tx:
            return []
        
        message = tx['transaction'].get('message', {})
        keys = message.get('accountKeys', [])
        if not keys and 'staticAccountKeys' in message:
            keys = message['staticAccountKeys']
        return keys

    def find_token_transfers(self, tx: Dict, token: str) -> List[Dict]:
        """Find all token transfers in a transaction"""
        if not tx or 'meta' not in tx:
            return []
        
        transfers = []
        meta = tx.get('meta', {})
        pre_balances = meta.get('preTokenBalances', [])
        post_balances = meta.get('postTokenBalances', [])
        
        # Build maps of accountIndex -> balance for this token
        pre_map = {}
        for p in pre_balances:
            if p.get('mint') == token:
                idx = p.get('accountIndex')
                amt = float(p.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                pre_map[idx] = amt
        
        post_map = {}
        for p in post_balances:
            if p.get('mint') == token:
                idx = p.get('accountIndex')
                amt = float(p.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                post_map[idx] = amt
        
        # Find accounts with balance changes
        all_indices = set(pre_map.keys()) | set(post_map.keys())
        for idx in all_indices:
            before = pre_map.get(idx, 0)
            after = post_map.get(idx, 0)
            change = after - before
            if abs(change) > 0.0001:
                transfers.append({
                    'account_index': idx,
                    'before': before,
                    'after': after,
                    'change': change
                })
        
        return transfers

    async def search_wallets(self, token: str, target_times: List[tuple]):
        """Search for wallets trading at specific times"""
        print(f"Searching for wallets trading {token[:16]}...")
        print(f"Target timestamps: {len(target_times)}\n")
        
        # Collect all transaction signatures
        all_sigs = []
        before = None
        
        print("Fetching transaction signatures...")
        for _ in range(20):  # Max 2000 transactions
            sigs = await self.get_token_transactions(token, before)
            if not sigs:
                break
            all_sigs.extend(sigs)
            if len(sigs) < 100:
                break
            before = sigs[-1].get('signature')
            await asyncio.sleep(0.1)
        
        print(f"Found {len(all_sigs)} total transactions\n")
        
        # Track wallets with matching timestamps
        matching_wallets = {}  # wallet -> list of matching timestamps
        
        for sig_info in all_sigs:
            sig = sig_info.get('signature')
            block_time = sig_info.get('blockTime')
            
            if not block_time:
                continue
            
            # Check if this timestamp matches any target
            for label, target_ts in target_times:
                if abs(block_time - target_ts) < TIME_WINDOW:
                    # This transaction is within our target window
                    print(f"Found matching tx at {label}: {sig[:20]}...")
                    
                    # Get details
                    tx = await self.get_transaction_details(sig)
                    if not tx:
                        continue
                    
                    keys = self.get_account_keys(tx)
                    transfers = self.find_token_transfers(tx, token)
                    
                    for transfer in transfers:
                        idx = transfer['account_index']
                        if idx < len(keys):
                            wallet = keys[idx]
                            change = transfer['change']
                            
                            if wallet not in matching_wallets:
                                matching_wallets[wallet] = []
                            
                            matching_wallets[wallet].append({
                                'time': label,
                                'timestamp': block_time,
                                'change': change,
                                'signature': sig
                            })
                            
                            print(f"  Wallet: {wallet[:16]}... Change: {change:+.2f}")
                    
                    break  # Don't check other timestamps for this tx
            
            await asyncio.sleep(0.02)
        
        # Print results
        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}\n")
        
        if not matching_wallets:
            print("No matching wallets found.")
            return
        
        # Sort by number of matching timestamps
        sorted_wallets = sorted(
            matching_wallets.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        print(f"Found {len(sorted_wallets)} wallets with matching transactions:\n")
        
        for wallet, matches in sorted_wallets[:10]:  # Top 10
            print(f"Wallet: {wallet}")
            print(f"Matching transactions: {len(matches)}")
            for m in matches:
                action = "BOUGHT" if m['change'] > 0 else "SOLD"
                print(f"  - {m['time']}: {action} {abs(m['change']):.2f} tokens")
            print()


async def main():
    finder = WalletFinder()
    await finder.connect()
    
    try:
        await finder.search_wallets(TOKEN, TARGET_TIMES)
    finally:
        await finder.close()


if __name__ == "__main__":
    asyncio.run(main())
