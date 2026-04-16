import asyncio
import asyncpg
import os
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

async def full_diagnostic():
    print("=== COMPREHENSIVE AGENT DIAGNOSTIC ===\n")
    
    # Connect
    try:
        db = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'shadowhunter'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'sh123')
        )
        print("✅ Database connected\n")
    except Exception as e:
        print(f"❌ Database error: {e}\n")
        return
    
    # 1. Show ALL recent wallet_positions (no time filter)
    print("1. ALL RECENT wallet_positions (last 50):")
    rows = await db.fetch(
        """SELECT token_address, wallet_address, first_buy_time,
                   total_sol_invested, total_bought
            FROM wallet_positions 
            ORDER BY first_buy_time DESC 
            LIMIT 5"""
    )
    
    if rows:
        for i, r in enumerate(rows):
            print(f"   {i+1}. {r['token_address'][:25]}...")
            print(f"      Wallet: {r['wallet_address'][:20]}...")
            print(f"      Time: {r['first_buy_time']} (type: {type(r['first_buy_time'])})")
            print(f"      SOL: {r['total_sol_invested']}")
    else:
        print("   ❌ NO DATA in wallet_positions table!")
    
    # 2. Show ALL clusters (no time filter)
    print("\n2. ALL CLUSTERS (2+ wallets):")
    clusters = await db.fetch(
        """SELECT token_address, COUNT(*) as cnt, MAX(first_buy_time) as latest
           FROM wallet_positions 
           GROUP BY token_address 
           HAVING COUNT(*) >= 2
           ORDER BY latest DESC
           LIMIT 5"""
    )
    
    if clusters:
        for i, c in enumerate(clusters):
            print(f"   {i+1}. {c['token_address'][:25]}... | {c['cnt']} wallets | {c['latest']}")
    else:
        print("   ❌ NO CLUSTERS found!")
    
    # 3. Check tracker cache table
    print("\n3. TRACKER CACHE (recent activity):")
    try:
        cache = await db.fetch(
            "SELECT * FROM tracker_cache ORDER BY timestamp DESC LIMIT 5"
        )
        if cache:
            for i, c in enumerate(cache):
                print(f"   {i+1}. {c.get('signature', 'N/A')[:30]}... | {c.get('timestamp')}")
        else:
            print("   No cache entries")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 4. Simulate agent query
    print("\n4. AGENT QUERY SIMULATION:")
    last_check = datetime.now() - timedelta(hours=2)
    print(f"   Agent last_check: {last_check}")
    
    # Query using the same logic as agent
    trades = await db.fetch(
        """SELECT COUNT(*) as cnt, MAX(first_buy_time) as latest
           FROM wallet_positions 
           WHERE first_buy_time > $1""",
        last_check
    )
    print(f"   Positions after last_check: {trades[0]['cnt']}")
    print(f"   Latest position time: {trades[0]['latest']}")
    
    # 5. Timezone check
    print("\n5. TIMEZONE INFO:")
    print(f"   Current local time: {datetime.now()}")
    print(f"   Current UTC time: {datetime.utcnow()}")
    
    db_time = await db.fetchval("SELECT NOW()")
    print(f"   Database NOW(): {db_time}")
    
    await db.close()
    
    print("\n=== DIAGNOSTIC COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(full_diagnostic())
