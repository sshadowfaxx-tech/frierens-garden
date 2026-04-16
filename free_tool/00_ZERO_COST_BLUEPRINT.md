# PROJECT SHADOWHUNTER: ZERO-COST EDITION
## The $0 Solana Memecoin Trading Intelligence Platform
### Complete Self-Hosted Blueprint for Personal Use

**Version:** Zero-Cost 1.0  
**Classification:** Personal Deployment Guide  
**Target Cost:** $0/month (hardware already owned)  
**Research Base:** 11,058 lines across 15 documents

---

# EXECUTIVE SUMMARY

## The $0 Promise

| Component | Commercial Cost | Zero-Cost Alternative | Savings |
|-----------|----------------|----------------------|---------|
| **Blockchain RPC** | $748/mo (Helius+QuickNode) | Public RPCs + Self-hosted | $748/mo |
| **Databases** | $500/mo (hosted) | Self-hosted (Docker) | $500/mo |
| **ML Infrastructure** | $800/mo (SageMaker) | Local GPU / Colab | $800/mo |
| **Market Data** | $1,798/mo (Birdeye+Nansen+CoinGecko) | Free APIs + On-chain | $1,798/mo |
| **Cloud Hosting** | $3,000/mo (AWS/GCP) | Old hardware / Oracle Free | $3,000/mo |
| **TOTAL** | **$6,846/mo** | **$0/mo** | **$6,846/mo** |

## What You Need (One-Time)

| Component | Minimum | Recommended | Cost |
|-----------|---------|-------------|------|
| **Hardware** | Old laptop (8GB RAM) | Desktop/Server (32GB+ RAM, RTX 3060+) | $0 (repurpose) |
| **Internet** | Standard broadband | 100+ Mbps | Already paying |
| **Storage** | 500GB free space | 2TB SSD | $0-200 |
| **TOTAL** | | | **$0-200 one-time** |

## Trade-offs at Zero Cost

| Aspect | Paid Version | Zero-Cost Version |
|--------|--------------|-------------------|
| **Latency** | <50ms p99 | <200ms p99 (acceptable for alerts) |
| **Uptime** | 99.99% | 95-99% (home power/internet) |
| **Scale** | Unlimited | 1000-5000 tokens tracked |
| **ML Training** | Continuous | Batch (nightly/weekly) |
| **Support** | 24/7 | Self-supported |

**Verdict:** For personal use, 95% of functionality at 0% of cost.

---

# 1. HARDWARE SETUP

## Option A: Repurpose Existing Hardware (FREE)

### Minimum Requirements (Light Usage)
```
CPU: 4 cores (Intel i5/AMD Ryzen 5, 6th gen+)
RAM: 16 GB DDR4
Storage: 500 GB SSD (NVMe preferred)
GPU: Optional (CPU inference acceptable)
Network: 50 Mbps down / 10 Mbps up
OS: Ubuntu 22.04 LTS Server
```

### Recommended (Full Experience)
```
CPU: 8+ cores (Intel i7/AMD Ryzen 7)
RAM: 32 GB DDR4
Storage: 2 TB NVMe SSD
GPU: RTX 3060 12GB+ (for ML inference)
Network: 100+ Mbps
OS: Ubuntu 24.04 LTS Server
```

### Setup Steps

```bash
# 1. Install Ubuntu Server (headless)
# Download: https://ubuntu.com/download/server

# 2. Enable SSH
sudo apt update && sudo apt install -y openssh-server
sudo systemctl enable ssh

# 3. Disable sleep (critical for laptops)
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

# 4. Configure static IP (optional but recommended)
sudo nano /etc/netplan/00-installer-config.yaml
```

```yaml
# /etc/netplan/00-installer-config.yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply

# 5. Install Docker
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker

# 6. Basic monitoring
sudo apt install -y htop iotop nethogs
```

## Option B: Used Enterprise Hardware ($100-300 one-time)

### Dell OptiPlex 7050 MT (Recommended)
- **Specs:** i7-7700, 32GB RAM, 512GB SSD
- **Cost:** $200-300 (eBay/Craigslist)
- **Pros:** Reliable, expandable, low power
- **Cons:** Older CPU

