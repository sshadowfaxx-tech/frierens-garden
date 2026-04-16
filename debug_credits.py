#!/usr/bin/env python3
"""
Debug script to check Helius credit usage and cache behavior
Run this on your FX 6300 server to diagnose the issue
"""

import asyncio
import aioredis
import os
from datetime import datetime

async def check_redis_cache():
    """Check if Redis cache is working and what's in it"""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost')
        cache = await aioredis.from_url(redis_url)
        
        # Get all transaction cache keys
        tx_keys = await cache.keys('tx:*')
        print(f"📝 Transaction cache entries: {len(tx_keys)}")
        
        if tx_keys:
            # Show sample of cached transactions
            sample = tx_keys[:5]
            print(f"   Sample keys: {[k.decode() if isinstance(k, bytes) else k for k in sample]}")
            
            # Check TTL on one entry
            if tx_keys:
                ttl = await cache.ttl(tx_keys[0])
                print(f"   Sample TTL: {ttl} seconds ({ttl//86400} days)")
        
        await cache.close()
        
    except Exception as e:
        print(f"❌ Redis error: {e}")

async def check_tracker_logs():
    """Analyze recent tracker log output"""
    print("\n📊 Recent Tracker Analysis:")
    print("   Check your logs for:")
    print("   - 'new txs' counts per cycle")
    print("   - Duplicate transaction signatures")
    print("   - Cache miss/hit patterns")
    print()
    print("   If you see the same signature being processed multiple times,")
    print("   the cache is NOT working properly.")

def estimate_credit_usage():
    """Estimate daily credit usage based on configuration"""
    print("\n💳 Credit Usage Estimate:")
    
    wallets = 43
    cycles_per_day = 24 * 60 * 60 // 5  # Every 5 seconds
    
    # Conservative: 1 transaction per wallet per hour
    tx_per_wallet_per_hour = 1
    tx_per_day = wallets * tx_per_wallet_per_hour * 24
    credits_per_tx = 100
    
    estimated_credits = tx_per_day * credits_per_tx
    
    print(f"   Wallets: {wallets}")
    print(f"   Estimated transactions/day: {tx_per_day}")
    print(f"   Estimated credits/day: {estimated_credits:,}")
    print(f"   Your usage: 300,000 (6× higher than estimate!)")
    print()
    
    if estimated_credits * 3 < 300000:
        print("   🚨 ALERT: Usage is 3× higher than conservative estimate!")
        print("   Likely causes:")
        print("   1. Cache not working - transactions re-processed")
        print("   2. Too many transactions being fetched per cycle")
        print("   3. Tracker restarted multiple times (cache cleared)")

async def main():
    print("=" * 50)
    print("ShadowHunter Credit Diagnostic")
    print("=" * 50)
    
    await check_redis_cache()
    check_tracker_logs()
    estimate_credit_usage()
    
    print("\n" + "=" * 50)
    print("Recommendations:")
    print("=" * 50)
    print("1. Check if Redis is running: redis-cli ping")
    print("2. Check logs for duplicate transaction processing")
    print("3. Verify cache is persisting across cycles")
    print("4. If cache is empty, transactions will be re-processed")

if __name__ == "__main__":
    asyncio.run(main())
