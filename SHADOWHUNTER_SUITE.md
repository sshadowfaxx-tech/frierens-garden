# ShadowHunter Trading Suite
## Professional Solana Memecoin Intelligence Platform

---

# 🎯 ShadowHunter Tracker v2.0
### Real-Time Wallet Intelligence & Cluster Detection System

**ShadowHunter Tracker** is a production-grade Solana wallet monitoring system designed for serious memecoin traders. Track 40+ wallets simultaneously with sub-second latency, intelligent clustering, and comprehensive performance analytics.

---

## Core Capabilities

### 📡 Real-Time Transaction Monitoring
- **Zero-Latency Detection**: Monitors 40+ wallets with 5-second refresh cycles
- **Multi-RPC Failover**: Uses free public Solana RPC endpoints with automatic fallback to premium Helius API when needed
- **30-Day Transaction Deduplication**: Redis-backed cache prevents duplicate alerts
- **Post-Script Filtering**: Only processes transactions occurring after startup (no historical spam)

### 🧠 Intelligent Cluster Detection
Automatically detects when multiple tracked wallets buy the same token:

- **Dynamic Clustering**: Groups wallets by token, tracks aggregate positions
- **Live Position Tracking**: PostgreSQL-backed position management with cost basis
- **Weighted Average Entry MC**: Calculates true average entry market cap across multiple buys
- **Hold Percentage Analysis**: Shows what % of position each wallet still holds
- **VIP Channel Alerts**: Separate high-priority channel for cluster formations

**Cluster Alert Features:**
```
🚨 WALLET CLUSTER UPDATE 🚨

TOKEN (Name)
Market Cap: $1.5M | Total SOL in Cluster: 45.2 SOL
Triggered by: WalletName (BUY)

6 Total Wallets | 4 Holding | 2 Sold

🏆 Wallet1 | 💎 HOLDING (75% held)
  💰 5.25 SOL | ⏱ 2h 📍$1.2M
✅ Wallet2 | 💎 HOLDING (100% held)
  💰 3.8 SOL | ⏱ 5m 📍$800K
...
```

### 📊 Performance Intelligence System
Every wallet is continuously scored based on live trading performance:

**Confidence Score Algorithm:**
- 60% weight on Winrate (wins / total trades)
- 40% weight on Average ROI (capped at 100% for normalization)
- Score range: 0-100

**Visual Confidence Indicators:**
| Emoji | Tier | Score Range | Description |
|-------|------|-------------|-------------|
| 🏆 | Elite | 80-100 | Proven consistent profitability |
| ✅ | Strong | 60-79 | Solid track record |
| ⚠️ | Moderate | 40-59 | Mixed results, use caution |
| 🔴 | Weak | 20-39 | Poor performance |
| 💀 | Poor | 0-19 | Significant losses |
| 🔍 | New | <3 trades | Insufficient data |

### 💬 Smart Alert Format

**Buy/Sell Alerts Include:**
- Confidence emoji replacing generic 👤 indicator
- Winrate, Avg ROI, Total PnL, Trade count
- Current Market Cap (fresh from DexScreener)
- Average Entry Market Cap (weighted across all buys)
- Token amount and SOL value
- Hold percentage for position tracking
- Photon & DexScreener links for instant trading

```
🟢 BUY ALERT
🏆 Wallet: ProTrader
`7xR9...k3mP`

📈 Winrate: 75.0% | Avg ROI: +120.5%
💰 Total PnL: +50.25 SOL (12 trades)

TOKEN (Token Name)
`EPjF...TDt1v`

Current MC: $1.5M
📍 Avg Entry: $800K
💰 Buy: 1.5 SOL
🪙 Tokens: 125,000.00
📊 Hold: 100%

[📊 DexScreener] | [⚡ Photon]
[🔗 Solscan]
```

### 🗄️ Robust Data Architecture

