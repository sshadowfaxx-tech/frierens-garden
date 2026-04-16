# FREE Alternatives to Bitquery API for Solana Token Metadata

## Executive Summary

Research conducted: March 12, 2026

This report documents FREE alternatives to Bitquery for fetching token metadata on Solana, with special focus on Pump.fun tokens that may not be indexed on DexScreener yet.

---

## Ranked List of Best Free Alternatives

### 🥇 #1: Helius RPC (DAS API) - BEST OVERALL

**API Name:** Helius Digital Asset Standard (DAS) API

**Free Tier Limits:**
- 1M credits/month
- 10 RPC requests/second
- 2 DAS API requests/second
- WebSockets included
- Archive data access included
- Webhooks included
- 1 API key

**Specific Endpoint for Token Metadata:**
```
POST https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY
```

**Method:** `getAsset`

**Example Request:**
```javascript
const response = await fetch("https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    jsonrpc: "2.0",
    id: "1",
    method: "getAsset",
    params: {
      id: "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", // Token mint address
      displayOptions: {
        showFungible: true  // Required for fungible tokens
      }
    },
  }),
});
const data = await response.json();
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "interface": "FungibleToken",
    "id": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "content": {
      "$schema": "https://schema.metaplex.com/nft.json",
      "json_uri": "https://arweave.net/...",
      "metadata": {
        "name": "Bonk",
        "symbol": "Bonk",
        "description": "..."
      }
    },
    "token_info": {
      "symbol": "Bonk",
      "supply": 8881594973561640000,
      "decimals": 5,
      "token_program": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
      "price_info": {
        "price_per_token": 0.0000192271,
        "currency": "USDC"
      }
    }
  }
}
```

**Covers Pre-migration Pump.fun Tokens:** ✅ YES - DAS API indexes all Metaplex metadata tokens, including Pump.fun tokens

**Pros:**
- Solana-specialized provider
- Includes price info in response
- Supports both SPL and Token-2022
- Very generous free tier (1M credits)
- No credit card required

**Cons:**
- 10 RPS limit on free tier
- Requires API key

---

### 🥈 #2: Solscan Public API - BEST FOR NO SIGNUP

**API Name:** Solscan Public API

**Free Tier Limits:**
- 150 requests per 30 seconds (5 RPS)
- 100,000 requests per day
- No API key required for basic access
- Contact for higher limits with free API key

**Specific Endpoint for Token Metadata:**
```
GET https://public-api.solscan.io/token/meta?tokenAddress={mint_address}
```

**Example Request:**
```bash
curl -X GET "https://public-api.solscan.io/token/meta?tokenAddress=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" \
  -H "accept: application/json"
```

**Example Response:**
```json
{
  "symbol": "USDC",
  "name": "USD Coin",
  "decimals": 6,
  "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "supply": "...",
  "holders": 1500000,
  "icon": "https://..."
}
```

**Covers Pre-migration Pump.fun Tokens:** ⚠️ PARTIAL - May not index very new tokens immediately

**Pros:**
- No API key needed for basic usage
- High daily limit (100k requests)
- Simple REST API
- Etherscan-acquired (reliable)

**Cons:**
- Lower rate limits than competitors
- Less metadata for new tokens
- May lag behind for brand new tokens

---

### 🥉 #3: Jupiter Token List API - BEST FOR VERIFIED TOKENS

**API Name:** Jupiter Token List

**Free Tier Limits:**
- Completely FREE (no rate limits enforced)
- Community-maintained
- Updated regularly

**Specific Endpoints:**
```
# Strict List (verified tokens)
GET https://token.jup.ag/strict

# All tokens (including unverified)
GET https://token.jup.ag/all
```

**Example Request:**
```bash
# Get strict token list
curl -X GET "https://token.jup.ag/strict" \
  -H "accept: application/json"

# Get specific token
curl -X GET "https://token.jup.ag/all" | jq '.[] | select(.address == "MINT_ADDRESS")'
```

**Example Response:**
```json
[
  {
    "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "chainId": 101,
    "decimals": 6,
    "name": "USD Coin",
    "symbol": "USDC",
    "logoURI": "https://...",
    "tags": ["stablecoin"],
    "extensions": {
      "coingeckoId": "usd-coin"
    }
  }
]
```

**Covers Pre-migration Pump.fun Tokens:** ❌ NO - Only includes verified tokens with sufficient liquidity/holders

