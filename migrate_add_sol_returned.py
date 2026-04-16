"""
Migration: Add total_sol_returned column to wallet_positions
Run this before using the new PnL features
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:sh123@localhost:5432/shadowhunter')


async def migrate():
    """Add total_sol_returned column to wallet_positions"""
    
    conn = await asyncpg.connect(DB_URL)
    
    try:
        print("🔧 Running migration...")
        
        # Check if column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'wallet_positions' 
                AND column_name = 'total_sol_returned'
            )
        """)
        
        if column_exists:
            print("✅ Column 'total_sol_returned' already exists")
        else:
            # Add the column
            await conn.execute("""
                ALTER TABLE wallet_positions 
                ADD COLUMN total_sol_returned NUMERIC DEFAULT 0
            """)
            print("✅ Added 'total_sol_returned' column")
        
        # Show current table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'wallet_positions'
            ORDER BY ordinal_position
        """)
        
        print("\n📊 wallet_positions columns:")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")
        
    finally:
        await conn.close()
        print("\n✨ Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
