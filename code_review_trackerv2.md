# ShadowHunter Trading Tracker - Code Review

## Review Date: 2026-03-28
## File: `/root/.openclaw/workspace/trackerv2_clean.py`

---

## 1. TRANSACTION DETECTION FIXES

### Changes Made:
- Changed `getSignaturesForAddress` limit from 5 to 50
- Removed `[:5]` slice that was double-limiting  
- Added warning when exactly 50 signatures returned
- Added sorting by blockTime (oldest first) - NOW ALWAYS SORTS
- Changed `script_start_time` from `time.time()` to `int(time.time()) - 300`

### ✅ Confirmations:
**Sorting Logic is Correct:**
```python
signatures = sorted(signatures, key=lambda x: x.get('blockTime', 0) or 0)
```
- Uses `0` as default for missing blockTime (prevents TypeError)
- Oldest first ensures chronological processing - important for position tracking
- Correctly handles the edge case where `blockTime` could be `None`

**The 50 Signature Limit Helps:**
- **Before:** Only checked 5 most recent transactions per wallet per cycle
- **After:** Checks 50 transactions, catching burst activity
- With 43 wallets × 50 = 2,150 max signatures fetched per cycle
- 5-second check interval means ~25,800 RPC calls/minute potential (see Performance concerns)

**Script Start Time Change:**
- `int(time.time()) - 300` allows processing transactions from the last 5 minutes on startup
- Prevents missing transactions that occurred during deployment/restart window
- ✅ **Good:** Smooths over cold-start gaps

### ⚠️ Issues Found:

#### 1.1. Still Missing Transactions (51+ Case)
**Severity: MEDIUM**

```python
if len(signatures) == 50:
    logger.warning(f"Wallet {wallet[:8]}... has 50+ new transactions - may have missed some!")
```

**Problem:** Only warns but doesn't actually fetch more. If a wallet has 100 new transactions in 5 seconds:
- Only the most recent 50 are fetched
- 50 older transactions are silently skipped
- Position calculations become inaccurate

**Recommendation:** Implement pagination using `before` parameter:
```python
# Pseudocode for pagination
all_signatures = []
while len(batch) == 50:
    batch = getSignaturesForAddress(wallet, limit=50, before=last_sig)
    all_signatures.extend(batch)
    if len(all_signatures) >= MAX_TO_PROCESS:  # Cap at reasonable number
        break
```

#### 1.2. Processing Order Issue
**Severity: LOW**

The code marks transactions as processed BEFORE successfully parsing them:
```python
if await self.cache.get(f"tx:{sig}"):  # Check
    continue
await self.cache.setex(f"tx:{sig}", 2592000, "1")  # Mark immediately
# ... then process ...
```

If parsing fails (RPC error, malformed response), the transaction is marked done but never actually processed.

**Recommendation:** Only mark as processed after successful handling:
```python
try:
    result = await process_transaction(tx)
    if result:
        await self.cache.setex(f"tx:{sig}", 2592000, "1")
except Exception:
    # Don't mark - will retry next cycle
    pass
```

---

## 2. CLUSTER ALERT THROTTLING

### Changes Made:
- Added 5-second Redis throttle per token
- Changed from check-then-set to atomic SET NX
- Key: `cluster_throttle:{token}`

### ✅ Confirmations:
**SET NX Implementation is Correct:**
```python
throttle_key = f"cluster_throttle:{token}"
throttle_set = await self.cache.set(throttle_key, "1", nx=True, ex=5)
if not throttle_set:
    # Key already exists = within throttle window
    return
```

- `nx=True` ensures atomic check-and-set (no race condition)
- `ex=5` sets 5-second expiration
- Returns `False` if key exists (throttled)
- Returns `True` if key was newly created (allow alert)
- ✅ **Race condition FREE** - multiple concurrent calls will result in exactly one success

### ⚠️ Issues Found:

#### 2.1. Throttle Key Doesn't Distinguish Alert Type
**Severity: LOW**

```python
throttle_key = f"cluster_throttle:{token}"
```

Same throttle key used for all alert triggers (buy or sell). If:
1. Wallet A buys token → Alert sent → Throttle set
2. Wallet B sells same token 2 seconds later → Alert suppressed

**Expected:** Should we alert on significant sells even within throttle window?

**Recommendation:** Consider separate throttles or event-type tracking if business logic requires different behavior for buy vs sell cluster alerts.

#### 2.2. No Fallback if Redis Fails
**Severity: MEDIUM**

```python
throttle_set = await self.cache.set(throttle_key, "1", nx=True, ex=5)
if not throttle_set:
    return
```

If Redis is unavailable or slow, `await self.cache.set()` will:
- Timeout after Redis connection timeout (default typically 5s+)
- Raise exception that's not caught
- Potentially crash the alert flow

