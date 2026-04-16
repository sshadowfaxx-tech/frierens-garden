# Solana Wallet Intelligence - Quick Reference

## Insider Detection Scoring Matrix

| Indicator | Weight | How to Detect | Critical Threshold |
|-----------|--------|---------------|-------------------|
| Deployer Funding | 15% | SOL transfer deployer→sniper | Any transfer = 1.0 |
| Same-Block Snipe | 10% | Buy in block 0 | Block diff = 0 |
| Early Buy Timing | 8% | Buy in first 5 blocks | Blocks 0-2 = high |
| Wallet Clustering | 10% | 3+ wallets, same funder | Confidence >80% |
| Temporal Correlation | 8% | Buy within 60s of cluster | Same block = 1.0 |
| Fresh Wallet | 5% | Age < 7 days | Age < 1 day = 1.0 |
| Rapid Exit History | 5% | Avg hold < 1 hour | Hold < 10 min = 1.0 |
| Repeat Offender | 5% | 5+ sniped tokens | 10+ tokens = 1.0 |

## Risk Score Interpretation

| Score | Level | Action |
|-------|-------|--------|
| 80-100 | 🔴 CRITICAL | Avoid completely |
| 60-79 | 🟠 HIGH | Extreme caution |
| 40-59 | 🟡 MEDIUM | Monitor closely |
| 20-39 | 🟢 LOW | Standard DD |
| 0-19 | ⚪ MINIMAL | Normal trading |

## Helius API Quick Queries

### Get Wallet Identity
```bash
curl "https://api.helius.xyz/v1/wallet/{ADDRESS}/identity?api-key=$KEY"
```

### Get Funding Source
```bash
curl "https://api.helius.xyz/v1/wallet/{ADDRESS}/funded-by?api-key=$KEY"
```

### Get Enhanced Transactions
```bash
curl "https://api-mainnet.helius-rpc.com/v0/addresses/{ADDRESS}/transactions?api-key=$KEY"
```

### Parse Transaction
```bash
curl -X POST "https://api-mainnet.helius-rpc.com/v0/transactions/?api-key=$KEY" \
  -H "Content-Type: application/json" \
  -d '{"transactions":["SIG_HERE"]}'
```

### DAS API - Get Token Accounts
```bash
curl -X POST "https://mainnet.helius-rpc.com/?api-key=$KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getTokenAccounts",
    "params": {"mint": "TOKEN_MINT", "limit": 100}
  }'
```

## Cluster Detection Heuristics

### Funding Graph Building
```
CEX/Wallet A → Wallet B → Wallet C → Sniper
                ↓
                → Wallet D → Sniper
```

### Time-Based Clustering
- **Same block (0s)**: 90% coordination confidence
- **Within 60s**: 75% confidence
- **Within 5 min**: 50% confidence

### Token Overlap Score
```
Overlap = (shared_tokens / min(wallets_tokens)) * 100
Score > 80% = high coordination probability
```

## Sniper Detection Algorithm

```python
def is_sniper(wallet, token_launch_block, buy_block, wallet_age_hours, funding_source):
    score = 0
    
    if buy_block == token_launch_block:
        score += 40
    elif buy_block <= token_launch_block + 2:
        score += 25
    elif buy_block <= token_launch_block + 5:
        score += 15
    
    if wallet_age_hours < 24:
        score += 20
    elif wallet_age_hours < 168:  # 7 days
        score += 10
    
    if funding_source == 'deployer':
        score += 50
    elif funding_source == 'intermediate_wallet':
        score += 30
    
    return score >= 60
```

## Pump.fun Launch Monitoring Checklist

### Immediate (Block 0-5)
- [ ] Log all buyers
- [ ] Check wallet ages
- [ ] Trace funding sources
- [ ] Flag deployer-funded wallets

### Short-term (First hour)
- [ ] Calculate sniper concentration
- [ ] Build cluster graph
- [ ] Score insider probability
- [ ] Set sell alerts on high-risk wallets

