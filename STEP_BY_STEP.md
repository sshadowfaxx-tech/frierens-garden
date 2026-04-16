# SHADOWHUNTER STEP-BY-STEP WALKTHROUGH
## Learn While Building — Every Command Explained

**Goal:** Understand every piece as we build it  
**Tool:** VS Code (with extensions I'll guide you to install)  
**Time:** 45-60 minutes (slower because we're learning)  
**Prerequisites:** Computer, internet, curiosity

---

## BEFORE WE START: SETUP VS CODE

### 1. Install VS Code
https://code.visualstudio.com/download

### 2. Install Required Extensions

Open VS Code → Extensions (left sidebar) → Search and install:

| Extension | Why We Need It |
|-----------|----------------|
| **Docker** | See containers running, view logs |
| **Python** | Syntax highlighting, IntelliSense |
| **PostgreSQL** | Query database directly in VS Code |
| **Markdown All in One** | Better README viewing |

**Install them now.** We'll use all of them.

### 3. Open VS Code Terminal

`View` → `Terminal` (or press `` Ctrl+` ``)

This is where we'll run all commands.

---

## STEP 1: CREATE PROJECT FOLDER (3 minutes)

### What We're Doing
Creating a folder structure so everything is organized.

### Commands

```bash
# Create the project folder
mkdir -p ~/shadowhunter-mvp

# Enter it
cd ~/shadowhunter-mvp

# Open VS Code here
code .
```

**What you should see:**
- VS Code opens
- Left sidebar shows empty folder "SHADOWHUNTER-MVP"
- Bottom panel shows terminal (if not, press `` Ctrl+` ``)

### Understanding
- `~/` means your home directory
- `mkdir` = make directory
- `code .` = "open VS Code in this folder"

---

## STEP 2: CREATE DOCKER COMPOSE (5 minutes)

### What We're Doing
Docker Compose defines what services (databases) we need. Think of it as a recipe file.

### Create the File

In VS Code:
1. Click "New File" icon (top left)
2. Name it: `docker-compose.yml`
3. Paste this:

```yaml
# docker-compose.yml
# This file tells Docker what containers to run

version: '3.8'  # Docker Compose version

services:       # List of services (containers)

  # PostgreSQL with TimescaleDB extension
  # Stores all our transaction data
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    container_name: sh-db  # Short name for convenience
    ports:
      - "5432:5432"  # Expose port 5432 to our computer
    environment:
      - POSTGRES_USER=sh
      - POSTGRES_PASSWORD=sh123
      - POSTGRES_DB=shadowhunter
    volumes:
      # Persist data even if container restarts
      - db-data:/var/lib/postgresql/data
    restart: unless-stopped

  # Redis cache
  # Stores temporary data, prevents duplicate alerts
  redis:
    image: redis:7-alpine
    container_name: sh-cache
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 256mb
    restart: unless-stopped

# Define volumes (persistent storage)
volumes:
  db-data:
```

### Save the File
Press `Ctrl+S`

### Understanding Each Piece

| Line | What It Means |
|------|---------------|
| `services:` | List of containers to run |
| `timescaledb:` | PostgreSQL + time-series extension |
| `image:` | Download this pre-built image |
| `container_name:` | nickname for the container |
| `ports:` | Map container port → your computer port |
| `environment:` | Set configuration variables |
| `volumes:` | Save data even if container stops |
| `restart:` | Auto-restart if it crashes |

### Start the Databases

In VS Code terminal:

```bash
# Pull images and start containers
docker-compose up -d

# -d = detached (run in background)
```

**What should happen:**
```
Creating volume "shadowhunter-mvp_db-data" 
Pulling timescaledb...
Pulling redis...
Creating sh-db ... done
Creating sh-cache ... done
```

### Verify It Worked

```bash
# List running containers
docker-compose ps
```

**Should see:**
```
NAME      STATUS
db        Up 5 seconds
cache     Up 5 seconds
```

**In VS Code Docker extension:**
- Left sidebar → Docker icon
- You should see two containers running with green dots

### Troubleshooting

**"docker-compose not found"**
```bash
# Install Docker Compose
sudo apt install docker-compose
```

**"permission denied"**
```bash
# Add yourself to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

---

## STEP 3: TEST DATABASE CONNECTION (5 minutes)

### What We're Doing
Make sure we can talk to PostgreSQL from VS Code.

### Using VS Code PostgreSQL Extension

1. Click PostgreSQL icon (elephant) in left sidebar
2. Click `+` to add connection
3. Fill in:
   - Host: `localhost`
   - Port: `5432`
   - Database: `shadowhunter`
   - Username: `sh`
   - Password: `sh123`
4. Click Connect

**What you should see:**
- Connection appears in sidebar
- Can expand to see databases

### Using Command Line

```bash
# Connect to database
docker exec -it sh-db psql -U sh -d shadowhunter

# You'll see:
# psql (16.x)
# Type "help" for help.
# shadowhunter=#

# Try a command:
\dt  # List tables (should be empty)

# Exit:
\q
```

**Understanding:**
- `docker exec` = run command inside container
- `-it` = interactive mode
- `sh-db` = container name from docker-compose
- `psql` = PostgreSQL command line tool
- `-U sh` = connect as user "sh"

---

## STEP 4: SETUP PYTHON ENVIRONMENT (5 minutes)

### What We're Doing
Create an isolated Python environment so our packages don't conflict with system Python.

### Commands

```bash
# Create virtual environment (isolated Python)
python3 -m venv venv

# Activate it
source venv/bin/activate

# Your prompt should change:
# (venv) user@computer:~/shadowhunter-mvp$
```

**Understanding:**
- `venv` = virtual environment
- Isolates our project packages
- Prevents conflicts with system Python

### Create .gitignore

Create file `.gitignore`:

```
# Don't commit these files
venv/
__pycache__/
*.pyc
.env
.DS_Store
```

**Why:**
- `venv/` is large (don't commit Python binaries)
- `__pycache__/` is auto-generated
- `.env` will contain secrets

### Install Packages

Create file `requirements.txt`:

```
# Core async HTTP library
aiohttp==3.9.1

# Async PostgreSQL
asyncpg==0.29.0

# Redis client
redis==5.0.1

# Telegram bot
python-telegram-bot==20.7

# Environment variables
python-dotenv==1.0.0
```

**Understanding:**
- `aiohttp` = make web requests asynchronously
- `asyncpg` = talk to PostgreSQL without blocking
- `redis` = cache data in memory
- `python-telegram-bot` = send messages to Telegram
- `python-dotenv` = load secrets from .env file

Install them:

```bash
pip install -r requirements.txt
```

**This downloads and installs ~50MB of packages.**

### Verify Installation

```bash
# Check Python can import them
python3 -c "import aiohttp, asyncpg, redis, telegram; print('✓ All packages installed')"
```

---

## STEP 5: CREATE TELEGRAM BOT (10 minutes)

### What We're Doing
Create a Telegram bot that will send us alerts.

### Step 5.1: Get Bot Token

1. Open Telegram on your phone or desktop
2. Search for: **@BotFather**
3. Click Start
4. Type: `/newbot`
5. Name it: `ShadowHunter_[YourName]`
6. Username: `shadowhunter_[yourname]_bot` (must end in bot)
7. **Save the token!** Looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`

### Step 5.2: Get Your Chat ID

1. In Telegram, search: **@userinfobot**
2. Click Start
3. It sends your info:
   ```
   @YourUsername
   Id: 123456789
   First: Your
   Last: Name
   ```
4. **Save the Id number!**

### Step 5.3: Create Environment File

Create file `.env`:

```
# Telegram credentials
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
TELEGRAM_CHAT_ID=123456789

# Database credentials
DB_PASSWORD=sh123
```

**⚠️ IMPORTANT:**
- Never share this file
- Never commit it to Git
- Add it to `.gitignore` (already done)

---

## STEP 6: CREATE DATABASE TABLES (10 minutes)

### What We're Doing
Create tables to store transactions and watched wallets.

### Create init_db.py

Create file `init_db.py`:

```python
"""
Initialize database tables
Run this once before starting the tracker
"""
import asyncpg
import asyncio

async def init_database():
    """Create tables if they don't exist"""
    
    # Connect to database
    conn = await asyncpg.connect(
        "postgresql://sh:sh123@localhost:5432/shadowhunter"
    )
    
    print("Connected to database")
    
    # Create transactions table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            time TIMESTAMPTZ DEFAULT NOW(),
            wallet_address TEXT NOT NULL,
            token_address TEXT,
            tx_type TEXT CHECK (tx_type IN ('buy', 'sell', 'unknown')),
            amount_sol NUMERIC(18, 9),
            signature TEXT UNIQUE NOT NULL
        )
    ''')
    print("✓ Created transactions table")
    
    # Create watched_wallets table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS watched_wallets (
            address TEXT PRIMARY KEY,
            label TEXT,
            added_at TIMESTAMPTZ DEFAULT NOW()
        )
    ''')
    print("✓ Created watched_wallets table")
    
    # Create index for faster queries
    await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_tx_wallet 
        ON transactions(wallet_address, time DESC)
    ''')
    print("✓ Created index")
    
    # Close connection
    await conn.close()
    print("\n✅ Database ready!")

# Run it
if __name__ == "__main__":
    asyncio.run(init_database())
```

### Run It

```bash
python3 init_db.py
```

**Expected output:**
```
Connected to database
✓ Created transactions table
✓ Created watched_wallets table
✓ Created index

✅ Database ready!
```

### Verify in VS Code

1. Click PostgreSQL extension (elephant icon)
2. Refresh connection
3. Expand `shadowhunter` → `Tables`
4. You should see:
   - `transactions`
   - `watched_wallets`

---

## STEP 7: CREATE THE TRACKER (15 minutes)

### What We're Doing
Build the actual wallet monitoring code.

### Understanding the Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Solana    │────▶│   Your PC   │────▶│  Telegram   │
│   Network   │     │  (tracker)  │     │  (your      │
│             │     │             │     │   phone)    │
└─────────────┘     └─────────────┘     └─────────────┘
        │                  │
        ▼                  ▼
   Free RPC calls    Save to database
   (check wallets)   (remember history)
```

### Create tracker.py

Create file `tracker.py`:

```python
"""
ShadowHunter MVP - Wallet Tracker
Monitors Solana wallets and sends Telegram alerts
"""
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
from telegram import Bot
from dotenv import load_dotenv
import os
from datetime import datetime

# Load secrets from .env file
load_dotenv()

# Free Solana RPC endpoints
# These are public and free to use
RPC_URLS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
]


class WalletTracker:
    """Main tracker class"""
    
    def __init__(self):
        # Initialize connections (will connect later)
        self.db = None          # PostgreSQL
        self.cache = None       # Redis
        self.bot = None         # Telegram
        self.rpc_index = 0      # Which RPC to use
        
    async def connect(self):
        """Connect to all services"""
        
        # Connect to PostgreSQL
        self.db = await asyncpg.connect(
            "postgresql://sh:sh123@localhost:5432/shadowhunter"
        )
        print("✓ Connected to database")
        
        # Connect to Redis
        self.cache = redis.Redis(
            host='localhost', 
            port=6379, 
            decode_responses=True
        )
        await self.cache.ping()
        print("✓ Connected to cache")
        
        # Connect to Telegram
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.bot = Bot(token=token)
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # Test Telegram connection
        me = await self.bot.get_me()
        print(f"✓ Connected to Telegram bot: @{me.username}")
        
    async def send_alert(self, wallet: str, token: str, 
                        tx_type: str, amount: float, sig: str):
        """Send alert to Telegram"""
        
        # Emoji based on transaction type
        emoji = "🟢" if tx_type == "buy" else "🔴" if tx_type == "sell" else "⚪"
        
        # Format message
        message = f"""
{emoji} *{tx_type.upper()} Detected*

Wallet: `{wallet[:16]}...`
Token: `{token[:16]}...`
Amount: {amount:.4f} SOL
Time: {datetime.now().strftime('%H:%M:%S')}

[View on Solscan](https://solscan.io/tx/{sig})
        """
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            print(f"  📱 Alert sent: {tx_type}")
        except Exception as e:
            print(f"  ✗ Telegram error: {e}")
    
    def get_next_rpc(self) -> str:
        """Get next RPC URL (round-robin)"""
        url = RPC_URLS[self.rpc_index % len(RPC_URLS)]
        self.rpc_index += 1
        return url
    
    async def check_wallet(self, wallet: str, session: aiohttp.ClientSession):
        """Check recent transactions for a wallet"""
        
        # Prepare RPC request
        rpc_url = self.get_next_rpc()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": 3}]  # Last 3 transactions
        }
        
        try:
            # Make request
            async with session.post(rpc_url, json=payload) as resp:
                data = await resp.json()
                signatures = data.get('result', [])
                
                # Process each signature
                for sig_info in signatures:
                    sig = sig_info['signature']
                    
                    # Check if we've seen this before (Redis cache)
                    seen = await self.cache.get(f"tx:{sig}")
                    if seen:
                        continue  # Skip duplicates
                    
                    # Mark as seen (24 hour expiry)
                    await self.cache.setex(f"tx:{sig}", 86400, "1")
                    
                    # Get transaction details
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
                    }
                    
                    async with session.post(rpc_url, json=tx_payload) as tx_resp:
                        tx_data = await tx_resp.json()
                        tx = tx_data.get('result')
                        
                        if not tx:
                            continue
                        
                        # Parse transaction (simplified)
                        meta = tx.get('meta', {})
                        pre_bal = meta.get('preBalances', [0])[0] / 1e9
                        post_bal = meta.get('postBalances', [0])[0] / 1e9 if meta.get('postBalances') else 0
                        change = post_bal - pre_bal
                        
                        # Determine type (very simplified)
                        if abs(change) < 0.001:  # Skip tiny transactions
                            continue
                            
                        tx_type = "buy" if change < 0 else "sell"
                        amount = abs(change)
                        
                        # Get token (simplified - just use first account)
                        accounts = tx.get('transaction', {}).get('message', {}).get('accountKeys', [])
                        token = accounts[1] if len(accounts) > 1 else "unknown"
                        
                        # Save to database
                        await self.db.execute('''
                            INSERT INTO transactions 
                            (wallet_address, token_address, tx_type, amount_sol, signature)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (signature) DO NOTHING
                        ''', wallet, token, tx_type, amount, sig)
                        
                        # Send alert
                        await self.send_alert(wallet, token, tx_type, amount, sig)
                        
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    async def run(self):
        """Main loop - run forever"""
        
        # Connect to services
        await self.connect()
        
        # Wallets to watch (you'll add more)
        # This is an example wallet - replace with real ones
        wallets = [
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",  # Example
        ]
        
        print(f"\n🔍 Watching {len(wallets)} wallet(s)")
        print("⏱️  Checking every 30 seconds")
        print("Press Ctrl+C to stop\n")
        
        # Main loop
        async with aiohttp.ClientSession() as session:
            while True:
                cycle_start = datetime.now()
                
                for wallet in wallets:
                    await self.check_wallet(wallet, session)
                    await asyncio.sleep(2)  # Be nice to RPC
                
                # Status update
                elapsed = (datetime.now() - cycle_start).total_seconds()
                print(f"✓ Cycle complete in {elapsed:.1f}s")
                
                # Wait before next cycle
                await asyncio.sleep(30)


