# API Integrations & Data Sources Architecture

## Executive Summary

This document outlines the comprehensive API integrations and data sources architecture for the ultimate Solana trading tool. Each integration is categorized by priority (Critical vs Nice-to-Have), with detailed specifications for rate limits, costs, data freshness, fallback strategies, and data normalization approaches.

---

## 1. Blockchain Data APIs

### 1.1 Helius (Solana Specialist)

| Attribute | Details |
|-----------|---------|
| **Type** | RPC Provider + Enhanced APIs |
| **Priority** | **CRITICAL** |
| **Free Tier** | 1M credits/month, 10 RPS |
| **Paid Tiers** | Developer ($49/mo, 10M credits, 50 RPS), Business ($499/mo, 100M credits, 200 RPS), Professional ($999/mo, 200M credits, 500 RPS) |
| **Rate Limits** | 10-500 RPS depending on tier; DAS API: 2-100 RPS |
| **Latency** | ~100-140ms average global response time |
| **Data Freshness** | Real-time via WebSockets; Enhanced WebSockets on Pro+ |
| **Key Features** | Staked RPC routing, Transaction parsing API, Webhooks, DAS API, LaserStream gRPC (Pro+) |
| **Cost Per Request** | Credit-based: ~1-10 credits per request depending on method |

**Fallback Strategy:**
- Primary: Helius Business tier for production
- Fallback 1: Helius Developer tier (lower RPS but same data)
- Fallback 2: QuickNode or Alchemy RPC

**Data Normalization:**
- Standardize transaction parsing through Helius Enhanced APIs
- Convert credit usage to per-request metrics for cost tracking
- Normalize WebSocket events to internal event schema

---

### 1.2 QuickNode

| Attribute | Details |
|-----------|---------|
| **Type** | Multi-chain RPC Provider |
| **Priority** | **CRITICAL** |
| **Free Tier** | 10M credits (31-day trial only) |
| **Paid Tiers** | $49-$999+/month; Flat Rate RPS available |
| **Rate Limits** | 50-500 RPS depending on tier |
| **Latency** | ~60-70ms average (industry-leading) |
| **Data Freshness** | Real-time via Streams API and WebSockets |
| **Key Features** | Multi-region endpoints, MEV protection add-on, gRPC support, Transaction Fastlane |
| **Method Multipliers** | 20x-120x per method (expensive for heavy calls) |

**Fallback Strategy:**
- Use as secondary RPC provider
- Geographic load balancing between Helius and QuickNode
- Method routing: light calls to QuickNode, heavy parsing to Helius

**Data Normalization:**
- Map QuickNode credit system to standardized cost metrics
- Normalize multi-region response times

---

### 1.3 Alchemy

| Attribute | Details |
|-----------|---------|
| **Type** | Multi-chain Developer Platform |
| **Priority** | **NICE-TO-HAVE** (primary for EVM, secondary for Solana) |
| **Free Tier** | 30M CUs/month (~1.2M-1.8M requests), 25 RPS |
| **Paid Tiers** | PAYG: $0.45/M CUs (up to 300M), then $0.40/M; Enterprise custom |
| **Rate Limits** | 25-300 RPS depending on tier |
| **Latency** | ~40-60ms (excellent in NA/Asia), ~170ms global average |
| **Key Features** | Cortex engine, Smart Wallets, Enhanced APIs, NFT/Token APIs |
| **Compute Units** | 10x-60x multipliers per method |

**Fallback Strategy:**
- Use for multi-chain projects needing unified infrastructure
- Backfill historical data via Alchemy's archive access
- EVM chain support when expanding beyond Solana

**Data Normalization:**
- Convert CU-based pricing to per-request equivalents
- Standardize cross-chain data formats

---

### 1.4 Custom Solana RPC

