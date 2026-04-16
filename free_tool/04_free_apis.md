# Free Crypto Data APIs & Market Data Alternatives

> Replace expensive tools like Birdeye ($299/mo), CoinGecko ($499/mo), and Nansen ($1,299/mo) with $0 alternatives

---

## 1. Price Data

### DexScreener API (FREE)
The best free alternative to Birdeye for DEX data across 80+ blockchains.

**Base URL:** `https://api.dexscreener.com/`

**Endpoints:**
| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /latest/dex/search` | Search token pairs | `/latest/dex/search?q=SOL/USDC` |
| `GET /latest/dex/pairs/{chain}/{pairId}` | Get specific pair | `/latest/dex/pairs/solana/...` |
| `GET /token-pairs/v1/{tokenAddress}` | Get all pairs for token | `/token-pairs/v1/solana/{address}` |

**Rate Limits:**
- **Unofficial limit:** ~60 requests/minute (not documented, community observed)
- **IP-based throttling** - Implement exponential backoff
- No API key required for public endpoints

**Workarounds for Higher Volume:**
```python
# Implement request batching and caching
import time
import requests
from functools import lru_cache

class DexScreenerClient:
    def __init__(self):
        self.base_url = "https://api.dexscreener.com"
        self.last_request = 0
        self.min_interval = 1.0  # 1 second between requests
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
    
    @lru_cache(maxsize=1000)
    def get_token_pairs(self, token_address):
        self._rate_limit()
        url = f"{self.base_url}/token-pairs/v1/solana/{token_address}"
        response = requests.get(url)
        return response.json()
```

**Features:**
- Real-time price data across 80+ chains
- Liquidity information
- Volume (24h, 6h, 1h)
- Price change percentages
- DEX information

---

### Jupiter Price API (FREE)
Solana's leading DEX aggregator provides free price feeds.

**Base URL:** `https://api.jup.ag/price/v2`

**Endpoints:**
| Endpoint | Rate Limit | Description |
|----------|------------|-------------|
| Price API | 600 req/min | Token prices vs USDC or custom quote |
| Quote API | 60 req/min | Swap quotes with route info |
| Swap API | 60 req/min | Transaction building |

**Example Usage:**
```bash
# Single token price vs USDC
curl "https://api.jup.ag/price/v2?ids=So11111111111111111111111111111111111111112"

# Multiple tokens (batch for efficiency)
curl "https://api.jup.ag/price/v2?ids=SOL,META,JUP&vsToken=USDC"

# Price vs SOL instead of USDC
curl "https://api.jup.ag/price/v2?ids=JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN&vsToken=So11111111111111111111111111111111111111112"
```

**Rate Limit Handling:**
```python
import asyncio
import aiohttp

class JupiterPriceClient:
    def __init__(self):
        self.base_url = "https://api.jup.ag/price/v2"
        self.rate_limit = 600  # per minute
        self.semaphore = asyncio.Semaphore(10)  # Concurrent requests
    
    async def get_prices(self, mints: list):
        """Batch multiple token price requests efficiently"""
        ids_param = ",".join(mints)
        url = f"{self.base_url}?ids={ids_param}"
        
        async with self.semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 429:
                        await asyncio.sleep(1)
                        return await self.get_prices(mints)
                    return await response.json()
```

**Migration Note:** `lite-api.jup.ag` is deprecated as of January 31, 2026. Migrate to new endpoints.

---

### Direct On-Chain Queries (FREE)
Query Solana RPC directly for real-time data with no rate limits (using your own node).

**Free RPC Providers:**
| Provider | Free Tier | Limitations |
|----------|-----------|-------------|
| Helius | Free tier available | Rate limited |
| QuickNode | 3M requests free | Good for testing |
| Chainstack | 3M requests free | No rate limits |
| Public RPC | Free | Unreliable, rate limited |

**Price Data from Raydium/Orca Pools:**
```python
from solana.rpc.api import Client
from solders.pubkey import Pubkey
import struct

class OnChainPriceFetcher:
    def __init__(self, rpc_url: str):
        self.client = Client(rpc_url)
    
    def get_raydium_pool_price(self, pool_address: str):
        """Fetch price directly from Raydium AMM pool"""
        pubkey = Pubkey.from_string(pool_address)
        account_info = self.client.get_account_info(pubkey)
        
        # Parse pool data (simplified)
        data = account_info.value.data
        # Raydium AMM layout parsing...
        base_reserve = struct.unpack('<Q', data[8:16])[0]
        quote_reserve = struct.unpack('<Q', data[16:24])[0]
        
        return quote_reserve / base_reserve if base_reserve > 0 else 0
```