### HP EliteDesk 800 G3
- **Specs:** i7-6700, 16-32GB RAM
- **Cost:** $150-250
- **Similar to OptiPlex**

### Custom Whitebox Build
```
Components:
- Motherboard: Used B450/B550 ($50)
- CPU: Ryzen 5 3600 ($80 used)
- RAM: 32GB DDR4 ($60 used)
- Storage: 2TB NVMe ($100)
- PSU: 500W 80+ Bronze ($30 used)
- Case: Any ATX ($20)
Total: ~$340
```

## Option C: Oracle Cloud Free Tier (Always Free)

### What's Included (Forever Free)
```
Compute: 2x AMD VM (1/8 OCPU, 1GB RAM each)
Block Storage: 200 GB total
Object Storage: 10 GB
Network: 10 TB/month egress
Load Balancer: 1 instance
```

### Reality Check
- **Too small for full platform**
- **Good for:** RPC relay, backup monitoring, Telegram bot
- **Not suitable for:** Database, ML, heavy processing

---

# 2. INFRASTRUCTURE STACK (Docker Compose)

## Complete docker-compose.yml

```yaml
version: '3.8'

services:
  # ============================================================================
  # MESSAGING & EVENT STREAMING
  # ============================================================================
  
  nats:
    image: nats:latest
    container_name: shadowhunter-nats
    ports:
      - "4222:4222"   # Client port
      - "8222:8222"   # HTTP monitoring
    command: >
      --js 
      --store_dir /data
      --max_memory_store 1GB
      --max_file_store 10GB
    volumes:
      - nats-data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8222/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ============================================================================
  # DATABASES
  # ============================================================================
  
  # Time-Series: TimescaleDB (PostgreSQL extension)
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
      - ./init-scripts/timescale-init.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres 
      -c shared_preload_libraries=timescaledb
      -c max_connections=100
      -c shared_buffers=1GB
      -c effective_cache_size=3GB
    shm_size: 512mb
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shadowhunter"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Graph Database: Neo4j Community Edition
  neo4j:
    image: neo4j:5-community
    container_name: shadowhunter-neo4j
    ports:
      - "7474:7474"   # HTTP
      - "7687:7687"   # Bolt
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-changeme}
      - NEO4J_dbms_memory_heap_initial__size=1G
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
      - NEO4J_PLUGINS=["apoc", "gds"]
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Cache: Redis
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
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Document Store: MongoDB Community
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

  # ============================================================================
  # MONITORING
  # ============================================================================
  
  prometheus:
    image: prom/prometheus:latest
    container_name: shadowhunter-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    restart: unless-stopped

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
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
    restart: unless-stopped

  # ============================================================================
  # REVERSE PROXY
  # ============================================================================
  
  caddy:
    image: caddy:2-alpine
    container_name: shadowhunter-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config
    restart: unless-stopped

  # ============================================================================
  # ML SERVING (Optional - requires GPU)
  # ============================================================================
  
  # Uncomment if you have GPU
  # triton:
  #   image: nvcr.io/nvidia/tritonserver:24.01-py3
  #   container_name: shadowhunter-triton
  #   runtime: nvidia
  #   ports:
  #     - "8000:8000"
  #     - "8001:8001"
  #     - "8002:8002"
  #   volumes:
  #     - ./models:/models:ro
  #   command: tritonserver --model-repository=/models
  #   restart: unless-stopped

volumes:
  nats-data:
  timescale-data:
  neo4j-data:
  neo4j-logs:
  redis-data:
  mongo-data:
  prometheus-data:
  grafana-data:
  caddy-data:
  caddy-config:

networks:
  default:
    name: shadowhunter-network
```

## Deployment Commands