| Attribute | Details |
|-----------|---------|
| **Type** | Self-hosted or dedicated node |
| **Priority** | **NICE-TO-HAVE** (for specialized needs) |
| **Cost** | $2,900-$3,200+/month for dedicated nodes |
| **Rate Limits** | Unlimited (dedicated resources) |
| **Latency** | Depends on infrastructure; can achieve <50ms |
| **Key Features** | Full control, no rate limits, custom indexing |
| **Trade-offs** | Requires DevOps, no built-in parsing/enhancements |

**Fallback Strategy:**
- Run as backup for critical high-frequency operations
- Use for proprietary indexing not available via providers

---

## 2. DEX Data APIs

### 2.1 Jupiter API

| Attribute | Details |
|-----------|---------|
| **Type** | DEX Aggregator API |
| **Priority** | **CRITICAL** |
| **Pricing** | Free tier available; paid tiers for high volume |
| **Rate Limits** | Varies by endpoint; generally permissive for legitimate use |
| **Latency** | Sub-second quote generation |
| **Data Freshness** | Real-time route optimization |
| **Key Endpoints** | Quote API, Swap API, Limit Orders, DCA, Price API |
| **Key Features** | Best-price routing, Multi-hop swaps, Limit orders via Keeper nodes |

**Fallback Strategy:**
- Primary: Jupiter Quote API for price discovery
- Fallback: Direct DEX queries (Raydium, Orca)
- Route simulation before execution to verify pricing

**Data Normalization:**
- Standardize route output format across all DEX aggregators
- Normalize slippage calculations (basis points)
- Convert Jupiter-specific token addresses to canonical format

---

### 2.2 Raydium API

| Attribute | Details |
|-----------|---------|
| **Type** | AMM + Orderbook DEX |
| **Priority** | **CRITICAL** |
| **Pricing** | Free (on-chain data via RPC) |
| **Rate Limits** | None (read from blockchain) |
| **Key Features** | AMM pools, Serum orderbook integration, Fusion pools |
| **Program ID** | 675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8 |

**Fallback Strategy:**
- Direct RPC calls to Raydium program accounts
- Use Birdeye/Bitquery for historical Raydium data
- Pool state monitoring via WebSocket subscriptions

---

### 2.3 Orca API

| Attribute | Details |
|-----------|---------|
| **Type** | Concentrated Liquidity AMM (Whirlpools) |
| **Priority** | **CRITICAL** |
| **Pricing** | Free (on-chain data) |
| **Key Features** | Whirlpools (concentrated liquidity), Fair launch price curves |
| **Program ID** | whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc |

**Fallback Strategy:**
- SDK integration via @orca-so/whirlpools
- Direct program account queries for pool states

---

### 2.4 Meteora DLMM API

| Attribute | Details |
|-----------|---------|
| **Type** | Dynamic Liquidity Market Maker |
| **Priority** | **NICE-TO-HAVE** |
| **Pricing** | Free (on-chain); Bitquery provides enhanced API |
| **Key Features** | Concentrated liquidity, Dynamic fees, Bin-based pricing |
| **Program ID** | LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo |

**Integration Approach:**
- Use @meteora-ag/dlmm SDK for interactions
- Bitquery GraphQL API for historical analysis

---

## 3. Market Data APIs

### 3.1 CoinGecko

| Attribute | Details |
|-----------|---------|
| **Type** | Market Data Aggregator |
| **Priority** | **CRITICAL** |
| **Free Tier** | 10,000 calls/month, rate limited |
| **Paid Tiers** | Analyst ($129/mo), Pro ($499/mo), Enterprise (custom) |
| **Rate Limits** | 30-300 calls/minute depending on tier |
| **Data Coverage** | 370+ exchanges, 7747+ assets |
| **Key Features** | Price data, Market cap, Volume, Exchange data |

**Fallback Strategy:**
- Implement aggressive caching (5-15 minute TTL)
- Fallback to CoinMarketCap for price data
- Use DEX direct queries for real-time pricing

---

### 3.2 CoinMarketCap

