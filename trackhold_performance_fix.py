# Performance Fix for /trackhold N+1 Query Issue
# Apply this patch to trackerv2_clean.py

# REPLACE the for loop section (lines 2593-2650) with this batch query version:

# OLD CODE (N+1 queries):
# for i, wallet in enumerate(tracker.wallets):
#     row = await tracker.db.fetchrow("""SELECT ... FROM wallet_positions WHERE wallet_address = $1""", wallet_address, token_address)

# NEW CODE (Single batch query):
# Query all wallet positions in ONE database call
wallet_addresses = [w['address'] for w in tracker.wallets]
rows = await tracker.db.fetch(
    """SELECT 
        wallet_address, 
        total_bought, 
        total_sold, 
        total_sol_invested, 
        first_buy_time, 
        avg_entry_mc
    FROM wallet_positions 
    WHERE wallet_address = ANY($1) AND token_address = $2""",
    wallet_addresses, 
    token_address
)

# Build lookup dict for O(1) access
position_data = {row['wallet_address']: row for row in rows}

# Then in the loop, use dict lookup instead of DB query:
for wallet in tracker.wallets:
    wallet_address = wallet['address']
    row = position_data.get(wallet_address)  # O(1) lookup, no DB call
    
    # Rest of the logic remains the same...
    if row:
        total_bought = float(row['total_bought'] or 0)
        # ... etc

# This reduces 50+ DB queries to 1 query.