```bash
# 1. Create project directory
mkdir -p ~/shadowhunter/{init-scripts,config,models,data}
cd ~/shadowhunter

# 2. Save docker-compose.yml (above)
nano docker-compose.yml

# 3. Create init script for TimescaleDB
cat > init-scripts/timescale-init.sql << 'EOF'
-- Enable TimescaleDB
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
    tx_type TEXT,
    amount_sol DECIMAL(18, 8),
    amount_token DECIMAL(24, 8),
    price_usd DECIMAL(18, 8),
    tx_hash TEXT
);

SELECT create_hypertable('wallet_transactions', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_wallet_tx_wallet ON wallet_transactions (wallet_address, time DESC);
CREATE INDEX idx_wallet_tx_token ON wallet_transactions (token_address, time DESC);

-- Create hypertable for predictions
CREATE TABLE ml_predictions (
    time TIMESTAMPTZ NOT NULL,
    token_address TEXT NOT NULL,
    model_version TEXT,
    pump_probability DECIMAL(5, 4),
    confidence TEXT,
    features JSONB
);

SELECT create_hypertable('ml_predictions', 'time', chunk_time_interval => INTERVAL '1 day');
EOF

# 4. Create Prometheus config
mkdir -p config
cat > config/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'shadowhunter-services'
    static_configs:
      - targets: ['nats:8222', 'redis:6379']
EOF

# 5. Create Caddyfile
cat > config/Caddyfile << 'EOF'
{
    auto_https off
}

:80 {
    respond "ShadowHunter API"
}
EOF

# 6. Start all services
docker-compose up -d

# 7. Check status
docker-compose ps

# 8. View logs
docker-compose logs -f
```

---

# 3. FREE RPC & DATA SOURCES

## 3.1 Free Solana RPC Endpoints

### Tier 1: Primary (Best Performance)
| Provider | Endpoint | Rate Limit | Notes |
|----------|----------|------------|-------|
| **Anza** | `https://api.mainnet-beta.solana.com` | 100 req/10s | Official, most reliable |
| **Helius Free** | `https://mainnet.helius-rpc.com/?api-key=YOUR_KEY` | 1M credits/mo | Requires free signup |
| **QuickNode Free** | `https://YOUR_SUBDOMAIN.solana-mainnet.quiknode.pro/` | 10M credits trial | 31-day trial |

### Tier 2: Fallback
| Provider | Endpoint | Rate Limit | Notes |
|----------|----------|------------|-------|
| **PublicNode** | `https://solana-rpc.publicnode.com` | 50 req/sec | Community maintained |
| **BlockDaemon** | Requires signup | Varies | Enterprise-grade |
| **Alchemy Free** | Requires signup | 30M CUs/mo | Good for multi-chain |

### Tier 3: Emergency
| Provider | Endpoint | Rate Limit | Notes |
----------|------------|-------|
| **GetBlock** | `https://go.getblock.io/YOUR_TOKEN` | Varies | Signup required |
| **Chainstack** | Requires signup | Varies | Good free tier |

### RPC Client Implementation (Python)

```python
import asyncio
import random
from typing import Optional
import aiohttp
from dataclasses import dataclass

@dataclass
class RPCEndpoint:
    url: str
    weight: int = 1
    last_latency: float = 0.0
    failures: int = 0

class FreeRPCClient:
    """
    Rotates between free RPC endpoints with automatic failover
    """
    
    def __init__(self):
        self.endpoints = [
            RPCEndpoint("https://api.mainnet-beta.solana.com", weight=3),
            RPCEndpoint("https://solana-rpc.publicnode.com", weight=2),
            # Add your Helius free key endpoint here
            # RPCEndpoint("https://mainnet.helius-rpc.com/?api-key=YOUR_KEY", weight=5),
        ]
        self.session: Optional[aiohttp.ClientSession] = None
        self.circuit_breaker = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def call(self, method: str, params: list = None) -> dict:
        """
        Make RPC call with automatic failover
        """
        payload = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 1000000),
            "method": method,
            "params": params or []
        }
        
        # Sort endpoints by health score
        healthy_endpoints = [
            e for e in self.endpoints 
            if self.circuit_breaker.get(e.url, 0) < 5  # Less than 5 failures
        ]
        
        if not healthy_endpoints:
            # Reset circuit breakers if all failed
            self.circuit_breaker = {}
            healthy_endpoints = self.endpoints
        
        # Try endpoints in order of health
        for endpoint in sorted(healthy_endpoints, key=lambda e: e.failures):
            try:
                start = asyncio.get_event_loop().time()
                
                async with self.session.post(
                    endpoint.url, 
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    data = await response.json()
                    
                    # Success - update stats
                    endpoint.last_latency = asyncio.get_event_loop().time() - start
                    endpoint.failures = max(0, endpoint.failures - 1)
                    
                    if "error" in data:
                        raise Exception(f"RPC Error: {data['error']}")
                    
                    return data["result"]
                    
            except Exception as e:
                # Failure - increment counter
                endpoint.failures += 1
                self.circuit_breaker[endpoint.url] = self.circuit_breaker.get(endpoint.url, 0) + 1
                print(f"RPC failed for {endpoint.url}: {e}")
                continue
        
        raise Exception("All RPC endpoints failed")
    
    async def get_account_info(self, pubkey: str) -> dict:
        return await self.call("getAccountInfo", [pubkey, {"encoding": "base64"}])
    
    async def get_signature_statuses(self, signatures: list) -> dict:
        return await self.call("getSignatureStatuses", [signatures])
    
    async def get_recent_blockhash(self) -> dict:
        return await self.call("getRecentBlockhash")

# Usage
async def main():
    async with FreeRPCClient() as client:
        # Get account info
        result = await client.get_account_info(
            "So11111111111111111111111111111111111111112"  # Wrapped SOL
        )
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 3.2 Free Price Data Sources

### DexScreener (FREE - No API Key)
```python
import requests
import time

