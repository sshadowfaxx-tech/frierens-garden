# Wallet Hunter API Comparison

## Current Approach (Helius RPC)

### Queries Used:

**1. `getSignaturesForAddress`** - Transaction discovery
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "getSignaturesForAddress",
  "params": [
    "WALLET_ADDRESS",
    {"limit": 100}
  ]
}
```

**2. `getTransaction`** - Transaction details
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "getTransaction",
  "params": [
    "SIGNATURE",
    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
  ]
}
```

**3. Token Balance Parsing** - Calculate trades
- Parse `preTokenBalances` and `postTokenBalances`
- Track token changes per wallet
- Calculate buy/sell activity

### Pros:
- ✅ Free tier: 1M credits/month
- ✅ Direct Solana data (most accurate)
- ✅ No middleman
- ✅ Real-time

### Cons:
- ❌ Requires transaction parsing logic
- ❌ PnL calculation needs price oracles
- ❌ Rate limited (10 RPS on free tier)
- ❌ Computationally expensive

---

## Alternative 1: DexCheck API

### Endpoint: `GET /api/v1/blockchain/top-traders-for-pair`

**What it does:**
- Returns top traders for a specific trading pair
- Includes realized/unrealized PnL
- Ranks by profitability metrics

### Sample Response Structure:
```json
{
  "traders": [
    {
      "address": "WALLET_ADDRESS",
      "total_profit": 123.45,
      "roi_percentage": 67.8,
      "win_rate": 0.72,
      "total_trades": 45,
      "avg_trade_size": 2.5
    }
  ]
}
```

### Pros:
- ✅ **Pre-calculated PnL** - No need for price oracles!
- ✅ **Win rate included** - Already computed
- ✅ **Top traders ranked** - Discovery built-in
- ✅ Fast query (single API call)

### Cons:
- ❌ Requires API key (even for free tier)
- ❌ Free tier: 20K calls/month, 100/min
- ❌ Pair-specific (need token address first)
- ❌ Less control over calculations

### Free Tier Limits:
- 20,000 calls/month
- 100 calls/minute
- Community support only

---

## Alternative 2: CoinStats Wallet API

### Endpoints:

**1. `GET /wallet/balance`** - Get wallet holdings
```bash
curl -H "X-API-KEY: your-api-key" \
  "https://openapiv1.coinstats.app/wallet/balance?address=WALLET&connectionId=solana"
```

**2. `GET /wallet/transactions`** - Get transaction history
```bash
curl -H "X-API-KEY: your-api-key" \
  "https://openapiv1.coinstats.app/wallet/transactions?address=WALLET&connectionId=solana&limit=100"
```

**3. `PATCH /wallet/transactions`** - Sync transactions (required before fetch)
```bash
curl -X PATCH \
  -H "X-API-KEY: your-api-key" \
  "https://openapiv1.coinstats.app/wallet/transactions?address=WALLET&connectionId=solana"
```

### Sample Response:
```json
[
  {
    "coinId": "solana",
    "amount": 2.5,
    "name": "Solana",
    "symbol": "SOL",
    "price": 185.42,
    "pCh24h": 5.2
  }
]
```

### Pros:
- ✅ Clean REST API
- ✅ Includes USD prices
- ✅ Multi-wallet support
- ✅ Historical data available

### Cons:
- ❌ **Requires sync before query** (extra step)
- ❌ **40-50 credits per request** (expensive!)
- ❌ No direct PnL calculation
- ❌ Still need to compute win rates manually

### Credit Costs:
- Get balance: 40 credits
- Get transactions: 40 credits
- Sync transactions: 50 credits
- Total per wallet analysis: ~130 credits

With free tier (assuming 1000 credits):
- Can analyze ~7 wallets

---

## Recommendation Matrix

| Use Case | Best API | Why |
|----------|----------|-----|
| **Find profitable wallets** | DexCheck | Pre-ranked by PnL |
| **Deep wallet analysis** | Helius (current) | Most control, free |
| **Quick balance check** | CoinStats | Clean API, includes prices |
| **High volume hunting** | Helius | 1M credits vs 20K |

---

## Proposed Hybrid Approach

### Phase 1: Discovery (DexCheck)
Use DexCheck to find top traders for hot tokens:
```python
# Get top traders for a memecoin
top_traders = dexcheck.get_top_traders_for_pair(
    chain="solana",
    token_address="PUMP_TOKEN_ADDRESS",
    limit=50
)
```

### Phase 2: Deep Analysis (Helius)
Use Helius to get detailed transaction history for the top wallets found:
```python
# Deep dive on promising wallets
for wallet in top_traders[:10]:
    txs = helius.get_transactions(wallet.address)
    detailed_analysis = analyze_trades(txs)
```

### Phase 3: Validation (Pump.fun API)
Cross-reference with Pump.fun for token metadata:
```python
# Get token info
metadata = pump_fun_api.get_token(token_address)
```

---

## Cost Comparison (Per 100 Wallets Analyzed)

| API | Cost | Limitations |
|-----|------|-------------|
| Helius Only | ~1,000 credits | Manual PnL calc |
| DexCheck Only | ~100 calls | 20K/month limit |
| CoinStats Only | ~13,000 credits | Expensive! |
| **Hybrid** (DexCheck+Helius) | ~500 credits + 20 calls | **Best balance** |

---

## Implementation Priority

1. **Keep Helius as primary** (free, flexible)
2. **Add DexCheck for discovery** (pre-ranked wallets)
3. **Skip CoinStats** (too expensive for this use case)
4. **Use Pump.fun API** for token metadata (free, no key)

---

## Next Steps

To implement DexCheck integration:

1. Sign up at https://dexcheck.ai/
2. Get API key from dashboard
3. Add `DEXCHECK_API_KEY` to environment
4. Implement fallback: DexCheck → Helius → Pump.fun
