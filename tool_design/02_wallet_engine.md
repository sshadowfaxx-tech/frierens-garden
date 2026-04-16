# Wallet Intelligence Engine Design

## Overview

The Wallet Intelligence Engine analyzes blockchain wallet behavior to identify high-performing traders, detect coordinated activity (clusters), and provide real-time intelligence for trading decisions.

---

## 1. Wallet Scoring Algorithm

### 1.1 Core Metrics

#### Profitability Score (P-Score)
```
P-Score = (Realized Profit + Unrealized Profit) / Total Investment * Risk Adjustment

Where:
- Realized Profit = Σ(Sell Amount - Buy Amount) for closed positions
- Unrealized Profit = Σ(Current Value - Cost Basis) for open positions
- Risk Adjustment = 1 - (Max Drawdown / Total Investment)

Normalized to 0-100 scale using percentile ranking against all wallets
```

#### Hold Time Score (H-Score)
```
H-Score Components:
1. Average Hold Duration = Σ(Hold Time per token) / Number of Trades
2. Hold Consistency = 1 - (Standard Deviation of Hold Times / Average Hold Duration)
3. Optimal Hold Bonus = Tokens held through full pump cycles

Formula:
Base Score = min(Average Hold Duration / Optimal Hold Time, 1) * 40
Consistency Bonus = Hold Consistency * 30
Cycle Bonus = (Successful Cycle Holds / Total Cycle Opportunities) * 30

H-Score = Base Score + Consistency Bonus + Cycle Bonus
```

#### Win Rate Score (W-Score)
```
W-Score Components:
1. Raw Win Rate = Winning Trades / Total Closed Trades
2. Profit Factor = Gross Profit / Gross Loss
3. Risk-Adjusted Win Rate = Wins weighted by position size

Formula:
Raw Score = Raw Win Rate * 50
Profit Factor Score = min(Profit Factor / 3, 1) * 30  # Cap at PF=3
Consistency Score = (1 - Variance in monthly win rates) * 20

W-Score = Raw Score + Profit Factor Score + Consistency Score
```

### 1.2 Composite Wallet Score

```python
# PSEUDO-CODE: calculate_wallet_score
function calculate_wallet_score(wallet_id, time_window_days=30):
    
    # Fetch wallet transactions
    transactions = get_wallet_transactions(wallet_id, time_window_days)
    
    # Calculate P-Score (Profitability)
    realized_pnl = calculate_realized_pnl(transactions)
    unrealized_pnl = calculate_unrealized_pnl(wallet_id)
    max_drawdown = calculate_max_drawdown(transactions)
    total_invested = calculate_total_invested(transactions)
    
    if total_invested > 0:
        raw_profitability = (realized_pnl + unrealized_pnl) / total_invested
        risk_adjustment = 1 - (max_drawdown / total_invested)
        p_score = normalize_percentile(raw_profitability * risk_adjustment, "profitability")
    else:
        p_score = 0
    
    # Calculate H-Score (Hold Time)
    hold_times = extract_hold_times(transactions)
    if len(hold_times) > 0:
        avg_hold = mean(hold_times)
        hold_std = std(hold_times)
        consistency = 1 - (hold_std / avg_hold) if avg_hold > 0 else 0
        
        optimal_hold = 7 * 24 * 3600  # 7 days in seconds
        base_score = min(avg_hold / optimal_hold, 1) * 40
        consistency_bonus = max(consistency, 0) * 30
        
        # Detect pump cycle participation
        cycles = detect_pump_cycles(wallet_id)
        cycle_bonus = (cycles.successful / cycles.total) * 30 if cycles.total > 0 else 0
        
        h_score = base_score + consistency_bonus + cycle_bonus
    else:
        h_score = 0
    
    # Calculate W-Score (Win Rate)
    closed_trades = get_closed_trades(transactions)
    if len(closed_trades) > 0:
        wins = count_profitable_trades(closed_trades)
        raw_win_rate = wins / len(closed_trades)
        
        gross_profit = sum([t.profit for t in closed_trades if t.profit > 0])
        gross_loss = sum([abs(t.profit) for t in closed_trades if t.profit < 0])
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        
        # Monthly consistency
        monthly_rates = calculate_monthly_win_rates(wallet_id, time_window_days)
        consistency = 1 - variance(monthly_rates) if len(monthly_rates) > 1 else 0
        
        w_score = (raw_win_rate * 50) + (min(profit_factor / 3, 1) * 30) + (consistency * 20)
    else:
        w_score = 0
    
    # Composite Score with weights
    COMPOSITE_WEIGHTS = {
        'profitability': 0.45,
        'hold_time': 0.25,
        'win_rate': 0.30
    }
    
    composite_score = (
        p_score * COMPOSITE_WEIGHTS['profitability'] +
        h_score * COMPOSITE_WEIGHTS['hold_time'] +
        w_score * COMPOSITE_WEIGHTS['win_rate']
    )
    
    # Confidence adjustment based on sample size
    confidence = min(len(closed_trades) / 20, 1)  # Full confidence at 20+ trades
    adjusted_score = composite_score * confidence
    
    return {
        'wallet_id': wallet_id,
        'composite_score': round(adjusted_score, 2),
        'p_score': round(p_score, 2),
        'h_score': round(h_score, 2),
        'w_score': round(w_score, 2),
        'confidence': round(confidence, 2),
        'trade_count': len(closed_trades),
        'last_updated': now()
    }
```