**Cost Comparison:**
| Method | Cost | Latency | Reliability |
|--------|------|---------|-------------|
| DexScreener | $0 | ~500ms | High |
| Jupiter API | $0 | ~200ms | High |
| On-Chain | $0 (self-hosted) | ~100ms | Very High |
| Birdeye | $299/mo | ~100ms | Very High |

---

## 2. Wallet Labeling

### DeBank API (Free Tier)
Track 130+ DeFi protocols across 35+ chains with basic labeling.

**Free Tier Features:**
- Multi-chain portfolio tracking
- Basic wallet analytics
- NFT tracking
- Transaction history
- Social features ( whale watching)

**Limitations:**
- No programmatic API on free tier (web interface only)
- Advanced analytics behind $15/mo paywall
- API access priced by compute units

**Workaround - Web Scraping (for personal use):**
```python
# Use Browse AI or similar tools to extract public profile data
# No API key required for reading public wallet profiles

import requests
from bs4 import BeautifulSoup

class DeBankScraper:
    """Read public wallet data from DeBank profiles"""
    
    def get_portfolio(self, address: str):
        url = f"https://debank.com/profile/{address}"
        # Extract token holdings, total value, protocol positions
        # Note: Respect robots.txt and rate limits
```

---

### Self-Built Heuristics (FREE)
Build your own wallet labeling system using on-chain patterns.

**Label Categories to Detect:**
```python
WALLET_HEURISTICS = {
    "smart_money": {
        "description": "Profitable traders",
        "criteria": [
            "avg_trade_profit > 5%",
            "win_rate > 60%",
            "min_30d_volume > $100k"
        ]
    },
    "whale": {
        "description": "High net worth",
        "criteria": [
            "portfolio_value > $1M",
            "avg_transaction > $50k"
        ]
    },
    "insider": {
        "description": "Early token buyers",
        "criteria": [
            "first_buy_within_1h_of_launch",
            "multiple_successful_early_buys"
        ]
    },
    "bot": {
        "description": "Automated trading",
        "criteria": [
            "transaction_frequency > 100/day",
            "consistent_gas_price",
            "mev_patterns"
        ]
    }
}
```

**Implementation:**
```python
import pandas as pd
from collections import defaultdict

class WalletLabeler:
    def __init__(self):
        self.labels = defaultdict(dict)
    
    def analyze_wallet(self, address: str, transactions: list):
        """Analyze transaction history to assign labels"""
        
        # Calculate metrics
        df = pd.DataFrame(transactions)
        
        metrics = {
            'total_volume_30d': df['amount'].sum(),
            'trade_count': len(df),
            'avg_trade_size': df['amount'].mean(),
            'profitable_trades': len(df[df['pnl'] > 0]),
            'win_rate': len(df[df['pnl'] > 0]) / len(df) if len(df) > 0 else 0
        }
        
        # Apply heuristics
        labels = []
        if metrics['win_rate'] > 0.6 and metrics['total_volume_30d'] > 100000:
            labels.append("smart_money")
        if metrics['total_volume_30d'] > 1000000:
            labels.append("whale")
        if metrics['trade_count'] > 100:
            labels.append("active_trader")
            
        return {
            'address': address,
            'labels': labels,
            'metrics': metrics
        }
```

---

### Open Source Labeling Datasets

**1. Nansen's Public Labels (Reference)**
- Search for published research with labeled wallets
- Many DeFi protocols publish treasury/team wallets

**2. Etherscan Labels (Community)**
- Exchange wallets
- Contract addresses
- Token contracts

**3. Build Your Own Database:**
```sql
-- Simple schema for wallet labels
CREATE TABLE wallet_labels (
    address VARCHAR(42) PRIMARY KEY,
    chain VARCHAR(20),
    labels JSONB,
    confidence_score DECIMAL(3,2),
    source VARCHAR(50),
    first_seen TIMESTAMP,
    last_updated TIMESTAMP
);

CREATE INDEX idx_labels ON wallet_labels USING GIN (labels);
CREATE INDEX idx_chain ON wallet_labels(chain);
```

---

## 3. Token Metadata

### Solana Token List (GitHub - FREE)
Community-maintained token registry with metadata.

**Repository:** `https://github.com/solana-labs/token-list`

