# Free Self-Hosted Database & Storage Alternatives

A comprehensive guide to $0 self-hosted alternatives for TimescaleDB, Neo4j, Redis, ClickHouse, and other commercial databases.

---

## Table of Contents

1. [Time-Series Databases](#1-time-series-databases)
2. [Graph Databases](#2-graph-databases)
3. [Cache Solutions](#3-cache-solutions)
4. [Analytics Databases](#4-analytics-databases)
5. [Document Stores](#5-document-stores)
6. [Object Storage](#6-object-storage)
7. [Quick Comparison Matrix](#7-quick-comparison-matrix)

---

## 1. Time-Series Databases

### 1.1 InfluxDB (Open Source)

**License:** MIT License  
**Best For:** DevOps monitoring, IoT metrics, high ingestion workloads

#### Docker Compose

```yaml
version: '3.8'

services:
  influxdb:
    image: influxdb:2.7
    container_name: influxdb
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=adminpassword
      - DOCKER_INFLUXDB_INIT_ORG=myorg
      - DOCKER_INFLUXDB_INIT_BUCKET=metrics
      - DOCKER_INFLUXDB_INIT_RETENTION=30d
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - influxdb-config:/etc/influxdb2
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Telegraf for metrics collection
  telegraf:
    image: telegraf:1.28
    container_name: telegraf
    volumes:
      - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
    depends_on:
      - influxdb
    restart: unless-stopped

volumes:
  influxdb-data:
  influxdb-config:
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Network |
|------------|-----|-----|---------|---------|
| **Minimal** | 1 core | 2 GB | 20 GB SSD | 100 Mbps |
| **Development** | 2 cores | 4 GB | 50 GB SSD | 1 Gbps |
| **Production** | 4+ cores | 8+ GB | 100+ GB NVMe | 1 Gbps+ |

#### Performance Characteristics

- **Ingestion:** Excellent for low-cardinality workloads (few devices)
- **Query Speed:** Fast for simple rollups; slower for complex queries
- **Compression:** Good compression ratios (up to 10:1 for metrics)
- **Limitations:** Performance degrades significantly with high cardinality (>100K series)

---

### 1.2 TimescaleDB (Self-Hosted)

**License:** Apache 2.0  
**Best For:** Hybrid workloads, SQL compatibility, financial analytics

#### Docker Compose

```yaml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    container_name: timescaledb
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=adminpassword
      - POSTGRES_DB=timeseries
      - TIMESCALEDB_TELEMETRY=basic
    volumes:
      - timescaledb-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres 
      -c shared_preload_libraries=timescaledb
      -c max_connections=200
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
      -c maintenance_work_mem=512MB
    restart: unless-stopped
    shm_size: 1gb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d timeseries"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Optional: pgAdmin for management
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    ports:
      - "5050:80"
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@example.com
      - PGADMIN_DEFAULT_PASSWORD=adminpassword
    depends_on:
      - timescaledb
    restart: unless-stopped

volumes:
  timescaledb-data:
```

#### Init SQL Script (init.sql)

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create hypertable for time-series data
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    pressure DOUBLE PRECISION
);

-- Convert to hypertable with 1-day chunks
SELECT create_hypertable('metrics', 'time', chunk_time_interval => INTERVAL '1 day');

-- Create indexes for common queries
CREATE INDEX idx_device_time ON metrics (device_id, time DESC);

-- Enable compression for older data
ALTER TABLE metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id'
);

-- Automatically compress chunks older than 7 days
SELECT add_compression_policy('metrics', INTERVAL '7 days');
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 1 core | 2 GB | 20 GB SSD | Single-node only |
| **Development** | 2 cores | 4 GB | 50 GB SSD | Can enable compression |
| **Production** | 4+ cores | 8+ GB | 100+ GB NVMe | Multi-node via streaming replication |

#### Performance Characteristics

- **Ingestion:** ~3.5x faster than InfluxDB at high cardinality
- **Query Speed:** 3.4x-71x faster for complex queries vs InfluxDB
- **SQL Support:** Full PostgreSQL compatibility (joins, window functions, geospatial)
- **Compression:** 90%+ storage savings with native compression

---

### 1.3 PostgreSQL with Time-Scale Partitioning (Native)

**License:** PostgreSQL License  
**Best For:** Existing PostgreSQL users, simple time-series needs

#### Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres-timeseries
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=adminpassword
      - POSTGRES_DB=timeseries
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-native-partition.sql:/docker-entrypoint-initdb.d/init.sql
    command: >
      postgres
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
      -c work_mem=16MB
      -c maintenance_work_mem=512MB
    restart: unless-stopped

volumes:
  postgres-data:
```

#### Partitioning SQL Script

```sql
-- Create partitioned table
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL,
    value DOUBLE PRECISION,
    metadata JSONB
) PARTITION BY RANGE (time);

-- Create monthly partitions
CREATE TABLE metrics_y2024m01 PARTITION OF metrics
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE metrics_y2024m02 PARTITION OF metrics
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- Add more partitions as needed...

-- Create indexes
CREATE INDEX idx_metrics_time ON metrics (time DESC);
CREATE INDEX idx_metrics_device ON metrics (device_id, time DESC);

-- Partition maintenance function
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_date := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
    partition_name := 'metrics_y' || EXTRACT(YEAR FROM partition_date) || 
                      'm' || LPAD(EXTRACT(MONTH FROM partition_date)::TEXT, 2, '0');
    start_date := partition_date;
    end_date := partition_date + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF metrics 
                    FOR VALUES FROM (%L) TO (%L)', 
                   partition_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

---

### 1.4 Time-Series DB Comparison

| Feature | InfluxDB OSS | TimescaleDB | PostgreSQL Native |
|---------|--------------|-------------|-------------------|
| **License** | MIT | Apache 2.0 | PostgreSQL |
| **SQL Support** | InfluxQL/Flux | Full SQL | Full SQL |
| **Best For** | Low cardinality metrics | High cardinality + relational | Simple use cases |
| **High Availability** | Limited | Streaming replication | Streaming replication |
| **Compression** | Good | Excellent | Manual (TOAST) |
| **Learning Curve** | Medium | Low (if SQL familiar) | Low |

---

## 2. Graph Databases

### 2.1 Neo4j Community Edition

**License:** GPL v3  
**Best For:** General graph use, Cypher expertise, 1-3 hop traversals

#### Docker Compose

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/adminpassword
      - NEO4J_dbms_memory_heap_initial__size=1G
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
      - neo4j-import:/import
      - neo4j-plugins:/plugins
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "adminpassword", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  neo4j-data:
  neo4j-logs:
  neo4j-import:
  neo4j-plugins:
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 2 cores | 4 GB | 20 GB SSD | No clustering |
| **Development** | 4 cores | 8 GB | 50 GB SSD | Single node only |
| **Production** | 8+ cores | 16+ GB | 100+ GB NVMe | CE has no HA |

#### Limitations (Community Edition)

- **No clustering/causal clustering** (Enterprise only)
- **No LDAP/AD integration**
- **No role-based access control**
- **Limited monitoring tools**

---

### 2.2 Memgraph

**License:** BSL 1.1 (becomes Apache 2.0 after 4 years)  
**Best For:** Real-time streaming, Kafka/Pulsar integration, Neo4j migration

#### Docker Compose

```yaml
version: '3.8'

services:
  memgraph:
    image: memgraph/memgraph:2.15
    container_name: memgraph
    ports:
      - "7687:7687"  # Bolt
      - "7444:7444"  # WebSocket (Lab)
    environment:
      - MEMGRAPH_USER=admin
      - MEMGRAPH_PASSWORD=adminpassword
    volumes:
      - memgraph-data:/var/lib/memgraph
      - memgraph-logs:/var/log/memgraph
    command: >
      --log-level=INFO
      --query-execution-timeout-sec=600
      --memory-limit=2048
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mgconsole", "--username", "admin", "--password", "adminpassword", "--query", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Memgraph Lab (Web UI)
  memgraph-lab:
    image: memgraph/lab:2.15
    container_name: memgraph-lab
    ports:
      - "3000:3000"
    environment:
      - QUICK_CONNECT_MG_HOST=memgraph
      - QUICK_CONNECT_MG_PORT=7687
    depends_on:
      - memgraph
    restart: unless-stopped

volumes:
  memgraph-data:
  memgraph-logs:
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 1 core | 2 GB | 10 GB SSD | In-memory only |
| **Development** | 2 cores | 4 GB | 20 GB SSD | WAL + snapshots |
| **Production** | 4+ cores | 16+ GB | 50+ GB NVMe | All data in RAM |

#### Performance Characteristics

- **Throughput:** 132x higher mixed workload vs Neo4j (vendor benchmark)
- **Latency:** <1ms p99 for queries
- **Streaming:** 50,000+ events/second with native Kafka/Pulsar
- **Compatibility:** Neo4j Bolt protocol (drivers work unchanged)

---

### 2.3 ArangoDB

**License:** Apache 2.0 (Community: 100GB limit, non-commercial)  
**Best For:** Multi-model (graph + document + key-value), database consolidation

#### Docker Compose

```yaml
version: '3.8'

services:
  arangodb:
    image: arangodb/arangodb:3.11.8
    container_name: arangodb
    ports:
      - "8529:8529"
    environment:
      - ARANGO_ROOT_PASSWORD=adminpassword
    volumes:
      - arangodb-data:/var/lib/arangodb3
      - arangodb-apps:/var/lib/arangodb3-apps
    command: >
      arangod
      --server.endpoint=tcp://0.0.0.0:8529
      --log.level=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8529/_api/version", "-u", "root:adminpassword"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  arangodb-data:
  arangodb-apps:
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 1 core | 2 GB | 20 GB SSD | 100GB limit CE |
| **Development** | 2 cores | 4 GB | 50 GB SSD | SmartGraphs available |
| **Production** | 4+ cores | 8+ GB | 100+ GB NVMe | Enterprise for sharding |

---

### 2.4 Apache AGE (PostgreSQL Extension)

**License:** Apache 2.0  
**Best For:** Existing PostgreSQL users, hybrid relational/graph workloads

#### Docker Compose

```yaml
version: '3.8'

services:
  postgres-age:
    image: apache/age:latest
    container_name: postgres-age
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=adminpassword
      - POSTGRES_DB=graphdb
    volumes:
      - age-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  age-data:
```

#### Setup SQL

```sql
-- Load extension
CREATE EXTENSION IF NOT EXISTS age;

-- Load the age library
LOAD 'age';

-- Set search path
SET search_path = ag_catalog, "$user", public;

-- Create graph
SELECT create_graph('mygraph');

-- Create vertices and edges using Cypher
SELECT * FROM cypher('mygraph', $$
    CREATE (a:Person {name: 'Alice', age: 30})
    CREATE (b:Person {name: 'Bob', age: 25})
    CREATE (a)-[:FRIENDS]->(b)
    RETURN a, b
$$) AS (a agtype, b agtype);

-- Query graph
SELECT * FROM cypher('mygraph', $$
    MATCH (p:Person)-[:FRIENDS]->(friend)
    RETURN p.name, friend.name
$$) AS (person agtype, friend agtype);
```

---

### 2.5 Graph DB Comparison

| Feature | Neo4j CE | Memgraph | ArangoDB | Apache AGE |
|---------|----------|----------|----------|------------|
| **License** | GPL v3 | BSL/Apache | Apache 2.0* | Apache 2.0 |
| **Query Language** | Cypher | openCypher | AQL | Cypher + SQL |
| **Storage** | Disk-based | In-memory | Disk-based | PostgreSQL |
| **Free Tier Limit** | None | Unlimited | 100GB/non-commercial | None |
| **Clustering** | ❌ No | ⚠️ Enterprise | ⚠️ Enterprise | ✅ PG replication |
| **Streaming** | Limited | Native Kafka/Pulsar | Limited | Via PG |
| **Migration from Neo4j** | N/A | Low (95% compatible) | High (AQL rewrite) | Medium |

---

## 3. Cache Solutions

### 3.1 Redis (Self-Hosted)

**License:** BSD 3-clause (Redis 7.2+), Server Side Public License (RSAL for modules)  
**Best For:** General caching, pub/sub, session storage

#### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7.2-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # Redis with persistence (AOF + RDB)
  redis-persistent:
    image: redis:7.2-alpine
    container_name: redis-persistent
    ports:
      - "6380:6379"
    volumes:
      - redis-persistent-data:/data
    command: >
      redis-server
      --appendonly yes
      --appendfsync everysec
      --save 900 1
      --save 300 10
      --save 60 10000
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    restart: unless-stopped

  # Redis Sentinel (for HA)
  redis-sentinel:
    image: redis:7.2-alpine
    container_name: redis-sentinel
    ports:
      - "26379:26379"
    volumes:
      - ./sentinel.conf:/usr/local/etc/redis/sentinel.conf:ro
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis
    restart: unless-stopped

  # Redis Cluster (3 masters + 3 replicas)
  redis-cluster-init:
    image: redis:7.2-alpine
    container_name: redis-cluster-init
    command: >
      sh -c "
        redis-cli --cluster create 
        redis-node-1:6379 redis-node-2:6379 redis-node-3:6379
        redis-node-4:6379 redis-node-5:6379 redis-node-6:6379
        --cluster-replicas 1
        --cluster-yes
      "
    depends_on:
      - redis-node-1
      - redis-node-2
      - redis-node-3
      - redis-node-4
      - redis-node-5
      - redis-node-6

volumes:
  redis-data:
  redis-persistent-data:
```

#### redis.conf

```conf
# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Performance
tcp-keepalive 60
timeout 0
tcp-backlog 511

# Security
# requirepass yourpassword

# Logging
loglevel notice
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 1 core | 512 MB | 5 GB SSD | Single instance |
| **Development** | 2 cores | 2 GB | 10 GB SSD | Persistence enabled |
| **Production** | 4+ cores | 8+ GB | 50+ GB NVMe | Sentinel or Cluster |

---

### 3.2 KeyDB (Redis Fork)

**License:** BSD 3-clause  
**Best For:** Higher throughput needs, multi-master replication, active replicas

#### Docker Compose

```yaml
version: '3.8'

services:
  keydb:
    image: eqalpha/keydb:latest
    container_name: keydb
    ports:
      - "6379:6379"
    environment:
      - KEYDB_PASSWORD=adminpassword
    volumes:
      - keydb-data:/data
    command: >
      keydb-server
      --server-threads 4
      --maxmemory 1gb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --active-replica no
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "keydb-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # Multi-master active replica setup
  keydb-master-1:
    image: eqalpha/keydb:latest
    container_name: keydb-master-1
    ports:
      - "6379:6379"
    volumes:
      - keydb-master1-data:/data
    command: >
      keydb-server
      --server-threads 4
      --maxmemory 1gb
      --active-replica yes
      --multi-master yes
      --replicaof keydb-master-2 6380
      --port 6379
    restart: unless-stopped

  keydb-master-2:
    image: eqalpha/keydb:latest
    container_name: keydb-master-2
    ports:
      - "6380:6380"
    volumes:
      - keydb-master2-data:/data
    command: >
      keydb-server
      --server-threads 4
      --maxmemory 1gb
      --active-replica yes
      --multi-master yes
      --replicaof keydb-master-1 6379
      --port 6380
    restart: unless-stopped

  # KeyDB Flash (NVMe-backed storage for larger datasets)
  keydb-flash:
    image: eqalpha/keydb:latest
    container_name: keydb-flash
    ports:
      - "6381:6381"
    volumes:
      - keydb-flash-data:/data
    command: >
      keydb-server
      --server-threads 4
      --storage-provider flash /data/flash
      --maxmemory 512mb
      --port 6381
    restart: unless-stopped

volumes:
  keydb-data:
  keydb-master1-data:
  keydb-master2-data:
  keydb-flash-data:
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 1 core | 512 MB | 5 GB SSD | Single threaded |
| **Development** | 2 cores | 2 GB | 10 GB SSD | Multi-threaded |
| **Flash** | 2 cores | 512 MB | 100+ GB NVMe | NVMe-backed storage |

#### Performance Comparison (Redis vs KeyDB)

| Metric | Redis 7.2 | KeyDB (multi-thread) | Notes |
|--------|-----------|----------------------|-------|
| **Single-thread** | Baseline | Similar | 1 thread |
| **Multi-thread writes** | ~1089 ops/sec | Similar | With replication |
| **Multi-thread reads** | ~35,000 ops/sec | Similar | 512KB values |
| **With load balancer** | N/A | ~35,505 ops/sec | 2 instances |
| **Active replication** | Async | Multi-master | Conflict resolution |

**Note:** Recent Redis 7.2+ has narrowed the performance gap significantly. KeyDB's main advantages are:
- Built-in multi-threading (no config needed)
- Active replication (multi-master)
- MVCC for better read concurrency

---

### 3.3 In-Memory Cache Alternatives

#### DragonflyDB (Modern Redis Alternative)

```yaml
version: '3.8'

services:
  dragonfly:
    image: docker.dragonflydb.io/dragonflydb/dragonfly:latest
    container_name: dragonfly
    ports:
      - "6379:6379"
    volumes:
      - dragonfly-data:/data
    command: >
      --maxmemory=4gb
      --dir=/data
    restart: unless-stopped
    ulimits:
      memlock: -1

volumes:
  dragonfly-data:
```

#### Resource Requirements: DragonflyDB

| Deployment | CPU | RAM | Notes |
|------------|-----|-----|-------|
| **Minimal** | 1 core | 1 GB | Single node |
| **Production** | 4+ cores | 8+ GB | Vertical scaling |

---

### 3.4 Cache Comparison

| Feature | Redis | KeyDB | DragonflyDB |
|---------|-------|-------|-------------|
| **License** | BSD/RSAL | BSD | BSL/SSPL |
| **Multi-threaded** | Yes (7.2+) | Yes (native) | Yes (native) |
| **Active Replication** | No | Yes | No |
| **RAM Efficiency** | Good | Good | Excellent |
| **Max Dataset** | RAM only | RAM + Flash | RAM only |
| **Redis Compatible** | 100% | 100% | 100% |

---

## 4. Analytics Databases

### 4.1 ClickHouse (Self-Hosted)

**License:** Apache 2.0  
**Best For:** OLAP, log analytics, real-time dashboards, columnar storage

#### Docker Compose

```yaml
version: '3.8'

services:
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: clickhouse
    ports:
      - "8123:8123"  # HTTP
      - "9000:9000"  # Native protocol
    environment:
      - CLICKHOUSE_DB=analytics
      - CLICKHOUSE_USER=admin
      - CLICKHOUSE_PASSWORD=adminpassword
      - CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - clickhouse-logs:/var/log/clickhouse-server
      - ./clickhouse-config.xml:/etc/clickhouse-server/config.d/custom.xml:ro
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "clickhouse-client", "--query", "SELECT 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ClickHouse Keeper (for replication)
  clickhouse-keeper:
    image: clickhouse/clickhouse-keeper:latest
    container_name: clickhouse-keeper
    ports:
      - "9181:9181"
    volumes:
      - clickhouse-keeper-data:/var/lib/clickhouse-keeper
    restart: unless-stopped

volumes:
  clickhouse-data:
  clickhouse-logs:
  clickhouse-keeper-data:
```

#### Sample Queries

```sql
-- Create MergeTree table (main engine for time-series)
CREATE TABLE events (
    timestamp DateTime,
    user_id UInt64,
    event_type String,
    properties String CODEC(ZSTD(1))
) ENGINE = MergeTree()
ORDER BY (timestamp, user_id)
PARTITION BY toYYYYMM(timestamp);

-- Insert data
INSERT INTO events VALUES
    (now(), 1, 'click', '{"button": "signup"}'),
    (now(), 2, 'view', '{"page": "home"}');

-- Aggregate query
SELECT 
    toStartOfHour(timestamp) as hour,
    event_type,
    count() as count,
    uniqExact(user_id) as unique_users
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY hour, event_type
ORDER BY hour DESC;

-- Materialized view for pre-aggregation
CREATE MATERIALIZED VIEW events_hourly_mv
ENGINE = SummingMergeTree()
ORDER BY (hour, event_type)
AS SELECT
    toStartOfHour(timestamp) as hour,
    event_type,
    count() as event_count
FROM events
GROUP BY hour, event_type;
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 2 cores | 4 GB | 50 GB SSD | Single node |
| **Development** | 4 cores | 8 GB | 100 GB SSD | Compression enabled |
| **Production** | 8+ cores | 16+ GB | 500+ GB NVMe | Sharding + replication |

#### Performance Characteristics

- **Query Speed:** Sub-second on billions of rows
- **Compression:** 10x+ compression with ZSTD
- **Ingestion:** 100K+ rows/second per node
- **Concurrency:** 1000+ simultaneous queries

---

### 4.2 Apache Druid

**License:** Apache 2.0  
**Best For:** Real-time streaming analytics, high concurrency, event-driven data

#### Docker Compose (Single Server)

```yaml
version: '3.8'

services:
  # ZooKeeper for coordination
  zookeeper:
    image: zookeeper:3.8
    container_name: druid-zookeeper
    ports:
      - "2181:2181"
    environment:
      - ZOO_MY_ID=1
    volumes:
      - zookeeper-data:/data
      - zookeeper-logs:/datalog

  # PostgreSQL for metadata
  postgres-metadata:
    image: postgres:16-alpine
    container_name: druid-postgres
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_USER=druid
      - POSTGRES_PASSWORD=druidpassword
      - POSTGRES_DB=druid
    volumes:
      - postgres-druid-data:/var/lib/postgresql/data

  # Druid Coordinator
  coordinator:
    image: apache/druid:latest
    container_name: druid-coordinator
    ports:
      - "8081:8081"
    environment:
      - DRUID_HOST=coordinator
      - DRUID_SERVICE=coordinator
    volumes:
      - druid-data:/opt/druid/var
    command: coordinator
    depends_on:
      - zookeeper
      - postgres-metadata

  # Druid Broker
  broker:
    image: apache/druid:latest
    container_name: druid-broker
    ports:
      - "8082:8082"
    environment:
      - DRUID_HOST=broker
      - DRUID_SERVICE=broker
    volumes:
      - druid-data:/opt/druid/var
    command: broker
    depends_on:
      - zookeeper
      - postgres-metadata

  # Druid Historical
  historical:
    image: apache/druid:latest
    container_name: druid-historical
    ports:
      - "8083:8083"
    environment:
      - DRUID_HOST=historical
      - DRUID_SERVICE=historical
    volumes:
      - druid-data:/opt/druid/var
    command: historical
    depends_on:
      - zookeeper
      - postgres-metadata

  # Druid MiddleManager
  middlemanager:
    image: apache/druid:latest
    container_name: druid-middlemanager
    ports:
      - "8091:8091"
    environment:
      - DRUID_HOST=middlemanager
      - DRUID_SERVICE=middlemanager
    volumes:
      - druid-data:/opt/druid/var
    command: middleManager
    depends_on:
      - zookeeper
      - postgres-metadata

  # Druid Router
  router:
    image: apache/druid:latest
    container_name: druid-router
    ports:
      - "8888:8888"
    environment:
      - DRUID_HOST=router
      - DRUID_SERVICE=router
    volumes:
      - druid-data:/opt/druid/var
    command: router
    depends_on:
      - zookeeper
      - postgres-metadata

volumes:
  zookeeper-data:
  zookeeper-logs:
  postgres-druid-data:
  druid-data:
```

#### Resource Requirements

| Component | CPU | RAM | Storage |
|-----------|-----|-----|---------|
| **Coordinator** | 1 core | 2 GB | 10 GB |
| **Broker** | 2 cores | 4 GB | 10 GB |
| **Historical** | 4 cores | 8 GB | 100+ GB |
| **MiddleManager** | 4 cores | 8 GB | 50 GB |
| **Router** | 1 core | 1 GB | 10 GB |
| **ZooKeeper** | 1 core | 2 GB | 10 GB |
| **PostgreSQL** | 1 core | 2 GB | 20 GB |

**Total Minimum:** 14 cores, 27 GB RAM

---

### 4.3 PostgreSQL with Columnar Extension

**License:** PostgreSQL License  
**Best For:** Mixed workloads, already using PostgreSQL

#### Docker Compose

```yaml
version: '3.8'

services:
  postgres-columnar:
    image: citusdata/citus:12.1
    container_name: postgres-columnar
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=adminpassword
      - POSTGRES_DB=analytics
    volumes:
      - citus-data:/var/lib/postgresql/data
    command: >
      postgres
      -c shared_preload_libraries=citus
      -c shared_buffers=4GB
      -c effective_cache_size=12GB
      -c work_mem=64MB
    restart: unless-stopped

volumes:
  citus-data:
```

#### Columnar Setup

```sql
-- Enable Citus extension
CREATE EXTENSION IF NOT EXISTS citus;

-- Create columnar table
CREATE TABLE events_columnar (
    event_id BIGSERIAL,
    event_time TIMESTAMP NOT NULL,
    user_id BIGINT,
    event_type TEXT,
    payload JSONB
) USING columnar;

-- Insert data
INSERT INTO events_columnar (event_time, user_id, event_type, payload)
SELECT 
    NOW() - INTERVAL '1 hour' * random() * 1000,
    (random() * 1000000)::BIGINT,
    CASE (random() * 3)::INT 
        WHEN 0 THEN 'click'
        WHEN 1 THEN 'view'
        WHEN 2 THEN 'purchase'
        ELSE 'other'
    END,
    '{}'::JSONB
FROM generate_series(1, 1000000);

-- Query with compression statistics
SELECT * FROM columnar_stats('events_columnar');
```

---

### 4.4 Analytics DB Comparison

| Feature | ClickHouse | Apache Druid | PostgreSQL+Citus |
|---------|------------|--------------|------------------|
| **License** | Apache 2.0 | Apache 2.0 | PostgreSQL |
| **Architecture** | Single-node/Cluster | Microservices | Single-node/Cluster |
| **Best For** | Batch OLAP | Streaming real-time | Mixed workloads |
| **Query Latency** | Sub-second | Sub-second | Seconds (large data) |
| **JOIN Support** | Good | Limited | Excellent |
| **SQL Support** | Extensive | Via Calcite | Full SQL |
| **Resource Usage** | Moderate | High | Low |
| **Auto-scaling** | Manual | Better | Manual |
| **Deep Storage** | No | Yes (S3/HDFS) | No |

---

## 5. Document Stores

### 5.1 MongoDB Community Edition

**License:** SSPL (Server Side Public License)  
**Best For:** Flexible schemas, rapid development, horizontal scaling

#### Docker Compose

```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: mongodb
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=adminpassword
      - MONGO_INITDB_DATABASE=myapp
    volumes:
      - mongodb-data:/data/db
      - mongodb-config:/data/configdb
      - ./mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js:ro
    restart: unless-stopped
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
      interval: 10s
      timeout: 10s
      retries: 5

  # MongoDB Replica Set (for production)
  mongo-primary:
    image: mongo:7.0
    container_name: mongo-primary
    ports:
      - "27017:27017"
    command: >
      mongod 
      --replSet rs0
      --bind_ip_all
      --keyFile /data/configdb/keyfile
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=adminpassword
    volumes:
      - mongo-primary-data:/data/db
      - mongo-primary-config:/data/configdb
    restart: unless-stopped

  mongo-secondary-1:
    image: mongo:7.0
    container_name: mongo-secondary-1
    command: >
      mongod 
      --replSet rs0
      --bind_ip_all
      --keyFile /data/configdb/keyfile
    volumes:
      - mongo-secondary1-data:/data/db
      - mongo-primary-config:/data/configdb:ro
    restart: unless-stopped

  mongo-secondary-2:
    image: mongo:7.0
    container_name: mongo-secondary-2
    command: >
      mongod 
      --replSet rs0
      --bind_ip_all
      --keyFile /data/configdb/keyfile
    volumes:
      - mongo-secondary2-data:/data/db
      - mongo-primary-config:/data/configdb:ro
    restart: unless-stopped

volumes:
  mongodb-data:
  mongodb-config:
  mongo-primary-data:
  mongo-primary-config:
  mongo-secondary1-data:
  mongo-secondary2-data:
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 1 core | 1 GB | 10 GB SSD | Single node |
| **Development** | 2 cores | 4 GB | 50 GB SSD | WiredTiger cache |
| **Production** | 4+ cores | 8+ GB | 100+ GB NVMe | Replica set |

---

### 5.2 PostgreSQL JSONB

**License:** PostgreSQL License  
**Best For:** Hybrid relational/document, ACID needs, SQL familiarity

#### Docker Compose

```yaml
version: '3.8'

services:
  postgres-jsonb:
    image: postgres:16-alpine
    container_name: postgres-jsonb
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=adminpassword
      - POSTGRES_DB=documentdb
    volumes:
      - postgres-jsonb-data:/var/lib/postgresql/data
      - ./init-jsonb.sql:/docker-entrypoint-initdb.d/init.sql:ro
    command: >
      postgres
      -c shared_buffers=2GB
      -c effective_cache_size=6GB
    restart: unless-stopped

volumes:
  postgres-jsonb-data:
```

#### JSONB Setup

```sql
-- Create document table
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    doc JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create GIN index for efficient JSON queries
CREATE INDEX idx_documents_doc ON documents USING GIN (doc);

-- Create B-tree index for specific JSON keys
CREATE INDEX idx_documents_user_id ON documents ((doc->>'user_id'));

-- Insert documents
INSERT INTO documents (doc) VALUES
    ('{"user_id": "1", "name": "Alice", "tags": ["admin", "user"], "metadata": {"login_count": 5}}'),
    ('{"user_id": "2", "name": "Bob", "tags": ["user"], "metadata": {"login_count": 12}}');

-- Query documents
SELECT * FROM documents WHERE doc @> '{"tags": ["admin"]}';

-- Aggregate with JSON
SELECT 
    doc->>'user_id' as user_id,
    doc->>'name' as name,
    (doc->'metadata'->>'login_count')::INT as logins
FROM documents
WHERE doc @> '{"tags": ["user"]}'
ORDER BY logins DESC;

-- Partial update
UPDATE documents 
SET doc = jsonb_set(doc, '{metadata,login_count}', 
    ((doc->'metadata'->>'login_count')::INT + 1)::TEXT::JSONB)
WHERE id = 1;
```

---

### 5.3 Document Store Comparison

| Feature | MongoDB CE | PostgreSQL JSONB |
|---------|------------|------------------|
| **License** | SSPL | PostgreSQL |
| **Schema** | Flexible | Flexible + constraints |
| **Horizontal Scaling** | Native sharding | Via Citus |
| **ACID** | Multi-doc (4.0+) | Full ACID |
| **Aggregation** | Pipeline | SQL + JSON functions |
| **Indexing** | Rich (text, geo, TTL) | GIN, B-tree on paths |
| **Replication** | Replica sets | Streaming replication |

#### Performance Comparison

| Workload | MongoDB | PostgreSQL JSONB | Winner |
|----------|---------|------------------|--------|
| Single inserts | 17,658/s | 17,373/s | Tie |
| Batch inserts | 115/s (1000 docs) | 81/s | MongoDB |
| Finds by ID | 41,494/s | 43,788/s | PostgreSQL |
| Sorted queries | 20,161 QPS | 4,867 QPS | MongoDB |
| Aggregation | Good | Excellent | PostgreSQL |

---

## 6. Object Storage

### 6.1 MinIO (Self-Hosted S3)

**License:** AGPL v3  
**Best For:** S3-compatible storage, multi-cloud, data lake foundation

#### Docker Compose (Single Node)

```yaml
version: '3.8'

services:
  minio:
    image: minio/minio:latest
    container_name: minio
    ports:
      - "9000:9000"  # S3 API
      - "9001:9001"  # Console
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=adminpassword
      - MINIO_BROWSER_REDIRECT_URL=http://localhost:9001
    volumes:
      - minio-data:/data
    command: server /data --console-address ":9001"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
```

#### Docker Compose (Distributed Cluster)

```yaml
version: '3.8'

# 4-node distributed setup with erasure coding
# Requires: 4 servers with docker

services:
  minio-node1:
    image: minio/minio:latest
    container_name: minio-node1
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=adminpassword
    volumes:
      - minio-data1-1:/data1
      - minio-data1-2:/data2
    command: >
      server 
      http://minio-node{1...4}/data{1...2}
      --console-address ":9001"
    restart: unless-stopped

volumes:
  minio-data1-1:
  minio-data1-2:
```

#### Resource Requirements

| Deployment | CPU | RAM | Storage | Notes |
|------------|-----|-----|---------|-------|
| **Minimal** | 1 core | 1 GB | 10 GB | Single node |
| **Development** | 2 cores | 4 GB | 100 GB | Single node |
| **Production** | 4+ cores | 8+ GB | 1+ TB per node | 4+ nodes, erasure coding |

#### Performance Characteristics

- **Throughput:** 10+ GB/s read, 5+ GB/s write (clustered)
- **Latency:** Sub-10ms for small objects
- **Scalability:** Scale-out architecture
- **Durability:** 99.999999999% (11 nines) with erasure coding

---

### 6.2 Local Filesystem (Simple Alternative)

**Best For:** Single-node applications, development, low complexity

#### Docker Compose (with NFS/SMB)

```yaml
version: '3.8'

services:
  # Simple file server with HTTP API
  filebrowser:
    image: filebrowser/filebrowser:latest
    container_name: filebrowser
    ports:
      - "8080:80"
    volumes:
      - file-storage:/srv
      - ./filebrowser.db:/database.db
      - ./settings.json:/config/settings.json
    restart: unless-stopped

  # SFTP server for file access
  sftp:
    image: atmoz/sftp:alpine
    container_name: sftp
    ports:
      - "2222:22"
    volumes:
      - file-storage:/home/admin/upload
    command: admin:adminpassword:1001
    restart: unless-stopped

volumes:
  file-storage:
```

---

### 6.3 Alternative Object Storage Options

| Solution | License | Best For | Complexity |
|----------|---------|----------|------------|
| **MinIO** | AGPL | Production S3 replacement | Low |
| **SeaweedFS** | Apache 2.0 | Large-scale distributed | Medium |
| **Garage** | AGPL | S3-compatible, lightweight | Medium |
| **S3Proxy** | Apache 2.0 | Gateway to other storage | Low |
| **Zenko CloudServer** | Apache 2.0 | Multi-cloud abstraction | Medium |

---

## 7. Quick Comparison Matrix

### Resource Requirements Summary

| Database | Min CPU | Min RAM | Min Storage | Best Use Case |
|----------|---------|---------|-------------|---------------|
| **InfluxDB OSS** | 1 core | 2 GB | 20 GB | IoT metrics |
| **TimescaleDB** | 1 core | 2 GB | 20 GB | Hybrid workloads |
| **Neo4j CE** | 2 cores | 4 GB | 20 GB | Graph analytics |
| **Memgraph** | 1 core | 2 GB | 10 GB | Real-time streaming |
| **Redis** | 1 core | 512 MB | 5 GB | General caching |
| **KeyDB** | 1 core | 512 MB | 5 GB | High-throughput cache |
| **ClickHouse** | 2 cores | 4 GB | 50 GB | OLAP analytics |
| **Apache Druid** | 14 cores* | 27 GB* | 200 GB+ | Streaming analytics |
| **MongoDB CE** | 1 core | 1 GB | 10 GB | Document storage |
| **PostgreSQL** | 1 core | 1 GB | 10 GB | All-purpose |
| **MinIO** | 1 core | 1 GB | 10 GB | Object storage |

*Druid requires multiple services - total cluster minimum

### License Comparison

| Database | License | Commercial Use | Distribution | Modifications |
|----------|---------|----------------|--------------|---------------|
| **InfluxDB OSS** | MIT | ✅ | ✅ | ✅ |
| **TimescaleDB** | Apache 2.0 | ✅ | ✅ | ✅ |
| **Neo4j CE** | GPL v3 | ✅ | ✅ | Must share source |
| **Memgraph** | BSL → Apache | ✅ | ✅ | Time-delayed OSS |
| **ArangoDB** | Apache 2.0* | ⚠️ Non-comm CE | ✅ | ✅ |
| **Apache AGE** | Apache 2.0 | ✅ | ✅ | ✅ |
| **Redis** | BSD/RSAL | ✅ | ✅ | Module restrictions |
| **KeyDB** | BSD | ✅ | ✅ | ✅ |
| **ClickHouse** | Apache 2.0 | ✅ | ✅ | ✅ |
| **Apache Druid** | Apache 2.0 | ✅ | ✅ | ✅ |
| **MongoDB** | SSPL | ✅ | ⚠️ SaaS restriction | ⚠️ |
| **PostgreSQL** | PostgreSQL | ✅ | ✅ | ✅ |
| **MinIO** | AGPL | ✅ | ✅ | Must share source |

### Performance at a Glance

| Workload | Top Choice | Alternative | Notes |
|----------|------------|-------------|-------|
| **Time-series (low card)** | InfluxDB | TimescaleDB | InfluxDB simpler |
| **Time-series (high card)** | TimescaleDB | ClickHouse | TimescaleDB better SQL |
| **Graph (general)** | Neo4j CE | Memgraph | Neo4j more mature |
| **Graph (streaming)** | Memgraph | Neo4j CE | Memgraph 132x throughput |
| **Cache (general)** | Redis | KeyDB | Redis more mature |
| **Cache (high throughput)** | KeyDB | Redis | KeyDB multi-master |
| **OLAP analytics** | ClickHouse | Apache Druid | ClickHouse simpler |
| **Streaming analytics** | Apache Druid | ClickHouse | Druid true real-time |
| **Document (flexible)** | MongoDB | PostgreSQL JSONB | MongoDB native |
| **Document + ACID** | PostgreSQL JSONB | MongoDB | PG better transactions |
| **Object storage** | MinIO | Local FS | MinIO S3-compatible |

---

## Migration Tips

### From Cloud to Self-Hosted

1. **Data Export**: Use native export tools (mysqldump, mongodump, etc.)
2. **Data Transform**: Convert formats if needed (e.g., BSON to JSON)
3. **Import**: Use bulk import features for faster loading
4. **Verify**: Run consistency checks after migration
5. **Optimize**: Tune configuration for your hardware

### Cost Comparison (Monthly, Approximate)

| Service | Cloud Cost | Self-Hosted (VPS) | Savings |
|---------|------------|-------------------|---------|
| Managed TimescaleDB | $200-500 | $20-50 | 90% |
| Neo4j Aura | $65-500 | $20-100 | 80% |
| Redis Cloud | $20-500 | $10-50 | 75% |
| ClickHouse Cloud | $200-1000 | $50-200 | 80% |
| MongoDB Atlas | $60-500 | $20-100 | 75% |
| AWS S3 (1TB) | $23 | $10 (MinIO) | 55% |

*Self-hosted costs based on 2-4 core VPS with 4-8GB RAM

---

## Conclusion

This guide covers production-ready, free alternatives to commercial database services. All solutions listed:

- ✅ Are free to use (no licensing fees)
- ✅ Can be self-hosted
- ✅ Have Docker Compose examples
- ✅ Are suitable for production use
- ✅ Have active communities

Choose based on your specific workload, existing expertise, and infrastructure constraints.

---

*Last updated: March 2025*
