# Solana Trading Tool - Core Architecture

## 1. System Architecture Pattern: Event-Driven Microservices

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY (Envoy/Nginx)                         │
│                     Rate Limit │ Auth │ SSL │ Load Balancer                 │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │
    ┌──────────────────┼──────────────────┬──────────────────┐
    ▼                  ▼                  ▼                  ▼
┌─────────┐      ┌─────────┐       ┌─────────┐        ┌─────────────┐
│  REST   │      │ WebSocket│       │  gRPC   │        │  FIX API    │
│  API    │      │ Stream  │       │ Stream  │        │ (Institutional)
└────┬────┘      └────┬────┘       └────┬────┘        └──────┬──────┘
     │                │                 │                    │
     └────────────────┴─────────────────┴────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
    ┌───────────────────┐   ┌──────────────────────┐
    │  Event Bus        │   │  Service Mesh        │
    │  (Kafka/Pulsar)   │   │  (Istio/Linkerd)     │
    └───────────────────┘   └──────────────────────┘
              │
    ┌─────────┼─────────┬─────────┬─────────┬─────────┬─────────┐
    ▼         ▼         ▼         ▼         ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Order  │ │Price  │ │Wallet │ │Risk   │ │Portfolio│ │Alert │ │Backtest│
│Svc    │ │Engine │ │Svc    │ │Engine │ │Svc      │ │Svc    │ │Engine │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │         │         │         │         │         │
    └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
          ┌─────────────────┐  ┌─────────────────┐
          │  Data Layer     │  │  Cache Layer    │
          │  (TSDB/Graph)   │  │  (Redis Cluster)│
          └─────────────────┘  └─────────────────┘