**Usage:**
```python
import requests

def get_token_metadata(mint_address: str):
    """Fetch token metadata from Solana Token List"""
    url = "https://raw.githubusercontent.com/solana-labs/token-list/main/src/tokens/solana.tokenlist.json"
    response = requests.get(url)
    token_list = response.json()
    
    for token in token_list['tokens']:
        if token['address'] == mint_address:
            return {
                'name': token.get('name'),
                'symbol': token.get('symbol'),
                'decimals': token.get('decimals'),
                'logoURI': token.get('logoURI'),
                'tags': token.get('tags', []),
                'extensions': token.get('extensions', {})
            }
    return None
```

**Note:** Token List is being deprecated in favor of Metaplex metadata.

---

### Metaplex Metadata (On-Chain - FREE)
Read token metadata directly from Solana blockchain.

**Implementation:**
```python
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from metaplex.metadata import get_metadata

class MetaplexMetadataFetcher:
    """Fetch token metadata from Metaplex on-chain"""
    
    METADATA_PROGRAM_ID = Pubkey.from_string(
        "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
    )
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.client = Client(rpc_url)
    
    def get_metadata_pda(self, mint: Pubkey):
        """Derive metadata PDA for mint"""
        seeds = [
            b"metadata",
            bytes(self.METADATA_PROGRAM_ID),
            bytes(mint)
        ]
        pda, _ = Pubkey.find_program_address(seeds, self.METADATA_PROGRAM_ID)
        return pda
    
    def fetch_metadata(self, mint_address: str):
        """Fetch and parse token metadata"""
        mint = Pubkey.from_string(mint_address)
        metadata_pda = self.get_metadata_pda(mint)
        
        account_info = self.client.get_account_info(metadata_pda)
        if not account_info.value:
            return None
            
        # Parse metadata account data
        data = account_info.value.data
        
        # Skip discriminator (1 byte)
        # Parse: name, symbol, uri, seller_fee_basis_points, etc.
        # Use metaplex-python library for full parsing
        
        return {
            'mint': mint_address,
            'metadata_account': str(metadata_pda),
            'data': data.hex()
        }
```

**Using Metaplex Python SDK:**
```bash
pip install metaplex-python
```

```python
from metaplex.metadata import get_metadata

metadata = get_metadata(
    client=client,
    mint_key="JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
)

print(metadata.data.name)      # "Jupiter"
print(metadata.data.symbol)    # "JUP"
print(metadata.data.uri)       # Off-chain JSON metadata URL
```

---

### Dune Analytics Token Tables (FREE)
Access curated token metadata via SQL queries.

**Solana Token Metadata Table:**
```sql
-- Query token metadata from Dune
SELECT 
    token_mint_address,
    symbol,
    name,
    decimals,
    created_at
FROM tokens_solana.fungible
WHERE symbol = 'USDC'
   OR token_mint_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
```

**Rate Limits:** 40 requests/minute on free tier

---

## 4. Social Data

### LunarCrush (Free Tier)
Social sentiment analysis for 4,000+ crypto assets.

**Free Tier Features:**
- Basic market insights
- Limited social data
- AltRank access
- Galaxy Score (limited)

**Pricing:**
- Free: Basic features
- Pro: $9.99/mo (advanced sentiment, custom alerts)
- API: Custom pricing (used to be pay-as-you-go from $1/day)

**Alternative - LunarCrush Discover (Free):**
```python
# Web scraping approach for public data
import requests

def get_social_sentiment(coin_symbol: str):
    """Scrape public sentiment data from LunarCrush pages"""
    url = f"https://lunarcrush.com/discover/{coin_symbol}"
    # Parse social metrics from public pages
```

---

### Free Twitter Scrapers

**1. Nitter (Self-Hosted - FREE)**
Privacy-focused Twitter front-end that can be scraped.

```python
# Using ntscraper library
from ntscraper import Nitter

scraper = Nitter()

# Get tweets from user
tweets = scraper.get_tweets("saylor", mode='user', number=50)

# Search by hashtag
btc_tweets = scraper.get_tweets("bitcoin", mode='hashtag', number=100)

# Get profile info
profile = scraper.get_profile_info("saylor")
```

**Limitations:**
- ~800 tweets max per user
- No trends data
- Instance reliability varies
- Twitter actively blocks scrapers

**2. twitter-api.io (Free Tier)**
```python
import requests

API_KEY = "your_key"

def get_user_tweets(username: str):
    url = f"https://api.twitterapi.io/twitter/user/last_tweets"
    headers = {"X-API-Key": API_KEY}
    params = {"username": username}
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()
```

