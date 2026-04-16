# Stealth/Insider Solana Wallet Research Report
## Finding Alpha Through On-Chain Analysis

---

## 1. ON-CHAIN ANALYSIS TECHNIQUES

### 1.1 Identifying Early Buyers & Peak Sellers

**Key Patterns to Detect:**

| Pattern | Description | Detection Method |
|---------|-------------|------------------|
| **Sniper Wallets** | Buy within 0-3 blocks of token launch | Block proximity analysis + timing |
| **Pre-Launch Accumulation** | Funded just before token creation | Wallet creation date + funding patterns |
| **Strategic Exits** | Sell before major dumps | Exchange inflow monitoring + holder distribution |
| **Front-running** | High priority fees + MEV bundles | Gas behavior analysis + transaction ordering |

**Early Buyer Detection Algorithm:**
```python
# Detect wallets that buy within first N blocks of token launch
EARLY_BUYER_BLOCKS = 3  # blocks after launch

def detect_early_buyers(token_launch_slot, transactions):
    early_buyers = []
    for tx in transactions:
        blocks_after_launch = tx['slot'] - token_launch_slot
        if blocks_after_launch <= EARLY_BUYER_BLOCKS:
            early_buyers.append({
                'wallet': tx['buyer'],
                'blocks_after_launch': blocks_after_launch,
                'tx_position': tx['index_in_block'],
                'amount': tx['amount'],
                'priority_fee': tx['priority_fee']
            })
    return early_buyers
```

### 1.2 Transaction Pattern Analysis

**Critical Timing Metrics:**
- **Block Proximity**: Transactions in same/next block as deployment
- **Transaction Index**: Position within block (lower = earlier)
- **Funding-to-Trade Gap**: Time between wallet funding and first trade
- **Hold Duration**: Time between buy and sell transactions

**Frequency Analysis:**
```python
# Calculate trading frequency patterns
def analyze_trading_frequency(wallet_txs, timeframe_hours=24):
    from collections import Counter
    
    timestamps = [tx['timestamp'] for tx in wallet_txs]
    timestamps.sort()
    
    # Calculate intervals between trades
    intervals = []
    for i in range(1, len(timestamps)):
        interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 60  # minutes
        intervals.append(interval)
    
    return {
        'avg_interval_minutes': sum(intervals) / len(intervals) if intervals else 0,
        'min_interval': min(intervals) if intervals else 0,
        'max_interval': max(intervals) if intervals else 0,
        'trades_per_hour': len(wallet_txs) / timeframe_hours,
        'burst_trading': len([i for i in intervals if i < 2])  # trades < 2 min apart
    }
```

### 1.3 Front-Running Detection

**Indicators of Front-Running:**
- High priority fees relative to network average
- Transaction lands in same block as target transaction
- MEV bundle participation
- Consistent timing advantage across multiple trades

```python
# Detect potential front-running behavior
FRONT_RUN_THRESHOLD_BLOCKS = 1
HIGH_PRIORITY_FEE_MULTIPLIER = 2.0

def detect_frontrunning(wallet_txs, network_avg_fee):
    suspicious_txs = []
    
    for tx in wallet_txs:
        # Check for high priority fees
        fee_multiplier = tx['priority_fee'] / network_avg_fee if network_avg_fee > 0 else 0
        
        # Check for Jito bundle or MEV
        is_mev = tx.get('is_jito_bundle', False) or tx.get('mev_protection', False)
        
        if fee_multiplier > HIGH_PRIORITY_FEE_MULTIPLIER or is_mev:
            suspicious_txs.append({
                'signature': tx['signature'],
                'fee_multiplier': fee_multiplier,
                'is_mev': is_mev,
                'blocks_before_major_move': tx.get('blocks_before_pump', 0)
            })
    
    return suspicious_txs
```

### 1.4 Cluster Analysis - Finding Related Wallets

**Cluster Detection Methods:**

