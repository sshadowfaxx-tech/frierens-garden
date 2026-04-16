# Crypto Wallet Investigation & Alpha Tracking Toolkit

## Executive Summary

A comprehensive research report on specialized tools, APIs, and data sources for crypto wallet investigation and alpha tracking across 7 key categories:

1. Wallet Clustering APIs
2. On-Chain Data Providers
3. Mempool Monitoring
4. Cross-Chain Tracking
5. Flash Loan Detection
6. New Token Launch Monitoring
7. Social Sentiment Correlation

---

## 1. WALLET CLUSTERING & ENTITY IDENTIFICATION

### 1.1 Arkham Intelligence ⭐ TOP PICK
**Focus:** Entity-level wallet deanonymization and clustering

**Capabilities:**
- Ultra AI labeling engine with 500M+ wallet labels
- Multi-chain support: BTC, ETH, Solana, Avalanche, Tron, BNB Chain, and more
- Entity pages with holdings, PnL history, and counterparties
- Visualizer & Tracer for fund flow mapping
- Key Opinion Leader (KOL) tracking
- Notable achievements: Tagged all US BTC/ETH ETFs, largest BTC miners, 96% of MicroStrategy BTC exposure

**Access Methods:**
- **Web Platform:** https://intel.arkm.com (Free tier available)
- **Intel API:** Requires application/approval, higher rate limits for institutional users
- **Pricing:** Core platform free; premium plans customized for institutions

**Key APIs:**
- Entity lookup by address
- Transaction tracing across chains
- Wallet relationship mapping
- Real-time alerts (webhook supported)

---

### 1.2 Nansen
**Focus:** Smart money tracking and behavioral analytics

**Capabilities:**
- 500M+ labeled wallets
- "Smart Money" tracking (top traders, funds, institutions)
- Token God Mode (holder analysis, liquidity)
- NFT God Mode (whale tracking, floor monitoring)
- Portfolio Dashboard (cross-chain asset tracking)
- On-chain alerts for wallet movements

**Access Methods:**
- **Web Platform:** https://nansen.ai (Paid subscription)
- **Nansen API:** https://api.nansen.ai
  - Beta profiler endpoints for address labels
  - Related wallets detection
  - Counterparties analysis
  - Historical balances and transactions

**Key API Endpoints:**
```
POST /api/beta/profiler/address/labels
POST /api/v1/profiler/address/related-wallets
POST /api/v1/profiler/address/counterparties
POST /api/v1/profiler/address/historical-balances
POST /api/v1/profiler/address/transactions
```

---

### 1.3 Breadcrumbs (by Bitfury)
**Focus:** Visual transaction tracing and investigation

**Capabilities:**
- Drag-and-drop visual graph builder
- Risk scoring for addresses
- Multi-hop tracing
- Cross-chain bridge tracing
- Mixer detection (Tornado Cash, Railgun, etc.)

**Access Methods:**
- **Web Platform:** https://breadcrumbs.app
- **Pricing:** Free & Pro plans available
- Best for: Non-technical users, bloggers, investigators

---

### 1.4 Additional Wallet Clustering Tools

| Tool | Focus | Access |
|------|-------|--------|
| **Chainalysis Reactor** | Law enforcement/enterprise forensics | Enterprise licensing |
| **TRM Labs** | Risk intelligence, sanctions screening | Enterprise API |
| **Elliptic Navigator** | AML/KYT compliance | Enterprise SaaS |
| **CipherTrace** | Transaction tracing, visual analysis | Enterprise |
| **MetaSleuth** | Graphical tracing, open-source friendly | Free/Paid tiers |

---

## 2. ON-CHAIN DATA PROVIDERS

### 2.1 Dune Analytics ⭐ TOP PICK
**Focus:** SQL-based analytics and community dashboards

**Capabilities:**
- 100+ chains supported
- DuneSQL (Spark SQL-based)
- Public and private dashboards
- Real-time and historical data
- API for query execution

**Access Methods:**
- **Web Platform:** https://dune.com (Free tier available)
- **Dune API:** Credit-based execution tiers
  - Query executions and results
  - Preset endpoints (contracts, DEX, EigenLayer)
  - Free tier: 120s engine timeout

**Best For:** Protocol analytics, competitive research, community dashboards

---

