# SHADOWHUNTER QUICK START
## Bare Bones MVP — Working in 30 Minutes

**What this gets you:**
- Database running (TimescaleDB + Redis)
- Wallet monitor tracking 5-10 wallets
- Telegram alerts when they buy/sell
- Everything local, $0 cost

**What this DOESN'T have:**
- Neo4j graph (overkill for MVP)
- MongoDB (not needed yet)
- ML predictions (manual analysis first)
- Grafana (check Telegram instead)

---

## STEP 0: PREREQUISITES (2 minutes)

```bash
# Check you have Docker
docker --version || echo "INSTALL DOCKER FIRST"

# Check Python
python3 --version || echo "INSTALL PYTHON 3.10+"

# Make project folder
mkdir -p ~/shadowhunter-quickstart && cd ~/shadowhunter-quickstart
```

---

## STEP 1: INFRASTRUCTURE (5 minutes)

Create `docker-compose.yml`:

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Only what we need: TimescaleDB + Redis
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=shadowhunter
      - POSTGRES_PASSWORD=shadow123
      - POSTGRES_DB=shadowhunter
    volumes:
      - timescale-data:/var/lib/postgresql/data
    command: >
      postgres 
      -c shared_preload_libraries=timescaledb
      -c max_connections=100
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    restart: unless-stopped

volumes:
  timescale-data:
EOF
```

Start it:

```bash
docker-compose up -d

# Verify
sleep 5
docker-compose ps
# Should show both "Up"
```

---

## STEP 2: PYTHON ENVIRONMENT (3 minutes)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install minimal deps
pip install asyncpg redis aiohttp python-telegram-bot python-dotenv
```

---

## STEP 3: TELEGRAM BOT SETUP (5 minutes)

### 3.1 Create Your Bot
1. Open Telegram, search **@BotFather**
2. Send `/newbot`
3. Name it: `ShadowHunter_YourName`
4. Get your **API token** (save it!)
5. Send `/start` to your new bot

### 3.2 Get Your Chat ID
1. Message **@userinfobot** on Telegram
2. It replies with your **Chat ID** (numbers, might be negative)

### 3.3 Create .env File

```bash
cat > .env << 'EOF'
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Database
DB_PASSWORD=shadow123
EOF
```

---

## STEP 4: THE CODE (10 minutes)

### 4.1 Database Setup

Create `init_db.py`:

```python
import asyncpg
import asyncio

async def init():
    conn = await asyncpg.connect(
        "postgresql://shadowhunter:shadow123@localhost:5432/shadowhunter"
    )
    
    # Create transactions table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id SERIAL PRIMARY KEY,
            time TIMESTAMPTZ DEFAULT NOW(),
            wallet_address TEXT,
            token_address TEXT,
            tx_type TEXT,
            amount_sol FLOAT,
            signature TEXT UNIQUE
        )
    ''')
    
    # Create watched wallets table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS watched_wallets (
            address TEXT PRIMARY KEY,
            label TEXT,
            added_at TIMESTAMPTZ DEFAULT NOW()
        )
    ''')
    
    print("✓ Database initialized")
    await conn.close()

asyncio.run(init())
```

Run it:
```bash
python init_db.py
```

### 4.2 Main Tracker

Create `tracker.py`:

```python
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
from telegram import Bot
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

# Free RPC endpoints (rotate if one fails)
RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
]

class QuickTracker:
    def __init__(self):
        self.db = None
        self.cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.rpc_index = 0
        
    async def connect(self):
        self.db = await asyncpg.connect(
            "postgresql://shadowhunter:shadow123@localhost:5432/shadowhunter"
        )
        print("✓ Connected to database and Telegram")
    
    async def send_alert(self, wallet: str, token: str, tx_type: str, amount: float, sig: str):
        """Send Telegram alert"""
        emoji = "🟢 BUY" if tx_type == "buy" else "🔴 SELL"
        message = f"""
{emoji} Alert!

Wallet: `{wallet[:20]}...`
Token: `{token[:20]}...`
Amount: {amount:.3f} SOL
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
            print(f"✓ Alert sent: {wallet[:20]}... {tx_type}")
        except Exception as e:
            print(f"✗ Failed to send alert: {e}")
    
    async def get_rpc(self):
        """Get next RPC endpoint"""
        endpoint = RPC_ENDPOINTS[self.rpc_index % len(RPC_ENDPOINTS)]
        self.rpc_index += 1
        return endpoint
    
    async def check_wallet(self, wallet: str, session: aiohttp.ClientSession):
        """Check recent transactions for a wallet"""
        rpc = await self.get_rpc()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": 5}]
        }
        
        try:
            async with session.post(rpc, json=payload) as resp:
                data = await resp.json()
                signatures = data.get('result', [])
                
                for sig_info in signatures:
                    sig = sig_info['signature']
                    
                    # Check if we've seen this transaction
                    seen = await self.cache.get(f"tx:{sig}")
                    if seen:
                        continue
                    
                    # Mark as seen (24 hour expiry)
                    await self.cache.setex(f"tx:{sig}", 86400, "1")
                    
                    # Get transaction details
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
                    }
                    
                    async with session.post(rpc, json=tx_payload) as tx_resp:
                        tx_data = await tx_resp.json()
                        tx = tx_data.get('result', {})
                        
                        if not tx:
                            continue
                        
                        # Parse transaction (simplified)
                        meta = tx.get('meta', {})
                        pre_bal = meta.get('preBalances', [0])[0] / 1e9
                        post_bal = meta.get('postBalances', [0]) / 1e9
                        change = post_bal - pre_bal
                        
                        # Determine buy/sell (simplified heuristic)
                        tx_type = "buy" if change < 0 else "sell"
                        amount = abs(change)
                        
                        if amount < 0.01:  # Skip dust
                            continue
                        
                        # Get token address (simplified)
                        token = "Unknown"
                        accounts = tx.get('transaction', {}).get('message', {}).get('accountKeys', [])
                        if len(accounts) > 1:
                            token = accounts[1]  # Usually the token account
                        
                        # Save to database
                        await self.db.execute('''
                            INSERT INTO wallet_transactions (wallet_address, token_address, tx_type, amount_sol, signature)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (signature) DO NOTHING
                        ''', wallet, token, tx_type, amount, sig)
                        
                        # Send alert
                        await self.send_alert(wallet, token, tx_type, amount, sig)
                        
        except Exception as e:
            print(f"Error checking {wallet[:20]}...: {e}")
    
    async def run(self):
        """Main loop"""
        await self.connect()
        
        # Add some test wallets to watch
        test_wallets = [
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",  # Example
        ]
        
        # Load from database or use defaults
        rows = await self.db.fetch("SELECT address FROM watched_wallets")
        wallets = [row['address'] for row in rows] or test_wallets
        
        print(f"\n🚀 Watching {len(wallets)} wallets...")
        print("Press Ctrl+C to stop\n")
        
        async with aiohttp.ClientSession() as session:
            while True:
                for wallet in wallets:
                    await self.check_wallet(wallet, session)
                    await asyncio.sleep(2)  # Rate limiting
                
                print(f"✓ Cycle complete at {datetime.now().strftime('%H:%M:%S')}")
                await asyncio.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    tracker = QuickTracker()
    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        print("\n\n👋 Stopped")
```

---

## STEP 5: RUN IT (5 minutes)

### 5.1 Add a Wallet to Watch

```bash
# Connect to database and add wallets
docker exec -it shadowhunter-quickstart_timescaledb_1 psql -U shadowhunter -c "
INSERT INTO watched_wallets (address, label) VALUES 
('7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU', 'Test Wallet')
ON CONFLICT DO NOTHING;
"
```

**Or** edit `tracker.py` and add wallets to the `test_wallets` list.

### 5.2 Start Tracking

```bash
# Make sure venv is active
source venv/bin/activate

# Run it
python tracker.py
```

**You should see:**
```
✓ Connected to database and Telegram
🚀 Watching 1 wallets...
Press Ctrl+C to stop

✓ Cycle complete at 14:32:15
✓ Cycle complete at 14:32:45
```

### 5.3 Test the Alert

When the wallet makes a transaction, you'll get a Telegram message:

```
🟢 BUY Alert!

Wallet: `7xKXtg2CW87d97TXJSD...`
Token: `DezXAZ8z7PnrnRJjz3w...`
Amount: 5.234 SOL
Time: 14:33:12

[View on Solscan](https://solscan.io/tx/5xK...)
```

---

## WHAT YOU HAVE NOW

✅ Database storing transactions  
✅ Cache preventing duplicate alerts  
✅ Telegram alerts on your phone  
✅ Free RPC rotation  
✅ Working foundation  

## NEXT STEPS (Build On This)

| Feature | How to Add |
|---------|-----------|
| **More wallets** | Add to `test_wallets` list or database |
| **Price data** | Integrate DexScreener API |
| **Smart wallets** | Add wallet scoring logic |
| **Clustering** | Add Neo4j for graph analysis |
| **ML predictions** | Train model on collected data |
| **Web dashboard** | Add Grafana or Flask app |

## TROUBLESHOOTING

**"Connection refused"**
```bash
docker-compose ps  # Check containers are up
docker-compose logs timescaledb  # Check logs
```

**"Telegram error"**
- Check `.env` file has correct token/chat_id
- Message your bot first to activate it

**"No transactions found"**
- Wallet might be inactive
- Try a different wallet address
- Check RPC endpoints are responding

**"Rate limited"**
- The code already has 2-second delays
- If still limited, increase delay in `tracker.py`

---

## FILES YOU HAVE

```
~/shadowhunter-quickstart/
├── docker-compose.yml    # Infrastructure
├── .env                  # Secrets (don't share!)
├── venv/                 # Python environment
├── init_db.py            # Database setup (run once)
└── tracker.py            # Main program
```

**Total time to working alerts: ~30 minutes**

**Total cost: $0**

---

*Foundation laid. Telegram buzzing. Now build the empire.*