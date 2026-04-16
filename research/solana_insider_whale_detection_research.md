# Solana Insider/Whale Wallet Pattern Detection: A Comprehensive Research Report

## Executive Summary

This report provides concrete methods for programmatically detecting insider wallets and whale clusters on Solana before they become known. With 98.6% of Pump.fun tokens showing signs of manipulation and sophisticated sniper bots capturing early-stage opportunities, understanding these patterns is critical for any serious market participant.

---

## 1. PRE-LAUNCH INDICATORS

### 1.1 How Insiders Acquire Tokens Before Public Launch

**Key Finding:** Insiders acquire tokens through several mechanisms that leave on-chain traces:

- **Dev/Team Allocations:** Direct minting to controlled addresses before public launch
- **Strategic Investor Pre-sales:** Private allocations at discounted rates
- **Creator Wallet Connections:** Vanity addresses funding "strategic investors" (as seen in the $HAWK case where a vanity address beginning with "HAWK" funded strategic investors who dumped at peak)
- **Bonding Curve Manipulation:** On Pump.fun, the bonding curve pricing inherently favors early buyers

**Detection Methods:**

```python
# Query: Identify wallets that receive tokens directly from mint authority
def detect_prelaunch_allocations(token_mint, launch_slot):
    """
    Find wallets that received tokens from mint authority before public trading
    """
    query = {
        "token_mint": token_mint,
        "from_address": "MINT_AUTHORITY",  # Creator wallet
        "before_slot": launch_slot,
        "min_amount": 0.01  # Filter dust
    }
    # Returns: List of (wallet_address, amount, slot, timestamp)
    return helius.getTokenTransfers(query)

# Query: Trace creator wallet funding patterns
def trace_creator_funding(creator_wallet, hours_before_launch=24):
    """
    Trace where creator wallet got its SOL from
    """
    return helius.getTransactionsForAddress(
        address=creator_wallet,
        before_launch=launch_slot,
        lookback_hours=hours_before_launch
    )
```

### 1.2 Identifying Dev Wallets and Team Allocations

**Heuristics:**

1. **First-Block Mints:** Wallets receiving tokens in the same block as token creation
2. **Large Initial Allocations:** Wallets receiving >5% of total supply at mint
3. **Authority Connections:** Wallets funded by the same source as the mint authority
4. **Freeze Authority Holders:** Wallets retaining token freeze capabilities

**Programmatic Detection:**

```python
# Scoring System for Dev Wallet Identification
def calculate_dev_wallet_score(wallet, token_data):
    score = 0
    
    # Factor 1: Received tokens in first 5 blocks (+40 points)
    if wallet.first_token_block <= token_data.creation_block + 5:
        score += 40
    
    # Factor 2: Received >10% of initial supply (+30 points)
    if wallet.initial_allocation_pct > 10:
        score += 30
    
    # Factor 3: Same funding source as mint authority (+20 points)
    if wallet.funding_source == token_data.mint_authority_funder:
        score += 20
    
    # Factor 4: Has mint/freeze authority (+10 points)
    if wallet.has_authority:
        score += 10
    
    return score  # Score >60 = High probability dev wallet
```

### 1.3 Sniping Patterns - First 1-5 Blocks

**Key Metrics:**

Research shows that sniper transactions are defined as buy trades within the first 3 minutes (approximately 450 blocks on Solana) of a token's first recorded trade.

**Detection Query:**

```python
def detect_snipers(token_mint, launch_slot, launch_timestamp):
    snipers = []
    
    # Get all buy transactions in first 5 blocks
    early_transactions = helius.getTransactionsForAddress(
        token_mint,
        from_slot=launch_slot,
        to_slot=launch_slot + 5
    )
    
    for tx in early_transactions:
        if tx.is_buy and tx.timestamp <= launch_timestamp + 180:  # 3 minutes
            snipers.append({
                'wallet': tx.buyer,
                'amount': tx.amount,
                'slot': tx.slot,
                'seconds_from_launch': tx.timestamp - launch_timestamp,
                'block_position': tx.slot - launch_slot
            })
    
    return snipers
```

**Sniper Probability Score:**