### 1.3 Score Decay and Recency Weighting

```python
function apply_recency_weighting(transactions, base_scores):
    """
    More recent trades weighted higher
    """
    now = current_timestamp()
    decay_factor = 0.95  # 5% decay per day
    
    weighted_scores = []
    for tx in transactions:
        days_ago = (now - tx.timestamp) / 86400
        weight = decay_factor ** days_ago
        weighted_scores.append(tx.score_component * weight)
    
    return sum(weighted_scores) / sum([decay_factor ** ((now - tx.timestamp) / 86400) for tx in transactions])
```

---

## 2. Cluster Detection Algorithm

### 2.1 Behavioral Similarity Detection

```python
# PSEUDO-CODE: detect_wallet_clusters
function detect_wallet_clusters(min_cluster_size=3, similarity_threshold=0.85):
    
    # Step 1: Build transaction graph
    recent_wallets = get_wallets_with_activity(days=7, min_trades=5)
    
    # Step 2: Calculate pairwise similarities
    similarity_matrix = {}
    
    for i, wallet_a in enumerate(recent_wallets):
        for wallet_b in recent_wallets[i+1:]:
            similarity = calculate_behavior_similarity(wallet_a, wallet_b)
            if similarity >= similarity_threshold:
                similarity_matrix[(wallet_a, wallet_b)] = similarity
    
    # Step 3: Graph-based clustering using connected components
    graph = build_undirected_graph(similarity_matrix)
    clusters = find_connected_components(graph, min_size=min_cluster_size)
    
    # Step 4: Validate clusters with temporal analysis
    validated_clusters = []
    for cluster in clusters:
        if validate_temporal_coordination(cluster):
            cluster_profile = analyze_cluster_profile(cluster)
            validated_clusters.append(cluster_profile)
    
    return validated_clusters

function calculate_behavior_similarity(wallet_a, wallet_b):
    """
    Multi-dimensional similarity scoring
    """
    # Timing similarity - coordinated entry/exit
    timing_sim = calculate_timing_similarity(wallet_a, wallet_b)
    
    # Token overlap - trading same tokens
    token_sim = calculate_token_overlap(wallet_a, wallet_b)
    
    # Amount correlation - similar position sizes
    amount_sim = calculate_amount_correlation(wallet_a, wallet_b)
    
    # Trade pattern similarity
    pattern_sim = calculate_trade_pattern_similarity(wallet_a, wallet_b)
    
    # Funding source similarity
    funding_sim = calculate_funding_similarity(wallet_a, wallet_b)
    
    # Weighted combination
    weights = {
        'timing': 0.35,
        'token': 0.25,
        'amount': 0.20,
        'pattern': 0.15,
        'funding': 0.05
    }
    
    total_sim = (
        timing_sim * weights['timing'] +
        token_sim * weights['token'] +
        amount_sim * weights['amount'] +
        pattern_sim * weights['pattern'] +
        funding_sim * weights['funding']
    )
    
    return total_sim
```

### 2.2 Timing Similarity Algorithm

