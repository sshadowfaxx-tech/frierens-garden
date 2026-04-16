#!/usr/bin/env python3
"""
Quick database fixes for ShadowHunter
Run this on FX 6300 to fix common data issues
"""

import asyncpg
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def apply_fixes():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'shadowhunter'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'sh123')
    )
    
    print("Applying database fixes...\n")
    
    # 1. Ensure total_sol_returned column exists
    print("1. Checking total_sol_returned column...")
    col_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'wallet_positions' AND column_name = 'total_sol_returned'
        )
    """)
    if not col_exists:
        await conn.execute("""
            ALTER TABLE wallet_positions 
            ADD COLUMN total_sol_returned NUMERIC(36, 9) DEFAULT 0
        """)
        print("   ✓ Added total_sol_returned column")
    else:
        print("   ✓ Column already exists")
    
    # 2. Fix inconsistent is_active flags
    print("\n2. Fixing inconsistent is_active flags...")
    fixed = await conn.execute("""
        UPDATE wallet_positions 
        SET is_active = FALSE 
        WHERE is_active = TRUE AND net_position <= 0.000001
    """)
    count = int(fixed.split()[-1]) if fixed.split()[-1].isdigit() else 0
    print(f"   ✓ Fixed {count} inconsistent active flags")
    
    # 3. Ensure indexes exist
    print("\n3. Checking indexes...")
    indexes = [
        ("idx_wallet_positions_wallet", "wallet_positions", "wallet_address"),
        ("idx_wallet_positions_token", "wallet_positions", "token_address"),
        ("idx_wallet_positions_active", "wallet_positions", "is_active"),
    ]
    
    for idx_name, table, column in indexes:
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = $1
            )
        """, idx_name)
        if not exists:
            await conn.execute(f"""
                CREATE INDEX {idx_name} ON {table}({column})
            """)
            print(f"   ✓ Created index {idx_name}")
        else:
            print(f"   ✓ Index {idx_name} exists")
    
    # 4. Clean up negative values (data corruption)
    print("\n4. Checking for negative values...")
    neg_positions = await conn.fetch("""
        SELECT wallet_address, token_address, total_bought, total_sold, total_sol_invested
        FROM wallet_positions 
        WHERE total_bought < 0 OR total_sold < 0 OR total_sol_invested < 0
    """)
    if neg_positions:
        print(f"   ⚠ Found {len(neg_positions)} positions with negative values")
        # Fix by setting to 0 (investigate manually if many)
        await conn.execute("""
            UPDATE wallet_positions 
            SET 
                total_bought = GREATEST(total_bought, 0),
                total_sold = GREATEST(total_sold, 0),
                total_sol_invested = GREATEST(total_sol_invested, 0),
                total_sol_returned = GREATEST(total_sol_returned, 0)
            WHERE total_bought < 0 OR total_sold < 0 OR total_sol_invested < 0
        """)
        print("   ✓ Fixed negative values (set to 0)")
    else:
        print("   ✓ No negative values found")
    
    # 5. Verify wallet_performance table structure
    print("\n5. Checking wallet_performance table...")
    perf_cols = await conn.fetch("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'wallet_performance'
        ORDER BY ordinal_position
    """)
    col_names = [c['column_name'] for c in perf_cols]
    required = ['wallet_address', 'total_trades', 'winning_trades', 'losing_trades', 
                'realized_pnl', 'avg_roi', 'updated_at']
    missing = [r for r in required if r not in col_names]
    if missing:
        print(f"   ⚠ Missing columns: {missing}")
    else:
        print("   ✓ All required columns present")
    
    # 6. Ensure paper_portfolio has initial record
    print("\n6. Checking paper_portfolio...")
    portfolio = await conn.fetchrow("SELECT * FROM paper_portfolio WHERE id = 1")
    if not portfolio:
        await conn.execute("""
            INSERT INTO paper_portfolio (id, data, updated_at)
            VALUES (1, '{"sol_balance": 2.0, "total_trades": 0}', NOW())
        """)
        print("   ✓ Created initial portfolio record (2.0 SOL)")
    else:
        print("   ✓ Portfolio record exists")
    
    await conn.close()
    print("\n✓ All fixes applied!")

if __name__ == "__main__":
    asyncio.run(apply_fixes())