```

### Microservice Boundaries

| Service | Responsibility | Scale Target | Critical Path |
|---------|---------------|--------------|---------------|
| `order-svc` | Order creation, validation, routing | 50K TPS | YES |
| `price-engine` | Real-time price aggregation, OHLCV | 100K updates/s | YES |
| `wallet-svc` | Balance tracking, ATA management | 10K TPS | YES |
| `risk-engine` | Pre-trade risk checks, position limits | 20K checks/s | YES |
| `portfolio-svc` | P&L, historical tracking | 1K queries/s | NO |
| `alert-svc` | Price alerts, webhooks | 10K alerts/min | NO |
| `backtest-engine` | Strategy simulation | Batch jobs | NO |

### Event Schema (CloudEvents)

```json
{
  "specversion": "1.0",
  "type": "solana.trade.order.submitted",
  "source": "order-svc",
  "id": "uuid-v7",
  "time": "2024-01-15T10:30:00.000Z",
  "data": {
    "orderId": "ord_...",
    "market": "SOL-USDC",
    "side": "buy",
    "type": "limit",
    "size": 1.5,
    "price": 98.50,
    "wallet": "...",
    "priorityFee": 10000,
    "jitoBundle": true
  }
}
```

---

## 2. Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                       │
├─────────────────┬─────────────────┬─────────────────┬──────────────────────────┤
│  Solana RPC     │  DEX Programs   │  Jito MEV       │  External Feeds          │
│  (Helius/QuickNode)│ (Raydium/Jupiter)│  Bundle Stream │  (CoinGecko/Birdeye)   │
│  • Blocks       │  • Swaps        │  • Bundle status │  • Market caps          │
│  • Account updates│ • Liquidity    │  • Leader schedule│ • Sentiment            │
│  • Logs         │  • Pool states  │                 │  • News signals         │
└────────┬────────┴────────┬────────┴────────┬────────┴────────────┬─────────────┘
         │                 │                 │                     │
         └─────────────────┴─────────────────┴─────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER (Rust/Go)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │RPC WebSocket│  │Geyser Plugin│  │Jito gRPC    │  │REST Polling Workers │    │
│  │(Account sub)│  │(Tx stream)  │  │(Bundle sub) │  │(Rate-limited)       │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘    │
│         └─────────────────┴─────────────────┴────────────────────┘              │
│                                    │                                            │
│                          ┌─────────┴─────────┐                                  │
│                          ▼                   ▼                                  │
│              ┌──────────────────┐  ┌──────────────────┐                         │
│              │ Circuit Breaker  │  │ Deduplication    │                         │
│              │ (Fail-fast)      │  │ (Idempotent keys)│                         │
│              └────────┬─────────┘  └────────┬─────────┘                         │
└───────────────────────┼─────────────────────┼───────────────────────────────────┘
                        │                     │
                        ▼                     ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                      STREAM PROCESSING (Flink/Custom Rust)                      │
│                                                                                 │
│   ┌───────────────┐    ┌───────────────┐    ┌───────────────┐    ┌───────────┐ │
│   │ Normalization │───▶│ Enrichment    │───▶│ Aggregation   │───▶│ Detection │ │
│   │ • Schema validation│ • Token metadata│  │ • OHLCV bars  │    │ • Anomaly │ │
│   │ • Unit conversion  │ • USD pricing   │  │ • VWAP        │    │ • MEV     │ │
│   └───────────────┘    └───────────────┘    └───────────────┘    └─────┬─────┘ │
│                                                                        │       │
│   ┌───────────────┐    ┌───────────────┐    ┌───────────────┐          │       │
│   │ Order Matching│◄───│ Risk Check    │◄───│ Pre-trade     │◄─────────┘       │
│   │ (Jupiter API) │    │ (Position)    │    │ Validation    │                  │
│   └───────────────┘    └───────────────┘    └───────────────┘                  │
└───────────────────────┬────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  TimescaleDB │  │    Neo4j    │  │Redis Cluster│
│  (Time-series)│  │  (Graph)    │  │   (Cache)   │
│              │  │             │  │             │
│ • Price ticks│  │ • Wallet    │  │ • Hot prices│
│ • Trade fills│  │   flows     │  │ • Order book│
│ • Aggregated │  │ • Token     │  │ • Session   │
│   OHLCV      │  │   clusters  │  │   state     │
│ • On-chain   │  │ • MEV paths │  │ • Rate limit│
│   events     │  │             │  │   counters  │
└──────┬───────┘  └──────┬──────┘  └──────┬──────┘
       │                 │                │
       └─────────────────┴────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                          │
│                                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│   │  REST API   │  │ WebSocket   │  │   gRPC      │  │  GraphQL (Analytics)│   │
│   │  (OpenAPI)  │  │  (Events)   │  │  (Streams)  │  │  (Complex queries)  │   │
│   │             │  │             │  │             │  │                     │   │
│   │ • Orders    │  │ • Ticker    │  │ • Market    │  │ • Historical        │   │
│   │ • Positions │  │ • Trades    │  │   data      │  │   analysis          │   │
│   │ • Balances  │  │ • Book L2   │  │ • Low-latency│  │ • Graph traversals  │   │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Latency Budget per Stage

| Stage | Target | Max | Notes |
|-------|--------|-----|-------|
| Ingestion | 5ms | 15ms | WebSocket to Kafka |
| Normalization | 3ms | 10ms | Schema validation |
| Enrichment | 10ms | 30ms | Price lookup (cached) |
| Risk Check | 15ms | 50ms | Position limits |
| Order Routing | 20ms | 100ms | Jupiter API call |
| Persistence | 5ms | 20ms | Async write |
| **TOTAL** | **58ms** | **225ms** | Critical path |

---

## 3. Database Selection

### 3.1 TimescaleDB (Primary Time-Series Store)

```
┌─────────────────────────────────────────────────────────────┐
│                    TimescaleDB Cluster                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Primary    │──│  Replica    │──│  Read Replica (x2)  │  │
│  │  (Writes)   │  │  (HA)       │  │  (Analytics)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  Hypertables:                                                │
│  ├── price_ticks (1s chunks, 7d retention)                   │
│  ├── trades (1min chunks, 30d retention)                     │
│  ├── candle_ohlcv (1h chunks, 1yr retention)                 │
│  └── onchain_events (1min chunks, 90d retention)             │
│                                                              │
│  Continuous Aggregates:                                      │
│  • 1min OHLCV → 5min → 15min → 1h → 4h → 1d                  │
│  • Real-time aggregation enabled                             │
└─────────────────────────────────────────────────────────────┘
```

**Why TimescaleDB:**
- Native SQL interface (familiar tooling)
- Automatic partitioning (hypertables)
- 10-100x faster queries on time-series vs PostgreSQL
- Built-in continuous aggregation
- Excellent compression (90%+ on historical)

**Schema Example:**
```sql
CREATE TABLE price_ticks (
    time TIMESTAMPTZ NOT NULL,
    market_id INT NOT NULL,
    price DECIMAL(24,10) NOT NULL,
    volume DECIMAL(24,10) NOT NULL,
    source SMALLINT NOT NULL
);