```python
function calculate_timing_similarity(wallet_a, wallet_b, window_seconds=300):
    """
    Detect if wallets trade the same tokens within a time window
    """
    tx_a = get_transactions(wallet_a)
    tx_b = get_transactions(wallet_b)
    
    coordinated_trades = 0
    total_overlapping_tokens = 0
    
    # Group by token
    tokens_a = group_transactions_by_token(tx_a)
    tokens_b = group_transactions_by_token(tx_b)
    
    common_tokens = set(tokens_a.keys()) & set(tokens_b.keys())
    
    for token in common_tokens:
        total_overlapping_tokens += 1
        
        # Check for temporal proximity
        for tx1 in tokens_a[token]:
            for tx2 in tokens_b[token]:
                time_diff = abs(tx1.timestamp - tx2.timestamp)
                if time_diff <= window_seconds:
                    coordinated_trades += 1
                    break
    
    if total_overlapping_tokens == 0:
        return 0
    
    # Score based on coordination rate
    coordination_rate = coordinated_trades / total_overlapping_tokens
    
    # Bonus for exact same-block trades
    same_block_trades = count_same_block_trades(wallet_a, wallet_b, common_tokens)
    same_block_bonus = min(same_block_trades / 10, 0.3)  # Max 0.3 bonus
    
    return min(coordination_rate + same_block_bonus, 1.0)
```

### 2.3 Funding Source Analysis

```python
function calculate_funding_similarity(wallet_a, wallet_b):
    """
    Detect if wallets share funding sources (CEX, mixer, same origin)
    """
    funding_a = trace_funding_sources(wallet_a, depth=3)
    funding_b = trace_funding_sources(wallet_b, depth=3)
    
    # Common funding addresses
    common_sources = set(funding_a.sources) & set(funding_b.sources)
    
    if len(common_sources) == 0:
        return 0
    
    # Weight by funding amount percentage
    common_amount_a = sum([f.amount for f in funding_a if f.source in common_sources])
    common_amount_b = sum([f.amount for f in funding_b if f.source in common_sources])
    
    pct_a = common_amount_a / funding_a.total if funding_a.total > 0 else 0
    pct_b = common_amount_b / funding_b.total if funding_b.total > 0 else 0
    
    return (pct_a + pct_b) / 2

function trace_funding_sources(wallet_id, depth=3):
    """
    Trace back transaction history to find funding sources
    """
    sources = []
    visited = set()
    queue = [(wallet_id, 0)]
    
    while queue:
        address, current_depth = queue.pop(0)
        
        if address in visited or current_depth > depth:
            continue
        visited.add(address)
        
        # Get incoming transactions
        incoming = get_incoming_transactions(address, limit=10)
        
        for tx in incoming:
            sender = tx.from_address
            
            # Check if known CEX, bridge, or mixer
            if is_known_cex(sender):
                sources.append({
                    'source': sender,
                    'type': 'cex',
                    'amount': tx.amount,
                    'timestamp': tx.timestamp
                })
            elif is_known_mixer(sender):
                sources.append({
                    'source': sender,
                    'type': 'mixer',
                    'amount': tx.amount,
                    'timestamp': tx.timestamp
                })
            elif current_depth < depth:
                queue.append((sender, current_depth + 1))
    
    return sources
```

### 2.4 Temporal Coordination Validation

```python
function validate_temporal_coordination(cluster_wallets):
    """
    Validate that cluster shows genuine coordination patterns
    vs. coincidence or following public signals
    """
    
    # Get all transactions for cluster
    all_tx = []
    for wallet in cluster_wallets:
        txs = get_transactions(wallet, days=30)
        all_tx.extend([{**tx, 'wallet': wallet} for tx in txs])
    
    # Sort by timestamp
    all_tx.sort(key=lambda x: x.timestamp)
    
    # Check for lead-follow pattern (information cascade)
    lead_follow_score = detect_lead_follow_pattern(all_tx)
    
    # Check for simultaneous execution (coordinated bot)
    simultaneous_score = detect_simultaneous_execution(all_tx)
    
    # Check for round-robin pattern (funding distribution)
    round_robin_score = detect_round_robin_pattern(cluster_wallets)
    
    # Cluster is valid if:
    # - Not purely lead-follow (that could be copy trading)
    # - Shows some simultaneous or round-robin behavior
    
    is_coordinated = (simultaneous_score > 0.3 or round_robin_score > 0.4)
    is_not_pure_copy = lead_follow_score < 0.8
    
    return is_coordinated and is_not_pure_copy

function detect_simultaneous_execution(transactions):
    """
    Detect trades executed in the same block or within seconds
    """
    token_groups = group_by_token(transactions)
    
    simultaneous_count = 0
    total_groups = 0
    
    for token, txs in token_groups.items():
        if len(txs) < 2:
            continue
        
        # Group by block/time window
        time_groups = group_by_time_window(txs, window_seconds=60)
        
        for group in time_groups:
            if len(group) >= 2 and len(set([t.wallet for t in group])) >= 2:
                simultaneous_count += 1
        
        total_groups += len(time_groups)
    
    return simultaneous_count / total_groups if total_groups > 0 else 0
```