**PostgreSQL (TimescaleDB) Tables:**
- `wallet_positions`: Live position tracking with cost basis, entry MC, hold %
- `wallet_performance`: PnL, winrate, trade history per wallet
- Automatic cleanup of removed wallets on startup

**Redis Caching:**
- Token info (5 min TTL) with DexScreener fallback
- Transaction deduplication (30 day TTL)
- Performance data caching for sub-millisecond alert generation

### 🔄 Database Resilience
- **Connection Pooling**: 10 concurrent connections with semaphore control
- **Exponential Backoff Retry**: 5 attempts with 0.5s → 8s delays
- **Automatic Reconnection**: Handles PostgreSQL "Too many connections" gracefully

### 📈 Telegram Command Interface

| Command | Function |
|---------|----------|
| `/start` | Bot status confirmation |
| `/status` | System health check |
| `/performance` | Live wallet leaderboard with aggregated stats |

**Performance Dashboard:**
- Top 15 wallets by PnL
- Individual: Winrate, Avg ROI, Total PnL, Trade count
- Summary: Total PnL, Total Trades, Overall Winrate with color coding

---

## Technical Specifications

**Concurrency:**
- 40+ wallet monitoring with `asyncio.gather()`
- 10 concurrent DB operations (semaphore controlled)
- 50 TCP connections per host (aiohttp connector)

**Rate Limiting:**
- 5-second check intervals (configurable)
- 3-second RPC timeouts
- Automatic RPC rotation on failure

**Resource Efficiency:**
- ~8-16 req/sec baseline (public RPC friendly)
- Peak: 49 req/sec (extreme activity, still within limits)
- Docker-ready with health checks

---

# 🔭 Himmel Scanner
### Token Holder Intelligence & Cross-Wallet Analysis

**Himmel Scanner** is a deep-dive token analysis tool for identifying smart money concentration and mutual holdings across whale wallets. Built for pre-trade due diligence and alpha discovery.

---

## Core Capabilities

### 📊 `/top` Command - Holder Deep Dive
Analyzes top 10 token holders (excluding LP programs and exchanges):

**Features:**
- Birdeye API integration for net worth calculation
- SOL balance per holder
- Top 3 holdings per wallet (>$100 USD, excluding stables/SOL/scanned token)
- Rate-limited requests (1.2s delay) with exponential backoff
- LP/Exchange filtering via external config files

**Output Format:**
```
Top 10 Holders for TOKEN

1. Wallet1... | 💰 $450K net worth | 1250 SOL
   Top: TOKEN-A ($50K), TOKEN-B ($30K), TOKEN-C ($20K)

2. Wallet2... | 💰 $280K net worth | 890 SOL
   Top: TOKEN-D ($45K), TOKEN-E ($25K)
...
```

### 🔗 `/cross` Command - Mutual Holdings Analysis
Revolutionary cross-wallet token discovery:

**How It Works:**
1. Fetches top 20 holders (filtered)
2. Queries each wallet's token accounts via Helius
3. Identifies tokens held by 3+ wallets (consensus signal)
4. Excludes: Unnamed tokens (???), balances < 1 unit, scanned token

**Output Format:**
```
🔍 MUTUAL HOLDINGS ANALYSIS
Analyzed 20 top holders
Found 5 tokens held by 3+ wallets

1. TOKEN-X (???)
   Held by: Wallet1..., Wallet3..., Wallet7...

2. TOKEN-Y (SYMBOL)
   Held by: Wallet2..., Wallet5..., Wallet9..., Wallet12...
...
```

### 🛡️ Smart Filtering System

**LP Program Exclusion (lpools.txt):**
- Raydium, Orca, Meteora, and 10+ other DEX programs
- Configurable via external file

**Exchange Wallet Exclusion (exchanges.txt):**
- Binance, Coinbase, Kraken, etc.
- Prevents institutional wash trading interference

**Token Quality Filters:**
- Minimum $100 USD holding value
- Excludes stables (USDC, USDT, USDS)
- Excludes SOL native token
- Excludes unnamed/unknown tokens