class DexScreenerClient:
    """
    Free price data from DexScreener
    Rate limit: ~60 req/min (observed, not documented)
    """
    
    BASE_URL = "https://api.dexscreener.com"
    
    def __init__(self):
        self.last_request = 0
        self.min_interval = 1.0  # 1 second between requests
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
    
    def get_token_pairs(self, token_address: str) -> dict:
        """Get all DEX pairs for a token"""
        self._rate_limit()
        url = f"{self.BASE_URL}/token-pairs/v1/solana/{token_address}"
        response = requests.get(url)
        return response.json()
    
    def search_pairs(self, query: str) -> dict:
        """Search for pairs by token name/symbol"""
        self._rate_limit()
        url = f"{self.BASE_URL}/latest/dex/search?q={query}"
        response = requests.get(url)
        return response.json()
    
    def get_token_price(self, token_address: str) -> float:
        """Extract best price from pairs"""
        data = self.get_token_pairs(token_address)
        pairs = data.get("pairs", [])
        
        if not pairs:
            return 0.0
        
        # Get highest liquidity pair price
        best_pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0)))
        return float(best_pair.get("priceUsd", 0))

# Usage
client = DexScreenerClient()
price = client.get_token_price("DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263")  # BONK
print(f"BONK Price: ${price}")
```

### Jupiter Price API (FREE - 600 req/min)
```python
import aiohttp
import asyncio

class JupiterPriceClient:
    """
    Free price feeds from Jupiter (Solana's leading DEX aggregator)
    Rate limit: 600 requests per minute
    """
    
    BASE_URL = "https://api.jup.ag/price/v2"
    
    async def get_prices(self, mints: list[str]) -> dict:
        """
        Get prices for multiple tokens in one request
        Batch up to 100 tokens per request for efficiency
        """
        ids_param = ",".join(mints)
        url = f"{self.BASE_URL}?ids={ids_param}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data.get("data", {})
    
    async def get_price(self, mint: str) -> float:
        """Get price for single token"""
        prices = await self.get_prices([mint])
        token_data = prices.get(mint)
        if token_data:
            return float(token_data.get("price", 0))
        return 0.0

# Usage
async def main():
    client = JupiterPriceClient()
    
    # Batch request (more efficient)
    tokens = [
        "So11111111111111111111111111111111111111112",  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    ]
    
    prices = await client.get_prices(tokens)
    for mint, data in prices.items():
        print(f"{mint}: ${data.get('price')}")

asyncio.run(main())
```

## 3.3 Free Wallet Intelligence

### DeBank (Free Tier)
```python
import requests