| Factor | Weight | Description |
|--------|--------|-------------|
| Block timing | 35% | Bought within first 3 blocks |
| Amount relative to liquidity | 25% | Large buy relative to initial LP |
| Wallet age | 20% | Newly created wallet (<24h) |
| Gas priority | 15% | Used extreme priority fees |
| Success rate | 5% | Historical sniping success |

### 1.4 Creator Wallet Tracing

**Critical Pattern:** "Deployer-funded, same-block sniping" - Creator funds wallets that immediately buy the token they just created.

```python
def trace_creator_sniping_pattern(token_mint):
    """
    Detect if creator funded wallets that sniped their own token
    """
    # Step 1: Get token creation transaction
    creation_tx = helius.getTransaction(token_mint.creation_signature)
    creator = creation_tx.signer
    
    # Step 2: Get first 10 block transactions
    early_txs = get_early_transactions(token_mint, blocks=10)
    
    # Step 3: Check funding sources of early buyers
    suspicious_wallets = []
    for buyer in early_txs.buyers:
        funding_txs = helius.getTransactionsForAddress(buyer, limit=5)
        for tx in funding_txs:
            if tx.from_address == creator and tx.timestamp < creation_tx.timestamp + 300:
                suspicious_wallets.append({
                    'wallet': buyer,
                    'funding_amount': tx.amount,
                    'funding_time_before_launch': creation_tx.timestamp - tx.timestamp
                })
    
    return suspicious_wallets
```

---

## 2. COORDINATED BUYING PATTERNS

### 2.1 Wallet Cluster Detection (Same Owner, Multiple Addresses)

**Key Heuristics for Solana:**

Solana has a unique account structure with System Accounts controlling Token and Stake Accounts. Clustering must account for:

1. **Common Input Ownership:** Multiple addresses used as inputs in the same transaction
2. **Shared Funding Sources:** Wallets funded from the same origin
3. **Coordinated Timing:** Wallets buying within seconds of each other
4. **Similar Transaction Patterns:** Same programs, similar amounts

**Clustering Algorithm:**

```python
class SolanaWalletClusterer:
    def __init__(self):
        self.clusters = {}
        
    def cluster_by_funding_source(self, wallets, time_window_hours=24):
        """
        Group wallets funded from the same source within time window
        """
        funding_graph = defaultdict(set)
        
        for wallet in wallets:
            # Get first 3 funding transactions
            funding_txs = helius.getFundedBy(wallet, limit=3)
            for tx in funding_txs:
                funding_graph[tx.from_address].add(wallet)
        
        # Wallets sharing 2+ funding sources are likely same entity
        clusters = []
        for source, recipients in funding_graph.items():
            if len(recipients) > 1:
                clusters.append({
                    'funding_source': source,
                    'wallets': list(recipients),
                    'confidence': 'high' if len(recipients) <= 5 else 'medium'
                })
        
        return clusters
    
    def cluster_by_coordinated_buying(self, token_mint, time_window_seconds=30):
        """
        Detect wallets buying the same token within seconds of each other
        """
        buys = helius.getTokenBuys(token_mint, hours=1)
        
        # Group by time buckets
        time_buckets = defaultdict(list)
        for buy in buys:
            bucket = buy.timestamp // time_window_seconds
            time_buckets[bucket].append(buy.wallet)
        
        suspicious_clusters = []
        for bucket, wallets in time_buckets.items():
            if len(wallets) >= 3:  # 3+ wallets buying simultaneously
                suspicious_clusters.append({
                    'wallets': wallets,
                    'timestamp_bucket': bucket,
                    'count': len(wallets),
                    'pattern': 'coordinated_buy'
                })
        
        return suspicious_clusters
```

### 2.2 Time-Based Clustering

**Pattern Detection:**

```python
def detect_time_clustering(token_mint, launch_time):
    """
    Score wallets based on timing patterns
    """
    scores = {}
    
    # Get all buy transactions in first hour
    transactions = helius.getTokenTransactions(
        token_mint,
        from_time=launch_time,
        to_time=launch_time + 3600
    )
    
    # Create timeline
    buy_times = [(tx.wallet, tx.timestamp) for tx in transactions if tx.is_buy]
    
    # Find clusters within 5-second windows
    for i, (wallet1, t1) in enumerate(buy_times):
        for wallet2, t2 in buy_times[i+1:]:
            time_diff = abs(t1 - t2)
            if time_diff <= 5:  # Within 5 seconds
                if wallet1 not in scores:
                    scores[wallet1] = {'cluster_wallets': set(), 'timing_score': 0}
                if wallet2 not in scores:
                    scores[wallet2] = {'cluster_wallets': set(), 'timing_score': 0}
                
                scores[wallet1]['cluster_wallets'].add(wallet2)
                scores[wallet2]['cluster_wallets'].add(wallet1)
                scores[wallet1]['timing_score'] += 1
                scores[wallet2]['timing_score'] += 1
    
    return scores
```