SELECT create_hypertable('price_ticks', 'time', chunk_time_interval => INTERVAL '1 hour');
CREATE INDEX ON price_ticks (market_id, time DESC);
```

---

### 3.2 Neo4j (Graph Analytics)

```
┌─────────────────────────────────────────────────────────────┐
│                     Neo4j Cluster                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Core (x3)  │──│  Core (x3)  │──│  Read Replica (x2)  │  │
│  │  (RAFT)     │  │  (RAFT)     │  │  (Graph analytics)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  Node Types:                                                 │
│  (:Wallet {address, first_seen, tags})                       │
│  (:Token {mint, symbol, decimals, supply})                   │
│  (:Transaction {signature, slot, timestamp, success})        │
│  (:Pool {address, dex, token_a, token_b, tvl})               │
│                                                              │
│  Relationship Types:                                         │
│  (:Wallet)-[:HOLDS {balance, last_updated}]->(:Token)        │
│  (:Wallet)-[:SENT {amount, timestamp}]->(:Wallet)            │
│  (:Wallet)-[:SWAPPED {amount_in, amount_out}]->(:Pool)       │
│  (:Token)-[:PAIRED_IN]->(:Pool)                              │
│                                                              │
│  Use Cases:                                                  │
│  • Wallet clustering (sophisticated vs retail)               │
│  • MEV path detection                                        │
│  • Token flow analysis                                       │
│  • Whitelist/blacklist propagation                           │
└─────────────────────────────────────────────────────────────┘
```

**Why Neo4j:**
- Native graph storage (not a relational layer)
- Cypher query language for complex traversals
- Real-time graph analytics with GDS library
- Excellent for fraud detection and relationship mapping

**Query Example:**
```cypher
// Find wallets that bought before a pump (insider detection)
MATCH (pumper:Wallet)-[:SWAPPED]->(pool:Pool)<-[:SWAPPED]-(early:Wallet)
WHERE pumper.tags CONTAINS 'whale'
  AND early.first_seen < datetime() - duration('P7D')
WITH early, count(DISTINCT pool) as pool_count
WHERE pool_count > 5
RETURN early.address, pool_count
ORDER BY pool_count DESC
LIMIT 100;
```

---

### 3.3 Redis Cluster (Cache & Hot Storage)

```
┌─────────────────────────────────────────────────────────────┐
│                   Redis Cluster (6 nodes)                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │ Master  │ │ Master  │ │ Master  │ │ Replica │ │ Replica ││
│  │:7000    │ │:7001    │ │:7002    │ │:7003    │ │:7004    ││
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘│
│       └───────────┴───────────┴───────────┴───────────┘     │
│                                                              │
│  Data Structures:                                            │
│  • Sorted Sets: Order books (price levels)                   │
│  • Hashes: Token metadata, wallet balances                   │
│  • Streams: Event log for replay                             │
│  • Strings: Latest prices (with TTL)                         │
│  • Pub/Sub: Real-time tickers                                │
│                                                              │
│  Key Patterns:                                               │
│  price:sol-usdc:latest → "98.50" (TTL: 5s)                   │
│  book:sol-usdc:bids → ZSET [price → size]                    │
│  wallet:{addr}:balances → HASH [token → amount]              │
│  stream:trades → XADD (maxlen ~1M)                           │
│  session:{jwt} → HASH (TTL: 24h)                             │
│  ratelimit:{ip} → INCR (expire 1min)                         │
└─────────────────────────────────────────────────────────────┘
```

**Redis Configuration:**
```
# Critical path optimizations
maxmemory-policy allkeys-lru
io-threads 4
io-threads-do-reads yes