| Attribute | Details |
|-----------|---------|
| **Type** | Market Data Aggregator |
| **Priority** | **NICE-TO-HAVE** |
| **Free Tier** | 10,000 calls/month, 30 calls/min |
| **Paid Tiers** | Hobbyist ($29/mo), Startup ($79/mo), Standard ($249/mo), Professional ($699/mo) |
| **Rate Limits** | 30-600 calls/minute depending on tier |
| **Data Coverage** | 300+ exchanges, 5837+ assets |
| **Key Features** | Rankings, Historical data, Global metrics |

---

### 3.3 Birdeye

| Attribute | Details |
|-----------|---------|
| **Type** | Solana Token Analytics |
| **Priority** | **CRITICAL** |
| **Free Tier** | 3 endpoints only, 1 RPS |
| **Paid Tiers** | Lite ($39/mo, 15 RPS), Starter ($49/mo, 15 RPS), Premium ($149/mo, 50 RPS), Business ($299/mo, 100 RPS), Enterprise (custom) |
| **Rate Limits** | 1-100 RPS per account (Wallet API: 30 RPM) |
| **Key Features** | Real-time token data, Wallet tracking, Trending tokens, OHLCV data |
| **Compute Units** | 1.5M-100M+ CUs/month depending on tier |

**Fallback Strategy:**
- Primary: Birdeye for Solana-specific token data
- Fallback: DexScreener for pair data
- Backup: Bitquery GraphQL for historical

---

### 3.4 DexScreener

| Attribute | Details |
|-----------|---------|
| **Type** | DEX Pair Explorer |
| **Priority** | **CRITICAL** |
| **Pricing** | **FREE** (public API) |
| **Rate Limits** | ~300 requests/minute (search), ~60 requests/minute (profiles) |
| **Key Features** | Real-time pair data, Multi-chain support, Token profiles, Hot pairs |
| **Endpoints** | /token-pairs, /pairs, /search, /token-profiles |

**Fallback Strategy:**
- No cost makes this ideal for redundant data sources
- Use for cross-validation of token prices
- Rate limit handling with exponential backoff

---

## 4. Social Data APIs

### 4.1 Twitter/X API

| Attribute | Details |
|-----------|---------|
| **Type** | Social Media Data |
| **Priority** | **NICE-TO-HAVE** (expensive) |
| **Free Tier** | 500 posts/month, 1 req/24hrs (useless for production) |
| **Paid Tiers** | Basic ($200/mo), Pro ($5,000/mo), Enterprise ($42,000+/mo) |
| **Rate Limits** | Basic: 15K read req/month; Pro: 1M read req/month |
| **New Pricing (Beta)** | Pay-per-use model launching |
| **Alternative** | Third-party scrapers (SociaVault, Apify actors) - $10-50/month |

**Fallback Strategy:**
- Use third-party Twitter scrapers instead of official API
- LunarCrush aggregates Twitter crypto sentiment
- Consider browser automation for critical monitoring

---

### 4.2 LunarCrush

| Attribute | Details |
|-----------|---------|
| **Type** | Crypto Social Intelligence |
| **Priority** | **NICE-TO-HAVE** |
| **Free Tier** | Basic market insights, limited social data, AltRank |
| **Paid Tiers** | Individual ($72/mo), Builder ($240/mo), Scale ($720/mo), Enterprise (custom) |
| **Rate Limits** | Free: limited; Individual: 10 req/min, 2K/day; Builder: 100 req/min, 20K/day; Scale: 500 req/min, 100K/day |
| **Key Features** | Social sentiment, Galaxy Score, AltRank, Influencer tracking |
| **API** | MCP SDK available for AI integration |

---

### 4.3 Telegram Bot API

| Attribute | Details |
|-----------|---------|
| **Type** | Messaging/Notifications |
| **Priority** | **CRITICAL** |
| **Pricing** | **FREE** |
| **Rate Limits** | 30 messages/second to different chats, 20 messages/minute to same group |
| **Key Features** | Real-time alerts, Bot commands, Group management |

---

## 5. Wallet Intelligence APIs

### 5.1 Nansen

