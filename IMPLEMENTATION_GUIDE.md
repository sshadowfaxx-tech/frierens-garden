# SHADOWHUNTER LOCAL DEVELOPMENT GUIDE
## Complete Implementation Plan for Personal Testing

**Version:** 1.0  
**Purpose:** Build and test ShadowHunter locally before any cloud deployment  
**Prerequisites:** Computer with 16GB+ RAM, internet connection, basic command line knowledge  
**Estimated Time:** 2-4 hours initial setup, 1-2 weeks testing

---

# TABLE OF CONTENTS

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites Check](#2-prerequisites-check)
3. [Project Structure](#3-project-structure)
4. [Phase 1: Infrastructure](#4-phase-1-infrastructure)
5. [Phase 2: Data Collection](#5-phase-2-data-collection)
6. [Phase 3: Wallet Intelligence](#6-phase-3-wallet-intelligence)
7. [Phase 4: Alert System](#7-phase-4-alert-system)
8. [Phase 5: Testing & Validation](#8-phase-5-testing--validation)
9. [Troubleshooting](#9-troubleshooting)
10. [Migration to Production](#10-migration-to-production)

---

# 1. ARCHITECTURE OVERVIEW

## System Diagram (Local)

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR COMPUTER                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Docker     │    │   Python     │    │   Node.js    │  │
│  │  (Databases) │    │  (Services)  │    │   (Telegram) │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             │                              │
│                    ┌────────▼────────┐                     │
│                    │  Free APIs      │                     │
│                    │  (Solana,       │                     │
│                    │   DexScreener)  │                     │
│                    └────────┬────────┘                     │
│                             │                              │
│                    ┌────────▼────────┐                     │
│                    │  Telegram Bot   │                     │
│                    │  (Your Phone)   │                     │
│                    └─────────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Breakdown

| Component | Technology | Purpose | Port |
|-----------|------------|---------|------|
| **TimescaleDB** | PostgreSQL + time-series | Store prices, transactions | 5432 |
| **Neo4j** | Graph database | Wallet relationships | 7474, 7687 |
| **Redis** | In-memory cache | Hot data, sessions | 6379 |
| **MongoDB** | Document store | Token metadata | 27017 |
| **Grafana** | Visualization | Dashboards | 3000 |
| **Wallet Tracker** | Python | Monitor wallet activity | - |
| **Cluster Detector** | Python | Detect coordinated buying | - |
| **Price Feed** | Python | Collect market data | - |
| **Telegram Bot** | Python | Send alerts | - |

---

# 2. PREREQUISITES CHECK

## System Requirements

Run these commands to verify your system:

```bash
# Check available RAM
free -h
# Need: 16GB+ available (32GB recommended)

# Check CPU cores
nproc
# Need: 4+ cores (8+ recommended)

# Check disk space
df -h
# Need: 100GB+ free (SSD strongly recommended)

# Check OS
uname -a
# Ubuntu 22.04/24.04 LTS recommended
```

## Required Software

Install these if not present:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install -y docker-compose

# Install Python 3.10+
sudo apt install -y python3 python3-pip python3-venv

# Install Git
sudo apt install -y git curl wget

# Install build tools (for Python packages)
sudo apt install -y build-essential libpq-dev

# Verify installations
docker --version
docker-compose --version
python3 --version
```

## Test Docker Works

```bash
docker run hello-world
# Should see: "Hello from Docker!"
```

---

# 3. PROJECT STRUCTURE

Create this directory structure:

```bash
mkdir -p ~/shadowhunter/{src,config,data,models,logs,tests}
cd ~/shadowhunter
tree  # Verify structure
```

Expected structure:
```
~/shadowhunter/
├── docker-compose.yml          # Infrastructure definition
├── requirements.txt            # Python dependencies
├── .env                        # Secrets (never commit)
├── config/
│   ├── prometheus.yml         # Monitoring config
│   ├── grafana-dashboard.json # Dashboard definition
│   └── telegram-config.yml    # Bot settings
├── src/
│   ├── __init__.py
│   ├── database.py            # DB connection managers
│   ├── rpc_client.py          # Solana RPC wrapper
│   ├── price_feed.py          # Price data collection
│   ├── wallet_tracker.py      # Wallet monitoring
│   ├── cluster_detector.py    # Graph analysis
│   ├── risk_analyzer.py       # Contract safety checks
│   ├── telegram_bot.py        # Alert bot
│   └── ml_predictor.py        # Prediction model
├── data/
│   ├── historical/            # CSV exports
│   └── training/              # ML training data
├── models/
│   └── .gitkeep               # Trained models go here
└── logs/
    └── .gitkeep               # Log files
```

---

# 4. PHASE 1: INFRASTRUCTURE

## 4.1 Create docker-compose.yml

```bash
cat > ~/shadowhunter/docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Time-Series Database
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    container_name: shadowhunter-timescale
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=shadowhunter
      - POSTGRES_PASSWORD=${DB_PASSWORD:-changeme}
      - POSTGRES_DB=shadowhunter
    volumes:
      - timescale-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    command: >
      postgres 
      -c shared_preload_libraries=timescaledb
      -c max_connections=100
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
    shm_size: 1gb
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shadowhunter"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Graph Database
  neo4j:
    image: neo4j:5-community
    container_name: shadowhunter-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-changeme}
      - NEO4J_dbms_memory_heap_initial__size=1G
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    restart: unless-stopped

  # Cache
  redis:
    image: redis:7-alpine
    container_name: shadowhunter-redis
    ports:
      - "6379:6379"
    command: >
      redis-server
      --maxmemory 1gb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redis-data:/data
    restart: unless-stopped

  # Document Store
  mongodb:
    image: mongo:7
    container_name: shadowhunter-mongo
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD:-changeme}
      - MONGO_INITDB_DATABASE=shadowhunter
    volumes:
      - mongo-data:/data/db
    restart: unless-stopped

  # Monitoring
  grafana:
    image: grafana/grafana:latest
    container_name: shadowhunter-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  timescale-data:
  neo4j-data:
  neo4j-logs:
  redis-data:
  mongo-data:
  grafana-data:

networks:
  default:
    name: shadowhunter-network
EOF
```

## 4.2 Create Initialization Scripts

```bash
mkdir -p ~/shadowhunter/init-scripts

# TimescaleDB initialization
cat > ~/shadowhunter/init-scripts/01-init-timescale.sql << 'EOF'
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create hypertable for token prices
CREATE TABLE token_prices (
    time TIMESTAMPTZ NOT NULL,
    token_address TEXT NOT NULL,
    price_usd DECIMAL(18, 8),
    volume_24h DECIMAL(24, 8),
    market_cap DECIMAL(24, 8),
    liquidity_usd DECIMAL(24, 8)
);

SELECT create_hypertable('token_prices', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_token_prices_address ON token_prices (token_address, time DESC);

-- Create hypertable for wallet transactions
CREATE TABLE wallet_transactions (
    time TIMESTAMPTZ NOT NULL,
    wallet_address TEXT NOT NULL,
    token_address TEXT NOT NULL,
    tx_type TEXT CHECK (tx_type IN ('buy', 'sell')),
    amount_sol DECIMAL(18, 8),
    amount_token DECIMAL(24, 8),
    price_usd DECIMAL(18, 8),
    tx_hash TEXT
);

SELECT create_hypertable('wallet_transactions', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_wallet_tx_wallet ON wallet_transactions (wallet_address, time DESC);
CREATE INDEX idx_wallet_tx_token ON wallet_transactions (token_address, time DESC);

-- Create table for wallet scores
CREATE TABLE wallet_scores (
    wallet_address TEXT PRIMARY KEY,
    alpha_score DECIMAL(5, 2),
    tier TEXT CHECK (tier IN ('GOD', 'WHALE', 'SHARK', 'FISH', 'RETAIL')),
    realized_pnl_30d DECIMAL(18, 2),
    win_rate DECIMAL(5, 4),
    avg_hold_time_hours DECIMAL(8, 2),
    total_trades INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create table for predictions
CREATE TABLE ml_predictions (
    time TIMESTAMPTZ NOT NULL,
    token_address TEXT NOT NULL,
    model_version TEXT,
    pump_probability DECIMAL(5, 4),
    confidence TEXT CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
    features JSONB
);

SELECT create_hypertable('ml_predictions', 'time', chunk_time_interval => INTERVAL '1 day');
EOF
```

## 4.3 Start Infrastructure

```bash
cd ~/shadowhunter

# Create environment file
cat > .env << 'EOF'
DB_PASSWORD=your_secure_db_password_here
NEO4J_PASSWORD=your_secure_neo_password_here
MONGO_PASSWORD=your_secure_mongo_password_here
GRAFANA_PASSWORD=your_secure_grafana_password_here
EOF

# Start all services
docker-compose up -d

# Check status (all should show "Up")
docker-compose ps

# Wait 30 seconds for services to initialize
sleep 30

# Test connections
echo "Testing TimescaleDB..."
docker exec shadowhunter-timescale psql -U shadowhunter -c "SELECT version();"

echo "Testing Neo4j..."
curl -s http://localhost:7474 | head -1

echo "Testing Redis..."
docker exec shadowhunter-redis redis-cli ping

echo "All services running!"
```

## 4.4 Verify Neo4j Schema

```bash
# Open Neo4j Browser: http://localhost:7474
# Login: neo4j / [your password from .env]

# Run this Cypher to create constraints:
CREATE CONSTRAINT wallet_address IF NOT EXISTS
FOR (w:Wallet) REQUIRE w.address IS UNIQUE;

CREATE CONSTRAINT token_address IF NOT EXISTS
FOR (t:Token) REQUIRE t.address IS UNIQUE;

CREATE INDEX wallet_alpha_score IF NOT EXISTS
FOR (w:Wallet) ON (w.alpha_score);
```

---

# 5. PHASE 2: DATA COLLECTION

## 5.1 Create Python Environment

```bash
cd ~/shadowhunter

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
cat > requirements.txt << 'EOF'
# Async HTTP
aiohttp==3.9.1
aiohttp-retry==2.8.3

# Databases
asyncpg==0.29.0
neo4j==5.15.0
redis==5.0.1
pymongo==4.6.1
psycopg2-binary==2.9.9

# Data processing
pandas==2.1.4
numpy==1.26.2

# ML
scikit-learn==1.3.2
xgboost==2.0.3

# Telegram
python-telegram-bot==20.7

# Utilities
python-dotenv==1.0.0
pydantic==2.5.2
tenacity==8.2.3
schedule==1.2.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
EOF

pip install -r requirements.txt
```

## 5.2 Create RPC Client

```bash
cat > ~/shadowhunter/src/rpc_client.py << 'EOF'
"""
Free Solana RPC client with automatic failover
"""
import asyncio
import random
from typing import Optional, List, Dict
import aiohttp
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RPCEndpoint:
    url: str
    weight: int = 1
    failures: int = 0
    last_used: float = 0

class FreeRPCClient:
    """
    Rotates between free RPC endpoints with automatic failover
    """
    
    FREE_ENDPOINTS = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-rpc.publicnode.com",
        # Add your free Helius key here if you get one
        # "https://mainnet.helius-rpc.com/?api-key=YOUR_KEY",
    ]
    
    def __init__(self):
        self.endpoints = [RPCEndpoint(url) for url in self.FREE_ENDPOINTS]
        self.session: Optional[aiohttp.ClientSession] = None
        self.circuit_breaker = {}
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def call(self, method: str, params: list = None) -> dict:
        """Make RPC call with automatic failover"""
        payload = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 1000000),
            "method": method,
            "params": params or []
        }
        
        # Filter healthy endpoints
        healthy = [e for e in self.endpoints if self.circuit_breaker.get(e.url, 0) < 3]
        if not healthy:
            self.circuit_breaker = {}
            healthy = self.endpoints
        
        # Try endpoints in order of health
        for endpoint in sorted(healthy, key=lambda e: e.failures):
            try:
                async with self.session.post(
                    endpoint.url, 
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    data = await response.json()
                    
                    if "error" in data:
                        raise Exception(f"RPC Error: {data['error']}")
                    
                    endpoint.failures = max(0, endpoint.failures - 1)
                    return data["result"]
                    
            except Exception as e:
                endpoint.failures += 1
                self.circuit_breaker[endpoint.url] = self.circuit_breaker.get(endpoint.url, 0) + 1
                logger.warning(f"RPC failed for {endpoint.url}: {e}")
                continue
        
        raise Exception("All RPC endpoints failed")
    
    async def get_account_info(self, pubkey: str) -> dict:
        return await self.call("getAccountInfo", [pubkey, {"encoding": "base64"}])
    
    async def get_signatures_for_address(self, address: str, limit: int = 100) -> list:
        return await self.call("getSignaturesForAddress", [address, {"limit": limit}])
    
    async def get_transaction(self, signature: str) -> dict:
        return await self.call("getTransaction", [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])

# Test
async def test_rpc():
    async with FreeRPCClient() as client:
        # Get SOL price feed account
        result = await client.get_account_info("So11111111111111111111111111111111111111112")
        print(f"RPC Test Success: Account data length = {len(result['value']['data'][0])}")

if __name__ == "__main__":
    asyncio.run(test_rpc())
EOF
```

## 5.3 Create Price Feed Collector

```bash
cat > ~/shadowhunter/src/price_feed.py << 'EOF'
"""
Free price data collection from DexScreener and Jupiter
"""
import asyncio
import aiohttp
from typing import Dict, Optional
import logging
from dataclasses import dataclass
from datetime import datetime
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TokenPrice:
    token_address: str
    price_usd: float
    volume_24h: float
    market_cap: float
    liquidity_usd: float
    timestamp: datetime

class PriceFeedCollector:
    """Collect price data from free APIs"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def fetch_dexscreener(self, token_address: str) -> Optional[TokenPrice]:
        """Fetch price from DexScreener (free, no API key)"""
        url = f"https://api.dexscreener.com/token-pairs/v1/solana/{token_address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                pairs = data.get("pairs", [])
                
                if not pairs:
                    return None
                
                # Get highest liquidity pair
                best = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
                
                return TokenPrice(
                    token_address=token_address,
                    price_usd=float(best.get("priceUsd", 0) or 0),
                    volume_24h=float(best.get("volume", {}).get("h24", 0) or 0),
                    market_cap=float(best.get("marketCap", 0) or 0),
                    liquidity_usd=float(best.get("liquidity", {}).get("usd", 0) or 0),
                    timestamp=datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"DexScreener error for {token_address}: {e}")
            return None
    
    async def fetch_jupiter(self, token_address: str) -> Optional[float]:
        """Fetch price from Jupiter (free, 600 req/min)"""
        url = f"https://api.jup.ag/price/v2?ids={token_address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                token_data = data.get("data", {}).get(token_address)
                
                if token_data:
                    return float(token_data.get("price", 0))
                return None
        except Exception as e:
            logger.error(f"Jupiter error for {token_address}: {e}")
            return None
    
    async def save_price(self, price: TokenPrice):
        """Save price to TimescaleDB"""
        query = """
            INSERT INTO token_prices (time, token_address, price_usd, volume_24h, market_cap, liquidity_usd)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        await self.db.execute(
            query,
            price.timestamp,
            price.token_address,
            price.price_usd,
            price.volume_24h,
            price.market_cap,
            price.liquidity_usd
        )
    
    async def track_token(self, token_address: str):
        """Fetch and save price for a token"""
        price = await self.fetch_dexscreener(token_address)
        if price:
            await self.save_price(price)
            logger.info(f"Tracked {token_address}: ${price.price_usd:.6f}")
            return True
        return False

# Test
async def test_price_feed():
    # Connect to database
    pool = await asyncpg.create_pool(
        "postgresql://shadowhunter:changeme@localhost:5432/shadowhunter"
    )
    
    async with PriceFeedCollector(pool) as collector:
        # Test with BONK
        success = await collector.track_token(
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        )
        print(f"Price feed test: {'SUCCESS' if success else 'FAILED'}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(test_price_feed())
EOF
```

---

# 6. PHASE 3: WALLET INTELLIGENCE

## 6.1 Create Database Connection Manager

```bash
cat > ~/shadowhunter/src/database.py << 'EOF'
"""
Database connection managers
"""
import asyncpg
from neo4j import AsyncGraphDatabase
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager

class DatabaseManager:
    """Manage all database connections"""
    
    def __init__(self):
        self.timescale_pool = None
        self.neo4j_driver = None
        self.redis_client = None
        self.mongo_client = None
    
    async def connect(self):
        """Initialize all connections"""
        # TimescaleDB
        self.timescale_pool = await asyncpg.create_pool(
            "postgresql://shadowhunter:changeme@localhost:5432/shadowhunter",
            min_size=5,
            max_size=20
        )
        
        # Neo4j
        self.neo4j_driver = AsyncGraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "changeme")
        )
        
        # Redis
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        
        # MongoDB
        self.mongo_client = AsyncIOMotorClient(
            "mongodb://admin:changeme@localhost:27017/shadowhunter"
        )
        
        # Test connections
        await self.timescale_pool.fetch("SELECT 1")
        await self.neo4j_driver.verify_connectivity()
        await self.redis_client.ping()
        
        print("✓ All databases connected")
    
    async def close(self):
        """Close all connections"""
        if self.timescale_pool:
            await self.timescale_pool.close()
        if self.neo4j_driver:
            await self.neo4j_driver.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.mongo_client:
            self.mongo_client.close()

# Global instance
db = DatabaseManager()
EOF
```

## 6.2 Create Wallet Tracker

```bash
cat > ~/shadowhunter/src/wallet_tracker.py << 'EOF'
"""
Track wallet transactions and calculate alpha scores
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from database import db
from rpc_client import FreeRPCClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalletTracker:
    """Monitor wallet activity and score performance"""
    
    def __init__(self):
        self.rpc = None
    
    async def __aenter__(self):
        self.rpc = FreeRPCClient()
        await self.rpc.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        if self.rpc:
            await self.rpc.__aexit__(*args)
    
    async def get_wallet_transactions(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Fetch recent transactions for a wallet"""
        signatures = await self.rpc.get_signatures_for_address(wallet_address, limit)
        
        transactions = []
        for sig_info in signatures:
            tx = await self.rpc.get_transaction(sig_info['signature'])
            if tx:
                transactions.append({
                    'signature': sig_info['signature'],
                    'timestamp': sig_info.get('blockTime'),
                    'transaction': tx
                })
        
        return transactions
    
    def calculate_alpha_score(self, wallet_data: Dict) -> Dict:
        """
        Calculate alpha score from wallet metrics
        
        Formula:
        - Profitability: 40% weight
        - Win rate: 25% weight
        - Hold time: 20% weight
        - Consistency: 15% weight
        """
        realized_pnl = wallet_data.get('realized_pnl_30d', 0)
        win_rate = wallet_data.get('win_rate', 0)
        avg_hold = wallet_data.get('avg_hold_time_hours', 0)
        trade_freq = wallet_data.get('trades_per_day', 0)
        
        # Calculate component scores
        pnl_score = min(realized_pnl / 10000, 1.0) * 40 if realized_pnl > 0 else 0
        win_score = win_rate * 25
        
        # Hold time sweet spot: 4-48 hours
        if 4 <= avg_hold <= 48:
            hold_score = 20
        elif avg_hold < 1:
            hold_score = 5  # Bot-like
        else:
            hold_score = 10
        
        # Consistency: 1-10 trades/day
        if 1 <= trade_freq <= 10:
            consistency_score = 15
        elif trade_freq > 50:
            consistency_score = 5  # Bot
        else:
            consistency_score = 8
        
        total_score = pnl_score + win_score + hold_score + consistency_score
        
        # Determine tier
        if total_score >= 90:
            tier = 'GOD'
        elif total_score >= 75:
            tier = 'WHALE'
        elif total_score >= 60:
            tier = 'SHARK'
        elif total_score >= 40:
            tier = 'FISH'
        else:
            tier = 'RETAIL'
        
        return {
            'alpha_score': total_score,
            'tier': tier,
            'component_scores': {
                'profitability': pnl_score,
                'win_rate': win_score,
                'hold_time': hold_score,
                'consistency': consistency_score
            }
        }
    
    async def save_wallet_score(self, wallet_address: str, score_data: Dict):
        """Save wallet score to database"""
        query = """
            INSERT INTO wallet_scores 
            (wallet_address, alpha_score, tier, realized_pnl_30d, win_rate, avg_hold_time_hours, total_trades)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (wallet_address) 
            DO UPDATE SET 
                alpha_score = EXCLUDED.alpha_score,
                tier = EXCLUDED.tier,
                updated_at = NOW()
        """
        
        await db.timescale_pool.execute(
            query,
            wallet_address,
            score_data['alpha_score'],
            score_data['tier'],
            0,  # realized_pnl_30d - would need calculation
            0,  # win_rate - would need calculation
            0,  # avg_hold_time - would need calculation
            0   # total_trades - would need calculation
        )
        
        # Also save to Neo4j for graph analysis
        async with db.neo4j_driver.session() as session:
            await session.run("""
                MERGE (w:Wallet {address: $address})
                SET w.alpha_score = $alpha_score,
                    w.tier = $tier,
                    w.updated_at = datetime()
            """, address=wallet_address, 
                alpha_score=score_data['alpha_score'],
                tier=score_data['tier'])

# Test
async def test_wallet_tracker():
    await db.connect()
    
    async with WalletTracker() as tracker:
        # Test with a known wallet
        test_wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        
        transactions = await tracker.get_wallet_transactions(test_wallet, limit=10)
        print(f"Found {len(transactions)} transactions")
        
        # Test scoring
        test_data = {
            'realized_pnl_30d': 15000,
            'win_rate': 0.65,
            'avg_hold_time_hours': 12,
            'trades_per_day': 3
        }
        score = tracker.calculate_alpha_score(test_data)
        print(f"Alpha Score: {score['alpha_score']}, Tier: {score['tier']}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(test_wallet_tracker())
EOF
```

---

Due to length, I'll continue with the remaining sections in a follow-up message. This covers the infrastructure setup and core data collection components. Should I continue with the cluster detection, telegram bot, and testing sections?