**Recommendation:** Wrap in try-except with fallback:
```python
try:
    throttle_set = await asyncio.wait_for(
        self.cache.set(throttle_key, "1", nx=True, ex=5),
        timeout=1.0
    )
    if not throttle_set:
        return
except (redis.RedisError, asyncio.TimeoutError):
    # Redis failed - allow alert (fail open) or deny (fail closed)
    # Current choice: implicit exception propagation = fail closed
    pass
```

---

## 3. DATABASE QUERY OPTIMIZATION

### Changes Made:
- Batch query for `/trackhold` command (N+1 fix)
- Single query with `ANY()` then dict lookup

### ✅ Confirmations:
**Implementation is Correct:**
```python
# FIX: Batch query all wallet positions in ONE database call (N+1 fix)
wallet_addresses = [w['address'] for w in tracker.wallets]
async with tracker.db_semaphore:
    all_position_rows = await tracker.db.fetch(
        """SELECT 
            wallet_address, 
            total_bought, 
            total_sold, 
            total_sol_invested, 
            first_buy_time, 
            avg_entry_mc
        FROM wallet_positions 
        WHERE wallet_address = ANY($1) AND token_address = $2""",
        wallet_addresses, 
        token_address
    )

# Build lookup dict for O(1) access
position_data = {row['wallet_address']: row for row in all_position_rows}
```

- ✅ `ANY($1)` uses PostgreSQL array containment - efficient index usage
- ✅ Single round-trip instead of N queries
- ✅ O(N) → O(1) lookup via dict
- For 43 wallets: was 43 queries, now 1 query

### ⚠️ Issues Found:

#### 3.1. Index May Be Missing
**Severity: MEDIUM**

Query pattern: `WHERE wallet_address = ANY($1) AND token_address = $2`

This requires an index like:
```sql
CREATE INDEX idx_wallet_positions_wallet_token 
ON wallet_positions(wallet_address, token_address);
```

Without this index, the query may still be slow with large `wallet_positions` table.

**Recommendation:** Verify index exists:
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'wallet_positions';
```

---

## 4. PERFORMANCE CONCERNS

### Current Load Calculation:

**Per Cycle (5 seconds):**
- 43 wallets × 1 `getSignaturesForAddress` call = 43 calls
- Each wallet may process up to 50 transactions
- Each transaction = 1 `getTransaction` call
- Max: 43 × 50 = 2,150 `getTransaction` calls per cycle
- **Total RPC calls per cycle: ~2,193**
- **Per minute: ~26,316 RPC calls**

### Rate Limiting Risks:

**Public RPC Endpoints:**
- `api.mainnet-beta.solana.com`: ~100 req/10s per IP (varies)
- `solana-rpc.publicnode.com`: Varies, often stricter
- **Current load exceeds public limits by ~20x**

**Helius/Alchemy (if configured):**
- Typically 100-1000 req/s depending on plan
- **Current load (~438 req/s) likely acceptable on paid plans**

### ⚠️ Issues Found:

#### 4.1. No Explicit Rate Limiting
**Severity: HIGH**

```python
for i, wallet in enumerate(tracker.wallets):
    # ... balance check ...
    if i % 5 == 0 and i > 0:
        await asyncio.sleep(0.1)  # Only in trackhold, minimal
```

The main transaction detection loop has **no rate limiting** between wallets.

**Recommendation:** Add semaphores or rate limiting:
```python
# Option 1: Semaphore for concurrent RPC calls
rpc_semaphore = asyncio.Semaphore(20)  # Max 20 concurrent RPC calls

async with rpc_semaphore:
    async with self.session.post(rpc_url, json=payload) as resp:
        ...

# Option 2: Explicit rate limiter
class RateLimiter:
    def __init__(self, rate_per_second):
        self.rate = rate_per_second
        self.tokens = rate_per_second
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens < 1:
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)
                self.tokens = 0
            else:
                self.tokens -= 1
```

#### 4.2. No RPC Backoff/Retry Strategy
**Severity: MEDIUM**

```python
except asyncio.TimeoutError:
    if attempt < max_retries - 1:
        continue
    return 0
```

On timeout, immediately tries next RPC. No exponential backoff.

**Recommendation:** Add exponential backoff between retries:
```python
import random

backoff = min(2 ** attempt + random.random(), 10)  # Max 10s
await asyncio.sleep(backoff)
```

---

## 5. BETTER SOLUTIONS & RECOMMENDATIONS

### 5.1. WebSocket vs Polling

**Current:** Polling every 5 seconds

**Recommended:** Helius WebSocket subscriptions

```python
# Helius WebSocket for real-time updates
# No polling needed - push-based
async def subscribe_transactions():
    ws_url = "wss://mainnet.helius-rpc.com/?api-key=YOUR_KEY"
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [wallet_address for wallet in wallets]},
                {"commitment": "confirmed"}
            ]
        }))
        
        async for message in ws:
            data = json.loads(message)
            # Process transaction immediately
