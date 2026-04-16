"""
Backfill script for wallet_performance.total_hold_time_seconds
Estimates hold times from existing position data

Run this after adding the column:
    python backfill_hold_time.py
"""

import asyncio
import asyncpg
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:sh123@localhost:5432/shadowhunter')


async def backfill_hold_times():
    """Estimate and backfill hold times for existing wallets"""
    
    conn = await asyncpg.connect(DB_URL)
    
    try:
        print("🔍 Analyzing existing position data...")
        
        # Get all wallets with position data
        wallets = await conn.fetch("""
            SELECT DISTINCT wallet_address 
            FROM wallet_positions 
            WHERE total_sold > 0 OR is_active = TRUE
        """)
        
        print(f"Found {len(wallets)} wallets with trading history")
        
        updated = 0
        skipped = 0
        
        for row in wallets:
            wallet = row['wallet_address']
            
            # Get position data for this wallet
            positions = await conn.fetch("""
                SELECT 
                    first_buy_time,
                    last_buy_time,
                    total_bought,
                    total_sold,
                    is_active,
                    net_position
                FROM wallet_positions
                WHERE wallet_address = $1
            """, wallet)
            
            total_hold_seconds = 0
            sell_count = 0
            
            for pos in positions:
                first_buy = pos['first_buy_time']
                last_buy = pos['last_buy_time']
                total_sold = float(pos['total_sold'] or 0)
                total_bought = float(pos['total_bought'] or 0)
                is_active = pos['is_active']
                net_position = float(pos['net_position'] or 0)
                
                if not first_buy:
                    continue
                
                # For fully sold positions: estimate hold time from first buy to last buy
                if not is_active and total_sold > 0 and last_buy:
                    # Estimate hold time as time from first buy to last buy
                    # This is a reasonable approximation
                    hold_time = (last_buy - first_buy).total_seconds()
                    if hold_time > 0:
                        # Weight by proportion sold (if partially sold)
                        sell_ratio = min(total_sold / total_bought, 1.0) if total_bought > 0 else 1.0
                        total_hold_seconds += hold_time * sell_ratio
                        sell_count += 1
                
                # For active positions: estimate hold time from first buy to now
                elif is_active and net_position > 0:
                    # Calculate hold time up to now for current holdings
                    now = datetime.utcnow()
                    if first_buy.tzinfo:
                        from datetime import timezone
                        now = datetime.now(timezone.utc)
                    
                    hold_time = (now - first_buy).total_seconds()
                    if hold_time > 0:
                        # Count as partial sell for calculation purposes
                        # This represents "would have sold by now" estimate
                        total_hold_seconds += hold_time * 0.5  # Weight as half a sell
                        sell_count += 0.5
            
            # Only update if we have meaningful data
            if total_hold_seconds > 0 and sell_count > 0:
                await conn.execute("""
                    UPDATE wallet_performance
                    SET total_hold_time_seconds = $1
                    WHERE wallet_address = $2
                """, total_hold_seconds, wallet)
                
                avg_hold = total_hold_seconds / sell_count
                avg_hold_hours = avg_hold / 3600
                
                print(f"✅ {wallet[:16]}... | Avg hold: {avg_hold_hours:.1f}h | Total: {total_hold_seconds/3600:.1f}h")
                updated += 1
            else:
                skipped += 1
        
        print(f"\n📊 Summary:")
        print(f"   Updated: {updated} wallets")
        print(f"   Skipped: {skipped} wallets (no time data)")
        print(f"   Total: {len(wallets)} wallets processed")
        
        # Show some statistics
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_wallets,
                AVG(total_hold_time_seconds) as avg_hold,
                MAX(total_hold_time_seconds) as max_hold,
                MIN(total_hold_time_seconds) as min_hold
            FROM wallet_performance
            WHERE total_hold_time_seconds > 0
        """)
        
        if stats and stats['total_wallets']:
            print(f"\n📈 Hold Time Statistics:")
            print(f"   Wallets with data: {stats['total_wallets']}")
            print(f"   Average hold time: {float(stats['avg_hold'] or 0)/3600:.1f} hours")
            print(f"   Longest hold: {float(stats['max_hold'] or 0)/3600:.1f} hours")
            print(f"   Shortest hold: {float(stats['min_hold'] or 0)/3600:.1f} hours")
        
    finally:
        await conn.close()
        print("\n✨ Backfill complete!")


if __name__ == "__main__":
    asyncio.run(backfill_hold_times())