# Persistence (for recovery only, not durability)
appendonly yes
appendfsync everysec

# Cluster
cluster-enabled yes
cluster-node-timeout 5000
```

---

## 4. Message Queue: Kafka vs Pulsar

### Decision: **Apache Pulsar**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Pulsar Architecture                                  │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        Pulsar Cluster (3 brokers)                   │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│   │  │  Broker 1   │  │  Broker 2   │  │  Broker 3   │                 │   │
│   │  │ (Topics A-F)│  │ (Topics G-L)│  │ (Topics M-Z)│                 │   │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │   │
│   │         └────────────────┴────────────────┘                        │   │
│   │                         │                                          │   │
│   │              ┌──────────┴──────────┐                               │   │
│   │              ▼                     ▼                               │   │
│   │   ┌─────────────────────┐  ┌─────────────────────┐                 │   │
│   │   │   BookKeeper       │  │   ZooKeeper         │                 │   │
│   │   │   (Ledger storage) │  │   (Coordination)    │                 │   │
│   │   │   - SSD/NVMe       │  │   - Ensemble: 3     │                 │   │
│   │   │   - Write quorum: 2│  │   - Write quorum: 2 │                 │   │
│   │   │   - Ack quorum: 2  │  │   - Ack quorum: 2   │                 │   │
│   │   └─────────────────────┘  └─────────────────────┘                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Topic Partitioning:                                                        │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ Topic: solana.trades (16 partitions)                             │      │
│   │                                                                  │      │
│   │  P0  P1  P2  P3  P4  P5  P6  P7  P8  P9  P10 P11 P12 P13 P14 P15 │      │
│   │  ├───────┬───────┬───────┬───────┬───────┬───────┬───────┤        │      │
│   │  │Hash by│market │for    │parallel│processing│within│topic│        │      │
│   │  └───────┴───────┴───────┴───────┴───────┴───────┴───────┘        │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│   Geo-Replication (optional):                                                │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐                    │
│   │ US-East  │◄───────►│ EU-West  │◄───────►│ APAC-SG  │                    │
│   │ (Primary)│         │ (Replica)│         │ (Replica)│                    │
│   └──────────┘         └──────────┘         └──────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Comparison Matrix

| Feature | Kafka | Pulsar | Winner |
|---------|-------|--------|--------|
| **Latency (p99)** | ~10ms | ~5ms | Pulsar |
| **Multi-tenancy** | Basic (topics) | Native (namespaces) | Pulsar |
| **Geo-replication** | MirrorMaker | Built-in | Pulsar |
| **Tiered storage** | Limited | Automatic offload to S3 | Pulsar |
| **Ecosystem maturity** | Very high | Growing | Kafka |
| **Operational complexity** | Medium | Higher | Kafka |
| **Resource overhead** | Higher (JVM) | Lower | Pulsar |
| **Exactly-once semantics** | Yes | Yes | Tie |
| **Consumer groups** | Yes | Yes + exclusive/failover/shared | Pulsar |

### Why Pulsar for This Use Case

1. **Lower Latency**: BookKeeper provides ~2x lower p99 latency than Kafka
2. **Unified Queuing**: One system for streaming (trades) and queuing (orders)
3. **Multi-tenancy**: Separate namespaces per client/strategy
4. **Tiered Storage**: Old data auto-offloads to S3 (cost savings)
5. **Function Mesh**: Native stream processing without Flink

### Topic Design

```
persistent://solana/trades/market-data      (16 partitions, 3x replication)
persistent://solana/trades/order-events     (8 partitions, 3x replication)
persistent://solana/trades/wallet-updates   (8 partitions, 3x replication)
persistent://solana/queue/order-requests    (4 partitions, 3x replication)
persistent://solana/queue/risk-checks       (4 partitions, 3x replication)
persistent://solana/analytics/aggregated    (2 partitions, 2x replication)
```

---

## 5. Latency Targets & SLOs

### Critical Path (Order Execution)

```
Target: p50 < 50ms, p99 < 100ms