### 2.3 Funding Source Analysis

**CEX Withdrawal Patterns:**

```python
def analyze_funding_sources(wallets):
    """
    Categorize wallet funding sources
    """
    source_categories = {
        'cex': ['binance', 'coinbase', 'okx', 'bybit', 'kraken'],
        'bridge': ['wormhole', 'allbridge', 'debridge'],
        'mixer': [],  # Known mixing services
        'new': [],    # Freshly created wallets
        'other_wallet': []
    }
    
    funding_analysis = {}
    
    for wallet in wallets:
        first_tx = helius.getFundedBy(wallet, limit=1)[0]
        source = first_tx.from_address
        
        # Check if source is labeled CEX
        labels = helius.getAddressLabels(source)
        
        if any(cex in labels for cex in source_categories['cex']):
            category = 'cex'
        elif is_bridge_contract(source):
            category = 'bridge'
        elif is_fresh_wallet(source, hours=1):
            category = 'cascading_fund'  # Funded by new wallet
        else:
            category = 'wallet_transfer'
        
        funding_analysis[wallet] = {
            'source': source,
            'category': category,
            'amount': first_tx.amount,
            'timestamp': first_tx.timestamp
        }
    
    return funding_analysis
```

**Insider Funding Pattern:**

High-probability insider indicator: Wallets funded by the same source within minutes of each other, all buying the same token.

### 2.4 Common CEX Withdrawal Patterns

**Red Flag Pattern:**
- Multiple wallets funded from same CEX account (traceable by timing + amounts)
- Round number withdrawals (100 SOL, 50 SOL)
- Sequential withdrawals in short timeframe
- All funds immediately used to buy same token

```python
def detect_cex_cluster(wallets):
    """
    Detect if wallets were funded from same CEX withdrawal batch
    """
    cex_funded = [w for w in wallets if w.funding_source.is_cex]
    
    clusters = []
    
    # Group by CEX and withdrawal time proximity
    from collections import defaultdict
    cex_groups = defaultdict(list)
    
    for wallet in cex_funded:
        key = (wallet.funding_source.exchange, wallet.funding_time // 300)  # 5-min buckets
        cex_groups[key].append(wallet)
    
    for (exchange, time_bucket), group in cex_groups.items():
        if len(group) >= 3:
            # Check for round numbers
            round_amounts = sum(1 for w in group if w.funding_amount % 10 == 0)
            if round_amounts / len(group) > 0.7:  # 70% round numbers
                clusters.append({
                    'exchange': exchange,
                    'wallets': group,
                    'confidence': 'high',
                    'pattern': 'batch_cex_withdrawal'
                })
    
    return clusters
```

---

## 3. BEHAVIORAL FINGERPRINTS

### 3.1 Trading Style Analysis

**Aggressive vs Conservative Indicators:**

| Metric | Aggressive | Conservative |
|--------|-----------|--------------|
| Position Size | >10% of portfolio | <5% of portfolio |
| Entry Timing | First 10 blocks | After price stabilization |
| Hold Duration | <1 hour average | >24 hours average |
| Slippage Tolerance | >5% | <1% |
| Priority Fees | Aggressive (>10000 μL) | Standard |