| Attribute | Details |
|-----------|---------|
| **Type** | On-chain Analytics & Wallet Intelligence |
| **Priority** | **NICE-TO-HAVE** (expensive but powerful) |
| **Pricing** | Pioneer ($129/mo), Professional ($1,299/mo), VIP/Enterprise (custom) |
| **Discounts** | Promo codes available (10-23% off) |
| **Key Features** | 500M+ labeled wallets, Smart Money tracking, Token God Mode, NFT analytics |
| **Coverage** | 12+ chains including Solana |
| **API** | Available with Enterprise; MCP integration for AI |

**Fallback Strategy:**
- Use DeBank for wallet portfolio tracking (free tier)
- Dune Analytics for custom wallet queries
- Self-built heuristics for smart money detection

---

### 5.2 Arkham

| Attribute | Details |
|-----------|---------|
| **Type** | Blockchain Intelligence & Deanonymization |
| **Priority** | **NICE-TO-HAVE** |
| **Pricing** | **FREE** (platform use); Intel marketplace has fees |
| **Key Features** | Entity labeling, Intel-to-Earn marketplace, Multi-chain support |
| **Token** | ARKM for bounties and governance |

---

### 5.3 GMGN

| Attribute | Details |
|-----------|---------|
| **Type** | Solana Memecoin Trading Platform |
| **Priority** | **NICE-TO-HAVE** |
| **Pricing** | Free tier; Pro features at $20/mo |
| **Key Features** | Token discovery, Smart money tracking, Sniper bots, Telegram automation |
| **API Status** | **NO OFFICIAL PUBLIC API** - web scraping or third-party proxies required |
| **Note** | Alternative: Bitquery provides similar data via GraphQL |

---

## 6. MEV/Trading Infrastructure

### 6.1 Jito Labs

| Attribute | Details |
|-----------|---------|
| **Type** | MEV Infrastructure & Liquid Staking |
| **Priority** | **CRITICAL** |
| **Pricing** | Block Engine: 5% fee on MEV tips (changing to 3% + 3% DAO) |
| **Key Features** | Bundle submission, MEV protection, Staked connections, ShredStream |
| **Market Share** | 90%+ of staked SOL runs Jito client |
| **API Methods** | sendBundle, sendTransaction, getBundleStatuses |
| **Tip Minimum** | 1,000 lamports (0.000001 SOL) |

**Fallback Strategy:**
- Direct RPC submission without bundles (lower success rate during congestion)
- Multiple Jito relayer endpoints for redundancy

---

### 6.2 Paladin

| Attribute | Details |
|-----------|---------|
| **Type** | MEV Protection & Fair MEV Distribution |
| **Priority** | **NICE-TO-HAVE** |
| **Pricing** | Open source (validator must run client) |
| **Key Features** | Atomic arbitrage bot, MEV protection, PAL token rewards |
| **Integration** | Via Bifrost API (ThorNode) for unified access |

---

### 6.3 MEV-Share (Flashbots)

| Attribute | Details |
|-----------|---------|
| **Type** | MEV Protection & Order Flow Auction |
| **Priority** | **NICE-TO-HAVE** (Ethereum-focused, limited Solana support) |
| **Pricing** | Free; Searchers pay for inclusion |
| **Key Features** | Private transaction submission, MEV refunds (90% to users) |
| **Note** | Primarily Ethereum; Solana ecosystem uses Jito instead |

---

## 7. Alternative Data Sources

### 7.1 Prop AMMs (HumidiFi, SolFi)

| Attribute | Details |
|-----------|---------|
| **Type** | Proprietary AMM Data |
| **Priority** | **NICE-TO-HAVE** |
| **Status** | Limited public API availability |
| **Approach** | Monitor on-chain programs directly |

### 7.2 Pump.fun

| Attribute | Details |
|-----------|---------|
| **Type** | Token Launchpad |
| **Priority** | **CRITICAL** (for memecoin trading) |
| **Official API** | **NO OFFICIAL PUBLIC API** |
| **Access Methods** | 
| - | QuickNode Metis add-on (recommended) |
| - | PumpPortal (third-party) |
| - | Direct program interaction via Anchor IDL |
| **Program ID** | 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P |