| Method | Signal Detected | Implementation |
|--------|-----------------|----------------|
| **Common Funder** | Multiple wallets funded from same source | Trace SOL transfers backward |
| **Transaction Graph** | Wallets that frequently transact with each other | Build adjacency matrix |
| **Timing Correlation** | Wallets buying/selling simultaneously | Cross-correlation analysis |
| **Amount Clustering** | Similar trade sizes across wallets | Statistical clustering (K-means) |

```python
# Wallet cluster detection using multiple signals
from sklearn.cluster import DBSCAN
import numpy as np

def detect_wallet_clusters(wallets_data, eps=0.3, min_samples=3):
    features = []
    wallet_ids = []
    
    for wallet, data in wallets_data.items():
        wallet_ids.append(wallet)
        # Feature vector: [avg_trade_size, funding_source_hash, avg_hold_time, trade_frequency]
        features.append([
            data['avg_trade_size'],
            hash(data.get('funding_source', '')) % 1000,
            data['avg_hold_time_hours'],
            data['trades_per_day']
        ])
    
    features = np.array(features)
    
    # Normalize features
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    features_normalized = scaler.fit_transform(features)
    
    # DBSCAN clustering
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(features_normalized)
    
    # Group wallets by cluster
    clusters = {}
    for idx, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(wallet_ids[idx])
    
    # Filter out noise (label = -1)
    return {k: v for k, v in clusters.items() if k != -1}
```

---

## 2. TOOLS & PLATFORMS

### 2.1 Helius RPC - Enhanced Transactions

**Key API Endpoints:**

```python
# Helius Enhanced Transaction API
HELIUS_BASE_URL = "https://api-mainnet.helius-rpc.com/v0"
API_KEY = "your_api_key"

def fetch_enhanced_transactions(wallet_address, api_key, transaction_type=None):
    """
    Types: NFT_SALE, TRANSFER, SWAP, COMPRESSED_NFT_MINT, etc.
    """
    url = f"{HELIUS_BASE_URL}/addresses/{wallet_address}/transactions?api-key={api_key}"
    
    if transaction_type:
        url += f"&type={transaction_type}"
    
    import requests
    response = requests.get(url)
    return response.json()

# Pagination for high-volume addresses
def fetch_all_transactions(wallet_address, api_key):
    all_transactions = []
    last_signature = None
    
    while True:
        url = f"{HELIUS_BASE_URL}/addresses/{wallet_address}/transactions?api-key={api_key}&limit=100"
        if last_signature:
            url += f"&before={last_signature}"
        
        response = requests.get(url)
        transactions = response.json()
        
        if not transactions:
            break
            
        all_transactions.extend(transactions)
        last_signature = transactions[-1]['signature']
        
        if len(transactions) < 100:
            break
    
    return all_transactions
```

### 2.2 Dune Analytics - SQL Queries

**Essential Queries:**

```sql
-- Query 1: Top Profitable Wallets for a Token
WITH token_trades AS (
  SELECT 
    trader,
    token_bought_amount,
    token_sold_amount,
    amount_usd,
    block_time,
    tx_id
  FROM dex_solana.trades
  WHERE token_bought_address = '{{token_address}}'
     OR token_sold_address = '{{token_address}}'
),
wallet_pnl AS (
  SELECT 
    trader,
    SUM(CASE WHEN token_bought_address = '{{token_address}}' THEN -amount_usd 
             ELSE amount_usd END) as net_pnl,
    COUNT(*) as trade_count
  FROM token_trades
  GROUP BY trader
)
SELECT * FROM wallet_pnl 
WHERE net_pnl > 0 AND trade_count >= 5
ORDER BY net_pnl DESC
LIMIT 100;
```

```sql
-- Query 2: Early Buyer Detection
WITH token_launch AS (
  SELECT MIN(block_slot) as launch_slot
  FROM dex_solana.trades
  WHERE token_bought_address = '{{token_address}}'
),
early_buyers AS (
  SELECT 
    t.trader,
    t.block_slot - l.launch_slot as blocks_after_launch,
    t.token_bought_amount,
    t.amount_usd
  FROM dex_solana.trades t
  CROSS JOIN token_launch l
  WHERE t.token_bought_address = '{{token_address}}'
    AND t.block_slot - l.launch_slot <= 3
)
SELECT 
  trader,
  COUNT(*) as early_buys,
  SUM(token_bought_amount) as total_bought
FROM early_buyers
GROUP BY trader
ORDER BY early_buys DESC;
```