```python
def analyze_trading_style(wallet, lookback_days=30):
    """
    Characterize wallet trading behavior
    """
    txs = helius.getTransactionsForAddress(
        wallet,
        lookback_days=lookback_days
    )
    
    metrics = {
        'avg_position_size': calculate_avg_position(txs),
        'avg_hold_time': calculate_hold_duration(txs),
        'slippage_tolerance': estimate_slippage(txs),
        'priority_fee_usage': analyze_priority_fees(txs),
        'entry_timing': analyze_entry_patterns(txs),
        'token_diversity': count_unique_tokens(txs),
        'success_rate': calculate_win_rate(txs)
    }
    
    # Classify style
    if metrics['avg_hold_time'] < 3600 and metrics['priority_fee_usage'] > 0.8:
        style = 'aggressive_sniper'
    elif metrics['avg_hold_time'] > 86400 and metrics['token_diversity'] < 10:
        style = 'conservative_holder'
    elif metrics['success_rate'] > 0.7:
        style = 'smart_money'
    else:
        style = 'retail'
    
    return {'style': style, 'metrics': metrics}
```

### 3.2 Token Selection Criteria

**What Makes Whales Pick Winners:**

Research indicates smart money wallets show these patterns:

1. **Liquidity Thresholds:** Minimum $50K liquidity for consideration
2. **Holder Distribution:** Prefer <50% top 10 holder concentration
3. **Smart Money Co-Buys:** Buy when other labeled smart money buys
4. **Social Signals:** Integrate Twitter/Telegram sentiment
5. **Contract Safety:** Avoid tokens with mint authority or unverified contracts

```python
def score_token_for_smart_money(token_mint):
    """
    Score how attractive a token is to smart money
    """
    scores = {}
    
    # Liquidity score
    liquidity = get_token_liquidity(token_mint)
    scores['liquidity'] = min(liquidity / 100000, 1.0)  # Max at $100K
    
    # Holder distribution
    holders = helius.getTokenLargestAccounts(token_mint)
    top_10_pct = sum(h['amount'] for h in holders[:10]) / get_total_supply(token_mint)
    scores['distribution'] = 1 - top_10_pct  # Lower concentration = better
    
    # Smart money presence
    smart_holders = count_labeled_holders(token_mint, label='smart_money')
    scores['smart_presence'] = min(smart_holders / 5, 1.0)
    
    # Contract safety
    contract = analyze_contract(token_mint)
    scores['safety'] = 1.0 if contract.verified and not contract.mint_authority else 0.3
    
    # Overall attractiveness
    total_score = sum(scores.values()) / len(scores)
    
    return {'total_score': total_score, 'breakdown': scores}
```

### 3.3 Exit Strategy Patterns

**How Whales Sell Without Crashing Price:**

1. **Graduated Selling:** Selling in small increments over time
2. **Multi-Wallet Distribution:** Splitting holdings across wallets, selling from each
3. **Liquidity Provision Exit:** Adding to LP, then removing + fees
4. **OTC Deals:** Large wallet-to-wallet transfers without DEX impact

```python
def detect_whale_exit_pattern(wallet, token_mint):
    """
    Identify how a whale is exiting their position
    """
    sells = get_wallet_sells(wallet, token_mint)
    
    patterns = {
        'graduated': False,
        'multi_wallet': False,
        'liquidity_exit': False,
        'panic_dump': False
    }
    
    # Check for graduated selling
    if len(sells) > 5:
        time_spans = [sells[i+1].timestamp - sells[i].timestamp for i in range(len(sells)-1)]
        avg_span = sum(time_spans) / len(time_spans)
        if avg_span > 3600:  # Averaging >1 hour between sells
            patterns['graduated'] = True
    
    # Check for multi-wallet distribution
    outgoing_transfers = get_large_transfers(wallet, token_mint)
    if len(outgoing_transfers) > 3:
        patterns['multi_wallet'] = True
    
    # Check for LP interaction
    lp_transactions = [tx for tx in sells if 'Raydium' in tx.program or 'Orca' in tx.program]
    if len(lp_transactions) > 0:
        patterns['liquidity_exit'] = True
    
    # Check for panic (large sells in short time)
    if len(sells) > 0:
      recent_sells = [s for s in sells if s.timestamp > time.time() - 3600]
        if sum(s.amount for s in recent_sells) > get_balance(wallet, token_mint) * 0.5:
            patterns['panic_dump'] = True
    
    return patterns
```

### 3.4 Re-Entry Patterns

**Dip Buying Behavior:**

