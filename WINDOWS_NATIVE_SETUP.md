# ShadowHunter Native Windows Setup Guide
## Complete Step-by-Step Instructions

---

## Prerequisites
- Windows 10 or 11 (any version works)
- Python 3.9+ installed
- Your tracker files copied to `C:\shadowhunter\`

---

## Step 1: Install PostgreSQL

### 1.1 Download
- Go to: https://www.postgresql.org/download/windows/
- Click "Download the installer"
- Download **PostgreSQL 16** (latest stable)

### 1.2 Install
1. Run the downloaded installer
2. **Installation Directory**: Keep default (`C:\Program Files\PostgreSQL\16`)
3. **Components to Install**: Check ALL (PostgreSQL Server, pgAdmin, Stack Builder, Command Line Tools)
4. **Data Directory**: Keep default
5. **Password**: Enter `sh123` (this will be your database password)
6. **Port**: Keep default `5432`
7. **Locale**: Keep default or select `English, United States`
8. Click through to finish

### 1.3 Verify Installation
Open PowerShell and type:
```powershell
psql --version
```
You should see: `psql (PostgreSQL) 16.x`

If you get "command not found", restart your computer (PATH needs to refresh).

---

## Step 2: Install Redis

### 2.1 Download
- Go to: https://github.com/tporadowski/redis/releases
- Download `Redis-x64-5.0.14.1.msi` (or latest version)

### 2.2 Install
1. Run the MSI installer
2. **Destination Folder**: Keep default
3. **Port**: Keep default `6379`
4. **Max Memory**: Can leave blank (unlimited) or set `2048` for 2GB
5. Check "Add to PATH environment variable"
6. Finish installation

### 2.3 Verify Installation
Open PowerShell:
```powershell
redis-cli ping
```
You should see: `PONG`

---

## Step 3: Create Database and Tables

### 3.1 Open PowerShell as Administrator
Right-click Start → "Terminal (Admin)" or "PowerShell (Admin)"

### 3.2 Create Database
```powershell
# Switch to postgres user and create database
cd "C:\Program Files\PostgreSQL\16\bin"
psql -U postgres -c "CREATE DATABASE shadowhunter;"
```

When prompted for password, enter: `sh123`

You should see: `CREATE DATABASE`

### 3.3 Create Tables
Run this command (copy-paste entire block):

```powershell
psql -U postgres -d shadowhunter -c @"
CREATE TABLE IF NOT EXISTS wallet_positions (
    wallet_address VARCHAR(44) NOT NULL,
    token_address VARCHAR(44) NOT NULL,
    total_bought NUMERIC DEFAULT 0,
    total_sold NUMERIC DEFAULT 0,
    net_position NUMERIC DEFAULT 0,
    total_sol_invested NUMERIC DEFAULT 0,
    first_buy_time TIMESTAMP DEFAULT NOW(),
    last_buy_time TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    avg_entry_mc NUMERIC DEFAULT 0,
    PRIMARY KEY (wallet_address, token_address)
);