### 2.2 Flipside Crypto
**Focus:** AI-powered analytics with natural language interface

**Capabilities:**
- 700M labeled wallet addresses
- 7 trillion rows of data
- FlipsideAI (natural language querying)
- ShroomDK (NFT-based SDK)
- Multi-chain integration

**Access Methods:**
- **Web Platform:** Dashboards and SDK
- **Data Access:** Now via Snowflake data shares (as of July 2025, legacy API sunset)
- **Pricing:** Freemium model

---

### 2.3 Goldsky
**Focus:** High-performance indexing and streaming

**Capabilities:**
- Subgraphs for GraphQL endpoints
- "Mirror" to stream decoded data to your own DB
- Firehose integration (3x faster indexing)
- Claims: >100k rows/s write speed
- Backfill Ethereum in ~3 hours

**Access Methods:**
- **Web Platform:** https://goldsky.com
- **Mirror & Subgraph APIs:**
  - GraphQL endpoints
  - Kafka streams
  - Webhooks

**Best For:** Real-time applications, high-frequency data needs

---

### 2.4 Additional On-Chain Data Providers

| Provider | Type | Best For | Access |
|----------|------|----------|--------|
| **Google BigQuery** | Analytics warehouse | Cross-chain joins, ML/AI training | Public datasets + paid queries |
| **The Graph** | Decentralized indexing | GraphQL workflows, dApps | Network queries (GRT) |
| **Alchemy** | Managed node + data | Transfers API, NFT data | API key, pay-as-you-go |
| **QuickNode** | Node provider | 60+ chains, NFT API v2 | API subscription |
| **Moralis** | Web3 streams | Real-time webhooks, wallet monitoring | Streams API |
| **Bitquery** | GraphQL + streaming | Real-time subscriptions (~1s), Kafka | GraphQL API |
| **Chainbase** | Pipelines + SQL | SQL transforms, fast backfills | DataCloud API |
| **Covalent (GoldRush)** | Unified API | 100+ chains, wallet/transactions/NFT | REST API |

---

## 3. MEMPOOL MONITORING

### 3.1 Blocknative ⭐ TOP PICK
**Focus:** Ethereum mempool monitoring and transaction preview

**Capabilities:**
- Real-time mempool monitoring
- Transaction preview (simulate before execution)
- MEV protection
- Gas estimation
- Cross-chain support (Ethereum, Polygon, BNB Chain, etc.)

**Access Methods:**
- **Platform:** https://blocknative.com
- **API:** Mempool data, transaction simulation
- **SDK:** JavaScript/TypeScript

---

### 3.2 Eden Network
**Focus:** MEV protection and priority transaction inclusion

**Capabilities:**
- Eden RPC (MEV protection)
- Priority block space
- Transaction bundles
- Slot auction mechanism

**Access Methods:**
- **RPC Endpoint:** Eden RPC
- **Documentation:** https://docs.edennetwork.io

---

### 3.3 Flashbots Protect
**Focus:** MEV protection and private transactions

**Capabilities:**
- Private transaction submission
- MEV protection for users
- Bundle simulation
- Flashbots Relay access

**Access Methods:**
- **RPC:** https://rpc.flashbots.net
- **Documentation:** https://docs.flashbots.net

---

### 3.4 Jito Labs (Solana)
**Focus:** Solana MEV infrastructure

**Capabilities:**
- Validator and trading tools
- MEV extraction on Solana
- Bundle simulation

**Access Methods:**
- **Website:** https://jito.wtf
- **Solana-specific:** MEV on Solana

---

## 4. CROSS-CHAIN TRACKING TOOLS

### 4.1 Range Security Cross-Chain Explorer ⭐ TOP PICK
**Focus:** Comprehensive bridge monitoring across 70+ chains

**Capabilities:**
- Monitors 14 key bridge protocols
- TVL and volume tracking
- Transaction status monitoring
- Protocol health monitoring

**Supported Protocols:**
- CCTP v1/v2 (Circle)
- IBC / IBC Eureka (Cosmos)
- Wormhole
- deBridge
- Hyperlane
- THORChain
- Axelar
- Across
- LayerZero
- Allbridge Core
- XCM (Polkadot)
- Snowbridge

**Access Methods:**
- **Explorer:** https://range.org
- **API:** Enterprise API for custom monitoring