**3. RSS Feeds (Nitter):**
```
https://nitter.net/{username}/rss
```

---

### Telegram Bot API (FREE)
Build custom crypto alert bots for free.

**Rate Limits:**
- 30 messages/second to different users
- 20 messages/minute to same group
- 1 message/second to same user

**Example Price Alert Bot:**
```python
import asyncio
from telegram import Bot
import aiohttp

class CryptoAlertBot:
    def __init__(self, token: str):
        self.bot = Bot(token)
        self.alerts = {}
    
    async def check_price(self, symbol: str, target_price: float, chat_id: int):
        """Check if price target is hit"""
        async with aiohttp.ClientSession() as session:
            url = f"https://api.jup.ag/price/v2?ids={symbol}"
            async with session.get(url) as response:
                data = await response.json()
                price = float(data['data'][symbol]['price'])
                
                if price >= target_price:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚀 {symbol} hit ${price}! Target: ${target_price}"
                    )
                    return True
                return False
```

**Free Alert Services:**
- **CryptoCurrencyAlerting.com** - Up to 300 alerts, Telegram/Discord webhooks
- **CoinMarketCap Alerts** - Free price notifications
- **DeFiPulse** - Protocol-specific alerts

---

## 5. On-Chain Analytics

### Dune Analytics (Free Tier)
Industry-standard blockchain data platform with SQL interface.

**Free Tier Limits:**
| Feature | Limit |
|---------|-------|
| Queries | 2,500 credits/month |
| API Requests | 40 req/min (high limit), 15 req/min (low limit) |
| Private Queries | 10 max |
| Concurrent Queries | 1 |
| Timeout | 2 minutes |

**Pricing:**
- Free: $0 - Basic access
- Plus: $349/mo - 25,000 credits, 200 req/min
- Enterprise: Custom

**Workarounds:**
```python
# Cache query results to reduce API calls
import hashlib
import json
from functools import wraps

def cached_query(ttl_hours=24):
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = hashlib.md5(
                json.dumps((args, kwargs), sort_keys=True).encode()
            ).hexdigest()
            
            # Check cache
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_hours * 3600:
                    return result
            
            # Execute query
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator
```

**Essential Free Dashboards:**
- Solana DEX Volume
- Token Transfer Analytics
- NFT Market Data
- Wallet Clustering

---

### Flipside Crypto (Free Tier)
Alternative to Dune with ShroomDK API.

**Free Tier:**
- Daily query credits
- Community SQL queries
- API access via ShroomDK

**Rate Limits:**
- Query execution: Based on warehouse-seconds
- API: Rate limited but generous for free tier
- Cached results: Available for 1-10 minutes (configurable)

**Usage:**
```python
from shroomdk import ShroomDK

sdk = ShroomDK("your_api_key")

sql = """
SELECT 
    block_timestamp,
    tx_id,
    sender,
    amount
FROM solana.transactions
WHERE block_timestamp >= CURRENT_DATE - 7
LIMIT 1000
"""

query_result = sdk.query(sql)
df = query_result.dataframe()
```

**ShroomDK Features:**
- Auto-pagination (up to 1GB data)
- Query result caching
- Cancel long-running queries

---

### Self-Built Dashboards (FREE)
Build your own analytics using open-source tools.

**Stack:**
```yaml
Data Collection:
  - Python scripts with async RPC calls
  - Web3.py / solana-py for on-chain data
  - Apache Kafka for streaming (optional)

Storage:
  - PostgreSQL with TimescaleDB extension
  - ClickHouse for analytics
  - Parquet files for cold storage

Visualization:
  - Grafana (open source)
  - Metabase (open source)
  - Apache Superset (open source)
```

**Example Pipeline:**
```python
# async_collector.py
import asyncio
from solana.rpc.async_api import AsyncClient

class SolanaDataCollector:
    def __init__(self, rpc_url: str, db_connection):
        self.client = AsyncClient(rpc_url)
        self.db = db_connection
    
    async def stream_transactions(self, program_id: str):
        """Stream transactions for a specific program"""
        # Use logsSubscribe or signatureSubscribe
        pass
    
    async def batch_save(self, transactions: list):
        """Batch insert to database"""
        query = """
            INSERT INTO transactions (signature, block_time, data)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
        """
        await self.db.executemany(query, transactions)
```

---

## 6. MEV Data

### Jito Bundles (Pay-Per-Use, No Subscription)
Solana's dominant MEV infrastructure - pay only tips, no monthly fee.