```python
def analyze_reentry_patterns(wallet, token_mint):
    """
    Detect if wallet buys back dips
    """
    transactions = get_token_transactions(wallet, token_mint)
    
    buy_sell_cycles = []
    last_sell_price = None
    
    for tx in transactions:
        if tx.is_sell:
            last_sell_price = tx.price
        elif tx.is_buy and last_sell_price:
            buy_sell_cycles.append({
                'sell_price': last_sell_price,
                'buy_price': tx.price,
                'dip_pct': (last_sell_price - tx.price) / last_sell_price * 100
            })
    
    # Calculate re-entry tendency
    if len(buy_sell_cycles) > 0:
        avg_dip_buy = sum(c['dip_pct'] for c in buy_sell_cycles) / len(buy_sell_cycles)
        reentry_score = len([c for c in buy_sell_cycles if c['dip_pct'] > 10]) / len(buy_sell_cycles)
    else:
        reentry_score = 0
    
    return {
        'reentry_score': reentry_score,
        'cycles': len(buy_sell_cycles),
        'avg_dip_percentage': avg_dip_buy if buy_sell_cycles else 0
    }
```

---

## 4. DATA SOURCES & APIs

### 4.1 Helius APIs for Transaction History

**Enhanced Transactions API:**

```python
# Get parsed transaction history
GET https://api.helius.xyz/v1/wallet/{address}/history?api-key={API_KEY}

# Key parameters:
# - before: Pagination cursor
# - tokenAccounts: 'balanceChanged' (recommended), 'none', or 'all'
# - Returns: Human-readable transactions with balance changes
```

**getTransactionsForAddress (Recommended):**

```python
import requests

def get_all_transactions(address, api_key):
    all_txs = []
    before = None
    
    while True:
        url = f"https://api.helius.xyz/v1/wallet/{address}/history"
        params = {"api-key": api_key}
        if before:
            params["before"] = before
            
        response = requests.get(url, params=params)
        data = response.json()
        
        all_txs.extend(data['data'])
        
        if not data['pagination']['hasMore']:
            break
        before = data['pagination']['nextCursor']
    
    return all_txs
```

**Rate Limits:** 100 transactions per request, manual pagination required.

### 4.2 DAS API for Token Accounts

**Key Methods:**

```python
# Get all assets for a wallet (including tokens)
POST https://mainnet.helius-rpc.com/?api-key={API_KEY}
{
  "jsonrpc": "2.0",
  "id": "my-id",
  "method": "getAssetsByOwner",
  "params": {
    "ownerAddress": "WALLET_ADDRESS",
    "page": 1,
    "limit": 1000,
    "displayOptions": {
      "showFungible": true  # Include fungible tokens
    }
  }
}

# Get token accounts for a mint
{
  "method": "getTokenAccounts",
  "params": {
    "mint": "TOKEN_MINT",
    "page": 1,
    "limit": 100
  }
}

# Get largest holders
# Use standard RPC: getTokenLargestAccounts
```

**Price Data:** Available for top 10K tokens by 24h volume in `token_info.price_info`.

### 4.3 Jupiter/Meteora/DLMM Liquidity Analysis

**Liquidity Pool Monitoring:**

```python
def analyze_liquidity_patterns(token_mint):
    """
    Monitor liquidity additions/removals
    """
    # Jupiter API for pool data
    pools = jupiter.getPools(token_mint)
    
    analysis = {
        'total_liquidity_usd': sum(p.liquidity for p in pools),
        'pool_count': len(pools),
        'concentration_risk': calculate_concentration(pools),
        'recent_additions': get_recent_liquidity_changes(pools, hours=24),
        'recent_removals': get_recent_removals(pools, hours=24)
    }
    
    return analysis
```

**Liquidity Scoring:**
- Healthy: >$100K liquidity, multiple pools
- Risky: <$10K liquidity, single pool
- Dangerous: Liquidity added then immediately removed

### 4.4 Pump.fun Launch Monitoring

**Program ID:** `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`

**Monitoring Strategy:**

