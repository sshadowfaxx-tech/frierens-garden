"""
Accurate backfill script using Helius API
Fetches historical transactions to calculate precise hold times

Run this after adding the column:
    python backfill_hold_time_helius.py

This fetches actual transaction history from Helius, so it's slower
but much more accurate than estimation.
"""

import asyncio
import asyncpg
import aiohttp
import os
import ssl
import certifi
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:sh123@localhost:5432/shadowhunter')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Rate limiting for Helius free tier
REQUEST_DELAY = 0.15  # ~6-7 req/sec to stay safe

# Create SSL context for Windows
def get_ssl_context():
    """Create SSL context with proper certificates for Windows"""
    return ssl.create_default_context(cafile=certifi.where())


async def get_signatures_for_address(
    session: aiohttp.ClientSession, 
    address: str, 
    before: str = None,
    limit: int = 100
) -> list:
    """Fetch transaction signatures for a wallet"""
    try:
        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                address,
                {"limit": limit, "before": before} if before else {"limit": limit}
            ]
        }
        
        async with session.post(HELIUS_RPC_URL, json=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if 'result' in data:
                    return data['result']
            else:
                print(f"  ⚠️ Helius status {resp.status} for signatures")
    except Exception as e:
        print(f"  ⚠️ Error fetching signatures: {e}")
    
    return []


async def get_transaction_details(
    session: aiohttp.ClientSession, 
    tx_signature: str
) -> dict:
    """Fetch full transaction details from Helius"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                tx_signature,
                {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}
            ]
        }
        
        async with session.post(HELIUS_RPC_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if 'result' in data and data['result']:
                    return data['result']
    except Exception as e:
        print(f"  ⚠️ Error fetching tx: {e}")
    
    return None


def extract_token_transfers(tx_details: dict, wallet: str) -> list:
    """Extract token transfers (buys/sells) from transaction"""
    transfers = []
    
    if not tx_details or 'transaction' not in tx_details:
        return transfers
    
    meta = tx_details.get('meta', {})
    pre_balances = meta.get('preTokenBalances', [])
    post_balances = meta.get('postTokenBalances', [])
    
    block_time = tx_details.get('blockTime')
    if not block_time:
        return transfers
    
    tx_time = datetime.fromtimestamp(block_time)
    
    # Parse pre balances into lookup
    pre_map = {}
    for bal in pre_balances:
        owner = bal.get('owner', '')
        if owner == wallet:
            mint = bal.get('mint', '')
            amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
            pre_map[mint] = amount
    
    # Parse post balances
    post_map = {}
    for bal in post_balances:
        owner = bal.get('owner', '')
        if owner == wallet:
            mint = bal.get('mint', '')
            amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
            post_map[mint] = amount
    
    # Calculate changes
    all_mints = set(pre_map.keys()) | set(post_map.keys())
    
    for mint in all_mints:
        # Skip SOL (wrapped SOL is ok)
        if mint == 'So11111111111111111111111111111111111111112':
            continue
        
        pre = pre_map.get(mint, 0)
        post = post_map.get(mint, 0)
        change = post - pre
        
        if abs(change) > 0.000001:  # Ignore dust
            transfers.append({
                'token': mint,
                'change': change,  # positive = buy/receive, negative = sell/send
                'timestamp': tx_time,
                'signature': tx_details.get('transaction', {}).get('signatures', [''])[0]
            })
    
    return transfers


async def backfill_wallet_hold_times(
    session: aiohttp.ClientSession,
    conn: asyncpg.Connection,
    wallet: str,
    max_txs: int = 1000
) -> tuple:
    """
    Calculate accurate hold times for a wallet by fetching tx history
    Returns: (total_hold_seconds, sell_count)
    """
    print(f"  Fetching history for {wallet[:16]}...")
    
    # Fetch transaction signatures
    all_sigs = []
    before = None
    
    while len(all_sigs) < max_txs:
        sigs = await get_signatures_for_address(session, wallet, before=before, limit=100)
        if not sigs:
            break
        
        all_sigs.extend(sigs)
        before = sigs[-1].get('signature')
        
        # Stop if we've fetched enough or if txs are too old (optional optimization)
        if len(sigs) < 100:
            break
        
        await asyncio.sleep(REQUEST_DELAY)
    
    print(f"    Found {len(all_sigs)} transactions")
    
    if not all_sigs:
        return 0, 0
    
    # Fetch full details for each transaction
    all_transfers = []
    
    for i, sig_data in enumerate(all_sigs):
        sig = sig_data.get('signature')
        if not sig:
            continue
        
        # Skip failed transactions
        if sig_data.get('err'):
            continue
        
        tx_details = await get_transaction_details(session, sig)
        if tx_details:
            transfers = extract_token_transfers(tx_details, wallet)
            all_transfers.extend(transfers)
        
        await asyncio.sleep(REQUEST_DELAY)
        
        if (i + 1) % 50 == 0:
            print(f"    Processed {i+1}/{len(all_sigs)} txs...")
    
    print(f"    Extracted {len(all_transfers)} token transfers")
    
    # Group transfers by token
    token_transfers = {}
    for t in all_transfers:
        token = t['token']
        if token not in token_transfers:
            token_transfers[token] = {'buys': [], 'sells': []}
        
        if t['change'] > 0:
            token_transfers[token]['buys'].append(t)
        else:
            token_transfers[token]['sells'].append(t)
    
    # Calculate hold times (FIFO matching)
    total_hold_seconds = 0
    total_sells = 0
    
    for token, data in token_transfers.items():
        if not data['sells']:
            continue  # No sells = no realized hold time
        
        # Sort by timestamp
        buys = sorted(data['buys'], key=lambda x: x['timestamp'])
        sells = sorted(data['sells'], key=lambda x: x['timestamp'])
        
        for sell in sells:
            if not buys:
                break
            
            # Match to earliest buy
            buy = buys[0]
            hold_seconds = (sell['timestamp'] - buy['timestamp']).total_seconds()
            
            if hold_seconds > 0:
                total_hold_seconds += hold_seconds
                total_sells += 1
            
            # Remove matched buy (simplified FIFO)
            buys.pop(0)
    
    return total_hold_seconds, total_sells


async def backfill_hold_times_accurate():
    """Main backfill process using Helius API"""
    
    if not HELIUS_API_KEY:
        print("❌ HELIUS_API_KEY not found in .env")
        print("Please add it and try again, or use backfill_hold_time.py for estimation.")
        return
    
    conn = await asyncpg.connect(DB_URL)
    
    try:
        print("🔍 Fetching tracked wallets from database...")
        
        # Get wallets with trading activity
        rows = await conn.fetch("""
            SELECT DISTINCT wallet_address
            FROM wallet_positions
            WHERE total_sold > 0 OR is_active = TRUE
            ORDER BY wallet_address
        """)
        
        wallets = [r['wallet_address'] for r in rows]
        print(f"Found {len(wallets)} wallets with activity")
        print()
        
        print("⚠️  Note: This will make API calls to Helius.")
        print(f"   Estimated time: ~{len(wallets) * 30} seconds minimum")
        print("   Press Ctrl+C to cancel, or wait 5 seconds to continue...")
        print()
        
        await asyncio.sleep(5)
        
        # Create SSL context for Windows
        ssl_context = get_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            updated = 0
            skipped = 0
            
            for i, wallet in enumerate(wallets, 1):
                print(f"\n[{i}/{len(wallets)}] Processing {wallet[:20]}...")
                
                try:
                    total_seconds, sell_count = await backfill_wallet_hold_times(
                        session, conn, wallet, max_txs=500
                    )
                    
                    if total_seconds > 0 and sell_count > 0:
                        await conn.execute("""
                            UPDATE wallet_performance
                            SET total_hold_time_seconds = $1
                            WHERE wallet_address = $2
                        """, total_seconds, wallet)
                        
                        avg_hold = total_seconds / sell_count
                        print(f"  ✅ Updated: Avg {avg_hold/3600:.1f}h | Total {total_seconds/3600:.1f}h | {sell_count} sells")
                        updated += 1
                    else:
                        print(f"  ⚠️ No sell data found")
                        skipped += 1
                    
                except Exception as e:
                    print(f"  ❌ Error processing wallet: {e}")
                    skipped += 1
                
                # Progress update every 5 wallets
                if i % 5 == 0:
                    print(f"\n--- Progress: {i}/{len(wallets)} wallets processed ---")
            
            print()
            print("=" * 60)
            print("📊 FINAL SUMMARY")
            print("=" * 60)
            print(f"Total wallets: {len(wallets)}")
            print(f"Updated: {updated}")
            print(f"Skipped: {skipped}")
            
            # Show statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    AVG(total_hold_time_seconds) as avg_hold,
                    MAX(total_hold_time_seconds) as max_hold
                FROM wallet_performance
                WHERE total_hold_time_seconds > 0
            """)
            
            if stats and stats['total']:
                print()
                print("📈 Hold Time Statistics:")
                print(f"   Wallets with data: {stats['total']}")
                print(f"   Average hold time: {float(stats['avg_hold'] or 0)/3600:.1f} hours")
                print(f"   Longest hold: {float(stats['max_hold'] or 0)/3600:.1f} hours")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    finally:
        await conn.close()
        print("\n✨ Backfill complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("Accurate Hold Time Backfill (Helius API)")
    print("=" * 60)
    print()
    print("This script fetches transaction history from Helius")
    print("and calculates exact hold times for each wallet.")
    print()
    print(f"Database: {DB_URL.split('@')[-1] if '@' in DB_URL else 'localhost'}")
    print(f"Helius API: {'✓ Configured' if HELIUS_API_KEY else '✗ Missing'}")
    print()
    
    asyncio.run(backfill_hold_times_accurate())
