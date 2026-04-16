# ShadowHunter Database Schema Reference

## Required Tables

### 1. wallet_positions
Tracks current token holdings for each wallet.

```sql
CREATE TABLE wallet_positions (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(44) NOT NULL,
    token_address VARCHAR(44) NOT NULL,
    first_buy_time TIMESTAMP,
    last_buy_time TIMESTAMP,
    total_bought NUMERIC(36, 9) DEFAULT 0,
    total_sold NUMERIC(36, 9) DEFAULT 0,
    net_position NUMERIC(36, 9) DEFAULT 0,
    total_sol_invested NUMERIC(36, 9) DEFAULT 0,
    avg_entry_mc NUMERIC(36, 2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    total_sol_returned NUMERIC(36, 9) DEFAULT 0,
    UNIQUE(wallet_address, token_address)
);

CREATE INDEX idx_wallet_positions_wallet ON wallet_positions(wallet_address);
CREATE INDEX idx_wallet_positions_token ON wallet_positions(token_address);
CREATE INDEX idx_wallet_positions_active ON wallet_positions(is_active) WHERE is_active = TRUE;
```

**Important:**
- `total_sol_returned` is REQUIRED for accurate PnL calculations
- `is_active` should be FALSE when `net_position` <= 0.000001

---

### 2. wallet_performance
Aggregated performance stats per wallet.

```sql
CREATE TABLE wallet_performance (
    wallet_address VARCHAR(44) PRIMARY KEY,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    realized_pnl NUMERIC(36, 9) DEFAULT 0,
    avg_roi NUMERIC(10, 2) DEFAULT 0,
    avg_hold_time_seconds BIGINT DEFAULT 0,
    total_hold_time_seconds BIGINT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Winrate is calculated: winning_trades / total_trades * 100
-- No stored winrate column needed (calculated on-the-fly)
```

**Winrate Calculation:**
```python
winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
```

---

### 3. paper_trades
Paper trading history for agent.

```sql
CREATE TABLE paper_trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    action VARCHAR(10) NOT NULL,  -- 'BUY', 'SELL', 'HOLD'
    token VARCHAR(44) NOT NULL,
    token_symbol VARCHAR(20),
    amount_sol NUMERIC(36, 9),
    fee NUMERIC(36, 9) DEFAULT 0,
    notes JSONB  -- Stores confidence, reasoning, etc.
);

CREATE INDEX idx_paper_trades_token ON paper_trades(token);
CREATE INDEX idx_paper_trades_timestamp ON paper_trades(timestamp);
```

---

### 4. paper_portfolio
Current paper trading balance.

```sql
CREATE TABLE paper_portfolio (
    id INTEGER PRIMARY KEY DEFAULT 1,
    data JSONB NOT NULL,  -- {sol_balance: float, total_trades: int}
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert initial record:
INSERT INTO paper_portfolio (id, data) VALUES (1, '{"sol_balance": 2.0, "total_trades": 0}');
```

---

## Data Integrity Checks

### Check for orphaned records
```sql
-- Find positions for wallets not in wallets.txt
SELECT DISTINCT wallet_address FROM wallet_positions
WHERE wallet_address NOT IN (SELECT DISTINCT wallet_address FROM wallet_positions WHERE wallet_address IN ('addr1', 'addr2', ...));
```

### Fix inconsistent is_active flags
```sql
UPDATE wallet_positions 
SET is_active = FALSE 
WHERE is_active = TRUE AND net_position <= 0.000001;
```

### Check for negative values
```sql
SELECT * FROM wallet_positions 
WHERE total_bought < 0 OR total_sold < 0 OR total_sol_invested < 0;
```

---

## Redis Key Patterns

### Critical Keys (Do Not Delete)
- `processed:{tx_signature}` - Prevents duplicate transaction processing
  - TTL: 30 days (2592000 seconds)

### Cache Keys (Safe to Delete)
- `token_info:{token_address}` - Token price/MC cache
  - TTL: 5 minutes
- `trackhold:{token_address}` - /trackhold command cache
  - TTL: 5 minutes
- `birdeye:{endpoint}` - Birdeye API response cache
  - TTL: Varies

### Cleanup Commands
```bash
# Delete all token info caches (will regenerate)
redis-cli KEYS "token_info:*" | xargs redis-cli DEL

# Delete all trackhold caches
redis-cli KEYS "trackhold:*" | xargs redis-cli DEL

# Delete processed transactions older than 30 days (auto-expires anyway)
# No action needed - Redis auto-cleans expired keys
```

---

## Common Issues & Fixes

### Issue: Missing total_sol_returned column
**Error:** `column "total_sol_returned" does not exist`

**Fix:**
```sql
ALTER TABLE wallet_positions ADD COLUMN total_sol_returned NUMERIC(36, 9) DEFAULT 0;
```

Then backfill:
```python
# Run backfill_sol_returned.py
```

### Issue: Incorrect winrate display
**Symptom:** Winrate shows 0% despite having winning trades

**Fix:** Check if winrate is calculated correctly:
```sql
SELECT 
    wallet_address,
    total_trades,
    winning_trades,
    (winning_trades::float / NULLIF(total_trades, 0) * 100) as calculated_winrate
FROM wallet_performance
WHERE total_trades > 0;
```

### Issue: Orphaned wallet data
**Symptom:** Performance data for removed wallets still showing

**Fix:**
```sql
-- Delete performance for wallets not in current list
DELETE FROM wallet_performance 
WHERE wallet_address NOT IN ('addr1', 'addr2', ...);

-- Delete positions for removed wallets
DELETE FROM wallet_positions 
WHERE wallet_address NOT IN ('addr1', 'addr2', ...);
```

---

## Migration Scripts

### Add total_sol_returned (if missing)
```sql
-- Check if column exists
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'wallet_positions' AND column_name = 'total_sol_returned';

-- Add if missing
ALTER TABLE wallet_positions ADD COLUMN IF NOT EXISTS total_sol_returned NUMERIC(36, 9) DEFAULT 0;
```

### Backfill hold_time data
```sql
-- Add hold time columns if missing
ALTER TABLE wallet_performance ADD COLUMN IF NOT EXISTS avg_hold_time_seconds BIGINT DEFAULT 0;
ALTER TABLE wallet_performance ADD COLUMN IF NOT EXISTS total_hold_time_seconds BIGINT DEFAULT 0;
```

---

## Performance Optimization

### Database Indexes (Ensure these exist)
```sql
-- Essential indexes
CREATE INDEX IF NOT EXISTS idx_wallet_positions_wallet_token ON wallet_positions(wallet_address, token_address);
CREATE INDEX IF NOT EXISTS idx_wallet_positions_first_buy ON wallet_positions(first_buy_time);
CREATE INDEX IF NOT EXISTS idx_paper_trades_timestamp ON paper_trades(timestamp);
```

### Redis Memory Management
- Set maxmemory policy: `allkeys-lru`
- Monitor memory usage: `redis-cli INFO memory`
- Expire old keys automatically via TTL