### 2.3 Birdeye API - Wallet PnL

```python
# Birdeye Wallet PnL API
BIRDEYE_API_KEY = "your_api_key"
BIRDEYE_BASE = "https://public-api.birdeye.so"

def get_wallet_pnl(wallet_address):
    """Get realized and unrealized PnL for a wallet"""
    url = f"{BIRDEYE_BASE}/v1/wallet/pnl?wallet={wallet_address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    import requests
    response = requests.get(url, headers=headers)
    data = response.json()
    
    return {
        'realized_pnl': data.get('realizedPnl', 0),
        'unrealized_pnl': data.get('unrealizedPnl', 0),
        'total_pnl': data.get('totalPnl', 0),
        'win_rate': data.get('winRate', 0),
        'total_trades': data.get('totalTrades', 0)
    }
```

---

## 3. STEALTH WALLET CHARACTERISTICS

### 3.1 Detection Signals

```python
STEALTH_WALLET_CRITERIA = {
    'min_wallet_age_days': 180,  # 6+ months old
    'max_twitter_followers': 100,  # Not an influencer
    'min_avg_hold_days': 7,  # Not a scalper
    'max_daily_trades': 10,  # Not a bot
    'min_win_rate': 0.60,  # 60%+ win rate
    'min_realized_pnl_sol': 50,  # Profitable
    'max_tokens_held': 20,  # Focused, not scattered
}

def is_stealth_alpha_wallet(wallet_data):
    checks = {
        'age_check': wallet_data['age_days'] >= STEALTH_WALLET_CRITERIA['min_wallet_age_days'],
        'win_rate_check': wallet_data['win_rate'] >= STEALTH_WALLET_CRITERIA['min_win_rate'],
        'profit_check': wallet_data['realized_pnl_sol'] >= STEALTH_WALLET_CRITERIA['min_realized_pnl_sol'],
        'activity_check': wallet_data['avg_daily_trades'] <= STEALTH_WALLET_CRITERIA['max_daily_trades'],
        'focus_check': wallet_data['unique_tokens_traded'] <= STEALTH_WALLET_CRITERIA['max_tokens_held'],
    }
    
    score = sum(checks.values()) / len(checks)
    return {
        'is_stealth_alpha': score >= 1.0,
        'score': score,
        'checks': checks
    }
```

### 3.2 Multi-Wallet Detection

```python
def trace_funding_source(wallet, depth=3):
    """Trace back through funding hops to find original source"""
    current_wallet = wallet
    path = [current_wallet]
    
    for i in range(depth):
        incoming = get_incoming_transfers(current_wallet, limit=10)
        if not incoming:
            break
            
        largest = max(incoming, key=lambda x: x['amount'])
        funder = largest['sender']
        path.append({'wallet': funder, 'amount': largest['amount']})
        current_wallet = funder
    
    return path
```

---

## 4. PROFITABILITY METRICS

### 4.1 ROI Calculations

```python
def calculate_realized_roi(trades):
    total_invested = sum(t['amount_usd'] for t in trades if t['type'] == 'buy')
    total_returned = sum(t['amount_usd'] for t in trades if t['type'] == 'sell')
    
    if total_invested == 0:
        return 0
    
    roi = ((total_returned - total_invested) / total_invested) * 100
    return {
        'roi_percent': roi,
        'total_invested': total_invested,
        'total_returned': total_returned,
        'net_profit': total_returned - total_invested
    }
```

### 4.2 Win Rate Analysis