---

## Technical Architecture

**Multi-Source Data Integration:**
- **Birdeye API**: Net worth, top holdings, price data
- **Helius RPC**: Token account queries (`getTokenAccountsByOwner`)
- **DexScreener**: Symbol resolution with caching

**Rate Limiting & Reliability:**
- 1.2s delay between Birdeye calls
- 100ms delay between Helius calls
- Exponential backoff with 3 retry attempts
- Message splitting for Telegram 4000 char limit

**Performance:**
- `/top`: ~5-10 API calls (completes in 8-12 seconds)
- `/cross`: ~20+ API calls (completes in 25-35 seconds)
- Caching reduces repeated calls by 80%

---

## Ideal Use Cases

### ShadowHunter Tracker
✅ Live trading signal generation  
✅ Copy-trading high-confidence wallets  
✅ Cluster-based momentum detection  
✅ Wallet performance auditing  
✅ Automated alert routing to Discord/Telegram

### Himmel Scanner
✅ Pre-trade due diligence  
✅ Identifying smart money concentration  
✅ Finding mutual holdings (consensus plays)  
✅ Whale wallet vetting  
✅ Alpha discovery through holder overlap

---

## Competitive Advantages

| Feature | ShadowHunter | Typical Competitor |
|---------|--------------|-------------------|
| Wallet Capacity | 40+ concurrent | 10-20 typical |
| Cluster Detection | Real-time, weighted entry MC | Basic grouping |
| Confidence Scoring | Algorithmic (winrate + ROI) | Manual/subjective |
| RPC Costs | Free public + optional premium | Premium required |
| Alert Latency | <5 seconds | 30-60 seconds |
| Position Tracking | Cost basis, hold %, avg entry | Basic buys/sells |
| Data Persistence | PostgreSQL + Redis | In-memory only |
| Cross-Wallet Analysis | Built-in (`/cross`) | Not available |

---

## System Requirements

**ShadowHunter Tracker:**
- Docker + Docker Compose
- 2GB RAM minimum
- TimescaleDB (PostgreSQL extension)
- Redis 7+
- Telegram Bot Token

**Himmel Scanner:**
- Python 3.9+
- Helius API key (10M free credits/month)
- Birdeye API key (free tier sufficient)
- Telegram Bot Token

---

## Deployment Options

**Local Development:**
```bash
docker-compose up -d  # Tracker
python himmel.py      # Scanner
```

**Production VPS (AWS/DigitalOcean):**
- Recommended: 2 vCPU, 4GB RAM
- Ubuntu 22.04 LTS
- Automated systemd services

---

## Pricing Philosophy

**Zero-Cost Operation Possible:**
- Public Solana RPCs: Unlimited, free
- Helius: 10M credits/month (free tier)
- Birdeye: Free tier sufficient for moderate usage
- DexScreener: Unlimited, free

**Premium Upgrades Available:**
- Helius paid tiers for higher throughput
- Birdeye paid tiers for faster rate limits
- Dedicated RPC nodes for institutional use

---

## Support & Community

- **Documentation**: In-code comments + README
- **Configuration**: Environment variables + external .txt files
- **Monitoring**: Built-in logging + Telegram status commands
- **Updates**: Modular design for easy feature additions

---

## Conclusion

The **ShadowHunter Trading Suite** represents the convergence of institutional-grade monitoring capabilities with retail-friendly deployment. Whether you're tracking 5 alpha wallets or 50, the system scales effortlessly while providing actionable intelligence through algorithmic confidence scoring and real-time cluster detection.

**ShadowHunter Tracker** excels at execution-speed alerts and position management.  
**Himmel Scanner** dominates pre-trade research and smart money identification.

Together, they form a complete memecoin trading intelligence platform that rivals tools costing thousands of dollars—available to run entirely on free infrastructure.

---

*Built for traders who demand precision, speed, and actionable data.*

**Ready to hunt?** 🎯