---

## 3. Real-Time Processing Architecture

### 3.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        REAL-TIME WALLET INTELLIGENCE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  RPC Node 1  │    │  RPC Node 2  │    │  RPC Node N  │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                           │
│         └───────────────────┼───────────────────┘                           │
│                             ▼                                               │
│                   ┌─────────────────┐                                       │
│                   │  Event Stream   │  ← Kafka / Redis Streams              │
│                   │    Pipeline     │                                       │
│                   └────────┬────────┘                                       │
│                            │                                                │
│         ┌──────────────────┼──────────────────┐                            │
│         ▼                  ▼                  ▼                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │  Transaction │  │   Token      │  │   Wallet     │                      │
│  │  Processor   │  │   Monitor    │  │   Scorer     │                      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                      │
│         │                 │                 │                               │
│         └─────────────────┼─────────────────┘                               │
│                           ▼                                                 │
│                 ┌──────────────────┐                                        │
│                 │  Graph Database  │  ← Neo4j / ArangoDB                     │
│                 │  (Relationships) │                                        │
│                 └────────┬─────────┘                                        │
│                          │                                                  │
│         ┌────────────────┼────────────────┐                                │
│         ▼                ▼                ▼                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                        │
│  │   Alert      │ │   Cluster    │ │    API       │                        │
│  │   Engine     │ │   Detector   │ │   Server     │                        │
│  └──────────────┘ └──────────────┘ └──────────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Stream Processing Pipeline

```python
# PSEUDO-CODE: Stream Processing Components

class TransactionStreamProcessor:
    """
    Processes incoming blockchain transactions in real-time
    """
    
    def __init__(self):
        self.kafka_consumer = KafkaConsumer('transactions')
        self.redis = Redis()
        self.graph_db = Neo4jDriver()
        
    def process_stream(self):
        for message in self.kafka_consumer:
            transaction = parse_transaction(message)
            
            # Parallel processing
            await asyncio.gather(
                self.update_wallet_state(transaction),
                self.update_token_metrics(transaction),
                self.check_cluster_membership(transaction),
                self.detect_new_patterns(transaction)
            )
    
    async def update_wallet_state(self, tx):
        """
        Update real-time wallet state in Redis
        """
        wallet_key = f"wallet:{tx.to_address}:state"
        
        # Incremental updates
        pipeline = self.redis.pipeline()
        
        # Update balance
        pipeline.hincrbyfloat(wallet_key, 'balance', tx.amount)
        
        # Update trade count
        pipeline.hincrby(wallet_key, 'trade_count', 1)
        
        # Update last activity
        pipeline.hset(wallet_key, 'last_activity', tx.timestamp)
        
        # Add to recent trades list (keep last 100)
        pipeline.lpush(f"wallet:{tx.to_address}:trades", serialize(tx))
        pipeline.ltrim(f"wallet:{tx.to_address}:trades", 0, 99)
        
        await pipeline.execute()
        
        # Trigger score recalculation if needed
        if should_recalculate_score(tx.to_address):
            await self.enqueue_score_recalculation(tx.to_address)
    
    async def check_cluster_membership(self, tx):
        """
        Check if transaction is from a known cluster
        """
        cluster_id = self.redis.get(f"wallet:{tx.from_address}:cluster")
        
        if cluster_id:
            # Alert: Cluster activity detected
            await self.emit_alert({
                'type': 'cluster_activity',
                'cluster_id': cluster_id,
                'wallet': tx.from_address,
                'token': tx.token_address,
                'amount': tx.amount,
                'timestamp': tx.timestamp
            })
            
            # Update cluster activity metrics
            await self.update_cluster_metrics(cluster_id, tx)
```

### 3.3 Sliding Window Analytics

