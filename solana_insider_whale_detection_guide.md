# Solana Insider/Whale Wallet Intelligence System
## A Comprehensive Guide to Detecting Coordinated Market Manipulation

**Research Date:** March 2026  
**Focus:** Pre-launch indicators, coordinated buying patterns, behavioral fingerprints, and programmatic detection

---

## 1. PRE-LAUNCH INDICATORS

### 1.1 How Insiders Acquire Tokens Before Public Launch

#### The Pump.fun Same-Block Sniping Phenomenon
- **Scale:** Over 50% of tokens on Pump.fun are sniped in the creation block
- **Mechanism:** Deployers transfer SOL to "sniper wallets" that buy in the same block as token creation
- **Requirements:** Pre-signed transactions, off-chain coordination, or shared infrastructure between deployers and buyers

#### Detection Heuristics for Pre-Launch Acquisition

| Signal | Detection Method | Confidence |
|--------|------------------|------------|
| Same-block sniping | Buy transaction in same block as token creation | High |
| Deployer funding | Direct SOL transfer from deployer to buyer before launch | Very High |
| Pre-signed transactions | Transaction prepared before token address is public | High |
| Private RPC usage | High priority fees or MEV bundles | Medium |

#### Critical Finding: Funding Chain Detection
The most reliable indicator of insider coordination is **direct SOL transfer between deployer and sniper wallet before launch**:

```
Case Study Pattern:
Deployer Wallet → [funds] → Sniper Wallet A (0.4 SOL)
             → [funds] → Sniper Wallet B (0.4 SOL)  
             → [funds] → Sniper Wallet C (0.4 SOL)
             → [deploys] → Token
All 3 snipers buy in creation block → coordinated flash exit
```

**Key Statistics:**
- 15,000+ tokens sniped by funded wallets in one month
- 4,600+ sniper wallets identified
- 10,400+ deployers involved
- 87% sniper profitability rate
- Average profit: 1-100 SOL per wallet (some exceed 500 SOL)

### 1.2 Identifying Dev Wallets and Team Allocations

#### Developer Wallet Detection Methods

| Method | Implementation | Indicators |
|--------|----------------|------------|
| Contract deployment tracing | Track token mint authority | Deployer = highest privilege |
| Update authority analysis | Check metaplex metadata update authority | Often equals deployer |
| Liquidity provider identification | First LP token holder | Dev often provides initial liquidity |
| Fee recipient tracking | Where do protocol fees go? | Dev treasury wallets |

#### Red Flags in Dev Behavior

1. **Early selling while promoting** - Team selling while publicly shilling
2. **Renounced contracts with hidden backdoors** - Check for mint authority or freeze authority
3. **Multiple deployments** - Same deployer launching dozens of tokens (farming behavior)
4. **Hidden allocations** - Tokens minted to wallets not in public distribution

### 1.3 Sniping Patterns - First 1-5 Blocks

#### Sniper Detection Algorithm

```python
# Pseudocode for sniper detection
def detect_snipers(token_launch_block, transactions):
    snipers = []
    for tx in transactions:
        block_diff = tx.block - token_launch_block
        
        # Sniping indicators
        is_early_buy = block_diff <= 3
        is_first_interaction = is_token_first_buy(tx)
        wallet_age = get_wallet_age(tx.signer)
        funding_pattern = analyze_funding(tx.signer, hours_before=24)
        
        # Scoring
        score = 0
        if block_diff == 0: score += 40  # Same block
        elif block_diff <= 3: score += 25
        if wallet_age < 7: score += 20  # Fresh wallet
        if funding_pattern == 'cex_withdrawal': score += 10
        if funding_pattern == 'deployer_funded': score += 50  # Critical
        if tx.priority_fee > 10000: score += 15  # High gas
        
        if score >= 60:
            snipers.append({
                'wallet': tx.signer,
                'score': score,
                'block_diff': block_diff,
                'funding_source': funding_pattern
            })
    
    return snipers
```

#### Sniper Categories

| Type | Characteristics | Risk Level |
|------|-----------------|------------|
| Net-casting luck bots | Testing heuristics, small scale | Low-Medium |
| Coordinated insiders | Deployer-funded, same-block | Very High |
| MEV searchers | Front-running, no deployer link | Medium |
| Sophisticated snipers | Private RPC, pre-signed txs | High |

### 1.4 Creator Wallet Tracing

#### Mint Authority Tracing

```javascript
// Using Helius DAS API to trace token creation
const traceCreator = async (mintAddress) => {
  // Get token metadata
  const metadata = await fetch(`https://mainnet.helius-rpc.com/?api-key=KEY`, {
    method: 'POST',
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 'my-request',
      method: 'getAsset',
      params: { id: mintAddress }
    })
  });
  
  // Find create instruction in transaction history
  const sigs = await connection.getSignaturesForAddress(mintAddress, { limit: 100 });
  const earliestTx = sigs[sigs.length - 1]; // First transaction
  
  // Parse for mint instruction
  const txDetails = await connection.getTransaction(earliestTx.signature);
  const creator = extractCreatorFromInstructions(txDetails);
  
  return {
    mint: mintAddress,
    creator: creator,
    creationTime: earliestTx.blockTime,
    transaction: earliestTx.signature
  };
};
```

#### Multi-Hop Funding Chain Detection

```
Deployer Wallet
    ↓ (0.5 SOL)
Intermediate Wallet A (1 hour delay)
    ↓ (0.5 SOL)  
Intermediate Wallet B (30 min delay)
    ↓ (0.5 SOL)