### Medium-term (24h)
- [ ] Track exit patterns
- [ ] Update wallet database
- [ ] Flag repeat offenders
- [ ] Generate risk report

## Red Flag Combinations

### CRITICAL (Avoid)
- Deployer funding + same-block snipe
- 3+ fresh wallets + same funder + same token
- Sniper concentration >50%

### HIGH RISK
- Same-block snipe + fresh wallet
- Cluster confidence >80% + no sells yet
- Dev wallet + early selling

### MEDIUM RISK
- Early snipe + CEX funding
- Cluster detected + gradual exits
- Fresh wallet + moderate position

## Trading Style Classification

| Style | Hold Time | Trade Freq | Win Rate |
|-------|-----------|------------|----------|
| Sniper | <1 hour | Very High | Variable |
| Scalper | 1-24h | High | Medium |
| Accumulator | Days-Weeks | Regular | High |
| Swing | Days-Weeks | Medium | Medium |
| Holder | Weeks+ | Low | High |

## Exit Strategy Detection

| Pattern | Indicator | Risk |
|---------|-----------|------|
| Single Dump | 1 sell = 100% position | High |
| Rapid Exit | >50% in <1 hour | High |
| Gradual | Small sells over days | Low |
| Camouflage | Sells during volume spikes | Medium |

## Useful Queries

### Find Deployer-Funded Snipers
```sql
SELECT 
    t.wallet_address,
    t.token_mint,
    t.block - tl.launch_block as blocks_from_launch,
    w.funding_source
FROM transactions t
JOIN token_launches tl ON t.token_mint = tl.mint_address
JOIN wallets w ON t.wallet_address = w.address
WHERE t.block <= tl.launch_block + 5
    AND w.funding_source = tl.deployer
    AND t.type = 'BUY';
```

### Detect Coordinated Clusters
```sql
SELECT 
    COUNT(DISTINCT wallet_address) as wallet_count,
    token_mint,
    block,
    STRING_AGG(wallet_address, ',') as wallets
FROM transactions
WHERE type = 'BUY'
    AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY token_mint, block
HAVING COUNT(DISTINCT wallet_address) >= 3;
```

### Find Repeat Offenders
```sql
SELECT 
    wallet_address,
    COUNT(DISTINCT token_mint) as tokens_sniped,
    AVG(insider_probability) as avg_score
FROM transactions
WHERE insider_probability > 0.7
GROUP BY wallet_address
HAVING COUNT(DISTINCT token_mint) >= 5
ORDER BY tokens_sniped DESC;
```

## API Resources

### Helius
- Dashboard: https://dashboard.helius.dev
- Docs: https://docs.helius.dev
- Pricing: Free tier + paid plans

### Jupiter
- API: https://station.jup.ag/docs/apis
- Quote API: https://quote-api.jup.ag/v6

### Meteora
- Docs: https://docs.meteora.ag
- DLMM SDK: Available on GitHub

### Bitquery
- API: https://graphql.bitquery.io
- Meteora DLMM: Available

## Monitoring Stack

```yaml
Components:
  - Postgres: Wallet/token/transaction storage
  - Redis: Queue + caching
  - API Server: REST endpoints
  - Worker: Background processing
  - Webhook Handler: Real-time ingestion

Data Flow:
  Helius Webhook → Webhook Handler → Redis Queue → Worker → Postgres
                                           ↓
                                    Scoring Engine → Alert System
```

## Key Statistics (2025-2026)

| Metric | Value |
|--------|-------|
| Pump.fun daily launches | ~10,000 |
| Same-block snipe rate | >50% |
| Sniper profitability | 87% |
| Avg sniper profit | 1-100 SOL |
| Deployer-funded rate | ~1.75% of launches |
| Peak activity hours | 14:00-23:00 UTC |

## Contact & Updates

- Research compiled: March 2026
- Sources: Pine Analytics, Nansen, Helius, Mobula
- For latest: Check on-chain data directly