┌────────────────────────────────────────────────────────────────────────┐
│  0ms        20ms       40ms       60ms       80ms      100ms          │
│   │         │          │          │          │          │              │
│   ▼         ▼          ▼          ▼          ▼          ▼              │
│  [API]─[Auth]─[Validation]─[Risk]─[Route]─[Confirm]                    │
│   2ms    3ms      5ms       15ms    20ms     10ms                      │
│                                                                        │
│  Budget breakdown:                                                     │
│  • Network ingress:        5ms                                         │
│  • API Gateway parsing:    3ms                                         │
│  • Auth + rate limit:      5ms  (Redis)                                │
│  • Validation:             5ms                                         │
│  • Risk engine:           15ms  (Position check)                       │
│  • Jupiter routing:       25ms  (External API)                         │
│  • Transaction confirm:   20ms  (Sim + submit)                         │
│  • Response:               5ms                                         │
│  ─────────────────────────────────                                     │
│  Total allocated:         83ms                                         │
│  Buffer:                  17ms                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Data Ingestion Path

```
Target: p50 < 10ms, p99 < 25ms

WebSocket ──► Parse ──► Normalize ──► Enrich ──► Pulsar ──► TimescaleDB
   1ms        2ms        3ms          5ms        2ms          5ms(async)
```

### SLO Definitions

| Metric | Target | Alert Threshold | Critical Threshold |
|--------|--------|-----------------|-------------------|
| Order latency (p50) | < 50ms | > 75ms | > 100ms |
| Order latency (p99) | < 100ms | > 150ms | > 200ms |
| Price feed latency | < 10ms | > 20ms | > 50ms |
| WebSocket connection uptime | 99.99% | < 99.95% | < 99.9% |
| API availability | 99.99% | < 99.95% | < 99.9% |
| Message backlog | < 1s | > 5s | > 30s |

### Circuit Breaker Thresholds

```yaml
risk-engine:
  error_threshold: 50%      # Open if >50% errors
  request_threshold: 10     # Min 10 requests
  timeout_duration: 30s     # Stay open for 30s
  half_open_requests: 3     # Test with 3 requests

jupiter-api:
  latency_threshold: 100ms  # Open if p99 > 100ms
  consecutive_errors: 5     # Or 5 consecutive errors
  fallback: internal-router # Route to backup
```

---

## 6. Infrastructure Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT STACK                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Orchestration:     Kubernetes (EKS/GKE) with Karpenter autoscaling     │
│  Service Mesh:      Istio (mTLS, traffic management)                    │
│  Monitoring:        Prometheus + Grafana + Jaeger tracing               │
│  Logging:           Loki + Vector                                       │
│  Secrets:           Vault + External Secrets Operator                   │
│  CI/CD:             ArgoCD (GitOps)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  Compute:                                                               │
│  • API Gateway:     3x c6i.2xlarge (arm64)                              │
│  • Microservices:   10+ pods, Karpenter node pools                      │
│  • Stream Process:  3x r6i.4xlarge (memory-optimized)                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Data Stores:                                                           │
│  • TimescaleDB:     3x db.r6g.2xlarge (AWS RDS)                         │
│  • Neo4j:           3x c6g.2xlarge (Aura Enterprise or self-hosted)     │
│  • Redis:           6-node cluster, cache.r6g.xlarge                    │
│  • Pulsar:          3x brokers + 3x bookies, i4i.2xlarge (NVMe)         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Event Bus | Pulsar | Lower latency, tiered storage, unified queuing |
| Time-series DB | TimescaleDB | SQL compatibility, continuous aggregates, compression |
| Graph DB | Neo4j | Native graph, Cypher queries, GDS analytics |
| Cache | Redis Cluster | Sub-ms latency, rich data structures, pub/sub |
| API Protocol | gRPC + REST | gRPC for internal, REST for external compatibility |
| Language | Rust (critical), Go (services), Python (ML) | Performance vs productivity balance |
| Deployment | Kubernetes | Portability, ecosystem, autoscaling |

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