Sniper Wallet → Buys token in first block
```

**Detection Strategy:**
- Look for funding within 24-48 hours before launch
- Trace back 2-3 hops from sniper wallets
- Flag wallets that appear in multiple token launch funding chains
- Time-based clustering: funding + buying within short windows

---

## 2. COORDINATED BUYING PATTERNS

### 2.1 Wallet Cluster Detection (Same Owner, Multiple Addresses)

#### Clustering Heuristics for Solana

Solana's unique account structure complicates clustering:
- Main System Account holds SOL
- Multiple Token Accounts for each SPL token
- Associated Token Accounts for each mint
- Stake Accounts for staking

**Clustering Signals:**

| Signal | Weight | Detection Method |
|--------|--------|------------------|
| Same funding source | 0.90 | Trace SOL transfers within 24h |
| Similar transaction timing | 0.75 | Time correlation analysis (±60 seconds) |
| Identical token selection | 0.60 | Same tokens bought across wallets |
| Synchronized exits | 0.80 | Sell timing correlation |
| Round number transfers | 0.70 | 0.5 SOL, 1 SOL, 2 SOL patterns |
| Cross-wallet transfers | 0.85 | Direct transfers between suspected wallets |

#### Cluster Detection Algorithm

```python
class WalletClusterDetector:
    def __init__(self):
        self.funding_graph = nx.DiGraph()
        self.timing_graph = nx.Graph()
        self.token_overlap = defaultdict(set)
    
    def build_funding_graph(self, wallets, timeframe_days=7):
        """Build graph of wallet funding relationships"""
        for wallet in wallets:
            funding_txs = self.get_funding_transactions(wallet, timeframe_days)
            for tx in funding_txs:
                source = tx.source
                self.funding_graph.add_edge(source, wallet, 
                    weight=tx.amount, 
                    timestamp=tx.timestamp)
    
    def detect_temporal_clusters(self, token_launch_time, transactions, window_seconds=120):
        """Find wallets buying within same time window"""
        buys = [tx for tx in transactions if tx.type == 'buy']
        clusters = []
        
        for i, tx1 in enumerate(buys):
            cluster = [tx1]
            for tx2 in buys[i+1:]:
                time_diff = abs(tx1.timestamp - tx2.timestamp)
                if time_diff <= window_seconds:
                    cluster.append(tx2)
            
            if len(cluster) >= 3:  # Minimum cluster size
                clusters.append({
                    'wallets': [tx.signer for tx in cluster],
                    'time_span': max(t.timestamp for t in cluster) - min(t.timestamp for t in cluster),
                    'avg_buy_amount': mean(tx.amount for tx in cluster)
                })
        
        return clusters
    
    def calculate_cluster_confidence(self, wallets):
        """Calculate confidence score for wallet cluster"""
        signals = {
            'same_funder': self.have_common_funder(wallets),
            'temporal_correlation': self.temporal_correlation_score(wallets),
            'token_overlap': self.token_overlap_score(wallets),
            'exit_correlation': self.exit_pattern_correlation(wallets),
            'transfer_patterns': self.cross_transfer_detection(wallets)
        }
        
        weights = {
            'same_funder': 0.30,
            'temporal_correlation': 0.20,
            'token_overlap': 0.15,
            'exit_correlation': 0.20,
            'transfer_patterns': 0.15
        }
        
        confidence = sum(signals[k] * weights[k] for k in signals)
        return confidence
```

### 2.2 Time-Based Clustering

#### Coordinated Buy Detection

**Red Flag Patterns:**
1. **Same-block coordination** - Multiple wallets buying in exact same block
2. **Sequential blocks** - Wallets buying in consecutive blocks (1, 2, 3, 4)
3. **Burst patterns** - 5+ wallets buying within 30 seconds
4. **Staggered accumulation** - Wallets buying same token over days with similar amounts

**Time-Based Heuristics:**

```javascript
// Time-based clustering detection
function detectTimeClustering(transactions, tokenMint) {
  const tokenBuys = transactions.filter(tx => 
    tx.tokenMint === tokenMint && 
    tx.type === 'BUY'
  );
  
  // Group by time windows
  const timeWindows = {};
  const WINDOW_MS = 60000; // 1 minute windows
  
  for (const tx of tokenBuys) {
    const windowKey = Math.floor(tx.timestamp / WINDOW_MS);
    if (!timeWindows[windowKey]) timeWindows[windowKey] = [];
    timeWindows[windowKey].push(tx);
  }
  
  // Find suspicious windows
  const suspicious = [];
  for (const [window, txs] of Object.entries(timeWindows)) {
    if (txs.length >= 3) {
      const uniqueWallets = new Set(txs.map(t => t.signer)).size;
      const avgAmount = txs.reduce((a, b) => a + b.amount, 0) / txs.length;
      const variance = calculateVariance(txs.map(t => t.amount));
      
      // Low variance in amounts suggests coordination
      if (variance / avgAmount < 0.3) {
        suspicious.push({
          window,
          wallets: txs.map(t => t.signer),
          transactionCount: txs.length,
          uniqueWallets,
          avgAmount,
          timeSpan: Math.max(...txs.map(t => t.timestamp)) - Math.min(...txs.map(t => t.timestamp))
        });
      }
    }
  }
  
  return suspicious;
}
```

### 2.3 Funding Source Analysis

#### CEX Withdrawal Pattern Detection

```python
class FundingSourceAnalyzer:
    CEX_HOT_WALLETS = {
        'binance': ['5tz...', '7xz...'],
        'coinbase': ['3ab...', '9kl...'],
        'okx': ['4cd...', '8mn...'],
        'bybit': ['2ef...', '6op...'],
        'kucoin': ['1gh...', '5qr...']
    }
    
    def analyze_funding_source(self, wallet_address, lookback_days=30):
        """Determine original funding source of a wallet"""
        history = self.get_transaction_history(wallet_address, lookback_days)
        
        # Find first incoming SOL transfer
        incoming = [tx for tx in history if tx.amount > 0]
        if not incoming:
            return {'type': 'unknown', 'confidence': 0}
        
        first_funding = incoming[-1]  # Oldest
        source = first_funding.source
        
        # Check if from CEX
        for cex, wallets in self.CEX_HOT_WALLETS.items():
            if source in wallets:
                return {
                    'type': 'cex',
                    'exchange': cex,
                    'confidence': 0.95,
                    'first_funding_time': first_funding.timestamp
                }
        
        # Check if from another user wallet
        source_analysis = self.analyze_wallet_age(source)
        if source_analysis['age_days'] > 365:
            return {
                'type': 'user_wallet',
                'wallet_age_days': source_analysis['age_days'],
                'confidence': 0.80
            }
        
        # Check if from deployer (suspicious)
        if self.is_deployer_wallet(source):
            return {
                'type': 'deployer_funded',
                'deployer': source,
                'confidence': 0.99,
                'risk_level': 'CRITICAL'
            }
        
        return {'type': 'unknown', 'source': source, 'confidence': 0.5}
    
    def detect_fresh_wallet_farms(self, token_buyers, max_wallet_age_days=7):
        """Detect groups of fresh wallets buying same token"""
        fresh_wallets = []
        
        for wallet in token_buyers:
            age = self.get_wallet_age(wallet)
            if age <= max_wallet_age_days:
                funding = self.analyze_funding_source(wallet)
                fresh_wallets.append({
                    'wallet': wallet,
                    'age_days': age,
                    'funding_source': funding
                })
        
        # Group by funding source
        by_funder = defaultdict(list)
        for fw in fresh_wallets:
            funder = fw['funding_source'].get('source', 'unknown')
            by_funder[funder].append(fw)
        
        # Flag clusters with same funder
        suspicious_clusters = []
        for funder, wallets in by_funder.items():
            if len(wallets) >= 3:
                suspicious_clusters.append({
                    'funder': funder,
                    'wallets': wallets,
                    'count': len(wallets),
                    'avg_age_days': mean(w['age_days'] for w in wallets)
                })
        
        return suspicious_clusters
