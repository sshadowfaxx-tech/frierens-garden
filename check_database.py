#!/usr/bin/env python3
"""
Database & Redis Diagnostic Script for ShadowHunter
Run this on your FX 6300 server to check and clean up data
"""

import asyncpg
import asyncio
import redis
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Colors for output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_ok(msg): print(f"{GREEN}✓{RESET} {msg}")
def log_warn(msg): print(f"{YELLOW}⚠{RESET} {msg}")
def log_err(msg): print(f"{RED}✗{RESET} {msg}")
def log_info(msg): print(f"{BLUE}ℹ{RESET} {msg}")

async def check_database():
    """Check database integrity and structure"""
    print("\n" + "="*60)
    print("DATABASE CHECK")
    print("="*60)
    
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'sh123')
        )
        log_ok("Connected to PostgreSQL")
        
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"\n{len(tables)} tables found:")
        for t in tables:
            table = t['table_name']
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
            size = await conn.fetchval(f'''
                SELECT pg_size_pretty(pg_total_relation_size('"{table}"'))
            ''')
            print(f"  • {table}: {count:,} rows ({size})")
        
        # === WALLET_POSITIONS CHECK ===
        print("\n" + "-"*40)
        print("WALLET_POSITIONS ANALYSIS")
        print("-"*40)
        
        # Check for orphaned positions (wallets not in wallets.txt)
        try:
            with open('wallets.txt', 'r') as f:
                tracked_wallets = set()
                for line in f:
                    if '|' in line:
                        addr = line.split('|')[0].strip()
                        tracked_wallets.add(addr)
            
            db_wallets = set(await conn.fetchval('''
                SELECT array_agg(DISTINCT wallet_address) FROM wallet_positions
            ''') or [])
            
            orphaned = db_wallets - tracked_wallets
            if orphaned:
                log_warn(f"Found {len(orphaned)} orphaned wallet positions")
                print(f"  Orphaned wallets: {', '.join(list(orphaned)[:5])}{'...' if len(orphaned) > 5 else ''}")
                
                # Ask to clean up
                response = input(f"\nDelete {len(orphaned)} orphaned positions? (yes/no): ")
                if response.lower() == 'yes':
                    deleted = await conn.execute('''
                        DELETE FROM wallet_positions 
                        WHERE wallet_address = ANY($1)
                    ''', list(orphaned))
                    log_ok(f"Deleted orphaned positions")
            else:
                log_ok("No orphaned wallet positions")
        except FileNotFoundError:
            log_err("wallets.txt not found - cannot check for orphans")
        
        # Check for data inconsistencies
        print("\n  Data consistency checks:")
        
        # Positions with negative values
        neg = await conn.fetchval('''
            SELECT COUNT(*) FROM wallet_positions 
            WHERE total_bought < 0 OR total_sold < 0 OR total_sol_invested < 0
        ''')
        if neg > 0:
            log_warn(f"{neg} positions with negative values")
        else:
            log_ok("No negative values in positions")
        
        # Positions where sold > bought
        oversold = await conn.fetchval('''
            SELECT COUNT(*) FROM wallet_positions 
            WHERE total_sold > total_bought AND total_bought > 0
        ''')
        if oversold > 0:
            log_warn(f"{oversold} positions where sold > bought (data inconsistency)")
        else:
            log_ok("No oversold positions")
        
        # Active positions with zero net_position
        zero_active = await conn.fetchval('''
            SELECT COUNT(*) FROM wallet_positions 
            WHERE is_active = TRUE AND net_position <= 0.000001
        ''')
        if zero_active > 0:
            log_warn(f"{zero_active} 'active' positions with zero balance (should be marked inactive)")
            
            response = input(f"\nFix {zero_active} inconsistent active flags? (yes/no): ")
            if response.lower() == 'yes':
                await conn.execute('''
                    UPDATE wallet_positions 
                    SET is_active = FALSE 
                    WHERE is_active = TRUE AND net_position <= 0.000001
                ''')
                log_ok("Fixed inconsistent active flags")
        else:
            log_ok("All active positions have positive balance")
        
        # === WALLET_PERFORMANCE CHECK ===
        print("\n" + "-"*40)
        print("WALLET_PERFORMANCE ANALYSIS")
        print("-"*40)
        
        # Check winrate calculation
        bad_winrate = await conn.fetch('''
            SELECT wallet_address, total_trades, winning_trades, winrate
            FROM wallet_performance
            WHERE total_trades > 0 
            AND ABS(winrate - (winning_trades::float / total_trades * 100)) > 0.1
        ''')
        if bad_winrate:
            log_warn(f"{len(bad_winrate)} performance records with incorrect winrate")
            for r in bad_winrate[:3]:
                calc_winrate = r['winning_trades'] / r['total_trades'] * 100
                print(f"    {r['wallet_address'][:16]}...: stored={r['winrate']:.1f}%, calc={calc_winrate:.1f}%")
        else:
            log_ok("All winrate calculations correct")
        
        # Check for orphaned performance records
        perf_wallets = set(await conn.fetchval('''
            SELECT array_agg(DISTINCT wallet_address) FROM wallet_performance
        ''') or [])
        orphaned_perf = perf_wallets - tracked_wallets if 'tracked_wallets' in locals() else set()
        if orphaned_perf:
            log_warn(f"{len(orphaned_perf)} orphaned performance records")
            response = input(f"\nDelete {len(orphaned_perf)} orphaned performance records? (yes/no): ")
            if response.lower() == 'yes':
                await conn.execute('''
                    DELETE FROM wallet_performance 
                    WHERE wallet_address = ANY($1)
                ''', list(orphaned_perf))
                log_ok("Deleted orphaned performance records")
        else:
            log_ok("No orphaned performance records")
        
        # === PAPER_TRADES CHECK ===
        print("\n" + "-"*40)
        print("PAPER_TRADES ANALYSIS")
        print("-"*40)
        
        trade_count = await conn.fetchval('SELECT COUNT(*) FROM paper_trades')
        print(f"  Total paper trades: {trade_count}")
        
        if trade_count > 0:
            buy_count = await conn.fetchval("SELECT COUNT(*) FROM paper_trades WHERE action = 'BUY'")
            sell_count = await conn.fetchval("SELECT COUNT(*) FROM paper_trades WHERE action = 'SELL'")
            print(f"  BUY: {buy_count}, SELL: {sell_count}")
            
            # Check for trades with null notes
            null_notes = await conn.fetchval('''
                SELECT COUNT(*) FROM paper_trades WHERE notes IS NULL
            ''')
            if null_notes > 0:
                log_warn(f"{null_notes} trades with NULL notes field")
            else:
                log_ok("All trades have notes field")
        
        # === PAPER_PORTFOLIO CHECK ===
        print("\n" + "-"*40)
        print("PAPER_PORTFOLIO CHECK")
        print("-"*40)
        
        portfolio = await conn.fetchrow('SELECT * FROM paper_portfolio WHERE id = 1')
        if portfolio:
            data = json.loads(portfolio['data'])
            log_ok("Portfolio record exists")
            print(f"  SOL Balance: {data.get('sol_balance', 'N/A')}")
            print(f"  Last Updated: {portfolio['updated_at']}")
        else:
            log_warn("No portfolio record found - will be created on first trade")
        
        await conn.close()
        
    except Exception as e:
        log_err(f"Database error: {e}")
        return