```python
class SlidingWindowAnalyzer:
    """
    Maintains rolling window statistics for real-time scoring
    """
    
    def __init__(self, window_size_hours=24):
        self.window_size = window_size_hours * 3600
        self.redis = Redis()
        
    def add_transaction(self, wallet_id, transaction):
        """
        Add transaction to sliding window
        """
        key = f"wallet:{wallet_id}:window"
        
        # Add to time-sorted set
        score = transaction.timestamp
        member = f"{transaction.tx_hash}:{transaction.token}"
        
        self.redis.zadd(key, {member: score})
        
        # Store transaction details
        self.redis.hset(f"{key}:data", member, serialize(transaction))
        
        # Expire old entries
        cutoff = current_timestamp() - self.window_size
        self.redis.zremrangebyscore(key, 0, cutoff)
        
    def get_window_stats(self, wallet_id):
        """
        Get current window statistics for scoring
        """
        key = f"wallet:{wallet_id}:window"
        
        # Get all transactions in window
        members = self.redis.zrange(key, 0, -1)
        
        transactions = []
        for member in members:
            data = self.redis.hget(f"{key}:data", member)
            transactions.append(deserialize(data))
        
        return {
            'trade_count': len(transactions),
            'unique_tokens': len(set([t.token for t in transactions])),
            'total_volume': sum([t.amount_usd for t in transactions]),
            'profit_realized': sum([t.profit for t in transactions if t.profit]),
            'avg_trade_size': mean([t.amount_usd for t in transactions]) if transactions else 0
        }
```

### 3.4 Incremental Score Updates

```python
class IncrementalScoreCalculator:
    """
    Update wallet scores incrementally without full recalculation
    """
    
    def update_score_incremental(self, wallet_id, new_transaction):
        """
        Update score based on new transaction only
        """
        current_score = self.get_current_score(wallet_id)
        
        # Calculate impact of new transaction
        if new_transaction.type == 'sell':
            pnl_impact = self.calculate_pnl_impact(wallet_id, new_transaction)
            
            # Update P-Score component
            old_realized = current_score.realized_pnl
            new_realized = old_realized + pnl_impact
            
            pnl_delta = (new_realized - old_realized) / current_score.total_invested
            p_score_delta = pnl_delta * 100 * RISK_ADJUSTMENT
            
            # Update W-Score component
            is_win = pnl_impact > 0
            new_win_rate = self.incremental_win_rate(
                current_score.win_count,
                current_score.loss_count,
                is_win
            )
            
            w_score_delta = (new_win_rate - current_score.win_rate) * 50
            
            # Apply weighted update
            new_composite = (
                current_score.composite +
                (p_score_delta * 0.45) +
                (w_score_delta * 0.30)
            )
            
            # Decay old score slightly (recency weighting)
            new_composite = (new_composite * 0.95) + (new_composite * 0.05)
            
            self.save_score(wallet_id, {
                'composite': new_composite,
                'p_score': current_score.p_score + p_score_delta,
                'w_score': current_score.w_score + w_score_delta,
                'last_updated': now()
            })
```

---

## 4. Data Structures for Wallet Relationships

### 4.1 Core Entity Schema

```
WALLET
------
wallet_id: string (PK)
first_seen: timestamp
last_active: timestamp
total_transactions: int
current_balance: decimal
risk_score: float  # 0-100
is_contract: boolean
is_exchange: boolean
labels: string[]

created_at: timestamp
updated_at: timestamp


TOKEN
-----
token_address: string (PK)
symbol: string
name: string
decimals: int
total_supply: decimal
creation_time: timestamp
creator_wallet: string (FK -> WALLET)
is_verified: boolean

market_cap: decimal
liquidity_usd: decimal
price_usd: decimal


TRANSACTION
-----------
tx_hash: string (PK)
block_number: int
block_timestamp: timestamp

from_wallet: string (FK -> WALLET)
to_wallet: string (FK -> WALLET)
token_address: string (FK -> TOKEN)

type: enum [BUY, SELL, TRANSFER, MINT, BURN]
amount: decimal
amount_usd: decimal
price_usd: decimal

gas_used: int
gas_price: decimal


CLUSTER
-------
cluster_id: string (PK)
detection_time: timestamp
confidence_score: float
cluster_type: enum [COORDINATED, COPY_TRADING, WHALE_GROUP]
member_count: int

total_volume_24h: decimal
primary_tokens: string[]
behavior_profile: json
```