**Integration Approaches:**
1. **QuickNode Metis**: `/pump-fun/swap` endpoint for quotes and swaps
2. **Direct RPC**: Subscribe to program logs for new token creation
3. **Bitquery**: GraphQL API for historical Pump.fun data

---

## 8. Notification APIs

### 8.1 Telegram Bot API

| Attribute | Details |
|-----------|---------|
| **Type** | Push Notifications |
| **Priority** | **CRITICAL** |
| **Cost** | Free |
| **Rate Limits** | 30 msg/sec globally, 20 msg/min per group |
| **Features** | Markdown support, Buttons, Inline keyboards |

### 8.2 Discord Webhooks

| Attribute | Details |
|-----------|---------|
| **Type** | Channel Notifications |
| **Priority** | **NICE-TO-HAVE** |
| **Cost** | Free |
| **Rate Limits** | 30 requests/60 seconds per webhook |
| **Features** | Rich embeds, Thread support |

### 8.3 PagerDuty

| Attribute | Details |
|-----------|---------|
| **Type** | Incident Management |
| **Priority** | **NICE-TO-HAVE** |
| **Cost** | $21-41/user/month |
| **Use Case** | Critical system alerts, downtime notifications |

---

## 9. APIs That DON'T Exist (Need to Build/Proxy)

### 9.1 Missing APIs to Build

| Need | Solution |
|------|----------|
| **Real-time Solana mempool** | Solana has no public mempool; build private relay network |
| **Unified wallet intelligence** | Aggregate Nansen, Arkham, DeBank, self-built heuristics |
| **Cross-DEX arbitrage signals** | Build custom indexer using Yellowstone gRPC |
| **Token launch detection** | Subscribe to token program and Pump.fun via WebSocket |
| **MEV opportunity feed** | Build searcher bot using Jito Block Engine |
| **Social sentiment aggregation** | Aggregate LunarCrush, Twitter scrapers, Telegram channels |
| **Whale alert system** | Build transaction monitor with wallet labeling |

### 9.2 Proxies Needed

| Service | Issue | Solution |
|---------|-------|----------|
| **GMGN** | No public API | Web scraping service or use Bitquery equivalent |
| **Pump.fun** | No official API | Use QuickNode Metis or build direct program integration |
| **Twitter/X** | Prohibitively expensive | Third-party scrapers or browser automation |
| **Nansen** | Expensive API access | Screen scraping or use limited free features |

---

## 10. Data Normalization Architecture

### 10.1 Unified Schema

```typescript
// Token Data Schema
interface NormalizedToken {
  address: string;
  symbol: string;
  name: string;
  decimals: number;
  chain: 'solana';
  priceUsd: number;
  priceChange24h: number;
  volume24h: number;
  marketCap: number;
  liquidityUsd: number;
  source: string[]; // ['birdeye', 'dexscreener', 'coingecko']
  lastUpdated: number;
}

// Trade Data Schema
interface NormalizedTrade {
  txHash: string;
  timestamp: number;
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  amountOut: string;
  price: number;
  slippage: number;
  dex: string;
  sender: string;
}

// Wallet Activity Schema
interface NormalizedWalletActivity {
  address: string;
  label?: string;
  classification: 'smart_money' | 'whale' | 'retail' | 'contract';
  portfolioValue: number;
  recentTrades: NormalizedTrade[];
  pnl24h: number;
  pnl7d: number;
}
```