def check_redis():
    """Check Redis cache integrity"""
    print("\n" + "="*60)
    print("REDIS CHECK")
    print("="*60)
    
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        r.ping()
        log_ok("Connected to Redis")
        
        # Get info
        info = r.info()
        print(f"\nRedis Version: {info.get('redis_version')}")
        print(f"Used Memory: {info.get('used_memory_human')}")
        print(f"Connected Clients: {info.get('connected_clients')}")
        
        # Get all keys
        keys = r.keys('*')
        print(f"\nTotal Keys: {len(keys)}")
        
        if not keys:
            log_info("Redis is empty - fresh start or all caches expired")
            return
        
        # Group by prefix
        prefixes = {}
        expired = 0
        no_ttl = 0
        
        for k in keys:
            prefix = k.split(':')[0] if ':' in k else 'other'
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
            
            ttl = r.ttl(k)
            if ttl == -2:
                expired += 1
            elif ttl == -1:
                no_ttl += 1
        
        print("\nKey Distribution:")
        for p, c in sorted(prefixes.items(), key=lambda x: -x[1]):
            print(f"  {p}: {c:,} keys")
        
        if expired > 0:
            log_warn(f"{expired} expired keys (will be auto-cleaned)")
        
        if no_ttl > 0:
            log_warn(f"{no_ttl} keys with no TTL (will persist forever)")
        
        # Check for old processed transaction caches
        old_processed = [k for k in keys if k.startswith('processed:')]
        if len(old_processed) > 1000:
            log_warn(f"{len(old_processed)} processed transaction keys (high memory usage)")
            response = input(f"\nDelete all processed transaction caches? (yes/no): ")
            if response.lower() == 'yes':
                for k in old_processed:
                    r.delete(k)
                log_ok(f"Deleted {len(old_processed)} processed keys")
        else:
            log_ok(f"{len(old_processed)} processed transaction keys (normal)")
        
        # Check for token price caches
        price_caches = [k for k in keys if k.startswith('token_info:')]
        print(f"\n  Token price caches: {len(price_caches)}")
        
        # Check for trackhold caches
        trackhold_caches = [k for k in keys if k.startswith('trackhold:')]
        print(f"  Trackhold caches: {len(trackhold_caches)}")
        
    except Exception as e:
        log_err(f"Redis error: {e}")

def cleanup_recommendations():
    """Provide cleanup recommendations"""
    print("\n" + "="*60)
    print("CLEANUP RECOMMENDATIONS")
    print("="*60)
    
    print("""
Safe to clean anytime:
  • Redis 'processed:*' keys older than 30 days
  • Redis 'token_info:*' caches (will regenerate)
  • Redis 'trackhold:*' caches (will regenerate)

Clean with caution:
  • Old paper_trades (keep for historical analysis)
  • Wallet positions marked inactive with no recent activity

DO NOT clean:
  • Active wallet_positions (live tracking data)
  • Wallet_performance (accumulated stats)
  • Paper_portfolio (current balance)
""")

async def main():
    print("\n" + "="*60)
    print("SHADOWHUNTER DATABASE & REDIS DIAGNOSTIC")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await check_database()
    check_redis()
    cleanup_recommendations()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