**How It Works:**
1. Submit bundle of up to 5 transactions
2. Include tip in last transaction (min 1,000 lamports ~ $0.0001)
3. Jito relays bundle to validators (92%+ of stake run Jito client)
4. Bundles execute atomically (all or nothing)

**Cost Structure:**
| Component | Cost |
|-----------|------|
| API Access | FREE |
| Bundle Submission | FREE |
| Validator Tip | Variable (min 0.00001 SOL) |
| Jito Fee | FREE |

**API Endpoints:**
```bash
# Get tip accounts
curl https://mainnet.block-engine.jito.wtf/api/v1/bundles/tip_accounts

# Send bundle
curl -X POST https://mainnet.block-engine.jito.wtf/api/v1/bundles \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "sendBundle",
    "params": [["base64_encoded_tx1", "base64_encoded_tx2"]]
  }'
```

**Python Implementation:**
```python
import json
import base64
from solders.transaction import Transaction

class JitoBundleClient:
    BLOCK_ENGINE_URL = "https://mainnet.block-engine.jito.wtf"
    
    def __init__(self):
        self.tip_accounts = self._get_tip_accounts()
    
    def _get_tip_accounts(self):
        response = requests.get(f"{self.BLOCK_ENGINE_URL}/api/v1/bundles/tip_accounts")
        return response.json()
    
    def create_tip_instruction(self, tip_amount_lamports: int):
        """Create SOL transfer to Jito tip account"""
        from solders.system_program import TransferParams, transfer
        
        tip_account = Pubkey.from_string(self.tip_accounts[0])
        
        return transfer(
            TransferParams(
                from_pubkey=payer.pubkey(),
                to_pubkey=tip_account,
                lamports=tip_amount_lamports
            )
        )
    
    async def send_bundle(self, transactions: list):
        """Send bundle to Jito block engine"""
        encoded_txs = [
            base64.b64encode(tx.serialize()).decode()
            for tx in transactions
        ]
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendBundle",
            "params": [encoded_txs]
        }
        
        response = requests.post(
            f"{self.BLOCK_ENGINE_URL}/api/v1/bundles",
            json=payload
        )
        return response.json()
```

---

### sandwich.me (FREE)
Track and analyze MEV activities on Solana.

**Features:**
- Sandwich attack tracking
- Arbitrage analysis
- Validator behavior metrics
- Live MEV statistics

**Data Available:**
- $370M-$500M extracted by sandwich bots (16-month period)
- Real-time sandwich attack detection
- Validator "sandwich rate" metrics
- Historical MEV trends

**API Access:**
- Web interface: FREE
- API: Planned (check website for updates)

**Key Metrics from sandwich.me:**
- 8.5 billion trades analyzed
- $1 trillion DEX volume tracked
- 30-60% sandwich rate on malicious validators
- Wide/blind sandwiching increased from 1% to 30%

---

## Summary: Cost Comparison

| Data Type | Paid Solution | Cost | Free Alternative | Savings |
|-----------|---------------|------|------------------|---------|
| Price Data | Birdeye | $299/mo | DexScreener + Jupiter | $299/mo |
| Price Data | CoinGecko | $499/mo | On-Chain Queries | $499/mo |
| Wallet Labels | Nansen | $1,299/mo | DeBank + Heuristics | $1,299/mo |
| Token Metadata | CoinMarketCap | $$$ | Metaplex On-Chain | 100% |
| Social Data | LunarCrush Pro | $72/mo | Nitter + Telegram | $72/mo |
| Analytics | Dune Plus | $349/mo | Dune Free + Flipside | $349/mo |
| MEV Data | Jito Subscription | N/A | Jito Tips Only | ~100% |
| **TOTAL** | | **~$2,500/mo** | | **~$2,500/mo** |

---

## Building Self-Sufficient Data Pipelines

### Architecture Pattern
```
┌─────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                    │
├─────────────────────────────────────────────────────────────┤
│  DexScreener API  │  Jupiter API  │  Solana RPC  │  Nitter  │
└───────────────────┴───────────────┴──────────────┴──────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CACHE & STORAGE LAYER                    │
├─────────────────────────────────────────────────────────────┤
│  Redis (hot cache)  │  PostgreSQL  │  Parquet (cold storage) │
└─────────────────────┴──────────────┴────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                         │
├─────────────────────────────────────────────────────────────┤
│  Wallet Labeling  │  Price Aggregation  │  Sentiment Analysis│
└───────────────────┴─────────────────────┴───────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
├─────────────────────────────────────────────────────────────┤
│  Grafana Dashboard  │  Telegram Alerts  │  Trading Bot       │
└─────────────────────┴───────────────────┴───────────────────┘
```