```

#### Multi-Hop Obfuscation Detection

```
Funding Obfuscation Pattern:
CEX Hot Wallet
    ↓
Wallet A (1 day old)
    ↓ (24 hour delay)
Wallet B (created same day)
    ↓ (6 hour delay)  
Wallet C (created same day)
    ↓ (1 hour delay)
Sniper Wallet → Buys token
```

**Detection Query:**
```sql
-- Pseudocode SQL for multi-hop detection
WITH funding_chain AS (
  SELECT 
    w1.address as wallet,
    w1.funded_by as hop1,
    w2.funded_by as hop2,
    w3.funded_by as hop3,
    COUNT(*) as chain_length
  FROM wallets w1
  LEFT JOIN wallets w2 ON w1.funded_by = w2.address
  LEFT JOIN wallets w3 ON w2.funded_by = w3.address
  WHERE w1.first_transaction > NOW() - INTERVAL '7 days'
    AND w1.address IN (SELECT buyer FROM token_purchases WHERE token = ?)
  GROUP BY w1.address, w1.funded_by, w2.funded_by, w3.funded_by
)
SELECT * FROM funding_chain WHERE chain_length >= 3;
```

### 2.4 Common CEX Withdrawal Patterns

#### Identifying Exchange Withdrawal Signatures

| CEX | Withdrawal Pattern | Identifiers |
|-----|-------------------|-------------|
| Binance | Round amounts, sequential nonces | Withdrawal fees ~0.000005 SOL |
| Coinbase | Round USD amounts | Specific instruction patterns |
| OKX | Timed batch withdrawals | Regular intervals |
| Bybit | Similar amounts to multiple addresses | Same block, multiple outputs |

---

## 3. BEHAVIORAL FINGERPRINTS

### 3.1 Trading Style Analysis

#### Trading Style Classification

```python
class TradingStyleClassifier:
    def classify_wallet(self, wallet_address, lookback_days=90):
        trades = self.get_trade_history(wallet_address, lookback_days)
        
        if len(trades) < 5:
            return {'style': 'insufficient_data'}
        
        metrics = {
            'avg_hold_time': self.calculate_avg_hold_time(trades),
            'trades_per_day': len(trades) / lookback_days,
            'avg_position_size': mean(t.amount for t in trades),
            'position_variance': variance(t.amount for t in trades),
            'win_rate': self.calculate_win_rate(trades),
            'early_entry_rate': self.calculate_early_entry_rate(trades),
            'dca_frequency': self.detect_dca_pattern(trades),
            'partial_sell_rate': self.calculate_partial_sell_rate(trades)
        }
        
        # Classification logic
        if metrics['avg_hold_time'] < 3600:  # Less than 1 hour
            style = 'sniper'
        elif metrics['avg_hold_time'] < 86400:  # Less than 1 day
            style = 'scalper'
        elif metrics['dca_frequency'] > 0.7:
            style = 'dca_accumulator'
        elif metrics['early_entry_rate'] > 0.6 and metrics['win_rate'] > 0.6:
            style = 'alpha_hunter'
        elif metrics['avg_hold_time'] > 604800:  # More than 1 week
            style = 'holder'
        else:
            style = 'swing_trader'
        
        # Aggressiveness scoring
        aggressiveness = self.calculate_aggressiveness(metrics)
        
        return {
            'style': style,
            'aggressiveness': aggressiveness,
            'metrics': metrics,
            'confidence': self.calculate_classification_confidence(metrics)
        }
    
    def calculate_aggressiveness(self, metrics):
        """Score trading aggressiveness 0-100"""
        score = 0
        score += min(30, metrics['trades_per_day'] * 3)
        score += 20 if metrics['avg_hold_time'] < 3600 else 0
        score += min(25, (1 - metrics['win_rate']) * 50)  # High variance = aggressive
        score += min(25, metrics['position_variance'] / metrics['avg_position_size'] * 10)
        return score
```

#### Trading Style Categories

| Style | Hold Time | Trade Frequency | Risk Level | Pattern |
|-------|-----------|-----------------|------------|---------|
| **Sniper** | <1 hour | Very high | Extreme | First block buys, quick flips |
| **Scalper** | 1-24 hours | High | High | Momentum trading, tight stops |
| **DCA Accumulator** | Days-Weeks | Regular intervals | Medium | Systematic buying, gradual builds |
| **Alpha Hunter** | Variable | Selective | Medium-High | Early entries, high win rate |
| **Swing Trader** | Days-Weeks | Medium | Medium | Technical analysis based |
| **Holder** | Weeks-Months | Low | Low | Long-term conviction |

### 3.2 Token Selection Criteria

#### Smart Money Selection Patterns

```python
class TokenSelectionAnalyzer:
    def analyze_selection_criteria(self, wallet_address):
        """Analyze what makes a wallet pick winners"""
        profitable_trades = self.get_profitable_trades(wallet_address, min_return=0.5)
        
        criteria = {
            'avg_market_cap_at_entry': [],
            'avg_holder_count_at_entry': [],
            'avg_liquidity_at_entry': [],
            'dev_wallet_patterns': [],
            'token_age_at_entry': [],
            'social_signals': [],
            'technical_indicators': []
        }
        
        for trade in profitable_trades:
            token_data = self.get_token_state_at_time(
                trade.token, 
                trade.entry_timestamp
            )
            
            criteria['avg_market_cap_at_entry'].append(token_data.market_cap)
            criteria['avg_holder_count_at_entry'].append(token_data.holder_count)
            criteria['avg_liquidity_at_entry'].append(token_data.liquidity_usd)
            criteria['token_age_at_entry'].append(
                trade.entry_timestamp - token_data.creation_time
            )
            
            # Check dev wallet patterns
            dev_analysis = self.analyze_dev_wallet(token_data.deployer)
            criteria['dev_wallet_patterns'].append(dev_analysis)
        
        return {
            'preferred_market_cap_range': {
                'min': percentile(criteria['avg_market_cap_at_entry'], 25),
                'max': percentile(criteria['avg_market_cap_at_entry'], 75)
            },
            'preferred_holder_count': {
                'min': percentile(criteria['avg_holder_count_at_entry'], 25),
                'max': percentile(criteria['avg_holder_count_at_entry'], 75)
            },
            'avg_token_age_at_entry': mean(criteria['token_age_at_entry']),
            'dev_pattern_preferences': self.summarize_dev_patterns(
                criteria['dev_wallet_patterns']
            )
        }