---

### 4.2 LayerZero Scan
**Focus:** LayerZero protocol activity

**Capabilities:**
- Cross-chain message tracking
- Transaction status
- Analytics dashboard

**Access Methods:**
- **Explorer:** https://layerzeroscan.com

---

### 4.3 deBridge Explorer
**Focus:** deBridge protocol analytics

**Capabilities:**
- 25+ chains supported
- Real-time flow visualization
- Transaction tracking
- DLN (liquidity network) analytics

**Access Methods:**
- **Explorer:** https://app.debridge.finance/analytics
- **API:** RESTful APIs for quotes and execution

---

### 4.4 Wormhole Scan
**Focus:** Wormhole bridge tracking

**Capabilities:**
- Transaction verification
- Cross-chain flow analysis
- Guardian network status

**Access Methods:**
- **Explorer:** https://wormholescan.io

---

## 5. FLASH LOAN DETECTION

### 5.1 EigenPhi ⭐ TOP PICK
**Focus:** MEV and flash loan analytics

**Capabilities:**
- Flash loan transaction tracking
- MEV trend analysis
- Arbitrage scanning
- Liquidation monitoring
- Lending analytics
- Token flow analysis
- Contract risk identification

**Notable Users:**
- Etherscan (MEV labeling)
- Curve, CoW Swap, PancakeSwap
- Academic research institutions

**Access Methods:**
- **Platform:** https://eigenphi.io
- **EigenTx Visualizer:** Transaction breakdowns
- **Data:** Free access with attribution

---

### 5.2 Guardrail
**Focus:** Real-time flash loan attack prevention

**Capabilities:**
- Mempool simulation for attack detection
- Automated defense mechanisms
- Transaction blocking
- Emergency pause triggering
- Pre-built "Guards" for common attacks

**Access Methods:**
- **Platform:** https://guardrail.ai
- **Integration:** Protocol SDK
- **Pricing:** Enterprise

---

### 5.3 Amberdata DeFi Intelligence
**Focus:** Institutional DeFi analytics

**Capabilities:**
- Flash loan attack detection
- Liquidity monitoring
- Smart contract analysis
- Price oracle manipulation detection

**Access Methods:**
- **Platform:** https://amberdata.io
- **API:** DeFi Intelligence solution
- **Pricing:** Enterprise

---

### 5.4 Flashbots MEV Dashboard
**Focus:** MEV ecosystem analysis

**Capabilities:**
- MEV-Boost relay statistics
- Block builder comparison
- MEV extraction trends

**Access Methods:**
- **Dashboard:** https://transparency.flashbots.net

---

## 6. NEW TOKEN LAUNCH MONITORING

### 6.1 Pump.fun Sniper Bots / Monitors
**Focus:** Solana memecoin launch detection

**Capabilities:**
- Real-time token creation detection
- Liquidity pool monitoring
- Automated buy execution
- Contract safety checks
- Whale inflow tracking

**Tools:**
| Tool | Type | Pricing |
|------|------|---------|
| **PumpFun Sniper** | Web platform | Free |
| **Snorter Bot** | Telegram bot | 0.85% fee (SNORT holders) |
| **Zeno Sniper** | No-code bot | 0.1% per transaction |
| **Smithii Pump Fun Sniper** | Web-based | Variable |

**Access Methods:**
- **PumpFun Sniper:** https://pumpfunsniper.net
- **Snorter:** Telegram bot, https://snortertoken.com
- **Apify Monitor:** $29.99/month + usage (programmatic access)

---

### 6.2 GraphLinq AI Wallet Sniper Agents
**Focus:** Wallet-following for alpha

**Capabilities:**
- High-performing wallet tracking
- Real-time move alerts
- Telegram integration
- Multi-wallet monitoring

**Access Methods:**
- **Platform:** https://graphlinq.io
- **Integration:** Chat-triggered on-chain actions

---

### 6.3 Token Launch Aggregators

| Platform | Focus | Access |
|----------|-------|--------|
| **DexScreener** | New pair detection | Free web + API |
| **CoinMarketCap New Listings** | Exchange listings | Free API |
| **CoinGecko New Coins** | New token discovery | Free API |
| **Token Sniffer** | Rug pull detection | Web platform |
| **RugDoc** | Contract safety | Web platform |

---