```python
# WebSocket subscription to Pump.fun program
import asyncio
import websockets

async def monitor_pumpfun():
    uri = "wss://mainnet.helius-rpc.com/?api-key=API_KEY"
    
    async with websockets.connect(uri) as ws:
        # Subscribe to Pump.fun program logs
        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"]},
                {"commitment": "processed"}
            ]
        }
        await ws.send(json.dumps(subscribe_msg))
        
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            
            # Parse for new token creation
            if is_token_creation(data):
                token_data = extract_token_info(data)
                await analyze_new_launch(token_data)

async def analyze_new_launch(token_data):
    """
    Immediate analysis of new Pump.fun token
    """
    alerts = []
    
    # Check creator history
    creator_score = score_creator_wallet(token_data.creator)
    if creator_score['rug_count'] > 0:
        alerts.append(f"Creator has {creator_score['rug_count']} previous rugs")
    
    # Monitor first 10 blocks for snipers
    snipers = await detect_snipers(token_data.mint, blocks=10)
    if len(snipers) > 5:
        alerts.append(f"High sniper activity: {len(snipers)} wallets")
    
    # Check for dev buying own token
    dev_buys = check_dev_purchases(token_data)
    if dev_buys:
        alerts.append("Creator immediately bought own token")
    
    return {
        'token': token_data,
        'risk_score': calculate_risk_score(alerts),
        'alerts': alerts,
        'snipers': snipers
    }
```

---

## 5. INSIDER PROBABILITY SCORING SYSTEM

### 5.1 Wallet-Level Scoring

```python
class InsiderProbabilityScorer:
    def __init__(self):
        self.weights = {
            'prelaunch_allocation': 0.25,
            'creator_connection': 0.20,
            'sniper_timing': 0.20,
            'cluster_association': 0.15,
            'behavioral_pattern': 0.15,
            'funding_source': 0.05
        }
    
    def score_wallet(self, wallet, token_mint):
        scores = {}
        
        # 1. Pre-launch allocation (0-100)
        scores['prelaunch_allocation'] = self.check_prelaunch_allocation(wallet, token_mint)
        
        # 2. Creator connection (0-100)
        scores['creator_connection'] = self.check_creator_connection(wallet, token_mint)
        
        # 3. Sniper timing (0-100)
        scores['sniper_timing'] = self.score_sniper_timing(wallet, token_mint)
        
        # 4. Cluster association (0-100)
        scores['cluster_association'] = self.score_cluster_risk(wallet)
        
        # 5. Behavioral pattern (0-100)
        scores['behavioral_pattern'] = self.score_behavioral_risk(wallet)
        
        # 6. Funding source (0-100)
        scores['funding_source'] = self.score_funding_risk(wallet)
        
        # Calculate weighted total
        total_score = sum(
            scores[k] * self.weights[k] for k in self.weights.keys()
        )
        
        return {
            'total_score': total_score,
            'risk_level': self.categorize_risk(total_score),
            'component_scores': scores
        }
    
    def categorize_risk(self, score):
        if score >= 75:
            return 'CRITICAL_INSIDER'
        elif score >= 50:
            return 'HIGH_RISK'
        elif score >= 25:
            return 'MEDIUM_RISK'
        else:
            return 'LOW_RISK'
```

### 5.2 Token-Level Scoring

```python
def score_token_insider_risk(token_mint):
    """
    Aggregate insider risk across all token holders
    """
    # Get all holders
    holders = helius.getTokenLargestAccounts(token_mint)
    
    holder_scores = []
    insider_concentration = 0
    
    for holder in holders:
        score = InsiderProbabilityScorer().score_wallet(holder['address'], token_mint)
        holder_scores.append({
            'wallet': holder['address'],
            'amount': holder['amount'],
            'score': score['total_score'],
            'level': score['risk_level']
        })
        
        if score['risk_level'] in ['CRITICAL_INSIDER', 'HIGH_RISK']:
            insider_concentration += holder['amount']
    
    total_supply = get_total_supply(token_mint)
    insider_pct = insider_concentration / total_supply * 100
    
    return {
        'token': token_mint,
        'insider_concentration_pct': insider_pct,
        'high_risk_holders': len([h for h in holder_scores if h['level'] in ['CRITICAL_INSIDER', 'HIGH_RISK']]),
        'holder_scores': sorted(holder_scores, key=lambda x: x['score'], reverse=True)[:20],
        'overall_risk': 'EXTREME' if insider_pct > 50 else 'HIGH' if insider_pct > 30 else 'MEDIUM' if insider_pct > 15 else 'LOW'
    }
```

---

## 6. BUILDING A WALLET INTELLIGENCE SYSTEM

