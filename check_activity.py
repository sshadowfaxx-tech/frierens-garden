import asyncio
import asyncpg
import os
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

async def diagnose():
    print("=== Agent Monitor Diagnostics ===\n")
    
    # Connect to database
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
    
    # Check recent wallet_positions
    print("Recent wallet_positions (last 10 minutes):")
    rows = await db.fetch(
        """SELECT token_address, wallet_address, first_buy_time, 
                   NOW() - first_buy_time as age
            FROM wallet_positions 
            WHERE first_buy_time > NOW() - INTERVAL '10 minutes'
            ORDER BY first_buy_time DESC 
            LIMIT 10"""
    )
    
    if rows:
        print(f"Found {len(rows)} positions:")
        for r in rows:
            print(f"  {r['token_address'][:20]}... | {r['age']} ago")
    else:
        print("  No recent positions found")
    
    # Check recent cluster activity
    print("\nRecent clusters (2+ wallets, last 10 minutes):")
    clusters = await db.fetch(
        """SELECT token_address, COUNT(*) as cnt, MAX(first_buy_time) as latest
           FROM wallet_positions 
           WHERE first_buy_time > NOW() - INTERVAL '10 minutes'
           GROUP BY token_address 
           HAVING COUNT(*) >= 2
           ORDER BY latest DESC"""
    )
    
    if clusters:
        print(f"Found {len(clusters)} clusters:")
        for c in clusters:
            print(f"  {c['token_address'][:20]}... | {c['cnt']} wallets")
    else:
        print("  No recent clusters found")
    
    # Check wallet_performance exists
    print("\nWallet performance table:")
    try:
        count = await db.fetchval("SELECT COUNT(*) FROM wallet_performance")
        print(f"  {count} wallets with performance data")
    except:
        print("  Table doesn't exist or error")
    
    # Show what the agent would see
    last_check = datetime.now(timezone.utc) - timedelta(minutes=5)
    last_check_naive = last_check.replace(tzinfo=None)
    
    print(f"\nAgent's last_check (naive): {last_check_naive}")
    print(f"Current time: {datetime.now()}")
    
    # Check positions after last_check
    new_positions = await db.fetch(
        "SELECT COUNT(*) FROM wallet_positions WHERE first_buy_time > $1",
        last_check_naive
    )
    print(f"\nPositions after agent's last_check: {new_positions[0]['count']}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