## 7. SOCIAL SENTIMENT CORRELATION TOOLS

### 7.1 LunarCrush ⭐ TOP PICK
**Focus:** Social intelligence for crypto

**Capabilities:**
- Galaxy Score (aggregated sentiment)
- AltRank (alternative ranking)
- Social volume tracking
- Influencer identification
- Cross-platform aggregation (Twitter, Reddit, YouTube, TikTok)
- 1M+ social posts analyzed daily

**Access Methods:**
- **Platform:** https://lunarcrush.com
- **API:** REST API for sentiment data
- **Pricing:** Free tier available; paid from $99/month

---

### 7.2 Santiment
**Focus:** On-chain + social sentiment combined

**Capabilities:**
- Social volume and sentiment balance
- Social dominance measurement
- Trending words analysis
- Whale activity correlation
- Development activity tracking
- API for sentiment metrics

**Access Methods:**
- **Platform:** https://santiment.net
- **API:** GraphQL API
  - get_sentiment_balance()
  - get_social_volume()
  - get_social_dominance()
  - get_trending_words()
- **MCP Server:** Available for AI agents
- **Pricing:** From $49/month (limited free tier)

---

### 7.3 The TIE
**Focus:** News and social sentiment

**Capabilities:**
- News sentiment analysis
- Social media sentiment
- Proprietary sentiment metrics
- Real-time data

**Access Methods:**
- **Platform:** https://thetie.io
- **API:** Sentiment data feeds
- **Pricing:** Enterprise

---

### 7.4 Additional Sentiment Tools

| Tool | Focus | Access |
|------|-------|--------|
| **Perception** | Media intelligence (650+ sources) | From $149/month |
| **Crypto Fear & Greed Index** | Market emotion | Free |
| **CryptoMood** | News sentiment | API available |
| **IntoTheBlock** | On-chain + sentiment insights | Freemium |

---

## INTEGRATION RECOMMENDATIONS

### For Wallet Investigation Pipeline:
1. **Primary:** Arkham Intelligence (entity labeling)
2. **Secondary:** Nansen (smart money tracking)
3. **Visualization:** Breadcrumbs or MetaSleuth
4. **Cross-chain:** Range Security API

### For Alpha Signal Generation:
1. **Token Launches:** Pump.fun monitors + DexScreener
2. **Mempool:** Blocknative for early transaction signals
3. **Sentiment:** LunarCrush + Santiment combined
4. **On-chain:** Dune for custom alerting queries

### For Security/Risk Monitoring:
1. **Flash Loan Detection:** EigenPhi + Guardrail
2. **Cross-chain Flows:** Range Security + Wormhole Scan
3. **Entity Risk:** Chainalysis or TRM Labs (enterprise)

---

## PRICING SUMMARY

| Category | Free Tier | Entry Paid | Enterprise |
|----------|-----------|------------|------------|
| Wallet Clustering | Arkham (basic), Breadcrumbs | Nansen ($100+/mo) | Chainalysis, TRM Labs |
| On-Chain Data | Dune (limited), BigQuery (free storage) | Dune Pro, Flipside | Goldsky, Alchemy |
| Mempool | Flashbots Protect (free) | Blocknative | Eden Network |
| Cross-Chain | Wormhole Scan, LayerZero Scan | Range API | Custom |
| Flash Loan | EigenPhi (free with attribution) | Guardrail | Amberdata |
| Token Launches | PumpFun Sniper (free) | Apify ($30/mo) | Custom bots |
| Sentiment | Fear & Greed, LunarCrush (limited) | Santiment ($49/mo) | The TIE, Perception |

---

## API INTEGRATION QUICK REFERENCE

### Most Accessible APIs (Free/Paid):
1. **Dune API** - SQL-based, credit system
2. **LunarCrush API** - Social sentiment
3. **Santiment API** - Sentiment + on-chain
4. **Arkham API** - Entity intelligence (application required)
5. **Covalent (GoldRush)** - Unified blockchain data
6. **Alchemy/QuickNode** - Node + data APIs

### Authentication Patterns:
- Most use API keys in headers
- Some require OAuth (enterprise tools)
- Rate limits vary (free tiers typically 100-1000 req/day)

---

*Research compiled: March 2025*
*Sources: Official documentation, platform websites, industry analysis*
