# Agent Monitor Server Setup

Deploy the agent monitor on your FX 6300 server to enable autonomous paper trading.

## Files to Copy to FX 6300

1. `agent_monitor_server.py` - Main monitoring script
2. `start_agent_monitor.bat` - Windows launcher
3. `paper_trading_schema.sql` - Database tables (if not already run)

## Setup Instructions

### 1. Copy Files

Copy these files to your FX 6300 (via USB, network share, or download):
```
C:\shadowhunter\agent_monitor_server.py
C:\shadowhunter\start_agent_monitor.bat
```

### 2. Install Dependencies (if not already installed)

Open Command Prompt and run:
```cmd
cd C:\shadowhunter
pip install asyncpg aiohttp certifi
```

If already installed from tracker setup, skip this.

### 3. Set Environment Variables

Add to your `.env` file:
```env
# Agent Monitor Settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shadowhunter
DB_USER=postgres
DB_PASSWORD=sh123
```

Or set them in Windows environment variables.

### 4. Create Database Tables (if not done)

Run the schema file:
```cmd
psql -U postgres -d shadowhunter -f paper_trading_schema.sql
```

Or execute the SQL from the file directly.

### 5. Initialize Paper Portfolio

Run this SQL to set starting balance:
```sql
INSERT INTO paper_portfolio (id, data) VALUES (1, '{
    "sol_balance": 2.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_fees_paid": 0,
    "realized_pnl": 0,
    "positions_count": 0
}') ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
```

### 6. Start the Monitor

Double-click `start_agent_monitor.bat` or run in Command Prompt:
```cmd
cd C:\shadowhunter
python agent_monitor_server.py
```

## What It Does

The monitor will:

1. **Check every 15 seconds** for new wallet cluster activity
2. **Research tokens** via DexScreener (price, MC, liquidity, age, narrative)
3. **Calculate weighted conviction** (Profit=3x, Cooker=3x, etc.)
4. **Make decisions:** BUY / WATCH / SKIP
5. **Execute paper trades** for BUY signals
6. **Log everything** to `agent_monitor.log`

## Decision Logic

| Weight | Confidence | Action | Position Size |
|--------|-----------|--------|---------------|
| ≥8 | 80%+ | BUY | 20% |
| ≥5 | 60%+ | BUY | 15% |
| ≥3 | 40%+ | BUY | 10% |
| <3 | <40% | WATCH/SKIP | - |

## Monitoring the Agent

### View Live Output
The monitor prints to console and logs to file.

### Check the Log
```cmd
type agent_monitor.log
tail -f agent_monitor.log  (if you have Unix tools)
```

### Check Paper Trades
Query the database:
```sql
SELECT * FROM paper_trades ORDER BY timestamp DESC LIMIT 10;
```

### Check Portfolio
```sql
SELECT * FROM paper_portfolio WHERE id = 1;
```

## Example Output

```
2025-03-26 04:15:23 | INFO | AGENT MONITOR STARTED
2025-03-26 04:15:23 | INFO | Paper Balance: 2.00 SOL
2025-03-26 04:15:38 | INFO | 🔔 NEW ACTIVITY: 7xKXtg2CW87d97TX with 4 wallets
2025-03-26 04:15:39 | INFO | 🟢 AGENT DECISION: BUY
2025-03-26 04:15:39 | INFO | AITOKEN
2025-03-26 04:15:39 | INFO | 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
2025-03-26 04:15:39 | INFO | 
2025-03-26 04:15:39 | INFO | Analysis:
2025-03-26 04:15:39 | INFO | • High conviction: 9.0x weight
2025-03-26 04:15:39 | INFO | • Key: Profit, Moonpie?, Cooker
2025-03-26 04:15:39 | INFO | • AI narrative
2025-03-26 04:15:39 | INFO | • Just launched
2025-03-26 04:15:39 | INFO | • Low MC
2025-03-26 04:15:39 | INFO | 
2025-03-26 04:15:39 | INFO | Confidence: 85%
2025-03-26 04:15:39 | INFO | Wallets: 4
2025-03-26 04:15:39 | INFO | 
2025-03-26 04:15:39 | INFO | Trade: 0.40 SOL
2025-03-26 04:15:39 | INFO | Balance: 1.59 SOL
2025-03-26 04:15:39 | INFO | ----------------------------------------
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'asyncpg'"
```cmd
pip install asyncpg aiohttp certifi
```

### "Connection refused"
- Check PostgreSQL is running
- Verify DB_PASSWORD in .env matches your PostgreSQL password
- Check DB_PORT (default 5432)

### Monitor not detecting activity
- Check tracker is running and writing to database
- Verify wallet_positions table has recent data
- Check `agent_monitor.log` for errors

## Stopping the Monitor

Press `Ctrl+C` in the console window, or close the window.

## Restarting

Simply run `start_agent_monitor.bat` again. The monitor will:
- Load your current paper balance
- Resume watching for new activity
- Not re-process already handled tokens

## Next Steps

Once running, I can:
1. Monitor the log file remotely (if you share it)
2. Review decisions and learn from patterns
3. Adjust strategy based on results
4. Eventually upgrade to live trading