```

**Benefits:**
- Real-time (sub-second latency vs 5-second polling)
- Lower RPC usage (only pays for actual transactions)
- No missing transactions due to pagination limits

**Trade-offs:**
- Requires WebSocket connection management (reconnect logic)
- Higher complexity
- Helius-specific (vendor lock-in)

### 5.2. Implement Proper Pagination

```python
async def get_all_signatures(self, wallet: str, since: int) -> List[dict]:
    """Fetch all signatures since timestamp with pagination"""
    all_sigs = []
    before = None
    max_pages = 5  # Prevent runaway pagination
    
    for page in range(max_pages):
        params = [wallet, {"limit": 50}]
        if before:
            params[1]["before"] = before
            
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": params
        }
        
        result = await self.rpc_call(payload)
        sigs = result.get('result', [])
        
        if not sigs:
            break
            
        # Filter by timestamp
        new_sigs = [s for s in sigs if s.get('blockTime', 0) >= since]
        all_sigs.extend(new_sigs)
        
        # Stop if we've gone back far enough
        if len(new_sigs) < len(sigs):
            break
            
        # Continue pagination
        before = sigs[-1]['signature']
    
    return all_sigs
```

### 5.3. Add Circuit Breaker for RPC Failures

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            raise
```

### 5.4. Add Metrics & Monitoring

```python
from prometheus_client import Counter, Histogram, Gauge

# Track RPC usage
rpc_calls_total = Counter('shadowhunter_rpc_calls_total', 'Total RPC calls', ['method', 'status'])
rpc_latency = Histogram('shadowhunter_rpc_latency_seconds', 'RPC latency', ['method'])
wallets_checked = Gauge('shadowhunter_wallets_checked', 'Wallets checked in last cycle')
transactions_processed = Counter('shadowhunter_transactions_processed_total', 'Transactions processed', ['type'])
cluster_alerts = Counter('shadowhunter_cluster_alerts_total', 'Cluster alerts sent')

# Usage in code:
with rpc_latency.labels(method='getSignaturesForAddress').time():
    response = await self.session.post(...)
rpc_calls_total.labels(method='getSignaturesForAddress', status='success').inc()
```

---

## 6. EDGE CASES TO ADDRESS

### 6.1. blockTime None Handling
```python
# Current:
signatures = sorted(signatures, key=lambda x: x.get('blockTime', 0) or 0)

# Better - separate handling:
valid_sigs = [s for s in signatures if s.get('blockTime')]
invalid_sigs = [s for s in signatures if not s.get('blockTime')]

# Sort valid ones
valid_sigs.sort(key=lambda x: x['blockTime'])

# Process invalid ones separately (or log warning)
if invalid_sigs:
    logger.warning(f"{len(invalid_sigs)} transactions have no blockTime")
```

### 6.2. Database Connection Pool Exhaustion
```python
# Current: max_size=8
self.db = await asyncpg.create_pool(..., min_size=2, max_size=8)

# With 43 wallets checking concurrently + db_semaphore(5):
# 5 concurrent DB operations max, but 8 connections in pool
# This is acceptable but monitor for wait times
```

### 6.3. Redis Connection Failures
```python
# Add health check and graceful degradation:
try:
    await self.cache.ping()
except redis.ConnectionError:
    logger.error("Redis unavailable - running without caching")
    self.cache = None  # Flag as unavailable

# In usage:
if self.cache:
    cached = await self.cache.get(key)
else:
    cached = None  # Skip cache
```

---

## 7. SUMMARY & PRIORITY FIXES

### 🔴 HIGH PRIORITY
1. **Add RPC rate limiting** - Current load will hit limits on public RPCs
2. **Implement pagination** - Missing transactions when 51+ in a cycle
3. **Add circuit breaker** - Prevent cascading failures when RPC is down

### 🟡 MEDIUM PRIORITY  
4. **Verify database index** - Ensure `wallet_positions(wallet_address, token_address)` index exists
5. **Add transaction processing confirmation** - Only mark as processed after successful handling
6. **Add Redis failure handling** - Graceful degradation when cache unavailable

### 🟢 LOW PRIORITY
7. **Add Prometheus metrics** - For monitoring and alerting
8. **Consider WebSocket migration** - For real-time, lower latency updates
9. **Distinguish throttle by alert type** - Buy vs sell cluster alerts

### ✅ CONFIRMED WORKING
- Cluster alert SET NX throttle (race-condition free)
- blockTime sorting logic (handles None correctly)
- Database batch query optimization (N+1 fixed)
- 5-minute startup window for transaction catching
- Basic retry logic for DB operations

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RPC rate limiting | HIGH | HIGH | Add rate limiter, use paid RPC |
| Missing transactions (51+) | MEDIUM | HIGH | Implement pagination |
| Redis failure | LOW | MEDIUM | Add fallback handling |
| DB pool exhaustion | LOW | MEDIUM | Monitor, increase pool if needed |
| Cascade failure on RPC down | MEDIUM | HIGH | Add circuit breaker |

**Overall Risk Level: MEDIUM-HIGH**
- Production deployment should address HIGH priority items first
- Current code may work with paid Helius/Alchemy on moderate volume
- Public RPCs will likely fail under current load
