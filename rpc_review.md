# ShadowHunter RPC & Error Handling Strategy Review

## Executive Summary

After reviewing `trackerv2_clean.py`, I've identified **5 critical issues** that could cause transaction loss or alert delays during high-volume scenarios. Below are the findings categorized by the questions asked.

---

## 1. HIGH VOLUME SCENARIOS - CRITICAL ISSUES

### Issue 1.1: Transaction Loss on High Volume (HIGH RISK)

**Problem:** When 20+ transactions occur in 5 seconds, the pagination logic WILL lose transactions.

**Current Logic:**
```python
# Fetches only 20 signatures
payload = {"method": "getSignaturesForAddress", "params": [wallet, {"limit": 20}]}

# If we hit the limit, only warn - don't recover
if len(signatures) == 20:
    logger.warning(f"Wallet {wallet[:8]}... has 20+ new transactions - some may be missed!")
```

**Why Transactions Get Lost:**
1. Wallet has 25 new transactions in 5 seconds
2. `getSignaturesForAddress` returns the 20 most recent
3. `last_seen_sigs` only stores the most recent sig (index 0)
4. Next cycle: fetch 20 sigs, compare to last_seen (which is #25 from previous cycle)
5. System only sees transactions #21-25, misses #1-20 entirely

**Root Cause:** The pagination only filters forward from `last_seen`, but when the limit is exceeded, older transactions are permanently skipped.

**Fix Required:**
```python
# After hitting limit, paginate backwards until we find last_seen
if len(signatures) == 20:
    # Keep fetching with 'before' parameter until we find last_seen
    all_signatures = []
    all_signatures.extend(signatures)
    
    while len(signatures) == 20:
        # Get the oldest signature from current batch
        oldest_sig = signatures[-1]['signature']
        
        # Fetch older signatures
        payload = {
            "method": "getSignaturesForAddress", 
            "params": [wallet, {"limit": 20, "before": oldest_sig}]
        }
        # ... fetch more
        
        # Stop if we found last_seen
        if last_seen in [s['signature'] for s in signatures]:
            break
```

---

### Issue 1.2: Race Condition in last_seen_sigs Update (MEDIUM RISK)

**Problem:** `last_seen_sigs` is updated BEFORE transactions are fully processed.

```python
# Current flow:
if signatures:
    self.last_seen_sigs[wallet] = signatures[0]['signature']  # Updated here
    
# ... but then if processing fails or is interrupted:
for sig_info in signatures:
    # If exception occurs here, those sigs are now "lost" because
    # last_seen was already updated
```

**Fix:** Only update `last_seen_sigs` after successful processing of all signatures.

---

## 2. RPC FALLBACK STRATEGY - ISSUES & RECOMMENDATIONS

### Issue 2.1: Round-Robin is Suboptimal

**Current:** Simple round-robin rotation through RPCs.

**Problems:**
1. No tracking of which RPCs are healthy
2. No detection of rate limits (429 responses)
3. No circuit breaker - keeps trying failed RPCs
4. 3-second timeout may be too aggressive for public RPCs under load

### Issue 2.2: Missing HTTP 429 Handling

The current error handling catches:
- `asyncio.TimeoutError` ✓
- `aiohttp.ClientSSLError` ✓
- `aiohttp.ClientConnectorError` ✓

**Missing:** HTTP 429 (Rate Limited) detection and backoff.

**Recommended Implementation:**

```python
class RPCManager:
    def __init__(self, urls):
        self.rpcs = [
            {
                'url': url,
                'healthy': True,
                'failures': 0,
                'last_failure': 0,
                'rate_limited_until': 0
            }
            for url in urls
        ]
        self.current_index = 0
    
    def get_healthy_rpc(self):
        now = time.time()
        healthy_rpcs = [
            r for r in self.rpcs 
            if r['healthy'] and r['rate_limited_until'] < now
        ]
        
        if not healthy_rpcs:
            # All unhealthy - reset oldest failure
            oldest = min(self.rpcs, key=lambda r: r['last_failure'])
            oldest['healthy'] = True
            oldest['failures'] = 0
            return oldest['url']
        
        # Round-robin among healthy
        idx = self.current_index % len(healthy_rpcs)
        self.current_index += 1
        return healthy_rpcs[idx]['url']
    
    def report_result(self, url, success, is_rate_limit=False):
        for rpc in self.rpcs:
            if rpc['url'] == url:
                if success:
                    rpc['failures'] = 0
                    rpc['healthy'] = True
                else:
                    rpc['failures'] += 1
                    rpc['last_failure'] = time.time()
                    
                    if is_rate_limit:
                        rpc['rate_limited_until'] = time.time() + 30  # 30s backoff
                    elif rpc['failures'] >= 5:
                        rpc['healthy'] = False  # Circuit breaker
```

---

## 3. CONCURRENCY ISSUES

### Issue 3.1: RPC Semaphore May Be Too Low

**Current Math:**
- 8 wallet checks concurrently
- Each wallet: 1 (getSignaturesForAddress) + up to 20 (getTransaction) = ~21 RPC calls
- Total potential: 8 × 21 = 168 concurrent RPC calls
- Semaphore: 20

**Result:** Significant queuing delay under load.

**Analysis:**
```
With 20 RPC semaphore and 168 potential calls:
- 148 calls will be queued
- At ~200ms per RPC = 29.6 seconds of queuing delay
- But CHECK_INTERVAL is only 5 seconds!
```

**Recommendation:** Either:
1. Increase `rpc_semaphore` to 40-50, OR
2. Reduce `wallet_check_semaphore` to 4, OR
3. Implement smarter batching

### Issue 3.2: Wallet A's Processing CAN Block Wallet B's Alerts

**Current Flow:**
```python
async with self.wallet_check_semaphore:
    return await self.check_wallet_fast(wallet)
```

Inside `check_wallet_fast`:
1. Fetch signatures (RPC)
2. For each signature:
   - Fetch transaction (RPC)
   - Update database (DB semaphore)
   - Check cluster (DB + potential Telegram API call)
   - **Send alert** (Telegram API - blocking)
   - `await asyncio.sleep(0.5)` between alerts

**Problem:** The entire wallet check holds the semaphore, including alert sending. If Wallet A has 5 transactions, it holds the semaphore for:
- 5 RPC calls (~1s)
- 5 DB updates (~500ms)
- 5 Telegram sends (~2-5s)
- 5 × 0.5s sleep = 2.5s
= **~6-9 seconds per wallet**

With only 8 concurrent wallet slots, this creates a significant bottleneck.

---

## 4. INFORMATION FLOW INTEGRITY - CRITICAL BLOCKING

### Issue 4.1: Alerts Are Blocking Operations (HIGH IMPACT)

**Current:**
```python
await self.send_alert(...)  # Blocks until Telegram responds
await asyncio.sleep(0.5)    # Additional blocking delay
```

**Problem:** Every alert waits for:
1. HTTP request to Telegram API
2. Network round-trip
3. Telegram server processing
4. Response return

This is typically 200-500ms per alert, but can spike to 2-3s during Telegram API congestion.

### Issue 4.2: Database Writes Are Synchronous in Flow

```python
async with self.db_semaphore:
    await self.cluster_detector.update_position(...)  # Blocks
    await self.cluster_detector.check_cluster(...)    # Blocks
    await self.performance_tracker.record_trade(...)  # Blocks
```

These are all awaited inline, delaying the next transaction processing.

### Issue 4.3: Cache Writes Are Inline

```python
await self.cache.setex(f"tx:{sig}", 2592000, "1")  # 30 days
```

Redis write happens synchronously in the processing loop.

---

## 5. SPEED OPTIMIZATIONS - RECOMMENDATIONS

### Recommendation 5.1: Implement Alert Queue

Separate alert sending from transaction processing:

```python
class AlertQueue:
    def __init__(self, bot, max_queue=1000):
        self.bot = bot
        self.queue = asyncio.Queue(maxsize=max_queue)
        self._task = None
    
    async def start(self):
        self._task = asyncio.create_task(self._process_loop())
    
    async def enqueue(self, alert_data):
        try:
            self.queue.put_nowait(alert_data)
        except asyncio.QueueFull:
            logger.error("Alert queue full - dropping alert")
    
    async def _process_loop(self):
        while True:
            try:
                alert = await self.queue.get()
                await self._send_alert(alert)
                self.queue.task_done()
            except Exception as e:
                logger.error(f"Alert sending failed: {e}")
            await asyncio.sleep(0.1)  # Rate limiting
```

**Impact:** Transaction processing no longer blocked by Telegram API latency.

### Recommendation 5.2: Batch Database Writes

Instead of 3 DB calls per transaction, batch them:

```python
# Collect all updates for a wallet
db_updates = []
for sig_info in signatures:
    # ... processing ...
    db_updates.append({
        'wallet': wallet,
        'token': token,
        'type': tx_type,
        'amount': token_amount,
        'sol': sol_amount
    })

# Single batch write
if db_updates:
    await self.batch_update_positions(db_updates)
```

### Recommendation 5.3: Fire-and-Forget Cache Writes

```python
# Instead of:
await self.cache.setex(f"tx:{sig}", 2592000, "1")

# Use:
asyncio.create_task(self._cache_tx(sig))  # Fire and forget

async def _cache_tx(self, sig):
    try:
        await self.cache.setex(f"tx:{sig}", 2592000, "1")
    except Exception:
        pass  # Cache failure shouldn't block
```

### Recommendation 5.4: Optimize RPC Calls

**Current:** 1 + N RPC calls per wallet (1 for signatures, N for transactions)

**Optimization:** Use `getSignatureStatuses` batching or Helius webhooks if available.

Since budget is constrained, consider:
1. Prioritize wallets with recent activity (track last activity time, check active wallets more frequently)
2. Use a "watermark" approach - only check wallets with on-chain changes

### Recommendation 5.5: Transaction Deduplication Before Processing

Check cache BEFORE fetching transaction details:

```python
# Current: Fetches tx, then checks cache
async with self.rpc_semaphore:
    async with self.session.post(...) as tx_resp:
        tx_data = await tx_resp.json()
        
if await self.cache.get(f"tx:{sig}"):  # Check after fetch
    continue

# Better: Check before expensive fetch
if await self.cache.get(f"tx:{sig}"):
    continue  # Skip fetch entirely

async with self.rpc_semaphore:
    # ... fetch only if not cached
```

---

## PRIORITY FIX LIST

### CRITICAL (Fix Immediately - Data Loss Risk)
1. **Fix pagination logic** - Implement proper "before" parameter pagination when hitting 20-sig limit
2. **Move last_seen_sigs update** - Only update after successful processing
3. **Add dedupe check before getTransaction** - Save unnecessary RPC calls

### HIGH (Fix Soon - Performance Impact)
4. **Implement alert queue** - Decouple alerts from processing
5. **Add RPC health tracking** - Stop using failed RPCs immediately
6. **Add HTTP 429 handling** - Respect rate limits with backoff

### MEDIUM (Optimize When Possible)
7. **Batch database writes** - Reduce DB round-trips
8. **Fire-and-forget cache writes** - Don't block on Redis
9. **Tune semaphore values** - Based on actual RPC capacity

### LOW (Nice to Have)
10. **Implement wallet prioritization** - Check active wallets more frequently
11. **Add metrics/logging** - Track RPC latency, alert latency, queue depths

---

## CODE PATTERN FIXES

### Fix 1: Proper Pagination

```python
async def _fetch_all_signatures(self, wallet: str, last_seen: str = None) -> list:
    """Fetch all signatures since last_seen, handling pagination."""
    all_sigs = []
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet, {"limit": 20}]
    }
    
    while True:
        url = self.get_rpc()
        async with self.rpc_semaphore:
            async with self.session.post(url, json=payload) as resp:
                data = await resp.json()
        
        signatures = data.get('result', [])
        if not signatures:
            break
        
        # Filter to only new signatures
        new_sigs = []
        for sig_info in signatures:
            if sig_info['signature'] == last_seen:
                break
            new_sigs.append(sig_info)
        
        all_sigs.extend(new_sigs)
        
        # If we found last_seen or got fewer than limit, we're done
        if len(new_sigs) < len(signatures) or len(signatures) < 20:
            break
        
        # Otherwise, fetch older signatures
        payload['params'][1]['before'] = signatures[-1]['signature']
        
        # Safety: limit total pagination to prevent infinite loops
        if len(all_sigs) >= 100:
            logger.warning(f"Pagination limit hit for {wallet[:8]}... - possible missed transactions")
            break
    
    return all_sigs
```

### Fix 2: Non-Blocking Alert Queue

```python
class ShadowHunterTracker:
    def __init__(self):
        # ... existing init ...
        self.alert_queue = asyncio.Queue(maxsize=500)
        self._alert_task = None
    
    async def connect(self):
        # ... existing connect ...
        self._alert_task = asyncio.create_task(self._alert_worker())
    
    async def _alert_worker(self):
        """Background task to send alerts without blocking processing."""
        while True:
            try:
                alert_data = await self.alert_queue.get()
                if alert_data is None:  # Shutdown signal
                    break
                
                await self._send_alert_impl(alert_data)
                self.alert_queue.task_done()
                await asyncio.sleep(0.3)  # Rate limit between alerts
            except Exception as e:
                logger.error(f"Alert worker error: {e}")
    
    async def send_alert(self, wallet, token, tx_type, sol_amount, token_amount, sig):
        """Queue alert for background sending."""
        try:
            self.alert_queue.put_nowait({
                'wallet': wallet,
                'token': token,
                'tx_type': tx_type,
                'sol_amount': sol_amount,
                'token_amount': token_amount,
                'sig': sig,
                'timestamp': time.time()
            })
        except asyncio.QueueFull:
            logger.error(f"Alert queue full - dropping alert for {sig[:16]}")
```

### Fix 3: RPC Health Tracking

```python
class RPCHandler:
    def __init__(self, urls, max_failures=3, cooldown_seconds=60):
        self.rpcs = [
            {'url': url, 'failures': 0, 'last_success': time.time(), 'cooldown_until': 0}
            for url in urls
        ]
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self._index = 0
    
    def get_rpc(self):
        now = time.time()
        available = [
            r for r in self.rpcs 
            if r['failures'] < self.max_failures or r['cooldown_until'] < now
        ]
        
        if not available:
            # All RPCs failing - reset and pray
            for r in self.rpcs:
                r['failures'] = 0
                r['cooldown_until'] = 0
            available = self.rpcs
        
        # Sort by failure count (ascending), then by last success (descending)
        available.sort(key=lambda r: (r['failures'], -r['last_success']))
        return available[0]['url']
    
    def report_success(self, url):
        for r in self.rpcs:
            if r['url'] == url:
                r['failures'] = 0
                r['last_success'] = time.time()
    
    def report_failure(self, url, is_rate_limit=False):
        for r in self.rpcs:
            if r['url'] == url:
                r['failures'] += 1
                if is_rate_limit or r['failures'] >= self.max_failures:
                    r['cooldown_until'] = time.time() + self.cooldown_seconds
```

---

## CONCLUSION

The current implementation has **transaction loss risk** under high volume due to pagination issues. The round-robin RPC strategy is suboptimal but functional. The main performance bottleneck is **blocking alert sending** during transaction processing.

**Immediate actions:**
1. Fix pagination to prevent transaction loss
2. Implement alert queue to decouple processing from alerting
3. Add RPC health tracking for faster failover

These changes can be implemented within the current budget constraints and will significantly improve reliability and speed.
