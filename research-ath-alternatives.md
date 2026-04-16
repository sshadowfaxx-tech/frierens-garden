# Free Alternatives to Bitquery API for Solana Token ATH Data

## Executive Summary

This research identifies the best **FREE** alternatives to Bitquery for fetching historical ATH (all-time high) price data for Solana tokens. The current Bitquery implementation uses GraphQL queries with `DEXTradeByTokens` and quantile aggregation to calculate ATH prices.

---

## 🏆 Ranked List of Best Free Alternatives

### 1. 🥇 CoinGecko API (BEST OVERALL)

**API Name:** CoinGecko API v3  
**Free Tier Limits:**
- 10,000-30,000 calls/month (Demo plan)
- ~30 calls/minute rate limit
- No API key required for basic access (Demo key optional)

**Historical Price Endpoint:**
```
GET https://api.coingecko.com/api/v3/coins/{id}/market_chart
```

**Example Request:**
```bash
curl -X GET "https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=max&interval=daily" \
  -H "accept: application/json"
```

**Example Response:**
```json
{
  "prices": [
    [1609459200000, 1.50],
    [1609545600000, 1.65],
    [1609632000000, 1.72]
  ],
  "market_caps": [
    [1609459200000, 500000000],
    [1609545600000, 550000000]
  ],
  "total_volumes": [
    [1609459200000, 100000000],
    [1609545600000, 120000000]
  ]
}
```

**Code Example - Calculate ATH:**
```javascript
async function getATHFromCoinGecko(coinId) {
  const response = await fetch(
    `https://api.coingecko.com/api/v3/coins/${coinId}/market_chart?vs_currency=usd&days=max`
  );
  const data = await response.json();
  
  // Extract all prices and find max
  const prices = data.prices.map(([timestamp, price]) => price);
  const ath = Math.max(...prices);
  const athIndex = prices.indexOf(ath);
  const athDate = new Date(data.prices[athIndex][0]);
  
  return {
    ath,
    athDate,
    athMarketCap: data.market_caps[athIndex]?.[1] || null
  };
}

// For Solana tokens by contract address
async function getATHByContractAddress(contractAddress, platform = 'solana') {
  const response = await fetch(
    `https://api.coingecko.com/api/v3/coins/${platform}/contract/${contractAddress}/market_chart?vs_currency=usd&days=max`
  );
  const data = await response.json();
  
  const prices = data.prices.map(([timestamp, price]) => price);
  return Math.max(...prices);
}
```

**Pros:**
- ✅ Most generous free tier (10K-30K calls/month)
- ✅ Supports Solana contract addresses directly
- ✅ Returns price, market cap, and volume history
- ✅ No API key required
- ✅ Simple REST API (easy migration from GraphQL)
- ✅ Historical data going back to token launch

**Cons:**
- ❌ Rate limited to ~30 calls/minute on free tier
- ❌ Data updates every 1-5 minutes (not real-time)
- ❌ No WebSocket on free tier

**Migration Difficulty:** EASY - Simple REST calls replace GraphQL queries

---

### 2. 🥈 Birdeye API (BEST FOR SOLANA-SPECIFIC DATA)

**API Name:** Birdeye Data Services API  
**Free Tier Limits:**
- 30,000 compute units/month
- 1 request/second (1 RPS)
- 20 free endpoints

**Historical Price Endpoints:**
```
GET https://public-api.birdeye.so/defi/history_price
GET https://public-api.birdeye.so/defi/ohlcv
GET https://public-api.birdeye.so/defi/historical_price_unix
```

**Example Request:**
```bash
curl -X GET "https://public-api.birdeye.so/defi/history_price?address=So11111111111111111111111111111111111111112&type_in_time=1D&time_from=1609459200&time_to=1704067200" \
  -H "accept: application/json" \
  -H "x-chain: solana" \
  -H "X-API-KEY: YOUR_API_KEY"