# Run the tracker
if __name__ == "__main__":
    tracker = WalletTracker()
    
    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        print("\n\n👋 Tracker stopped by user")
    except Exception as e:
        print(f"\n💥 Error: {e}")
```

---

## STEP 8: RUN EVERYTHING (10 minutes)

### 8.1 Add a Wallet to Watch

Edit `tracker.py`, find this line:
```python
wallets = [
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
]
```

Replace with a real wallet address you want to watch.

**Where to find wallets:**
- Solscan.io
- Look up successful traders
- Or keep the example for testing

### 8.2 Start the Tracker

```bash
# Make sure you're in the project folder
cd ~/shadowhunter-mvp

# Activate Python environment
source venv/bin/activate

# Run the tracker
python3 tracker.py
```

### 8.3 What You Should See

```
✓ Connected to database
✓ Connected to cache
✓ Connected to Telegram bot: @shadowhunter_yourname_bot

🔍 Watching 1 wallet(s)
⏱️  Checking every 30 seconds
Press Ctrl+C to stop

✓ Cycle complete in 2.3s
✓ Cycle complete in 2.1s
✓ Cycle complete in 2.4s
```

### 8.4 Test Telegram

1. Send yourself a message from Telegram bot
2. Or wait for the watched wallet to make a transaction
3. When it does, you'll get:

```
🟢 BUY Detected