### 4.2 Relationship Schema (Graph Database)

```cypher
// Wallet -> Wallet Relationships
(wallet_a:Wallet)-[:FUNDED {amount, timestamp, token}]->(wallet_b:Wallet)
(wallet_a:Wallet)-[:COORDINATED_WITH {similarity_score, common_tokens}]->(wallet_b:Wallet)

// Wallet -> Token Relationships
(wallet:Wallet)-[:BOUGHT {amount, amount_usd, timestamp}]->(token:Token)
(wallet:Wallet)-[:SOLD {amount, amount_usd, timestamp, pnl}]->(token:Token)
(wallet:Wallet)-[:HOLDS {balance, value_usd, avg_entry}]->(token:Token)

// Cluster Relationships
(wallet:Wallet)-[:MEMBER_OF {join_time, contribution_score}]->(cluster:Cluster)
(cluster:Cluster)-[:INFLUENCED]->(token:Token)
(cluster:Cluster)-[:COPIES]->(wallet:Wallet)  // Copy-trading clusters
```

### 4.3 Wallet Relationship Index

```python
# PSEUDO-CODE: Wallet Relationship Data Structure

@dataclass
class WalletRelationship:
    """
    Represents relationship between two wallets
    """
    source_wallet: str
    target_wallet: str
    relationship_type: str  # FUNDED, COORDINATED, SIMILAR
    strength: float  # 0-1
    evidence: List[RelationshipEvidence]
    first_detected: timestamp
    last_updated: timestamp
    
    # Temporal metrics
    interaction_frequency: float  # interactions per day
    avg_time_delta: float  # avg seconds between coordinated actions
    
    # Token overlap
    common_tokens: Set[str]
    token_overlap_ratio: float


@dataclass
class RelationshipEvidence:
    """
    Specific evidence supporting a relationship
    """
    evidence_type: str  # SAME_FUNDING, TEMPORAL_PROXIMITY, etc.
    timestamp: timestamp
    details: dict
    confidence: float


class WalletGraph:
    """
    In-memory graph for fast relationship queries
    """
    
    def __init__(self):
        self.adjacency_list = defaultdict(set)
        self.relationship_cache = {}
        self.wallet_metadata = {}
        
    def add_relationship(self, rel: WalletRelationship):
        """
        Add or update relationship
        """
        key = (rel.source_wallet, rel.target_wallet)
        self.relationship_cache[key] = rel
        
        # Update adjacency list
        self.adjacency_list[rel.source_wallet].add(rel.target_wallet)
        self.adjacency_list[rel.target_wallet].add(rel.source_wallet)
        
    def get_related_wallets(self, wallet_id, min_strength=0.5):
        """
        Get all wallets related to given wallet
        """
        related = []
        for neighbor in self.adjacency_list[wallet_id]:
            key = (wallet_id, neighbor)
            rel = self.relationship_cache.get(key)
            if rel and rel.strength >= min_strength:
                related.append((neighbor, rel.strength, rel.relationship_type))
        
        return sorted(related, key=lambda x: x[1], reverse=True)
    
    def find_connection_path(self, wallet_a, wallet_b, max_depth=3):
        """
        Find shortest path between two wallets through relationships
        """
        if wallet_a == wallet_b:
            return [wallet_a]
        
        visited = {wallet_a}
        queue = deque([(wallet_a, [wallet_a])])
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            for neighbor in self.adjacency_list[current]:
                if neighbor == wallet_b:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None  # No path found
```

### 4.4 Cluster Data Structure