### 6.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Wallet Intelligence System                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Data Layer   │  │ Analysis     │  │ Alert        │          │
│  │              │  │ Engine       │  │ System       │          │
│  │ - Helius RPC │  │ - Scoring    │  │ - Webhooks   │          │
│  │ - DAS API    │  │ - Clustering │  │ - Telegram   │          │
│  │ - Jupiter    │  │ - ML Models  │  │ - Discord    │          │
│  │ - Pump.fun   │  │ - Graph      │  │ - Dashboard  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌──────────────────────────────────────────────────────┐     │
│  │              Knowledge Graph Database                 │     │
│  │  (Neo4j/PostgreSQL + TimescaleDB for time-series)    │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Continuous Monitoring Pipeline

```python
class WalletIntelligenceSystem:
    def __init__(self):
        self.scorer = InsiderProbabilityScorer()
        self.alerts = AlertManager()
        self.db = KnowledgeGraph()
        
    async def monitor_new_launches(self):
        """
        Real-time monitoring of Pump.fun and Raydium launches
        """
        while True:
            # Get new tokens from last 5 minutes
            new_tokens = self.get_recent_launches(minutes=5)
            
            for token in new_tokens:
                # Immediate risk assessment
                risk_report = score_token_insider_risk(token['mint'])
                
                # Store in knowledge graph
                self.db.store_token_risk(risk_report)
                
                # Alert if high risk
                if risk_report['overall_risk'] in ['EXTREME', 'HIGH']:
                    self.alerts.send_alert({
                        'type': 'HIGH_RISK_LAUNCH',
                        'token': token['mint'],
                        'risk_score': risk_report['insider_concentration_pct'],
                        'details': risk_report
                    })
    
    async def monitor_wallet_clusters(self):
        """
        Continuously update wallet cluster assignments
        """
        while True:
            # Get wallets with recent activity
            active_wallets = self.db.get_active_wallets(hours=1)
            
            # Update clusters
            clusters = self.cluster_by_funding_source(active_wallets)
            
            for cluster in clusters:
                # Check if this is a new cluster
                existing = self.db.get_cluster(cluster['funding_source'])
                
                if not existing:
                    self.alerts.send_alert({
                        'type': 'NEW_WALLET_CLUSTER',
                        'funding_source': cluster['funding_source'],
                        'wallet_count': len(cluster['wallets']),
                        'wallets': cluster['wallets']
                    })
                
                self.db.update_cluster(cluster)
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def detect_coordinated_movement(self):
        """
        Detect when wallet clusters move together
        """
        clusters = self.db.get_all_clusters()
        
        for cluster in clusters:
            # Check for coordinated buying
            recent_buys = self.get_cluster_buys(cluster, minutes=30)
            
            if len(recent_buys) >= 3:  # 3+ wallets from cluster bought
                token = recent_buys[0]['token']
                
                # Check if they're all buying same token
                if all(b['token'] == token for b in recent_buys):
                    self.alerts.send_alert({
                        'type': 'COORDINATED_BUY',
                        'cluster': cluster['id'],
                        'token': token,
                        'participating_wallets': [b['wallet'] for b in recent_buys],
                        'total_volume': sum(b['amount'] for b in recent_buys)
                    })
```

### 6.3 Key Queries for Detection

**Query 1: Find wallets funded by same source that all bought same token**

```cypher
// Neo4j Cypher query
MATCH (f:Wallet)-[:FUNDED]->(w:Wallet)-[:BOUGHT]->(t:Token)
WHERE t.mint = $token_mint
  AND w.first_buy_time < t.launch_time + 300  // Within 5 min of launch
WITH f, collect(DISTINCT w) as funded_wallets, t
WHERE size(funded_wallets) >= 3
RETURN f.address as funding_source,
       size(funded_wallets) as wallet_count,
       [w in funded_wallets | w.address] as wallets,
       t.mint as token
```

**Query 2: Find creator-connected snipers**

```cypher
MATCH (c:Wallet)-[:CREATED]->(t:Token)<-[:BOUGHT]-(w:Wallet)
WHERE (c)-[:FUNDED]->(w) OR (c)-[:INTERACTED_WITH]->(w)
  AND w.buy_slot <= t.creation_slot + 5
RETURN c.address as creator,
       t.mint as token,
       collect({wallet: w.address, slot: w.buy_slot, amount: w.buy_amount}) as snipers
```