class DeBankClient:
    """
    DeBank Open API - Free tier
    Rate limits: Not documented, be respectful
    """
    
    BASE_URL = "https://api.debank.com"
    
    def get_user_info(self, address: str) -> dict:
        """Get user portfolio info"""
        url = f"{self.BASE_URL}/user/info?id={address}"
        response = requests.get(url)
        return response.json()
    
    def get_token_list(self, address: str, chain: str = "solana") -> dict:
        """Get token holdings"""
        url = f"{self.BASE_URL}/token/balance_list?user_addr={address}&chain={chain}"
        response = requests.get(url)
        return response.json()
    
    def get_transaction_list(self, address: str, chain: str = "solana") -> dict:
        """Get recent transactions"""
        url = f"{self.BASE_URL}/history/list?user_addr={address}&chain={chain}"
        response = requests.get(url)
        return response.json()

# Usage
client = DeBankClient()
# info = client.get_user_info("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
```

### Self-Built Wallet Heuristics
```python
class WalletHeuristics:
    """
    Analyze wallets using only free on-chain data
    """
    
    def __init__(self, rpc_client):
        self.rpc = rpc_client
    
    async def analyze_wallet(self, address: str) -> dict:
        """
        Build wallet profile from public transaction data
        """
        # Get recent transactions
        signatures = await self.rpc.call("getSignaturesForAddress", [address, {"limit": 100}])
        
        analysis = {
            "address": address,
            "tx_count_24h": 0,
            "tx_count_7d": 0,
            "unique_tokens": set(),
            "avg_trade_size_sol": 0,
            "profit_estimate": 0,
        }
        
        for sig_info in signatures:
            # Analyze each transaction
            tx = await self.rpc.call("getTransaction", [sig_info["signature"], {"encoding": "jsonParsed"}])
            # ... process transaction data
        
        return analysis
```

---

# 4. FREE ML INFRASTRUCTURE

## 4.1 Local Training (Consumer GPU)

### Setup for RTX 3060/4060/4090

```bash
# 1. Install NVIDIA drivers
sudo apt update
sudo apt install -y nvidia-driver-535

# 2. Install CUDA
wget https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda_12.3.0_545.23.06_linux.run
sudo sh cuda_12.3.0_545.23.06_linux.run --toolkit --silent

# 3. Install Python ML stack
conda create -n shadowhunter-ml python=3.10
conda activate shadowhunter-ml

# 4. Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 5. Install XGBoost, scikit-learn
pip install xgboost scikit-learn pandas numpy

# 6. Verify GPU
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}')"
```

### Training Script (Local)

```python
# train_model.py
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score
import joblib
import torch

# Check GPU
if torch.cuda.is_available():
    device = "cuda"
    print(f"Training on GPU: {torch.cuda.get_device_name(0)}")
else:
    device = "cpu"
    print("Training on CPU")

# Load data (from Dune export or self-collected)
df = pd.read_csv("historical_token_data.csv")

# Feature engineering
def engineer_features(df):
    """Create features from raw data"""
    df['volume_4d_ratio'] = df['volume_4d'] / df['volume_7d_avg']
    df['holder_growth_rate'] = df['new_holders_24h'] / df['total_holders']
    df['price_volatility'] = df['price_std_7d'] / df['price_mean_7d']
    # ... more features
    return df

df = engineer_features(df)

# Prepare features
feature_cols = [
    'volume_4d_ratio', 'volume_6d_ratio', 'holder_growth_rate',
    'smart_money_inflow', 'liquidity_to_mcap', 'price_volatility'
]
X = df[feature_cols]
y = df['is_stealth_pump']  # 1 if token did 10x+ without hype

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# Train XGBoost
model = XGBClassifier(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=10,  # Handle class imbalance
    tree_method='hist',
    device=device,  # Use GPU if available
    eval_metric='aucpr'
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    early_stopping_rounds=50,
    verbose=True
)

# Evaluate
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(f"F1 Score: {f1_score(y_test, y_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall: {recall_score(y_test, y_pred):.4f}")

# Save model
joblib.dump(model, "models/stealth_pump_xgb_v1.joblib")
print("Model saved!")
```

## 4.2 Google Colab (Free GPU)

### Colab Notebook Template

```python
# Run this in Google Colab

# 1. Check GPU allocation
!nvidia-smi

# 2. Mount Google Drive for persistent storage
from google.colab import drive
drive.mount('/content/drive')

# 3. Install packages
!pip install -q xgboost torch pandas numpy scikit-learn

# 4. Download training data (from Drive or Dune)
!cp /content/drive/MyDrive/shadowhunter/training_data.csv .