```

#### Selection Criteria Patterns

| Smart Money Type | Market Cap Preference | Holder Count | Token Age | Dev Pattern |
|-----------------|----------------------|--------------|-----------|-------------|
| Early Snipers | <$100K | <50 | <1 hour | Any |
| Quality Hunters | $100K-$5M | 100-2000 | 1-7 days | Renounced, locked |
| Momentum Chasers | $5M-$50M | 2000+ | 7-30 days | Active community |
| Value Finders | <$10M | 500+ | Any | Transparent team |

### 3.3 Exit Strategy Patterns

#### Detecting Stealth Exits

```python
class ExitPatternAnalyzer:
    def analyze_exit_strategy(self, wallet_address, token_mint):
        """Analyze how a wallet exits positions without crashing price"""
        sells = self.get_sell_transactions(wallet_address, token_mint)
        
        if not sells:
            return {'status': 'still_holding'}
        
        # Analyze sell pattern
        total_position = sum(s.token_amount for s in sells)
        exit_pattern = {
            'total_sells': len(sells),
            'time_span': sells[0].timestamp - sells[-1].timestamp,
            'avg_sell_size': total_position / len(sells),
            'sell_size_variance': variance(s.token_amount for s in sells),
            'price_impact_pattern': [],
            'timing_pattern': []
        }
        
        # Categorize exit style
        if len(sells) == 1:
            exit_pattern['style'] = 'single_dump'
            exit_pattern['toxicity'] = 'HIGH'
        elif exit_pattern['time_span'] < 3600:  # 1 hour
            exit_pattern['style'] = 'rapid_exit'
            exit_pattern['toxicity'] = 'HIGH'
        elif len(sells) > 10 and exit_pattern['time_span'] > 86400:  # 24 hours
            exit_pattern['style'] = 'gradual_dca_exit'
            exit_pattern['toxicity'] = 'LOW'
        elif self.detect_volume_spike_selling(sells):
            exit_pattern['style'] = 'volume_camouflage'
            exit_pattern['toxicity'] = 'MEDIUM'
        else:
            exit_pattern['style'] = 'standard_exit'
            exit_pattern['toxicity'] = 'MEDIUM'
        
        # Calculate stealth score (lower = more stealthy)
        exit_pattern['stealth_score'] = self.calculate_stealth_score(sells)
        
        return exit_pattern
    
    def detect_volume_camouflage(self, sells):
        """Detect selling during high volume to hide impact"""
        for sell in sells:
            volume_24h = self.get_volume_24h_before(sell.token, sell.timestamp)
            volume_at_sell = self.get_volume_at_timestamp(sell.token, sell.timestamp)
            
            if volume_at_sell > volume_24h * 3:  # 3x average volume
                return True
        return False
```

#### Exit Strategy Types

| Strategy | Pattern | Detection | Risk |
|----------|---------|-----------|------|
| **Single Dump** | All at once | One large sell | Price crash |
| **Rapid Exit** | Multiple sells, short time | >50% position in <1 hour | High impact |
| **Gradual Exit** | Small sells over days | Consistent small sells | Low impact |
| **Volume Camouflage** | Sell during volume spikes | Sells during 3x+ volume | Moderate impact |
| **Cross-DEX Arbitrage** | Sell across multiple DEXs | Split sells different venues | Hidden impact |
| **Stop-Loss Cascade** | Trigger stop losses then sell | Sell after large down move | Accelerates dump |

### 3.4 Re-entry Patterns

#### Dip Buying Detection

```python
class ReentryAnalyzer:
    def detect_reentry_patterns(self, wallet_address, token_mint):
        """Detect if wallet buys back after selling (dip buying)"""
        trades = self.get_all_trades(wallet_address, token_mint)
        
        reentries = []
        for i, trade in enumerate(trades):
            if trade.type == 'SELL' and i < len(trades) - 1:
                # Look for buy after sell
                for j in range(i + 1, len(trades)):
                    next_trade = trades[j]
                    if next_trade.type == 'BUY':
                        time_diff = next_trade.timestamp - trade.timestamp
                        price_change = (next_trade.price - trade.price) / trade.price
                        
                        if time_diff < 604800:  # Within 1 week
                            reentries.append({
                                'exit_price': trade.price,
                                'reentry_price': next_trade.price,
                                'time_between': time_diff,
                                'price_change': price_change,
                                'is_dip_buy': price_change < -0.1  # 10% lower
                            })
                        break
        
        if not reentries:
            return {'reentry_pattern': 'none'}
        
        dip_buy_rate = sum(1 for r in reentries if r['is_dip_buy']) / len(reentries)
        
        return {
            'reentry_pattern': 'dip_buyer' if dip_buy_rate > 0.6 else 'occasional_reentry',
            'reentry_count': len(reentries),
            'dip_buy_rate': dip_buy_rate,
            'avg_time_before_reentry': mean(r['time_between'] for r in reentries),
            'avg_discount_captured': mean(r['price_change'] for r in reentries if r['is_dip_buy'])
        }
```

---

## 4. DATA SOURCES & PROGRAMMATIC DETECTION

### 4.1 Helius APIs for Transaction History

#### Essential Helius Endpoints

```javascript
// 1. Enhanced Transaction History
const getWalletTransactions = async (address) => {
  const response = await fetch(
    `https://api-mainnet.helius-rpc.com/v0/addresses/${address}/transactions?api-key=${HELIUS_KEY}`
  );
  return await response.json();
};

// 2. Wallet Identity/Labels
const getWalletIdentity = async (address) => {
  const response = await fetch(
    `https://api.helius.xyz/v1/wallet/${address}/identity?api-key=${HELIUS_KEY}`
  );
  return await response.json();
};

// 3. Funding Source Analysis
const getFundingSource = async (address) => {
  const response = await fetch(
    `https://api.helius.xyz/v1/wallet/${address}/funded-by?api-key=${HELIUS_KEY}`
  );
  return await response.json();
};