```python
def calculate_win_rate_metrics(trades_by_token):
    wins = losses = 0
    win_amounts = []
    loss_amounts = []
    
    for token, trades in trades_by_token.items():
        pnl = calculate_token_pnl(trades)
        if pnl > 0:
            wins += 1
            win_amounts.append(pnl)
        elif pnl < 0:
            losses += 1
            loss_amounts.append(abs(pnl))
    
    total_trades = wins + losses
    avg_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0
    avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0
    
    profit_factor = sum(win_amounts) / sum(loss_amounts) if loss_amounts else float('inf')
    
    return {
        'win_rate': (wins / total_trades * 100) if total_trades > 0 else 0,
        'avg_win_usd': avg_win,
        'avg_loss_usd': avg_loss,
        'profit_factor': profit_factor
    }
```

### 4.3 Holding Time Analysis

```python
def analyze_holding_patterns(trades_by_token):
    hold_times = []
    
    for token, trades in trades_by_token.items():
        buys = [t for t in trades if t['type'] == 'buy']
        sells = [t for t in trades if t['type'] == 'sell']
        
        for sell in sells:
            if buys:
                buy = buys.pop(0)
                hold_time = (sell['timestamp'] - buy['timestamp']).total_seconds() / 3600
                hold_times.append(hold_time)
    
    # Classification
    scalper = len([h for h in hold_times if h < 1/60])
    day_trade = len([h for h in hold_times if 1/60 <= h < 24])
    swing = len([h for h in hold_times if 24 <= h < 168])
    holder = len([h for h in hold_times if h >= 168])
    
    return {
        'avg_hold_hours': sum(hold_times) / len(hold_times) if hold_times else 0,
        'style': max([('SCALPER', scalper), ('DAY', day_trade), 
                      ('SWING', swing), ('HOLDER', holder)], key=lambda x: x[1])[0]
    }
```

### 4.4 Sharpe Ratio

```python
import math

def calculate_sharpe_ratio(daily_returns, risk_free_rate=0.02):
    if not daily_returns or len(daily_returns) < 2:
        return 0
    
    avg_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - avg_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std_dev = math.sqrt(variance)
    
    if std_dev == 0:
        return 0
    
    # Annualize
    annual_return = avg_return * 365
    annual_std = std_dev * math.sqrt(365)
    
    return (annual_return - risk_free_rate) / annual_std
```

---

## 5. KEY FINDINGS SUMMARY

### Most Profitable Wallet Types to Track:

1. **The "Ghost" Trader**
   - Wallet age: 6+ months
   - No social media presence
   - 60-75% win rate
   - 7-30 day hold times
   - 50+ SOL realized profit

2. **The Early Sniper (Non-Bot)**
   - Buys within 1-3 blocks of launch
   - Uses moderate gas (not MEV)
   - Sells 50-200% gains consistently
   - Doesn't ape into everything

3. **The Insider Cluster**
   - Multiple wallets funded from same source
   - Buy same tokens within hours of each other
   - Show consistent profitability across cluster
   - Use CEX exits

### Red Flags to Avoid:

- Wallets with >100% win rate (likely fake/bot)
- <2 minute hold times consistently (bot)
- Fresh wallets (<30 days) with high activity
- Wallets that only trade one token (shillers)
- Clusters with 50%+ of token supply

### Actionable Implementation Priority:

1. **Start with Helius API** - Free tier, enhanced transactions
2. **Use Dune for backtesting** - SQL queries on historical data
3. **Implement cluster detection** - Trace funding sources
4. **Build scoring algorithm** - Weight the criteria
5. **Monitor in real-time** - Webhooks for new trades

---

## API RESOURCES

| Service | Free Tier | Best For |
|---------|-----------|----------|
| Helius | 10M credits/month | Transaction parsing, webhooks |
| Birdeye | 100K calls/month | PnL tracking, token prices |
| Dune | Community queries | SQL analysis, backtesting |
| Solscan | 10 calls/second | Basic explorer data |
| QuickNode | 100K requests/month | Reliable RPC |

---

*Report compiled: March 2026*
*Focus: Finding true alpha through on-chain analysis, not social signals*