**Pros:**
- Completely free
- No API key required
- No rate limits
- Community-verified tokens only (quality filter)

**Cons:**
- Only verified tokens (new Pump.fun tokens won't appear)
- No pricing data
- Not suitable for pre-migration/new tokens

---

### #4: Birdeye API (Standard/Free Tier)

**API Name:** Birdeye Data Services API

**Free Tier Limits:**
- 30,000 Compute Units (CU) per month
- 1 request per second
- Limited to 3 specific endpoints:
  - `/defi/tokenlist`
  - `/defi/price` (limited)
  - `/defi/history` (limited)

**Specific Endpoint for Token Metadata:**
```
GET https://public-api.birdeye.so/defi/tokenlist
```

**Example Request:**
```bash
curl -X GET "https://public-api.birdeye.so/defi/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=50" \
  -H "accept: application/json" \
  -H "x-chain: solana" \
  -H "X-API-KEY: YOUR_API_KEY"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "updateUnixTime": 1725507085,
    "tokens": [
      {
        "address": "So11111111111111111111111111111111111111112",
        "decimals": 9,
        "liquidity": 11305713600.578115,
        "logoURI": "https://...",
        "mc": 76959192381.0279,
        "name": "Wrapped SOL",
        "symbol": "SOL",
        "v24hChangePercent": -5.90,
        "v24hUSD": 896018873.56
      }
    ],
    "total": 14815
  }
}
```

**Covers Pre-migration Pump.fun Tokens:** ✅ YES - Birdeye indexes most tokens with liquidity

**Pros:**
- Rich metadata (liquidity, market cap, volume)
- Multi-chain support
- Good for trading data

**Cons:**
- Very limited free tier (30k CU, 1 RPS)
- API key required even for free tier
- Limited endpoints on free tier
- Not suitable for high-frequency use

---

### #5: Metaplex DAS API (via QuickNode or Self-hosted)

**API Name:** Metaplex Digital Asset Standard API

**Free Tier Limits:**
- Available via QuickNode free tier (50K CU/day)
- Or self-host your own indexer (complex)

**Specific Endpoint:**
```
POST https://{quicknode_endpoint}/
```

**Method:** `getAsset` (same as Helius DAS)

**Example Request:**
```javascript
const response = await fetch("https://your-quicknode-endpoint", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "getAsset",
    params: {
      id: "MINT_ADDRESS",
      displayOptions: { showFungible: true }
    }
  })
});
```

**Covers Pre-migration Pump.fun Tokens:** ✅ YES - All Metaplex metadata tokens

**Pros:**
- Official Metaplex standard
- Comprehensive metadata
- Supports compressed NFTs

**Cons:**
- Requires QuickNode or self-hosted infrastructure
- Complex setup for self-hosting
- Limited free tier via QuickNode

---

### #6: PumpAPI (Third-party Pump.fun API)

**API Name:** PumpAPI

**Free Tier Limits:**
- Unknown rate limits
- Community/third-party service

**Specific Endpoint:**
```
GET https://pumpapi.fun/api/get_metadata/{mint_address}
```

**Example Request:**
```bash
curl -X GET "https://pumpapi.fun/api/get_metadata/9QUYvUGiqCALxrMCyJrVYXtJSpt4BYzPRv5ZRjsdqzkh"
```

**Covers Pre-migration Pump.fun Tokens:** ✅ YES - Specialized for Pump.fun

**Pros:**
- Specialized for Pump.fun tokens
- Simple REST API

**Cons:**
- Unofficial/third-party service
- Unknown reliability/uptime
- Rate limits unclear
- May not be actively maintained

---

### #7: Solana Vibe Station (SVS) Token Metadata API

**API Name:** SVS Token Metadata API

**Free Tier Limits:**
- Free tier available (requires signup)
- Limits not clearly documented

**Specific Endpoint:**
```
POST https://api.solanavibestation.com/token/metadata
```

**Example Request:**
```bash
curl -X POST "https://api.solanavibestation.com/token/metadata" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mints": ["EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"]}'
```

**Covers Pre-migration Pump.fun Tokens:** ✅ YES

**Pros:**
- Community-focused
- Based on Yellowstone Geyser

**Cons:**
- Requires signup for API key
- Limited documentation
- Less established

---

## Comparison Table

| API | Free Tier | RPS | Pre-migration Pump.fun | Price Data | API Key |
|-----|-----------|-----|----------------------|------------|---------|
| **Helius DAS** | 1M credits/mo | 10 RPC / 2 DAS | ✅ Yes | ✅ Yes | ✅ Required |
| **Solscan** | 100k/day | 5 | ⚠️ Partial | ❌ No | ❌ Optional |
| **Jupiter List** | Unlimited | Unlimited | ❌ No | ❌ No | ❌ No |
| **Birdeye** | 30k CU/mo | 1 | ✅ Yes | ✅ Yes | ✅ Required |
| **Metaplex DAS** | 50k CU/day | 20 | ✅ Yes | ❌ No | ✅ Required |
| **PumpAPI** | Unknown | Unknown | ✅ Yes | ❌ No | ❌ No |
| **SVS** | Limited | Unknown | ✅ Yes | ❌ No | ✅ Required |

---

## Recommended Implementation Strategy

### For Production Applications (High Reliability)

**Primary:** Helius DAS API
- Best free tier (1M credits)
- Includes price data
- Fast and reliable

**Fallback:** Solscan Public API
- No API key needed
- Good for redundancy

### For Pump.fun Specific Applications

**Option 1:** Helius DAS API (recommended)
- Covers all Pump.fun tokens
- Includes pricing

**Option 2:** PumpAPI (unofficial)
- Specialized for Pump.fun
- Use with caution (unofficial)

### For Cost-Sensitive/High Volume

**Primary:** Jupiter Token List (strict)
- Completely free
- No limits

**Fallback:** Solscan Public API
- 100k requests/day
- No key required

---

## Code Example: Multi-Provider Fallback

```typescript
const TOKEN_MINT = "YOUR_TOKEN_MINT";

// Priority order: Helius -> Solscan -> Jupiter
async function getTokenMetadata(mintAddress: string) {
  // Try Helius first
  try {
    const heliusData = await fetchHeliusMetadata(mintAddress);
    if (heliusData) return heliusData;
  } catch (e) {
    console.log("Helius failed, trying Solscan...");
  }

  // Fallback to Solscan
  try {
    const solscanData = await fetchSolscanMetadata(mintAddress);
    if (solscanData) return solscanData;
  } catch (e) {
    console.log("Solscan failed, trying Jupiter...");
  }

  // Final fallback to Jupiter
  try {
    const jupiterData = await fetchJupiterMetadata(mintAddress);
    if (jupiterData) return jupiterData;
  } catch (e) {
    console.log("All providers failed");
    return null;
  }
}

async function fetchHeliusMetadata(mint: string) {
  const response = await fetch(`https://mainnet.helius-rpc.com/?api-key=${process.env.HELIUS_API_KEY}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: "1",
      method: "getAsset",
      params: {
        id: mint,
        displayOptions: { showFungible: true }
      }
    })
  });
  const data = await response.json();
  return data.result ? {
    name: data.result.content?.metadata?.name,
    symbol: data.result.content?.metadata?.symbol,
    decimals: data.result.token_info?.decimals,
    price: data.result.token_info?.price_info?.price_per_token,
    supply: data.result.token_info?.supply,
    source: "helius"
  } : null;
}

async function fetchSolscanMetadata(mint: string) {
  const response = await fetch(`https://public-api.solscan.io/token/meta?tokenAddress=${mint}`);
  const data = await response.json();
  return data ? {
    name: data.name,
    symbol: data.symbol,
    decimals: data.decimals,
    price: null,
    supply: data.supply,
    source: "solscan"
  } : null;
}

async function fetchJupiterMetadata(mint: string) {
  const response = await fetch("https://token.jup.ag/all");
  const tokens = await response.json();
  const token = tokens.find((t: any) => t.address === mint);
  return token ? {
    name: token.name,
    symbol: token.symbol,
    decimals: token.decimals,
    price: null,
    supply: null,
    source: "jupiter"
  } : null;
}
```

---

## Conclusion

**Best Overall Free Alternative:** **Helius DAS API**
- Most generous free tier
- Best data quality
- Includes pricing
- Solana-specialized

**Best No-Signup Option:** **Solscan Public API**
- No API key required
- Decent limits
- Simple to use

**Best for Verified Tokens Only:** **Jupiter Token List**
- Completely free
- No limits
- Community-curated

For Pump.fun tokens specifically, Helius DAS API is the recommended choice as it covers pre-migration tokens and provides comprehensive metadata including pricing.