```

**Example Response:**
```json
{
  "data": {
    "items": [
      {
        "unixTime": 1609459200,
        "value": 1.50,
        "volume": 1000000
      },
      {
        "unixTime": 1609545600,
        "value": 1.65
      }
    ]
  },
  "success": true
}
```

**Code Example - Calculate ATH:**
```javascript
async function getATHFromBirdeye(tokenAddress, fromTime, toTime) {
  const response = await fetch(
    `https://public-api.birdeye.so/defi/history_price?address=${tokenAddress}&type_in_time=1D&time_from=${fromTime}&time_to=${toTime}`,
    {
      headers: {
        'accept': 'application/json',
        'x-chain': 'solana',
        'X-API-KEY': process.env.BIRDEYE_API_KEY
      }
    }
  );
  const data = await response.json();
  
  if (!data.success || !data.data.items) return null;
  
  const prices = data.data.items.map(item => item.value);
  const ath = Math.max(...prices);
  const athItem = data.data.items.find(item => item.value === ath);
  
  return {
    ath,
    athTimestamp: athItem.unixTime,
    athDate: new Date(athItem.unixTime * 1000)
  };
}

// Using OHLCV for more detailed data
async function getATHFromOHLCV(tokenAddress, fromTime, toTime) {
  const response = await fetch(
    `https://public-api.birdeye.so/defi/ohlcv?address=${tokenAddress}&type=1D&time_from=${fromTime}&time_to=${toTime}`,
    {
      headers: {
        'accept': 'application/json',
        'x-chain': 'solana',
        'X-API-KEY': process.env.BIRDEYE_API_KEY
      }
    }
  );
  const data = await response.json();
  
  // Get ATH from high prices
  const highs = data.data.items.map(item => item.h);
  return Math.max(...highs);
}
```

**Pros:**
- ✅ Solana-native (best coverage for Solana tokens)
- ✅ OHLCV data available
- ✅ Real-time and historical data
- ✅ Supports 10+ blockchains
- ✅ Good for memecoins and new tokens

**Cons:**
- ❌ Limited to 30K CUs/month on free tier
- ❌ Requires API key
- ❌ 1 RPS rate limit on free tier
- ❌ WebSocket only on paid tiers

**Migration Difficulty:** MEDIUM - Need to use multiple API calls to reconstruct ATH

---

### 3. 🥉 DEX Screener API (BEST FOR REAL-TIME DATA)

**API Name:** DEX Screener API  
**Free Tier Limits:**
- FREE (no tier specified)
- ~5 requests/second
- No API key required for public endpoints

**Endpoints:**
```
GET https://api.dexscreener.com/latest/dex/tokens/{chain}/{tokenAddress}
GET https://api.dexscreener.com/latest/dex/pairs/{chain}/{pairAddress}
```

**Example Request:**
```bash
curl "https://api.dexscreener.com/latest/dex/tokens/solana/So11111111111111111111111111111111111111112"
```

**Example Response:**
```json
{
  "schemaVersion": "1.0.0",
  "pairs": [
    {
      "chainId": "solana",
      "dexId": "raydium",
      "pairAddress": "...",
      "baseToken": {
        "address": "So11111111111111111111111111111111111111112",
        "name": "Wrapped SOL",
        "symbol": "SOL"
      },
      "quoteToken": {
        "address": "...",
        "symbol": "USDC"
      },
      "priceNative": "100.00",
      "priceUsd": "100.00",
      "txns": {
        "m5": { "buys": 10, "sells": 5 },
        "h1": { "buys": 100, "sells": 50 }
      },
      "volume": {
        "h24": 1000000,
        "h6": 500000
      },
      "priceChange": {
        "h24": 5.2
      },
      "liquidity": {
        "usd": 10000000
      },
      "fdv": 50000000000,
      "marketCap": 45000000000
    }
  ]
}
```

**Important Note:** DEX Screener API does NOT provide historical price data directly. You would need to:
1. Poll the API regularly to build your own price history
2. Use the price change fields (h24, h6, etc.) for limited historical context

**Code Example:**
```javascript
async function getCurrentPriceFromDexScreener(tokenAddress, chain = 'solana') {
  const response = await fetch(
    `https://api.dexscreener.com/latest/dex/tokens/${chain}/${tokenAddress}`
  );
  const data = await response.json();
  
  if (!data.pairs || data.pairs.length === 0) return null;
  
  // Get the pair with highest liquidity
  const bestPair = data.pairs.sort((a, b) => 
    (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0)
  )[0];
  
  return {
    priceUsd: parseFloat(bestPair.priceUsd),
    marketCap: bestPair.marketCap,
    fdv: bestPair.fdv,
    liquidityUsd: bestPair.liquidity?.usd,
    priceChange24h: bestPair.priceChange?.h24
  };
}
```

**Pros:**
- ✅ Completely free, no API key needed
- ✅ Real-time price data
- ✅ Good for current market data
- ✅ Supports 50+ chains

**Cons:**
- ❌ **NO historical price data endpoint**
- ❌ Cannot calculate true ATH without building your own history
- ❌ Limited to current/24h data only

**Migration Difficulty:** HARD - Not suitable for historical ATH without additional infrastructure

---

### 4. Helius (BEST FOR ARCHIVAL DATA)

**API Name:** Helius Solana API  
**Free Tier Limits:**
- 1M credits/month
- 10 requests/second
- Archive data included

**Historical Data Endpoints:**
```
getTransactionsForAddress
getSignaturesForAddress + getTransaction
```

**Note:** Helius provides RPC access to historical Solana data, but you need to:
1. Query transaction history for token trades
2. Parse the transactions to extract price data
3. Calculate ATH from the trade history

**Code Example:**
```javascript
async function getHistoricalTradesFromHelius(tokenAddress, heliusApiKey) {
  const response = await fetch(
    `https://mainnet.helius-rpc.com/?api-key=${heliusApiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 'helius-test',
        method: 'getTransactionsForAddress',
        params: {
          address: tokenAddress,
          limit: 100,
          commitment: 'confirmed'
        }
      })
    }
  );
  
  const data = await response.json();
  // Parse transactions to extract price data
  // This requires understanding of Solana transaction structure
  return data.result;
}
```

**Pros:**
- ✅ 1M free credits/month
- ✅ Full archival data from Solana genesis
- ✅ Solana-specialized
- ✅ Fast, reliable infrastructure

**Cons:**
- ❌ Requires parsing transactions manually
- ❌ No direct price history endpoint
- ❌ Complex to extract ATH from raw transaction data

**Migration Difficulty:** HARD - Requires significant data processing

---

### 5. Alchemy (BEST FREE TIER VOLUME)

**API Name:** Alchemy Solana API  
**Free Tier Limits:**
- 30M compute units/month (most generous!)
- 25 requests/second
- Archive data included

**Similar to Helius**, Alchemy provides RPC access to historical data but requires manual transaction parsing.

**Pros:**
- ✅ **30M CUs/month - largest free tier**
- ✅ Full archival access
- ✅ 20x faster archive queries than competitors
- ✅ Multi-chain support

**Cons:**
- ❌ No direct price history endpoint
- ❌ Requires building your own price extraction logic

**Migration Difficulty:** HARD

---

### 6. CoinMarketCap API

**API Name:** CoinMarketCap API  
**Free Tier Limits:**
- 10,000 calls/month (Basic/Free plan)
- Limited historical data

**Historical Price Endpoint:**
```
GET https://pro-api.coinmarketcap.com/v1/cryptocurrency/ohlcv/historical
```

**Note:** Free tier has limited access to historical data. Full historical data requires paid plan.

**Pros:**
- ✅ Well-known, trusted data source
- ✅ Good for major tokens

**Cons:**
- ❌ Limited Solana token coverage (especially new/meme tokens)
- ❌ Historical data restricted on free tier
- ❌ Requires API key

**Migration Difficulty:** MEDIUM - Limited utility for Solana memecoins

---

### 7. Solana FM

**API Name:** Solana FM API  
**Free Tier:** Free access available

**Features:**
- REST API for transaction data
- GraphQL API for flexible queries
- WebSocket for real-time data

**Limitations:**
- Primarily an explorer API
- No direct historical price aggregation
- Requires building custom queries for ATH calculation

---

## 📊 Comparison Matrix

| API | Free Tier | Historical Data | Solana Tokens | Ease of Migration | Best For |
|-----|-----------|-----------------|---------------|-------------------|----------|
| **CoinGecko** | 10K-30K calls/mo | ✅ Full history | ✅ Excellent | ⭐ Easy | General purpose, portfolio tracking |
| **Birdeye** | 30K CUs/mo | ✅ Full history | ✅ Solana-native | ⭐⭐ Medium | Solana-specific tokens, memecoins |
| **DEX Screener** | Unlimited | ❌ No history | ✅ Good | ❌ Hard | Real-time data only |
| **Helius** | 1M credits/mo | ✅ Raw archival | ✅ Solana-only | ⭐⭐⭐ Hard | Infrastructure, custom parsing |
| **Alchemy** | 30M CUs/mo | ✅ Raw archival | ✅ Good | ⭐⭐⭐ Hard | High volume, multi-chain |
| **CoinMarketCap** | 10K calls/mo | ⚠️ Limited | ⚠️ Major tokens only | ⭐⭐ Medium | Established cryptocurrencies |

---

## 🎯 Recommended Migration Strategy

### For Simple ATH Calculation (Best Bang for Buck):
```javascript
// Primary: CoinGecko
// Fallback: Birdeye

async function getATHWithFallback(tokenAddress, coinGeckoId) {
  try {
    // Try CoinGecko first
    const ath = await getATHFromCoinGecko(coinGeckoId);
    return { source: 'coingecko', ath };
  } catch (e) {
    // Fallback to Birdeye for Solana tokens
    const fromTime = Math.floor(Date.now() / 1000) - (365 * 24 * 60 * 60); // 1 year ago
    const toTime = Math.floor(Date.now() / 1000);
    const ath = await getATHFromBirdeye(tokenAddress, fromTime, toTime);
    return { source: 'birdeye', ath };
  }
}
```

### For Real-Time + Historical Hybrid:
```javascript
// Use Birdeye for historical ATH
// Use DEX Screener for current price validation
```

---

## 💡 Key Takeaways

1. **CoinGecko** is the best free alternative for most use cases - generous limits, easy API, full historical data

2. **Birdeye** is best for Solana-specific tokens, especially memecoins that may not be on CoinGecko

3. **DEX Screener** is NOT suitable for historical ATH calculation (no history endpoint)

4. **Helius/Alchemy** provide the most raw data but require significant development effort to extract prices

5. For a robust solution, implement a **fallback strategy**: CoinGecko → Birdeye → Custom parsing (Helius/Alchemy)

---

## 📝 Implementation Notes

### Calculating ATH Market Cap
```javascript
// Once you have ATH price, calculate ATH market cap:
function calculateATHMarketCap(athPrice, totalSupply) {
  return athPrice * totalSupply;
}

// Get total supply from Solana RPC or token metadata
async function getTokenSupply(tokenAddress) {
  // Use Solana web3.js or @solana/spl-token
  const connection = new Connection('https://api.mainnet-beta.solana.com');
  const mintInfo = await getMint(connection, new PublicKey(tokenAddress));
  return Number(mintInfo.supply) / Math.pow(10, mintInfo.decimals);
}
```

### Rate Limiting Best Practices
```javascript
class RateLimiter {
  constructor(maxRequests, windowMs) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
    this.requests = [];
  }
  
  async waitForSlot() {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < this.windowMs);
    
    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = this.requests[0];
      const waitTime = this.windowMs - (now - oldestRequest);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    this.requests.push(Date.now());
  }
}

// Usage
const coingeckoLimiter = new RateLimiter(30, 60000); // 30 calls/minute
await coingeckoLimiter.waitForSlot();
const data = await fetchCoinGeckoData();
```

---

*Research conducted: March 12, 2026*
*All rate limits and pricing subject to change - verify with official documentation*