// 4. Batch Identity Lookup (up to 100 addresses)
const batchIdentityLookup = async (addresses) => {
  const response = await fetch(
    `https://api.helius.xyz/v1/wallet/batch-identity?api-key=${HELIUS_KEY}`,
    {
      method: 'POST',
      body: JSON.stringify({ addresses })
    }
  );
  return await response.json();
};

// 5. Token Balances with USD Values
const getWalletBalances = async (address) => {
  const response = await fetch(
    `https://api.helius.xyz/v1/wallet/${address}/balances?api-key=${HELIUS_KEY}`
  );
  return await response.json();
};

// 6. Parse Specific Transactions
const parseTransactions = async (signatures) => {
  const response = await fetch(
    `https://api-mainnet.helius-rpc.com/v0/transactions/?api-key=${HELIUS_KEY}`,
    {
      method: 'POST',
      body: JSON.stringify({ transactions: signatures })
    }
  );
  return await response.json();
};
```

### 4.2 DAS API for Token Accounts

#### DAS API Methods for Wallet Intelligence

```javascript
// Search Assets (Tokens & NFTs)
const searchAssets = async (ownerAddress) => {
  const response = await fetch('https://mainnet.helius-rpc.com/?api-key=KEY', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 'my-request',
      method: 'searchAssets',
      params: {
        ownerAddress,
        tokenType: 'fungible',  // or 'nonFungible'
        limit: 100
      }
    })
  });
  return await response.json();
};

// Get Token Accounts
const getTokenAccounts = async (mint) => {
  const response = await fetch('https://mainnet.helius-rpc.com/?api-key=KEY', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 'my-request',
      method: 'getTokenAccounts',
      params: { mint, page: 1, limit: 100 }
    })
  });
  return await response.json();
};

// Get Assets by Owner (with pricing)
const getAssetsByOwner = async (ownerAddress) => {
  const response = await fetch('https://mainnet.helius-rpc.com/?api-key=KEY', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 'my-request',
      method: 'getAssetsByOwner',
      params: {
        ownerAddress,
        displayOptions: { showFungible: true, showNativeBalance: true }
      }
    })
  });
  return await response.json();
};
```

### 4.3 Jupiter/Meteora/DLMM Liquidity Analysis

#### Monitoring Liquidity Patterns

```javascript
// Jupiter Quote API - Check liquidity depth
const checkLiquidityDepth = async (tokenMint, amount) => {
  const response = await fetch(
    `https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=${tokenMint}&amount=${amount}&slippageBps=50`
  );
  const quote = await response.json();
  
  return {
    route_count: quote.routePlan?.length || 0,
    price_impact: quote.priceImpactPct,
    liquidity_score: calculateLiquidityScore(quote)
  };
};

// Meteora DLMM Pool Analysis
const analyzeDLMMPool = async (poolAddress) => {
  // Use Meteora SDK or direct RPC calls
  const poolData = await fetchPoolData(poolAddress);
  
  return {
    bin_step: poolData.binStep,
    base_fee: poolData.baseFee,
    liquidity_distribution: poolData.liquidityDistribution,
    active_bin: poolData.activeBin,
    total_liquidity: poolData.totalLiquidity,
    volatility: calculateVolatility(poolData)
  };
};

// Detect Liquidity Manipulation
const detectLiquidityManipulation = async (tokenMint, timeframe = 86400) => {
  const liquidityEvents = await getLiquidityEvents(tokenMint, timeframe);
  
  const patterns = {
    add_then_remove: 0,
    flash_liquidity: 0,
    asymmetric_lp: 0
  };
  
  for (let i = 0; i < liquidityEvents.length - 1; i++) {
    const current = liquidityEvents[i];
    const next = liquidityEvents[i + 1];
    
    // Flash liquidity: add and remove within short time
    if (current.type === 'ADD' && next.type === 'REMOVE') {
      const timeDiff = next.timestamp - current.timestamp;
      if (timeDiff < 3600) {  // Within 1 hour
        patterns.flash_liquidity++;
      }
    }
    
    // Asymmetric LP: Large add, small remove (partial extraction)
    if (current.type === 'ADD' && next.type === 'REMOVE') {
      const ratio = next.amount / current.amount;
      if (ratio > 0.8) {  // Removed >80%
        patterns.add_then_remove++;
      }
    }
  }
  
  return patterns;
};
```

### 4.4 Pump.fun Launch Monitoring

#### Real-Time Launch Detection

```javascript
// Webhook for new Pump.fun launches
const setupPumpFunMonitoring = () => {
  // Helius Webhook for Pump.fun program
  const webhookConfig = {
    webhookURL: 'https://your-server.com/webhook/pumpfun',
    accountAddresses: ['6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'], // Pump.fun program
    transactionTypes: ['ANY'],
    webhookType: 'enhanced'
  };
  
  // Subscribe to Helius webhook
  fetch('https://api.helius.xyz/v0/webhooks?api-key=KEY', {
    method: 'POST',
    body: JSON.stringify(webhookConfig)
  });
};