# 5. Training script (same as local)
import pandas as pd
from xgboost import XGBClassifier
# ... (same training code)

# 6. Save model back to Drive
!cp stealth_pump_model.joblib /content/drive/MyDrive/shadowhunter/models/
```

### Tips for Colab
- **Keep alive:** Run keep-alive script in browser console
- **Batch training:** Train overnight, download model in morning
- **Data:** Store datasets in Google Drive

## 4.3 Free Model Serving

### Flask API (Self-Hosted)

```python
# model_server.py
from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)

# Load model on startup
model = joblib.load("models/stealth_pump_xgb_v1.joblib")

@app.route('/predict', methods=['POST'])
def predict():
    """
    Endpoint for real-time predictions
    
    Request: {"features": [volume_ratio, holder_growth, ...]}
    Response: {"probability": 0.85, "prediction": 1}
    """
    data = request.json
    features = np.array(data['features']).reshape(1, -1)
    
    probability = model.predict_proba(features)[0][1]
    prediction = int(probability > 0.6)
    
    return jsonify({
        'probability': float(probability),
        'prediction': prediction,
        'confidence': 'high' if probability > 0.8 else 'medium' if probability > 0.6 else 'low'
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'model': 'stealth_pump_xgb_v1'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Run with Docker

```dockerfile
# Dockerfile.model
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY models/ ./models/
COPY model_server.py .

EXPOSE 5000

CMD ["python", "model_server.py"]
```

```yaml
# Add to docker-compose.yml
  model-server:
    build:
      context: .
      dockerfile: Dockerfile.model
    container_name: shadowhunter-model
    ports:
      - "5000:5000"
    volumes:
      - ./models:/app/models
    restart: unless-stopped
```

---

# 5. COMPLETE ZERO-COST ARCHITECTURE

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHADOWHUNTER ZERO-COST                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Your PC   │    │  Docker     │    │  Free APIs  │         │
│  │  (8-32GB)   │◄──►│  Compose    │◄──►│  (Jupiter,  │         │
│  │             │    │  Stack      │    │  DexScreener│         │
│  └─────────────┘    └──────┬──────┘    └─────────────┘         │
│                            │                                     │
│        ┌───────────────────┼───────────────────┐                │
│        │                   │                   │                │
│        ▼                   ▼                   ▼                │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │TimescaleDB│     │  Neo4j   │      │  Redis   │              │
│  │(Prices)  │      │(Wallets) │      │(Cache)   │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│        │                   │                   │                │
│        └───────────────────┼───────────────────┘                │
│                            │                                     │
│                            ▼                                     │
│                    ┌──────────────┐                             │
│                    │   Your App   │                             │
│                    │  (Python/JS) │                             │
│                    └──────────────┘                             │
│                            │                                     │
│                            ▼                                     │
│                    ┌──────────────┐                             │
│                    │ Telegram Bot │                             │
│                    │  (Alerts)    │                             │
│                    └──────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Hardware Tiers

### Tier 1: Minimal (Old Laptop)
```
Cost: $0
Can Handle:
- 500 tokens tracked
- 100 wallets monitored
- 1-hour delayed ML predictions (batch)
- Single user (you)

Limitations:
- No real-time streaming
- Hourly updates only
- 5-10 second query times
```

### Tier 2: Good (Desktop/Used Server)
```
Cost: $0-300 one-time
Can Handle:
- 2000+ tokens tracked
- 1000+ wallets monitored
- Real-time alerts (<30s latency)
- ML inference on GPU
- Multiple alert channels

Specs:
- 16-32GB RAM
- 4-8 cores
- RTX 3060+ (optional but recommended)
- 1TB SSD
```

### Tier 3: Excellent (Gaming PC)
```
Cost: $0 (if you already have one)
Can Handle:
- 5000+ tokens tracked
- 5000+ wallets monitored
- Sub-second alerts
- Real-time ML inference
- Full feature set

Specs:
- 32-64GB RAM
- 8+ cores
- RTX 4090 (24GB VRAM)
- 2TB NVMe
```

## Complete File Structure

```
~/shadowhunter/
├── docker-compose.yml          # All services
├── .env                        # Secrets (not in git)
├── init-scripts/
│   └── timescale-init.sql     # Database setup
├── config/
│   ├── prometheus.yml         # Monitoring config
│   ├── Caddyfile              # Reverse proxy
│   └── grafana/
│       └── dashboards/        # Pre-built dashboards
├── models/
│   └── stealth_pump_xgb_v1.joblib  # ML model
├── src/
│   ├── wallet_tracker.py      # Main application
│   ├── cluster_detector.py    # Neo4j graph analysis
│   ├── price_feed.py          # Free API aggregation
│   ├── ml_predictor.py        # Local inference
│   └── telegram_bot.py        # Alert bot
├── data/
│   └── historical/            # Local data cache
└── notebooks/
    └── model_training.ipynb   # Colab-compatible
```

## Resource Requirements Summary

| Component | CPU | RAM | Storage | Network |
|-----------|-----|-----|---------|---------|
| **TimescaleDB** | 1 core | 2GB | 50GB | Low |
| **Neo4j** | 2 cores | 4GB | 100GB | Low |
| **Redis** | 0.5 core | 1GB | 10GB | Low |
| **MongoDB** | 0.5 core | 1GB | 20GB | Low |
| **App Services** | 2 cores | 4GB | 10GB | Medium |
| **ML Inference** | 2 cores* | 4GB* | 5GB | Low |
| **TOTAL** | **6-8 cores** | **16GB** | **195GB** | **Medium** |

*GPU recommended for ML (RTX 3060+)

---

# 6. SETUP GUIDE (Step-by-Step)

## Prerequisites
- [ ] Hardware ready (old PC/laptop)
- [ ] Ubuntu Server installed
- [ ] SSH access configured
- [ ] Internet connection

## Step 1: System Preparation (15 minutes)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    git curl wget htop \
    docker.io docker-compose \
    python3 python3-pip \
    nodejs npm

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Test docker
docker run hello-world
```

## Step 2: Deploy Infrastructure (10 minutes)

```bash
# Create directory
mkdir -p ~/shadowhunter && cd ~/shadowhunter

# Download docker-compose.yml
# (Copy from Section 2 above)
nano docker-compose.yml

# Create environment file
cat > .env << 'EOF'
DB_PASSWORD=your_secure_password
NEO4J_PASSWORD=your_secure_password
MONGO_PASSWORD=your_secure_password
GRAFANA_PASSWORD=your_secure_password
EOF

# Start services
docker-compose up -d

# Check all running
docker-compose ps
```

## Step 3: Install Application (20 minutes)

```bash
# Create Python environment
python3 -m venv ~/shadowhunter/venv
source ~/shadowhunter/venv/bin/activate

# Install dependencies
pip install \
    aiohttp websockets \
    asyncpg neo4j redis pymongo \
    pandas numpy xgboost scikit-learn \
    python-telegram-bot

# Clone/copy application code
mkdir -p ~/shadowhunter/src
# (Copy Python files from blueprint)
```

## Step 4: Configure Data Sources (10 minutes)

```bash
# Create config file
mkdir -p ~/shadowhunter/config
cat > ~/shadowhunter/config/sources.json << 'EOF'
{
  "rpc_endpoints": [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com"
  ],
  "price_apis": {
    "dexscreener": "https://api.dexscreener.com",
    "jupiter": "https://api.jup.ag/price/v2"
  },
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "alert_chat_id": "YOUR_CHAT_ID"
}
EOF
```

## Step 5: Start Monitoring (5 minutes)

```bash
# Start wallet tracker
cd ~/shadowhunter
source venv/bin/activate
python src/wallet_tracker.py &

# Start price feed
python src/price_feed.py &

# Start Telegram bot
python src/telegram_bot.py &

# Check logs
tail -f logs/shadowhunter.log
```

## Step 6: First ML Training (Optional, 1-2 hours)

```bash
# Download historical data from Dune (free)
# Or collect for 1 week

# Train model
python src/train_model.py

# Model saved to models/
ls -la models/
```

---

# 7. OPERATIONS & MAINTENANCE

## Daily Operations

```bash
# Check service status
cd ~/shadowhunter
docker-compose ps

# View logs
docker-compose logs -f --tail=100

# Check disk usage
df -h
docker system df

# Backup databases
docker exec shadowhunter-timescale pg_dump -U shadowhunter shadowhunter > backup.sql
```

## Weekly Maintenance

```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean up old logs
docker system prune -f

# Retrain ML model (if needed)
python src/train_model.py

# Check alerts are working
# Send test message via Telegram bot
```

## Monitoring Commands

```bash
# Real-time resource usage
htop

# Container stats
docker stats

# Database queries
# TimescaleDB
docker exec -it shadowhunter-timescale psql -U shadowhunter

# Neo4j
docker exec -it shadowhunter-neo4j cypher-shell -u neo4j -p yourpassword
```

---

# 8. LIMITATIONS & WORKAROUNDS

## Known Limitations

| Feature | Paid Version | Zero-Cost | Workaround |
|---------|--------------|-----------|------------|
| **Uptime** | 99.99% | 95-99% | UPS for power outages |
| **Latency** | <50ms | <200ms | Acceptable for alerts |
| **Scale** | Unlimited | 1000-5000 tokens | Focus on high-quality tokens |
| **ML Training** | Real-time | Batch (nightly) | Schedule training at night |
| **Support** | 24/7 | Self | Community Discord/forums |
| **Backup** | Automated | Manual | Weekly manual backups |

## When to Upgrade

Consider paid alternatives when:
1. **You need >99% uptime** (run a validator/business)
2. **You're tracking >10,000 tokens**
3. **You need sub-50ms latency**
4. **You have team members needing access**
5. **You've outgrown your hardware**

**Migration path:** All data is in standard formats (PostgreSQL, Neo4j) — easy to migrate to hosted versions later.

---

# 9. COST COMPARISON SUMMARY

## Total Cost of Ownership (5 Years)

| Approach | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | **5-Year Total** |
|----------|--------|--------|--------|--------|--------|------------------|
| **Commercial** | $82,152 | $82,152 | $82,152 | $82,152 | $82,152 | **$410,760** |
| **Zero-Cost** | $200 | $120 | $120 | $120 | $120 | **$680** |
| **Savings** | | | | | | **$410,080** |

*Commercial: $6,846/mo × 12 months  
Zero-Cost: $200 hardware + $10/mo power × 12 months

## What You Get for $0

✅ Real-time wallet cluster detection  
✅ Stealth pump prediction (batch ML)  
✅ Risk analysis + rug detection  
✅ Telegram alerts  
✅ Web dashboard (Grafana)  
✅ 1000-5000 token tracking  
✅ Full data ownership  
✅ No subscription fees ever  

## What You Give Up

❌ 99.99% uptime guarantee  
❌ Sub-50ms latency  
❌ Unlimited scale  
❌ 24/7 support  
❌ Automatic backups  
❌ Team collaboration features  

**Verdict:** For personal use, the trade-off is overwhelmingly favorable.

---

# 10. QUICK START CHECKLIST

## Pre-Flight Checklist

- [ ] Hardware secured (old PC/laptop)
- [ ] Ubuntu Server installed
- [ ] Docker + Docker Compose installed
- [ ] SSH access working
- [ ] Internet connection stable

## Deployment Checklist

- [ ] docker-compose.yml created
- [ ] .env file configured
- [ ] Databases initialized
- [ ] All containers running (`docker-compose ps`)
- [ ] Telegram bot created (@BotFather)
- [ ] Bot token added to config

## Testing Checklist

- [ ] Price data flowing (DexScreener API test)
- [ ] RPC connections working
- [ ] Wallet transactions being recorded
- [ ] Neo4j graph queries working
- [ ] Telegram alerts received
- [ ] Grafana dashboard accessible

## Go-Live Checklist

- [ ] Start tracking 10-50 tokens (test phase)
- [ ] Verify alerts are actionable
- [ ] Check disk space usage
- [ ] Set up weekly backup reminder
- [ ] Join ShadowHunter community Discord

---

**Document Version:** Zero-Cost 1.0  
**Last Updated:** March 2026  
**Total Research:** 11,058 lines across 15 documents  
**Target:** Personal use, $0/month, full functionality

---

*The weapon is forged. Zero cost. Full control. Your edge is now truly yours.*