CREATE TABLE IF NOT EXISTS wallet_performance (
    wallet_address VARCHAR(44) PRIMARY KEY,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_sol_invested NUMERIC DEFAULT 0,
    total_sol_returned NUMERIC DEFAULT 0,
    realized_pnl NUMERIC DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_positions_token ON wallet_positions(token_address);
CREATE INDEX IF NOT EXISTS idx_positions_wallet ON wallet_positions(wallet_address);
"@
```

Password: `sh123`

You should see multiple `CREATE TABLE` and `CREATE INDEX` confirmations.

---

## Step 4: Set Up Python Environment

### 4.1 Verify Python
Open PowerShell (regular, not admin):
```powershell
python --version
```
Should show Python 3.9 or higher.

If Python is not installed:
- Download from https://python.org
- **IMPORTANT**: During install, check "Add Python to PATH"

### 4.2 Create Virtual Environment
```powershell
cd C:\shadowhunter
python -m venv venv
```

### 4.3 Activate and Install Dependencies
```powershell
.\venv\Scripts\activate
pip install aiohttp asyncpg redis python-telegram-bot python-dotenv
```

Wait for installation to complete (1-2 minutes).

---

## Step 5: Update Configuration

### 5.1 Edit .env File
Open `C:\shadowhunter\.env` in Notepad and update the database section:

```env
# Database Configuration (NATIVE WINDOWS)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shadowhunter
DB_USER=postgres
DB_PASSWORD=sh123

# Redis Configuration (NATIVE WINDOWS)
REDIS_HOST=localhost
REDIS_PORT=6379

# Keep your existing Telegram and other settings...
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
CHANNEL_PINGS=-100your_channel_id
CHANNEL_VIP=-100your_vip_channel_id
```

Save the file.

### 5.2 Verify Files
Your `C:\shadowhunter\` folder should contain:
```
C:\shadowhunter\
├── trackerv2_clean.py    (main tracker)
├── himmel.py             (optional: scanner bot)
├── .env                  (configuration)
├── wallets.txt           (wallet list)
├── venv\                 (Python environment)
└── [any .txt config files]
```

---

## Step 6: Test the Tracker

### 6.1 Run in Terminal (First Test)
```powershell
cd C:\shadowhunter
.\venv\Scripts\activate
python trackerv2_clean.py
```

### 6.2 Expected Output
```
Connecting to database...
Database connected
Connecting to Redis...
Redis connected
Connecting to Telegram...
Bot connected: @shadowhuntermvpbot
Loaded 41 wallets
Starting tracker | 41 wallets | min: 0.02 SOL
Monitoring 41 wallets | check interval: 5.0s | batch size: 10
```

### 6.3 Stop the Tracker
Press `Ctrl+C` to stop.

---

## Step 7: Create Auto-Start Script

### 7.1 Create Launcher Script
Open Notepad and paste:

```batch
@echo off
cd /d C:\shadowhunter
call venv\Scripts\activate.bat
python trackerv2_clean.py
pause
```

Save as: `C:\shadowhunter\start_tracker.bat`

### 7.2 Test the Launcher
Double-click `start_tracker.bat` - it should start the tracker in a command window.

### 7.3 Create Auto-Start Shortcut (Optional)
1. Press `Win+R`, type `shell:startup`, press Enter
2. Right-click → New → Shortcut
3. Location: `C:\shadowhunter\start_tracker.bat`
4. Name it "ShadowHunter"

Now the tracker starts automatically when you log in.

---

## Step 8: Verify Services Are Running

### Check PostgreSQL
```powershell
# Should return PostgreSQL version
psql -U postgres -c "SELECT version();"
```

### Check Redis
```powershell
# Should return PONG
redis-cli ping
```

### Check Services in Task Manager
1. Press `Ctrl+Shift+Esc` (Task Manager)
2. Go to "Services" tab
3. Look for:
   - `postgresql-x64-16` - Should be "Running"
   - `Redis` - Should be "Running"

---

## Troubleshooting

### "Password authentication failed"
- Make sure you're using password: `sh123`
- Check that PostgreSQL service is running

### "Connection refused" to Redis
- Redis service might not be running
- Open Services app (`Win+R` → `services.msc`), find Redis, right-click → Start

### "Module not found" when running tracker
- Make sure virtual environment is activated: `.\venv\Scripts\activate`
- Reinstall packages: `pip install aiohttp asyncpg redis python-telegram-bot python-dotenv`

### PostgreSQL command not found
- Restart computer (PATH update needed)
- Or use full path: `"C:\Program Files\PostgreSQL\16\bin\psql.exe"`

### Tracker crashes immediately
- Check `.env` file has correct credentials
- Verify `wallets.txt` exists and has valid wallets
- Check Telegram bot token is valid

---

## Quick Reference Commands

| Action | Command |
|--------|---------|
| Start tracker | `cd C:\shadowhunter && .\venv\Scripts\activate && python trackerv2_clean.py` |
| Or use batch file | Double-click `start_tracker.bat` |
| View database | `psql -U postgres -d shadowhunter` |
| Check Redis | `redis-cli ping` |
| Stop tracker | `Ctrl+C` in the window |
| Restart services | `services.msc` → right-click service → Restart |

---

## Next Steps

1. ✅ Install PostgreSQL
2. ✅ Install Redis
3. ✅ Create database and tables
4. ✅ Set up Python environment
5. ✅ Update .env configuration
6. ✅ Test tracker
7. ✅ Set up auto-start (optional)

**You're ready to run ShadowHunter 24/7 on your FX 6300!**

---

## Monitoring Your Setup

### View Logs
The tracker outputs logs to the terminal. To save logs to file:

Modify `start_tracker.bat`:
```batch
@echo off
cd /d C:\shadowhunter
call venv\Scripts\activate.bat
python trackerv2_clean.py >> tracker.log 2>&1
```

Then view with: `type tracker.log` or open in Notepad.

### Restart If Needed
If Windows updates restart your PC, just double-click `start_tracker.bat` again.

---

*Setup complete! Your FX 6300 is now a dedicated ShadowHunter server.*
