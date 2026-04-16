#!/usr/bin/env python3
"""
Clear all caches and trade data for ShadowHunter
Use this to start fresh for analysis purposes
"""
import asyncio
import asyncpg
import redis.asyncio as redis
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Config
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'shadowhunter')
DB_USER = os.getenv('DB_USER', 'sh')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'sh123')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

async def clear_redis_cache():
    """Clear all Redis cache keys"""
    print("🔄 Connecting to Redis...")
    try:
        r = redis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            decode_responses=True
        )
        await r.ping()
        print("✅ Redis connected")
        
        # Get all keys
        print("🔍 Scanning for cache keys...")
        keys = []
        async for key in r.scan_iter(match="*"):
            keys.append(key)
        
        if not keys:
            print("ℹ️ No keys found in Redis")
        else:
            print(f"🗑️ Found {len(keys)} keys to delete:")
            for key in keys[:20]:  # Show first 20
                print(f"   - {key}")
            if len(keys) > 20:
                print(f"   ... and {len(keys) - 20} more")
            
            # Delete all keys
            deleted = await r.delete(*keys)
            print(f"✅ Deleted {deleted} keys from Redis")
            
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False
    return True

async def clear_database():
    """Clear all trade data from database"""
    print("\n🔄 Connecting to PostgreSQL...")
    try:
        pool = await asyncpg.create_pool(
            host=DB_HOST, 
            port=DB_PORT, 
            database=DB_NAME,
            user=DB_USER, 
            password=DB_PASSWORD
        )
        print("✅ Database connected")
        
        async with pool.acquire() as conn:
            # Check wallet_positions table
            print("🔍 Checking wallet_positions table...")
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM wallet_positions"
            )
            print(f"📊 Found {count} position records")
            
            if count > 0:
                print("🗑️ Truncating wallet_positions table...")
                await conn.execute("TRUNCATE TABLE wallet_positions RESTART IDENTITY")
                print(f"✅ Cleared {count} position records")
            
            # Check wallet_performance table
            print("🔍 Checking wallet_performance table...")
            perf_count = await conn.fetchval(
                "SELECT COUNT(*) FROM wallet_performance"
            )
            print(f"📊 Found {perf_count} performance records")
            
            if perf_count > 0:
                print("🗑️ Truncating wallet_performance table...")
                await conn.execute("TRUNCATE TABLE wallet_performance RESTART IDENTITY")
                print(f"✅ Cleared {perf_count} performance records")
            
            # Check if there's a transactions table
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            table_names = [t['tablename'] for t in tables]
            
            # Clear transactions table if exists
            if 'transactions' in table_names:
                tx_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM transactions"
                )
                if tx_count > 0:
                    print(f"🗑️ Clearing {tx_count} transaction records...")
                    await conn.execute("TRUNCATE TABLE transactions RESTART IDENTITY")
                    print(f"✅ Cleared {tx_count} transaction records")
            
            # Clear any alert history or cache tables
            for table in ['alert_history', 'cache', 'processed_tx']:
                if table in table_names:
                    tbl_count = await conn.fetchval(
                        f"SELECT COUNT(*) FROM {table}"
                    )
                    if tbl_count > 0:
                        print(f"🗑️ Clearing {tbl_count} records from {table}...")
                        await conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY")
                        print(f"✅ Cleared {table}")
        
        await pool.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    return True

async def clear_all():
    """Clear all caches and data"""
    print("=" * 50)
    print("🧹 SHADOWHUNTER CACHE CLEANER")
    print("=" * 50)
    print("\n⚠️  This will DELETE all cached data and trade history!")
    print("   - Redis cache (token info, processed tx signatures)")
    print("   - Database trade positions (wallet_positions)")
    print("   - Database performance stats (wallet_performance)")
    print("   - Transaction history\n")
    
    # Confirm
    response = input("Are you sure? Type 'yes' to continue: ")
    if response.lower() != 'yes':
        print("\n❌ Cancelled")
        return
    
    print("\n" + "=" * 50)
    
    # Clear Redis
    redis_ok = await clear_redis_cache()
    
    # Clear Database
    db_ok = await clear_database()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    print(f"   Redis Cache: {'✅ Cleared' if redis_ok else '❌ Failed'}")
    print(f"   Database:    {'✅ Cleared' if db_ok else '❌ Failed'}")
    print("\n🎉 All caches cleared! You can now start fresh.")
    print("   Run trackerv2.py to begin new analysis.\n")

if __name__ == "__main__":
    try:
        asyncio.run(clear_all())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
