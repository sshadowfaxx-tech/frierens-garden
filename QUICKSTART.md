# QUICK START - Agent Full Visibility

## Files to Copy to FX 6300

From your laptop, copy to `C:\shadowhunter\`:
1. ✅ `agent_full_visibility.py` (the main script)
2. ✅ `start_agent.bat` (the launcher)
3. ✅ `wallets.txt` (should already be there)

## 5-Minute Setup

### 1. Open Command Prompt on FX 6300
```cmd
cd C:\shadowhunter
```

### 2. Check Python
```cmd
python --version
```
Should show version. If not, Python isn't installed properly.

### 3. Install Dependencies (if needed)
```cmd
pip install asyncpg aiohttp python-telegram-bot certifi
```

### 4. Update .env File
Add this line to your existing `.env`:
```env
CHANNEL_AGENT_LOGS=-1003778576771
```

Your `.env` should look like:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
CHANNEL_PINGS=-1003640122337
CHANNEL_RAW_PINGS=-1003784020043
CHANNEL_AGENT_LOGS=-1003778576771
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shadowhunter
DB_USER=postgres
DB_PASSWORD=sh123
```

### 5. Initialize Paper Trading (run once)

Create a file `init_paper.sql`:
```sql
CREATE TABLE IF NOT EXISTS paper_portfolio (
    id INTEGER PRIMARY KEY DEFAULT 1,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

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

Then run:
```cmd
psql -U postgres -d shadowhunter -f init_paper.sql
```

### 6. Start the Agent

Double-click `start_agent.bat`

Or run:
```cmd
python agent_full_visibility.py
```

## Verify It's Working

You should see in the Command Prompt:
```
2025-03-26 XX:XX:XX | INFO | Full-visibility agent started
```

And in Telegram channel (-1003778576771):
```
🤖 Agent Monitor Started

Monitoring all wallet activity...
```

## What Happens Next

When the tracker detects activity, you'll see in Telegram:

**Cluster alerts:**
```
🚨 CLUSTER ALERT (4 wallets)
*TOKEN*
📊 Weight: 9.0x | Key: Profit, Moonpie?
🟢 AGENT DECISION: BUY
💰 Paper Trade: 0.40 SOL
```

**Individual trades:**
```
👤 INDIVIDUAL TRADE (Profit)
*TOKEN*
📊 Winrate: 83% | PnL: +19.2 SOL
👀 AGENT DECISION: WATCH
```

**Status updates (every ~10 min):**
```
📊 Status Update
Balance: 1.84 SOL | Trades: 3
```

## Stop the Agent

Press `Ctrl+C` in the Command Prompt window, or close it.

## Check Status Anytime

Open new Command Prompt:
```cmd
psql -U postgres -d shadowhunter -c "SELECT data FROM paper_portfolio WHERE id = 1;"
```

Shows current paper balance and trade count.

---

**That's it! Once running, I can see every alert and trade independently.**
