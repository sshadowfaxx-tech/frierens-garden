# Agent Full Visibility Setup Guide

Complete setup for the independent trading agent with full alert visibility.

## What This Does

The agent monitors ALL wallet activity (not just clusters) and reports everything to Telegram:
- Individual wallet trades
- Cluster alerts (2+ wallets)
- Token research for every alert
- Decision process (BUY/WATCH/SKIP)
- Paper trade execution
- Learning data for strategy improvement

## Files to Copy to FX 6300

Copy these files to your `C:\shadowhunter\` folder:

1. `agent_full_visibility.py` - Main monitoring script
2. `wallets.txt` - Wallet list (should already be there)
3. This setup guide

## Step-by-Step Setup

### Step 1: Verify Python Environment

Open Command Prompt on FX 6300:
```cmd
cd C:\shadowhunter
python --version
```

Should show Python 3.11+ (or whatever you installed).

### Step 2: Install Dependencies

```cmd
cd C:\shadowhunter
pip install asyncpg aiohttp python-telegram-bot certifi
```

If already installed from tracker setup, you'll see "Requirement already satisfied".

### Step 3: Update Environment Variables

Edit your `.env` file (in `C:\shadowhunter\.env`) and add:

```env
# Agent Monitor Settings
CHANNEL_AGENT_LOGS=-1003778576771

# Database (should already be set)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shadowhunter
DB_USER=postgres
DB_PASSWORD=sh123

# Telegram (should already be set)
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### Step 4: Initialize Paper Trading Database

Run this SQL to set up the paper trading tables:

```sql
-- Create paper portfolio table
CREATE TABLE IF NOT EXISTS paper_portfolio (
    id INTEGER PRIMARY KEY DEFAULT 1,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create paper trades table
CREATE TABLE IF NOT EXISTS paper_trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    action VARCHAR(10) NOT NULL,
    token VARCHAR(44) NOT NULL,
    token_symbol VARCHAR(50),
    amount_sol NUMERIC(20, 9),
    tokens NUMERIC(36, 9),
    price_usd NUMERIC(36, 18),
    market_cap NUMERIC(36, 2),
    fee NUMERIC(10, 9) DEFAULT 0.01,
    realized_pnl NUMERIC(20, 9) DEFAULT 0,
    realized_roi NUMERIC(10, 2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Initialize with 2 SOL starting balance
INSERT INTO paper_portfolio (id, data) VALUES (1, '{
    "sol_balance": 2.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_fees_paid": 0,
    "realized_pnl": 0,
    "positions_count": 0,
    "mode": "learning"
}') ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
```

To run this SQL, open Command Prompt:
```cmd
psql -U postgres -d shadowhunter
```
Then paste the SQL above and press Enter.

Or create a file `init_paper.sql` with the SQL and run:
```cmd
psql -U postgres -d shadowhunter -f init_paper.sql
```

### Step 5: Create Launcher Script

Create a file `start_agent.bat` with:

```batch
@echo off
echo Starting Agent Monitor...
echo.
cd /d "C:\shadowhunter"
python agent_full_visibility.py
pause
```

### Step 6: Start the Agent

Double-click `start_agent.bat` or run:
```cmd
cd C:\shadowhunter
python agent_full_visibility.py
```

You should see:
```
2025-03-26 XX:XX:XX | INFO | Full-visibility agent started
```

And a Telegram message in the channel:
> 🤖 *Agent Monitor Started*
> 
> Monitoring all wallet activity...

## What You'll See in Telegram

### 1. Cluster Alerts (2+ wallets on same token)
```
🚨 CLUSTER ALERT (4 wallets)

*TOKEN_SYMBOL*
`token_address`

📊 Cluster Data:
• Total SOL: 15.50
• Weight: 9.0x
• Key: Profit, Moonpie?, Cooker

📈 Token Info:
• Narrative: AI
• MC: $450K
• Age: 0.5h
• Liq: $85K

🟢 AGENT DECISION: BUY
• Confidence: 85%
• High weight: 9.0x
• AI narrative
• Just launched

💰 Paper Trade: 0.40 SOL
💼 Balance: 1.59 SOL
```

### 2. Individual Trades
```
👤 INDIVIDUAL TRADE (Profit)

*TOKEN_SYMBOL*
`token_address`

📊 Wallet Data:
• Invested: 2.50 SOL
• Winrate: 83%
• PnL: +19.2 SOL

👀 AGENT DECISION: WATCH
• Confidence: 50%
• Strong wallet: 83% WR

[Not enough for trade - watching]
```

### 3. Status Updates (every ~10 minutes)
```
📊 Status Update
Balance: 1.84 SOL | Trades: 3
```

## How I Learn From This

I see:
- **Every wallet trade** - even individual ones
- **Cluster formation** - how many wallets before I decide
- **Token research** - narrative, age, liquidity
- **Decision reasoning** - why I bought/watched/skipped
- **Results** - which decisions were good/bad

I can then:
- Adjust wallet weights
- Change confidence thresholds
- Update narrative preferences
- Refine position sizing

## Troubleshooting

### "ModuleNotFoundError: No module named 'asyncpg'"
```cmd
pip install asyncpg aiohttp python-telegram-bot certifi
```

### "Connection refused" or database errors
- Check PostgreSQL is running: `services.msc` → PostgreSQL
- Verify password in `.env` matches your PostgreSQL password
- Check database exists: `psql -U postgres -l`

### "Failed to send to Telegram"
- Check TELEGRAM_BOT_TOKEN is correct in `.env`
- Verify bot is admin in channel -1003778576771
- Check bot can post messages (send a test message)

### No alerts appearing
- Check tracker is running and writing to database
- Verify wallet_positions table has recent data:
  ```sql
  SELECT COUNT(*), MAX(first_buy_time) FROM wallet_positions;
  ```
- Check agent_monitor.log for errors

## Managing the Agent

### Stop the Agent
Press `Ctrl+C` in the Command Prompt window, or close the window.

### Restart the Agent
Double-click `start_agent.bat` again.

### Check Status
Query the database:
```sql
-- Paper balance
SELECT data FROM paper_portfolio WHERE id = 1;

-- Recent trades
SELECT * FROM paper_trades ORDER BY timestamp DESC LIMIT 10;

-- Trade count
SELECT COUNT(*) FROM paper_trades;
```

### Reset Paper Portfolio
If you want to start fresh with 2 SOL:
```sql
UPDATE paper_portfolio SET data = '{
    "sol_balance": 2.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_fees_paid": 0,
    "realized_pnl": 0
}' WHERE id = 1;

-- Optional: Clear trade history
TRUNCATE paper_trades;
```

## Next Steps

1. **Start the agent** and let it run
2. **Watch Telegram** for alerts
3. **I analyze patterns** and suggest improvements
4. **Update strategy** based on results
5. **Eventually go live** when paper trading is profitable

## Questions?

If something doesn't work, check:
1. `agent_monitor.log` file for errors
2. PostgreSQL is running
3. Bot token and channel ID are correct
4. Database tables exist
5. Tracker is actively writing to database

**Once running, I can monitor independently and refine the strategy.**