### Rate Limit Management
```python
import asyncio
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self):
        self.calls = defaultdict(list)
    
    async def acquire(self, api_name: str, max_calls: int, window_seconds: int):
        now = time.time()
        
        # Remove old calls outside window
        self.calls[api_name] = [
            t for t in self.calls[api_name]
            if now - t < window_seconds
        ]
        
        # Check if we're at limit
        if len(self.calls[api_name]) >= max_calls:
            sleep_time = window_seconds - (now - self.calls[api_name][0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.calls[api_name].append(now)

# Usage
limiter = RateLimiter()

async def fetch_with_limit():
    await limiter.acquire("dexscreener", max_calls=60, window_seconds=60)
    return requests.get("https://api.dexscreener.com/...")
```

### Fallback Strategy
```python
class PriceDataProvider:
    """Multi-source price provider with fallback"""
    
    SOURCES = [
        ("jupiter", JupiterPriceClient(), 600),
        ("dexscreener", DexScreenerClient(), 60),
        ("onchain", OnChainProvider(), None)  # Self-hosted, no limit
    ]
    
    async def get_price(self, mint: str):
        for name, client, limit in self.SOURCES:
            try:
                if limit:
                    await self.rate_limiter.acquire(name, limit, 60)
                return await client.get_price(mint)
            except Exception as e:
                logger.warning(f"{name} failed: {e}, trying next...")
                continue
        
        raise Exception("All price sources failed")
```

---

## Quick Start Scripts

### 1. Multi-Source Price Tracker
```python
#!/usr/bin/env python3
"""
Free multi-source price tracker
Replaces: CoinGecko Pro ($499/mo)
"""
import asyncio
import aiohttp

class FreePriceTracker:
    async def get_price(self, mint: str):
        # Try Jupiter first (600 req/min)
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.jup.ag/price/v2?ids={mint}"
                async with session.get(url) as resp:
                    data = await resp.json()
                    return float(data['data'][mint]['price'])
        except:
            pass
        
        # Fallback to DexScreener
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.dexscreener.com/token-pairs/v1/solana/{mint}"
                async with session.get(url) as resp:
                    data = await resp.json()
                    return float(data[0]['priceUsd'])
        except:
            pass
        
        return None

# Usage
async def main():
    tracker = FreePriceTracker()
    price = await tracker.get_price("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
    print(f"JUP Price: ${price}")

asyncio.run(main())
```

### 2. Whale Wallet Monitor
```python
#!/usr/bin/env python3
"""
Free whale wallet monitoring
Replaces: Nansen Smart Money ($1,299/mo)
"""
from solana.rpc.api import Client

class WhaleMonitor:
    def __init__(self, rpc_url: str):
        self.client = Client(rpc_url)
        self.wallets = set()
    
    def add_wallet(self, address: str, label: str):
        self.wallets.add((address, label))
    
    def monitor_transactions(self, callback):
        """Monitor whale wallet transactions"""
        for address, label in self.wallets:
            sigs = self.client.get_signatures_for_address(
                address,
                limit=10
            )
            
            for sig in sigs.value:
                tx = self.client.get_transaction(sig.signature)
                callback(label, address, tx)

# Usage
monitor = WhaleMonitor("https://api.mainnet-beta.solana.com")
monitor.add_wallet("7n...", "Smart Money Wallet 1")
monitor.add_wallet("9x...", "Whale Wallet 2")
```

---

## Resources & Links

### APIs
- **DexScreener:** https://docs.dexscreener.com/
- **Jupiter:** https://station.jup.ag/docs/apis/
- **Jito:** https://docs.jito.wtf/
- **Dune:** https://docs.dune.com/
- **Flipside:** https://docs.flipsidecrypto.com/
- **Telegram Bot API:** https://core.telegram.org/bots/api

### GitHub Repositories
- **Solana Token List:** https://github.com/solana-labs/token-list
- **Metaplex:** https://github.com/metaplex-foundation/metaplex
- **Nitter Scraper:** https://github.com/zedeus/nitter

### Community Dashboards
- **sandwich.me:** https://sandwich.me
- **LunarCrush:** https://lunarcrush.com
- **DeBank:** https://debank.com

---

*Last Updated: March 2026*
*Maintained by: OpenClaw Community*