// Process new token launch
const processPumpFunLaunch = async (transaction) => {
  const tokenMint = extractMintFromTransaction(transaction);
  const deployer = transaction.feePayer;
  
  // Immediate analysis
  const analysis = {
    token: tokenMint,
    deployer: deployer,
    launchTime: transaction.timestamp,
    snipers: [],
    insiderProbability: 0
  };
  
  // Check first 5 blocks for snipers
  const snipers = await detectSnipers(tokenMint, 
    transaction.slot, 
    transaction.slot + 5
  );
  
  analysis.snipers = snipers;
  analysis.insiderProbability = calculateInsiderProbability({
    sniperCount: snipers.length,
    deployerFundedCount: snipers.filter(s => s.deployerFunded).length,
    sameBlockCount: snipers.filter(s => s.blockDiff === 0).length
  });
  
  // Alert if high risk
  if (analysis.insiderProbability > 0.7) {
    await sendAlert('HIGH_RISK_LAUNCH', analysis);
  }
  
  return analysis;
};
```

---

## 5. INSIDER PROBABILITY SCORING SYSTEM

### 5.1 Scoring Algorithm

```python
class InsiderProbabilityScorer:
    def __init__(self):
        self.weights = {
            # Pre-launch indicators (40%)
            'deployer_funding': 0.15,
            'same_block_snipe': 0.10,
            'early_buy_timing': 0.08,
            'pre_launch_funding': 0.07,
            
            # Coordinated patterns (30%)
            'wallet_clustering': 0.10,
            'temporal_correlation': 0.08,
            'funding_obfuscation': 0.07,
            'cex_withdrawal_pattern': 0.05,
            
            # Behavioral fingerprints (20%)
            'fresh_wallet_pattern': 0.05,
            'rapid_exit_history': 0.05,
            'repeat_offender': 0.05,
            'position_sizing_pattern': 0.05,
            
            # Context (10%)
            'dev_wallet_flags': 0.05,
            'token_metadata_risk': 0.03,
            'liquidity_pattern': 0.02
        }
    
    def calculate_score(self, wallet_address, token_mint, transaction_data):
        """Calculate insider probability score 0-100"""
        scores = {}
        
        # 1. Deployer Funding Check
        scores['deployer_funding'] = self.check_deployer_funding(
            wallet_address, token_mint, transaction_data
        )
        
        # 2. Same-block sniping
        scores['same_block_snipe'] = self.check_same_block_snipe(
            wallet_address, token_mint, transaction_data
        )
        
        # 3. Early buy timing
        scores['early_buy_timing'] = self.score_early_buy_timing(
            transaction_data.block, 
            transaction_data.token_launch_block
        )
        
        # 4. Pre-launch funding
        scores['pre_launch_funding'] = self.check_pre_launch_funding(
            wallet_address, 
            transaction_data.timestamp,
            transaction_data.token_launch_time
        )
        
        # 5. Wallet clustering
        scores['wallet_clustering'] = self.analyze_cluster_membership(
            wallet_address, token_mint
        )
        
        # 6. Temporal correlation
        scores['temporal_correlation'] = self.analyze_temporal_patterns(
            wallet_address, token_mint
        )
        
        # 7. Funding obfuscation
        scores['funding_obfuscation'] = self.detect_funding_obfuscation(
            wallet_address
        )
        
        # 8. CEX withdrawal pattern
        scores['cex_withdrawal_pattern'] = self.analyze_cex_pattern(
            wallet_address
        )
        
        # 9. Fresh wallet
        scores['fresh_wallet_pattern'] = self.score_wallet_age(wallet_address)
        
        # 10. Rapid exit history
        scores['rapid_exit_history'] = self.analyze_exit_history(wallet_address)
        
        # 11. Repeat offender
        scores['repeat_offender'] = self.check_repeat_offender_status(wallet_address)
        
        # 12. Position sizing
        scores['position_sizing_pattern'] = self.analyze_position_sizing(
            wallet_address, transaction_data
        )
        
        # 13. Dev wallet flags
        scores['dev_wallet_flags'] = self.check_dev_wallet_risk(token_mint)
        
        # 14. Token metadata
        scores['token_metadata_risk'] = self.analyze_token_metadata(token_mint)
        
        # 15. Liquidity pattern
        scores['liquidity_pattern'] = self.analyze_liquidity_pattern(token_mint)
        
        # Calculate weighted total
        total_score = sum(
            scores[key] * self.weights[key] 
            for key in self.weights
        ) * 100
        
        return {
            'total_score': min(100, total_score),
            'component_scores': scores,
            'risk_level': self.categorize_risk(total_score),
            'confidence': self.calculate_confidence(scores)
        }
    
    def check_deployer_funding(self, wallet, token_mint, tx_data):
        """Check if wallet was funded by deployer"""
        deployer = self.get_token_deployer(token_mint)
        funding_chain = self.trace_funding_chain(wallet, hops=3)
        
        if deployer in funding_chain:
            return 1.0  # Maximum score
        return 0.0
    
    def check_same_block_snipe(self, wallet, token_mint, tx_data):
        """Check if buy was in same block as token creation"""
        launch_block = self.get_token_launch_block(token_mint)
        if tx_data.block == launch_block:
            return 1.0
        elif tx_data.block <= launch_block + 2:
            return 0.7
        elif tx_data.block <= launch_block + 5:
            return 0.4
        return 0.0
    
    def categorize_risk(self, score):
        if score >= 80: return 'CRITICAL'
        if score >= 60: return 'HIGH'
        if score >= 40: return 'MEDIUM'
        if score >= 20: return 'LOW'
        return 'MINIMAL'
```

### 5.2 Risk Categories

| Score Range | Risk Level | Action |
|-------------|------------|--------|
| 80-100 | CRITICAL | Avoid / Flag for investigation |
| 60-79 | HIGH | Exercise extreme caution |
| 40-59 | MEDIUM | Monitor closely |
| 20-39 | LOW | Standard due diligence |
| 0-19 | MINIMAL | Normal trading considerations |

### 5.3 Component Scoring Details

| Component | Max Score | Detection Method |
|-----------|-----------|------------------|
| Deployer funding | 1.0 | Direct SOL transfer trace |
| Same-block snipe | 1.0 | Block number comparison |
| Early buy timing | 1.0 | Block difference from launch |
| Pre-launch funding | 1.0 | Funding within 24h of launch |
| Wallet clustering | 1.0 | Graph analysis of related wallets |
| Temporal correlation | 1.0 | Time-window analysis |
| Funding obfuscation | 1.0 | Multi-hop funding detection |
| CEX pattern | 0.5 | Withdrawal signature analysis |
| Fresh wallet | 0.5 | Account age < 7 days |
| Rapid exit history | 0.5 | Historical sell pattern analysis |
| Repeat offender | 1.0 | Database of known insiders |
| Position sizing | 0.5 | Amount pattern analysis |
| Dev wallet flags | 0.5 | Deployer risk scoring |
| Token metadata | 0.3 | Metadata quality scoring |
| Liquidity pattern | 0.2 | LP analysis |

---

## 6. WALLET INTELLIGENCE SYSTEM ARCHITECTURE

### 6.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                  WALLET INTELLIGENCE SYSTEM                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Data Layer  │───▶│  Analysis    │───▶│  Alert       │      │
│  │              │    │  Engine      │    │  System      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Helius API   │    │ Scoring      │    │ Real-time    │      │
│  │ DAS API      │    │ Algorithms   │    │ Notifications│      │
│  │ Jupiter API  │    │ Clustering   │    │ Dashboard    │      │
│  │ Pump.fun     │    │ ML Models    │    │ Reports      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Database Schema

```sql
-- Wallets table
CREATE TABLE wallets (
    address VARCHAR(44) PRIMARY KEY,
    first_seen TIMESTAMP,
    last_active TIMESTAMP,
    total_transactions INT,
    funding_source VARCHAR(44),
    funding_source_type VARCHAR(20),
    risk_score DECIMAL(5,2),
    trading_style VARCHAR(20),
    is_deployer BOOLEAN DEFAULT FALSE,
    is_known_insider BOOLEAN DEFAULT FALSE,
    cluster_id VARCHAR(44),
    labels JSONB
);