```python
@dataclass
class WalletCluster:
    """
    Represents a group of coordinated wallets
    """
    cluster_id: str
    created_at: timestamp
    updated_at: timestamp
    
    # Members
    wallets: Set[str]
    member_scores: Dict[str, float]  # Individual contribution scores
    
    # Detection metadata
    detection_confidence: float
    cluster_type: ClusterType
    detection_method: List[str]
    
    # Behavioral profile
    profile: ClusterProfile
    
    # Temporal data
    first_coordinated_action: timestamp
    last_coordinated_action: timestamp
    
    # Performance tracking
    total_pnl: decimal
    successful_pumps: int
    failed_pumps: int


@dataclass
class ClusterProfile:
    """
    Behavioral fingerprint of the cluster
    """
    # Timing patterns
    avg_time_between_trades: float
    preferred_entry_window: int  # seconds (e.g., 300 = 5min coordination)
    
    # Token preferences
    favorite_tokens: List[str]
    avg_token_age_at_entry: float  # seconds since token creation
    preferred_market_cap_range: Tuple[float, float]
    
    # Trade characteristics
    avg_position_size: decimal
    avg_hold_time: float
    preferred_dex: str
    
    # Risk profile
    max_slippage_tolerance: float
    gas_price_behavior: str  # aggressive, conservative, adaptive


class ClusterIndex:
    """
    Index for efficient cluster queries
    """
    
    def __init__(self):
        self.wallet_to_cluster = {}  # wallet_id -> cluster_id
        self.token_to_clusters = defaultdict(set)  # token -> set(cluster_ids)
        self.active_clusters = {}  # cluster_id -> WalletCluster
        
    def add_cluster(self, cluster: WalletCluster):
        """
        Index new cluster
        """
        self.active_clusters[cluster.cluster_id] = cluster
        
        for wallet in cluster.wallets:
            self.wallet_to_cluster[wallet] = cluster.cluster_id
        
        for token in cluster.profile.favorite_tokens:
            self.token_to_clusters[token].add(cluster.cluster_id)
    
    def get_clusters_for_token(self, token_address):
        """
        Get all clusters active on a specific token
        """
        cluster_ids = self.token_to_clusters.get(token_address, set())
        return [self.active_clusters[cid] for cid in cluster_ids if cid in self.active_clusters]
    
    def get_cluster_for_wallet(self, wallet_id):
        """
        Get cluster membership for a wallet
        """
        cluster_id = self.wallet_to_cluster.get(wallet_id)
        return self.active_clusters.get(cluster_id) if cluster_id else None
```

---

## 5. Alert and Signal Generation

### 5.1 Signal Types

```python
class WalletSignals:
    """
    Signal definitions for the intelligence engine
    """
    
    SIGNALS = {
        # Wallet-level signals
        'WHALE_BUY': {
            'description': 'High-scoring wallet making large purchase',
            'priority': 'HIGH',
            'cooldown_seconds': 300
        },
        'SMART_MONEY_ENTRY': {
            'description': 'Multiple high-scoring wallets entering same token',
            'priority': 'HIGH',
            'cooldown_seconds': 600
        },
        'CLUSTER_ACTIVATION': {
            'description': 'Known cluster showing coordinated activity',
            'priority': 'CRITICAL',
            'cooldown_seconds': 60
        },
        'PROFIT_TAKING': {
            'description': 'Wallet with high P-Score taking profits',
            'priority': 'MEDIUM',
            'cooldown_seconds': 300
        },
        'SCORE_SPIKE': {
            'description': 'Wallet score increasing rapidly',
            'priority': 'MEDIUM',
            'cooldown_seconds': 3600
        }
    }
    
    def generate_signal(self, signal_type, wallet_id, token_id, metadata):
        """
        Generate and emit signal
        """
        signal_config = self.SIGNALS[signal_type]
        
        # Check cooldown
        cooldown_key = f"signal:{signal_type}:{wallet_id}:{token_id}"
        if self.redis.exists(cooldown_key):
            return None
        
        signal = {
            'type': signal_type,
            'wallet_id': wallet_id,
            'token_id': token_id,
            'timestamp': now(),
            'priority': signal_config['priority'],
            'metadata': metadata
        }
        
        # Set cooldown
        self.redis.setex(
            cooldown_key,
            signal_config['cooldown_seconds'],
            '1'
        )
        
        # Emit to subscribers
        self.emit_signal(signal)
        
        return signal
```

### 5.2 Signal Aggregation

```python
class SignalAggregator:
    """
    Aggregate multiple signals into actionable intelligence
    """
    
    def aggregate_token_signals(self, token_id, time_window=3600):
        """
        Aggregate all signals for a token into a composite score
        """
        signals = self.get_signals_for_token(token_id, time_window)
        
        # Count by type
        whale_buys = len([s for s in signals if s['type'] == 'WHALE_BUY'])
        smart_money = len([s for s in signals if s['type'] == 'SMART_MONEY_ENTRY'])
        cluster_activity = len([s for s in signals if s['type'] == 'CLUSTER_ACTIVATION'])
        
        # Calculate composite intensity
        intensity = (
            whale_buys * 1.0 +
            smart_money * 2.0 +
            cluster_activity * 3.0
        )
        
        # Determine sentiment
        if cluster_activity > 0:
            sentiment = 'STRONG_BULLISH'
        elif smart_money >= 2:
            sentiment = 'BULLISH'
        elif whale_buys >= 3:
            sentiment = 'MODERATE_BULLISH'
        else:
            sentiment = 'NEUTRAL'
        
        return {
            'token_id': token_id,
            'intensity': intensity,
            'sentiment': sentiment,
            'signal_breakdown': {
                'whale_buys': whale_buys,
                'smart_money': smart_money,
                'cluster_activity': cluster_activity
            },
            'timestamp': now()
        }
```