**Query 3: Detect wash trading patterns**

```cypher
MATCH (w1:Wallet)-[:SOLD]->(t:Token)<-[:BOUGHT]-(w2:Wallet)
WHERE w1 <> w2
  AND (w1)-[:FUNDED|INTERACTED_WITH]-(w2)  // Connected wallets
  AND w1.sell_time - w2.buy_time < 60  // Within 1 minute
WITH t, w1, w2, count(*) as trade_count
WHERE trade_count > 6  // More than 6 circular trades
RETURN t.mint as token,
       w1.address as wallet1,
       w2.address as wallet2,
       trade_count,
       'WASH_TRADING_SUSPECTED' as alert
```

---

## 7. RED FLAGS & ALERTS

### 7.1 Critical Alerts (Immediate Action)

1. **Creator Self-Sniping:** Creator-funded wallets buying within first block
2. **Extreme Concentration:** Top 10 wallets hold >70% of supply
3. **Known Rugger:** Creator wallet associated with previous rugs
4. **Instant Migration:** Token migrated to Raydium within minutes of launch

### 7.2 High-Priority Alerts

1. **Coordinated Cluster:** 5+ connected wallets buying same token
2. **Sniper Army:** >10 snipers detected in first 3 blocks
3. **Liquidity Removal:** Large LP removal by creator after pump
4. **Team Selling:** Team wallets selling while promoting on social

### 7.3 Medium-Priority Alerts

1. **Fresh Wallet Cluster:** Multiple new wallets funded from same source
2. **Unusual Trading Pattern:** Aggressive bot-like behavior
3. **Social Mismatch:** High on-chain activity but low social presence

---

## 8. IMPLEMENTATION CHECKLIST

### Phase 1: Data Infrastructure (Week 1-2)
- [ ] Set up Helius API access with adequate rate limits
- [ ] Deploy PostgreSQL + TimescaleDB for time-series data
- [ ] Implement WebSocket connections for real-time monitoring
- [ ] Set up knowledge graph (Neo4j) for relationship tracking

### Phase 2: Core Detection (Week 3-4)
- [ ] Implement pre-launch allocation detection
- [ ] Build sniper detection for first 10 blocks
- [ ] Create funding source tracing
- [ ] Develop wallet clustering algorithms

### Phase 3: Scoring System (Week 5-6)
- [ ] Build insider probability scoring
- [ ] Implement behavioral analysis
- [ ] Create token risk aggregation
- [ ] Calibrate scoring thresholds

### Phase 4: Monitoring & Alerts (Week 7-8)
- [ ] Deploy continuous monitoring pipeline
- [ ] Set up multi-channel alerting
- [ ] Build dashboard for visualization
- [ ] Implement backtesting framework

---

## 9. REFERENCES & DATA SOURCES

1. **Helius Documentation:** https://docs.helius.dev
2. **DAS API Reference:** https://www.helius.dev/docs/das-api
3. **Enhanced Transactions API:** https://www.helius.dev/docs/wallet-api/history
4. **Pump.fun Program ID:** `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`
5. **Chainalysis Solana Clustering:** https://www.chainalysis.com/blog/solana-chainalysis/
6. **Nansen Smart Money:** https://www.nansen.ai
7. **Solidus Labs Pump.fun Research:** https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance

---

## 10. CONCLUSION

Detecting insider wallets and whale clusters on Solana requires a multi-layered approach combining:

1. **Pre-launch forensics** - tracing creator connections and early allocations
2. **On-chain clustering** - identifying same-entity wallets through funding and timing patterns  
3. **Behavioral analysis** - distinguishing smart money from retail through trading patterns
4. **Continuous monitoring** - real-time detection of coordinated movements

With 98.6% of Pump.fun tokens showing manipulation patterns, a robust Wallet Intelligence System is essential for anyone serious about Solana trading. The techniques and code samples in this report provide a foundation for building such a system.

**Key Takeaway:** Insiders leave traces. The combination of pre-launch allocations, coordinated buying patterns, and behavioral fingerprints makes programmatic detection not just possible, but essential for navigating the Solana memecoin ecosystem.