-- Token launches table
CREATE TABLE token_launches (
    mint_address VARCHAR(44) PRIMARY KEY,
    deployer VARCHAR(44),
    launch_time TIMESTAMP,
    launch_block BIGINT,
    total_snipers INT,
    deployer_funded_snipers INT,
    insider_score DECIMAL(5,2),
    holder_concentration DECIMAL(5,2),
    metadata JSONB
);

-- Transactions table
CREATE TABLE transactions (
    signature VARCHAR(88) PRIMARY KEY,
    wallet_address VARCHAR(44),
    token_mint VARCHAR(44),
    type VARCHAR(10), -- BUY/SELL/TRANSFER
    amount DECIMAL(20,8),
    price DECIMAL(20,8),
    timestamp TIMESTAMP,
    block BIGINT,
    slot BIGINT,
    insider_probability DECIMAL(5,2),
    FOREIGN KEY (wallet_address) REFERENCES wallets(address),
    FOREIGN KEY (token_mint) REFERENCES token_launches(mint_address)
);

-- Wallet clusters table
CREATE TABLE wallet_clusters (
    cluster_id VARCHAR(44) PRIMARY KEY,
    wallet_count INT,
    total_funding DECIMAL(20,8),
    common_funding_source VARCHAR(44),
    confidence_score DECIMAL(5,2),
    detection_time TIMESTAMP,
    last_activity TIMESTAMP
);

-- Cluster members table
CREATE TABLE cluster_members (
    cluster_id VARCHAR(44),
    wallet_address VARCHAR(44),
    confidence DECIMAL(5,2),
    PRIMARY KEY (cluster_id, wallet_address)
);

-- Alerts table
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50),
    severity VARCHAR(20),
    wallet_address VARCHAR(44),
    token_mint VARCHAR(44),
    description TEXT,
    score DECIMAL(5,2),
    timestamp TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE
);

-- Indexes for performance
CREATE INDEX idx_transactions_wallet ON transactions(wallet_address);
CREATE INDEX idx_transactions_token ON transactions(token_mint);
CREATE INDEX idx_transactions_time ON transactions(timestamp);
CREATE INDEX idx_wallets_cluster ON wallets(cluster_id);
CREATE INDEX idx_wallets_risk ON wallets(risk_score);
```

### 6.3 Real-Time Monitoring Queries

```sql
-- Find high-risk wallet clusters
SELECT 
    c.cluster_id,
    c.wallet_count,
    c.confidence_score,
    COUNT(DISTINCT t.token_mint) as tokens_targeted,
    SUM(t.amount) as total_volume
FROM wallet_clusters c
JOIN cluster_members cm ON c.cluster_id = cm.cluster_id
JOIN wallets w ON cm.wallet_address = w.address
JOIN transactions t ON w.address = t.wallet_address
WHERE c.confidence_score > 0.8
    AND t.timestamp > NOW() - INTERVAL '24 hours'
GROUP BY c.cluster_id
HAVING COUNT(DISTINCT t.token_mint) > 3;

-- Detect coordinated sniping
SELECT 
    t.token_mint,
    t.block,
    COUNT(DISTINCT t.wallet_address) as sniper_count,
    STRING_AGG(DISTINCT t.wallet_address, ',') as wallets
FROM transactions t
JOIN token_launches tl ON t.token_mint = tl.mint_address
WHERE t.type = 'BUY'
    AND t.block <= tl.launch_block + 3
    AND tl.launch_time > NOW() - INTERVAL '1 hour'
GROUP BY t.token_mint, t.block
HAVING COUNT(DISTINCT t.wallet_address) >= 3;

-- Identify repeat insider wallets
SELECT 
    t.wallet_address,
    COUNT(DISTINCT t.token_mint) as tokens_sniped,
    AVG(t.insider_probability) as avg_insider_score,
    SUM(CASE WHEN t.block <= tl.launch_block + 1 THEN 1 ELSE 0 END) as same_block_snipes
FROM transactions t
JOIN token_launches tl ON t.token_mint = tl.mint_address
WHERE t.insider_probability > 0.7
GROUP BY t.wallet_address
HAVING COUNT(DISTINCT t.token_mint) >= 5
ORDER BY same_block_snipes DESC;
```

---

## 7. ACTIONABLE DETECTION CHECKLISTS

### 7.1 New Token Launch Analysis Checklist

```markdown
## Pre-Launch Analysis (Before Trading)

- [ ] Trace token deployer wallet
  - [ ] Check deployer history (how many tokens launched?)
  - [ ] Check if deployer is flagged in database
  - [ ] Analyze deployer's previous token performance
  
- [ ] Examine token metadata
  - [ ] Verify if mint authority is renounced
  - [ ] Check freeze authority
  - [ ] Review metadata update authority
  
- [ ] Set up monitoring
  - [ ] Subscribe to token transactions via webhook
  - [ ] Set block range for first 10 blocks
  - [ ] Prepare sniper detection algorithm

## Launch Block Analysis (Blocks 0-5)

- [ ] Identify all buyers in first 5 blocks
  - [ ] Record wallet addresses
  - [ ] Record buy amounts
  - [ ] Calculate buy timing (block diff from launch)
  
- [ ] Analyze sniper wallets
  - [ ] Check wallet age (< 7 days = suspicious)
  - [ ] Trace funding source
  - [ ] Check if funded by deployer
  - [ ] Calculate insider probability score
  
- [ ] Detect coordination
  - [ ] Check for same-block buys
  - [ ] Analyze temporal clustering
  - [ ] Build funding relationship graph
  - [ ] Identify wallet clusters

## Post-Launch Analysis (First 24 hours)

- [ ] Monitor sell patterns
  - [ ] Track sniper exits
  - [ ] Calculate holding duration
  - [ ] Identify dump patterns
  
- [ ] Update risk scores
  - [ ] Recalculate insider probability
  - [ ] Flag high-risk clusters
  - [ ] Update wallet database
```

### 7.2 Wallet Investigation Checklist

```markdown
## Wallet Background Check

- [ ] Basic Information
  - [ ] Wallet age (creation date)
  - [ ] Total transaction count
  - [ ] SOL balance history
  - [ ] First funding source
  