---

## 6. Performance Optimization

### 6.1 Caching Strategy

```python
class ScoreCache:
    """
    Multi-tier caching for wallet scores
    """
    
    TIERS = {
        'L1': {'ttl': 60, 'store': 'memory'},      # 1 minute
        'L2': {'ttl': 300, 'store': 'redis'},      # 5 minutes
        'L3': {'ttl': 3600, 'store': 'redis'},     # 1 hour
    }
    
    def get_score(self, wallet_id):
        # L1: In-memory cache
        if wallet_id in self.memory_cache:
            return self.memory_cache[wallet_id]
        
        # L2: Redis fast lookup
        score = self.redis.get(f"score:l2:{wallet_id}")
        if score:
            self.memory_cache[wallet_id] = score
            return score
        
        # L3: Calculate and cache
        score = self.calculate_wallet_score(wallet_id)
        self.cache_score(wallet_id, score)
        return score
    
    def cache_score(self, wallet_id, score):
        # L1
        self.memory_cache[wallet_id] = score
        
        # L2 & L3
        self.redis.setex(f"score:l2:{wallet_id}", 300, serialize(score))
        self.redis.setex(f"score:l3:{wallet_id}", 3600, serialize(score))
```

### 6.2 Batch Processing

```python
class BatchScoreProcessor:
    """
    Process wallet scores in batches for efficiency
    """
    
    BATCH_SIZE = 100
    
    async def process_batch(self, wallet_ids):
        """
        Process multiple wallets efficiently
        """
        # Fetch all transactions in one query
        all_transactions = await self.fetch_transactions_batch(wallet_ids)
        
        # Calculate scores in parallel
        tasks = []
        for wallet_id in wallet_ids:
            txs = all_transactions.get(wallet_id, [])
            task = self.calculate_score_async(wallet_id, txs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Batch write to database
        await self.save_scores_batch(results)
        
        return results
```

---

## 7. Implementation Roadmap

### Phase 1: Core Scoring (Week 1-2)
- [ ] Implement P-Score calculation
- [ ] Implement H-Score calculation  
- [ ] Implement W-Score calculation
- [ ] Composite scoring engine
- [ ] Score caching layer

### Phase 2: Cluster Detection (Week 2-3)
- [ ] Transaction graph builder
- [ ] Similarity calculation algorithms
- [ ] Connected components detection
- [ ] Temporal validation
- [ ] Cluster persistence

### Phase 3: Real-Time Pipeline (Week 3-4)
- [ ] Stream processor setup
- [ ] Sliding window implementation
- [ ] Incremental score updates
- [ ] Signal generation
- [ ] Alert dispatch

### Phase 4: Integration (Week 4)
- [ ] Graph database setup
- [ ] API endpoints
- [ ] Performance optimization
- [ ] Monitoring and alerting

---

## Appendix: Configuration Constants

```python
CONFIG = {
    # Scoring
    'SCORE_DECAY_DAYS': 30,
    'MIN_TRADES_FOR_SCORE': 5,
    'CONFIDENCE_THRESHOLD': 0.7,
    
    # Cluster Detection
    'MIN_CLUSTER_SIZE': 3,
    'SIMILARITY_THRESHOLD': 0.85,
    'COORDINATION_WINDOW_SECONDS': 300,
    
    # Real-time Processing
    'SLIDING_WINDOW_HOURS': 24,
    'SCORE_RECALC_INTERVAL_MINUTES': 15,
    'ALERT_COOLDOWN_SECONDS': 300,
    
    # Performance
    'CACHE_TTL_SECONDS': 300,
    'BATCH_SIZE': 100,
    'MAX_GRAPH_DEPTH': 3
}
```