Wallet: `7xKXtg2CW87d9...`
Token: `DezXAZ8z7PnrnR...`
Amount: 5.2340 SOL
Time: 14:32:15

[View on Solscan]
```

---

## WHAT YOU'VE BUILT

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    YOUR COMPUTER                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐        ┌──────────────┐          │
│  │  tracker.py  │◄──────►│  PostgreSQL  │          │
│  │              │        │  (Docker)    │          │
│  │  - Checks    │        │              │          │
│  │    wallets   │        │  - Stores    │          │
│  │  - Sends     │        │    history   │          │
│  │    alerts    │        └──────────────┘          │
│  │              │                ▲                  │
│  └──────┬───────┘                │                  │
│         │                        │                  │
│         ▼                        │                  │
│  ┌──────────────┐        ┌──────┴──────┐          │
│  │    Redis     │        │   Telegram  │          │
│  │  (Docker)    │        │   (phone)   │          │
│  │              │        │             │          │
│  │  - Prevents  │        └─────────────┘          │
│  │    duplicates│                                 │
│  └──────────────┘                                 │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Files You Have

```
shadowhunter-mvp/
├── docker-compose.yml      # Infrastructure definition
├── requirements.txt        # Python packages
├── .env                    # Secrets (never share!)
├── .gitignore             # What not to commit
├── init_db.py             # Database setup
├── tracker.py             # Main application
└── venv/                  # Python environment
```

---

## NEXT STEPS (To Expand)

| Feature | What To Do | Difficulty |
|---------|-----------|------------|
| **More wallets** | Edit `wallets` list in tracker.py | Easy |
| **Price data** | Add DexScreener API integration | Medium |
| **Smart filtering** | Only alert on transactions > 1 SOL | Easy |
| **Web dashboard** | Add Flask web server | Medium |
| **Wallet scoring** | Track PnL, calculate alpha | Hard |
| **Neo4j graph** | Add docker-compose service, cluster detection | Hard |
| **ML predictions** | Collect data, train XGBoost | Very Hard |

---

## COMMON ISSUES

### "Connection refused" to database
```bash
# Check if containers are running
docker-compose ps

# If not, start them
docker-compose up -d

# Check logs
docker-compose logs timescaledb
```

### "Module not found"
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall packages
pip install -r requirements.txt
```

### "Telegram error"
- Check `.env` file has correct token
- Make sure you messaged the bot first
- Verify chat_id is correct (no quotes, just numbers)

### "No transactions found"
- Wallet might be inactive
- Try a different wallet
- Check RPC is responding

---

## COMMANDS CHEAT SHEET

```bash
# Start infrastructure
docker-compose up -d

# Stop infrastructure
docker-compose down

# View logs
docker-compose logs -f

# Activate Python environment
source venv/bin/activate

# Run tracker
python3 tracker.py

# Connect to database
docker exec -it sh-db psql -U sh -d shadowhunter

# Check Redis
docker exec -it sh-cache redis-cli ping
```

---

**You now have a working foundation.** Every piece is connected. Every piece is understandable. Build from here.

*Questions? Errors? Stuck? Paste the error and I'll debug with you.*