- [ ] Trading History Analysis
  - [ ] Tokens traded (last 90 days)
  - [ ] Win/loss ratio
  - [ ] Average hold time
  - [ ] Position sizing patterns
  
- [ ] Relationship Analysis
  - [ ] Funding source tracing (2-3 hops)
  - [ ] Related wallet detection
  - [ ] Cluster membership
  - [ ] Cross-wallet transfers

## Risk Assessment

- [ ] Pre-Launch Activity
  - [ ] Number of first-block purchases
  - [ ] Deployer funding connections
  - [ ] Fresh wallet pattern
  
- [ ] Coordination Indicators
  - [ ] Temporal correlation with other wallets
  - [ ] Same-token purchases with known clusters
  - [ ] Exit timing synchronization
  
- [ ] Behavioral Red Flags
  - [ ] Rapid exit history
  - [ ] Never-held positions
  - [ ] Wash trading patterns
```

### 7.3 Cluster Investigation Checklist

```markdown
## Cluster Identification

- [ ] Funding Chain Analysis
  - [ ] Common funding source identification
  - [ ] Multi-hop funding obfuscation detection
  - [ ] CEX withdrawal pattern analysis
  
- [ ] Temporal Analysis
  - [ ] Buy timing correlation
  - [ ] Exit timing correlation
  - [ ] Activity time windows
  
- [ ] Behavioral Analysis
  - [ ] Token selection overlap
  - [ ] Position sizing similarity
  - [ ] Trading style consistency

## Cluster Risk Scoring

- [ ] Calculate confidence score
  - [ ] Funding relationship weight: 40%
  - [ ] Temporal correlation weight: 30%
  - [ ] Token overlap weight: 15%
  - [ ] Exit correlation weight: 15%
  
- [ ] Historical Performance
  - [ ] Previous token targets
  - [ ] Profit extraction rate
  - [ ] Retail impact assessment
```

---

## 8. TOOLS & RESOURCES

### 8.1 Recommended APIs

| Service | Purpose | Key Features |
|---------|---------|--------------|
| **Helius** | Core data infrastructure | Enhanced transactions, DAS API, webhooks, identity |
| **Bitquery** | Historical analysis | Meteora DLMM data, cross-chain tracking |
| **Jupiter** | Liquidity analysis | Quote API, price impact, routing |
| **Solscan** | Explorer verification | Manual verification, instruction decoding |
| **Nansen** | Smart money labels | Pre-labeled wallets, portfolio tracking |
| **Mobula** | Pre-launch detection | Sniper/bundler/insider labeling |

### 8.2 Open Source Resources

- **Solana Web3.js** - Core Solana interactions
- **Helius SDK** - Simplified API access
- **Meteora SDK** - DLMM pool analysis
- **Jupiter Core** - Swap routing and quotes

### 8.3 Monitoring Infrastructure

```yaml
# Docker Compose example for monitoring stack
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: wallet_intel
      POSTGRES_USER: analyst
      POSTGRES_PASSWORD: secure_pass
    volumes:
      - pgdata:/var/lib/postgresql/data
      
  redis:
    image: redis:7-alpine
    
  api:
    build: ./api
    environment:
      HELIUS_API_KEY: ${HELIUS_API_KEY}
      DATABASE_URL: postgres://analyst:secure_pass@postgres:5432/wallet_intel
    depends_on:
      - postgres
      - redis
      
  worker:
    build: ./worker
    environment:
      HELIUS_API_KEY: ${HELIUS_API_KEY}
      DATABASE_URL: postgres://analyst:secure_pass@postgres:5432/wallet_intel
    depends_on:
      - postgres
      - redis
      
  webhook:
    build: ./webhook
    ports:
      - "8080:8080"
    environment:
      HELIUS_API_KEY: ${HELIUS_API_KEY}
      DATABASE_URL: postgres://analyst:secure_pass@postgres:5432/wallet_intel
    depends_on:
      - postgres
      
volumes:
  pgdata:
```

---

## 9. KEY FINDINGS SUMMARY

### 9.1 Critical Statistics

| Metric | Value | Source |
|--------|-------|--------|
| Pump.fun tokens sniped in creation block | >50% | Pine Analytics |
| Sniper profitability rate | 87% | Pine Analytics |
| Monthly SOL extracted via deployer sniping | 15,000+ SOL | Pine Analytics |
| Sniper wallets identified (monthly) | 4,600+ | Pine Analytics |
| Deployers involved in coordinated sniping | 10,400+ | Pine Analytics |
| Average sniper profit | 1-100 SOL | Multiple sources |

### 9.2 High-Confidence Insider Indicators

1. **Same-block purchase + deployer funding** (99% confidence)
2. **Multiple fresh wallets funded from same source buying same token** (95% confidence)
3. **Wallet buying in block 0-2 with < 7 day age** (90% confidence)
4. **Direct SOL transfer from deployer within 24h before launch** (95% confidence)
5. **Cluster of 3+ wallets with synchronized timing** (85% confidence)

### 9.3 Risk Mitigation Recommendations

1. **Never ape into launches with >30% sniper concentration**
2. **Avoid tokens where top 5 wallets are all deployer-funded**
3. **Monitor wallet clusters - if they start selling, exit immediately**
4. **Use insider probability scores >60 as hard avoid threshold**
5. **Track repeat offender deployers - maintain blacklist**

---

## 10. CONCLUSION

Detecting insider wallets and whale clusters on Solana requires a multi-signal approach combining:

1. **Pre-launch funding analysis** - The strongest signal is direct deployer funding
2. **Temporal clustering** - Same-block coordination is nearly impossible without insider knowledge
3. **Behavioral fingerprinting** - Consistent patterns reveal coordination
4. **Continuous monitoring** - Real-time alerting on suspicious patterns

The key insight from this research is that **coordinated insider activity on Solana is systematic, profitable, and often automated**. The same patterns repeat across thousands of token launches, creating detectable signatures that can be programmatically identified.

By implementing the scoring system and monitoring infrastructure outlined in this guide, you can build a robust Wallet Intelligence System that provides early warning of manipulation, protects against coordinated dumps, and identifies genuine alpha opportunities.

**Remember:** No single indicator is definitive. Combine multiple signals, weight them appropriately, and continuously refine your models based on observed behavior.

---

*Document Version: 1.0*  
*Last Updated: March 2026*  
*For questions or updates, consult the latest on-chain research*