### 10.2 Data Flow Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                │
├───────────┬───────────┬───────────┬───────────┬─────────────────┤
│ Blockchain│ DEX APIs  │ Market    │ Social    │ Wallet Intel    │
│ (Helius,  │ (Jupiter, │ (Birdeye, │ (Twitter, │ (Nansen,        │
│ QuickNode)│ Raydium)  │ CoinGecko)│ LunarCrush│ Arkham)         │
└─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴────────┬────────┘
      │           │           │           │              │
      └───────────┴───────────┴───────────┴──────────────┘
                          │
              ┌───────────▼───────────┐
              │   INGESTION LAYER     │
              │  - Rate limiting      │
              │  - Authentication     │
              │  - Request batching   │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   NORMALIZATION       │
              │  - Schema mapping     │
              │  - Unit conversion    │
              │  - Source tagging     │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   STORAGE/CACHE       │
              │  - Redis (hot)        │
              │  - TimescaleDB (warm) │
              │  - ClickHouse (cold)  │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   CONSUMPTION API     │
              │  - GraphQL            │
              │  - WebSocket streams  │
              │  - Webhooks           │
              └───────────────────────┘
```

---

## 11. Fallback & Resilience Strategy

### 11.1 Tiered Fallback

| Service Type | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|--------------|---------|------------|------------|------------|
| RPC | Helius | QuickNode | Alchemy | Public RPC |
| Token Prices | Birdeye | DexScreener | CoinGecko | Jupiter |
| Wallet Data | Nansen | Arkham | DeBank | Direct RPC |
| Social | LunarCrush | Twitter API | Telegram bots | - |
| MEV | Jito | Direct RPC | - | - |

### 11.2 Circuit Breaker Pattern

```typescript
class CircuitBreaker {
  private failures = 0;
  private threshold = 5;
  private timeout = 60000; // 1 minute
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  
  async call<T>(fn: () => Promise<T>, fallback: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      return fallback();
    }
    
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      return fallback();
    }
  }
}
```

---

## 12. Cost Optimization Matrix

| Service | Monthly Cost Est. | Optimization Strategy |
|---------|-------------------|----------------------|
| Helius Business | $499 | Use DAS API efficiently; cache parsed transactions |
| QuickNode | $49-249 | Route heavy methods to cheaper alternatives |
| Birdeye Business | $299 | Cache trending data; batch wallet queries |
| CoinGecko Pro | $499 | Aggressive caching; only fetch active tokens |
| Nansen Pro | $1,299 | Use for research only; cache smart money lists |
| **TOTAL** | **~$2,645/mo** | With optimizations: **~$1,500-2,000/mo** |

### Free Tier Maximization

| Service | Free Tier Strategy |
|---------|-------------------|
| Helius | Use for development; upgrade only for production scale |
| Birdeye | Limited endpoints sufficient for basic price checks |
| DexScreener | Unlimited use for pair data - primary price source |
| CoinGecko | Cache aggressively; use for top 1000 tokens only |
| Twitter | Use third-party scrapers instead of official API |

---

## 13. Critical vs Nice-to-Have Summary

### Critical (Must Have)

| Category | Services |
|----------|----------|
| Blockchain RPC | Helius, QuickNode |
| DEX Data | Jupiter, Raydium, Orca |
| Market Data | Birdeye, DexScreener |
| Trading | Jito (for MEV protection) |
| Notifications | Telegram Bot API |

### Nice-to-Have (Enhancements)

| Category | Services |
|----------|----------|
| Blockchain RPC | Alchemy, Custom RPC |
| Market Data | CoinGecko, CoinMarketCap |
| Social | Twitter/X, LunarCrush |
| Wallet Intel | Nansen, Arkham |
| MEV | Paladin, MEV-Share |
| Notifications | Discord, PagerDuty |
| Alternative | Meteora, GMGN, Pump.fun APIs (via workarounds) |

---

## 14. Implementation Recommendations

### Phase 1: MVP (Weeks 1-4)
- Helius Developer tier
- Jupiter API
- DexScreener (free)
- Telegram Bot API
- Jito bundles (basic)

### Phase 2: Production (Weeks 5-8)
- Upgrade to Helius Business
- Add Birdeye Premium
- Implement Nansen (or alternatives)
- Build custom wallet tracking

### Phase 3: Scale (Weeks 9-12)
- Multi-RPC fallback
- Advanced MEV strategies
- Social sentiment integration
- Real-time alerting system

---

*Document Version: 1.0*  
*Last Updated: March 2025*  
*Next Review: Monthly*
