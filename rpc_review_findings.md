# ShadowHunter RPC Management System - Code Review

**Date:** 2026-03-28  
**File:** `trackerv2_clean.py`  
**Reviewer:** RPC Infrastructure Engineer

---

## EXECUTIVE SUMMARY

**CRITICAL BUGS FOUND:** 2  
**MODERATE ISSUES:** 4  
**RECOMMENDATIONS:** 5

The RPC management system has **critical flaws** in its rotation logic that cause:
1. Uneven load distribution across public RPCs
2. Premature fallback to Helius (paid RPC)
3. Potential transaction detection gaps due to RPC exhaustion

---

## CRITICAL BUGS

### 🔴 BUG #1: Broken Round-Robin Logic in `get_rpc()` (Line ~1173)

**Problem:**
```python
def get_rpc(self, force_public: bool = False) -> str:
    now = time.time()
    
    for i in range(len(self.public_rpcs)):
        idx = (self.rpc_index + i) % len(self.public_rpcs)  # Start from current index
        rpc = self.public_rpcs[idx]
        if rpc not in self.rate_limited_until or now > self.rate_limited_until[rpc]:
            self.rpc_index = idx + 1  # BUG: Sets index to found position + 1
            return rpc
```

**Impact:** 
- **Uneven distribution**: RPCs at the start of the list get disproportionately more traffic
- When `rpc_index=5` and all RPCs fail, next successful call sets `rpc_index = 0+1 = 1`, skipping index 0 forever after failures
- This breaks proper round-robin cycling

**Fix:**
```python
def get_rpc(self, force_public: bool = False) -> str:
    now = time.time()
    
    for i in range(len(self.public_rpcs)):
        idx = (self.rpc_index + i) % len(self.public_rpcs)
        rpc = self.public_rpcs[idx]
        if rpc not in self.rate_limited_until or now > self.rate_limited_until[rpc]:
            self.rpc_index = (idx + 1) % len(self.public_rpcs)  # Proper wrap-around
            self.current_rpc = rpc
            self.public_usage_count += 1
            return rpc
    # ... fallback logic
```

---

### 🔴 BUG #2: Duplicate `get_rpc()` Methods

**Problem:**
There are **TWO** `get_rpc()` implementations:

1. **`Config` class** (lines 32-37) - Simple round-robin on `Config.RPC_URLS`:
```python
def get_rpc(self) -> str:
    url = self.rpc_urls[self.rpc_index % len(self.rpc_urls)]
    self.rpc_index += 1
    return url
```

2. **`SpeedTracker` class** (lines 1173-1206) - Complex routing with rate limiting

**Impact:**
- Code confusion and maintenance overhead
- `Config.RPC_URLS` is defined but never actually used for RPC routing
- `Config.get_rpc()` exists but is never called (wasted code)

**Fix:** Remove `Config.RPC_URLS` and `Config.get_rpc()` - they're shadowed by `SpeedTracker` implementation.

---

## MODERATE ISSUES

### 🟡 ISSUE #3: Retry Loop Doesn't Guarantee Different RPC

**Location:** `check_wallet_fast()` (line ~1980)

```python
max_retries = min(3, len(self.public_rpcs) + 1)
for attempt in range(max_retries):
    rpc_url = self.get_rpc()  # May return same RPC if only 1 is healthy
```

**Problem:** If only 1-2 public RPCs are healthy, the retry loop may try the same RPC multiple times, defeating the purpose.

**Fix:** Track attempted RPCs per retry cycle:
```python
attempted_rpcs = set()
for attempt in range(max_retries):
    rpc_url = self.get_rpc(exclude=attempted_rpcs)
    if not rpc_url:
        break
    attempted_rpcs.add(rpc_url)
    # ... rest of retry logic
```

---

### 🟡 ISSUE #4: Non-429 Errors Don't Trigger RPC Failure Reporting

**Location:** `check_wallet_fast()` retry handling

**Problem:** Only HTTP 429 (rate limit) calls `report_rpc_failure()`:
```python
if resp.status != 200:
    if resp.status == 429:
        self.report_rpc_failure(rpc_url, 'rate_limit')
    continue  # Other errors don't mark RPC as failed
```

**Impact:** 
- Timeout errors, 500/503 errors, connection failures don't mark RPC as unhealthy
- The same failing RPC gets retried immediately in the next wallet check
- Wastes retry attempts on known-bad endpoints

**Fix:** Report failures for all error conditions:
```python
if resp.status != 200:
    if resp.status == 429:
        self.report_rpc_failure(rpc_url, 'rate_limit')
    elif resp.status >= 500:
        self.report_rpc_failure(rpc_url, 'server_error')
    continue
```

---

### 🟡 ISSUE #5: RPC Exhaustion Within Single Wallet Check Cycle

**Current math:**
- 6 public RPCs
- 3 retries max per wallet
- 51+ wallets checking concurrently
- 10-minute cooldown on rate limit

**Problem:** With 51 wallets and only 3 retries, a rate-limited RPC can burn through all 6 public RPCs in just 2 wallet checks, then immediately fall back to Helius.

**Impact:** Excessive Helius usage, wasted paid credits.

---

### 🟡 ISSUE #6: No Per-RPC Success Rate Tracking

**Current state:** Only tracks `rate_limited_until` timestamps.

**Missing metrics:**
- Success/failure rate per RPC
- Average response time per RPC
- Error type distribution
- Time-to-recovery after rate limit

**Impact:** No data to optimize RPC selection or cooldown timing.

---

## RECOMMENDATIONS

### 1. Implement Proper RPC Health Scoring

Replace simple cooldown with health score-based routing:

```python
class RPCHealth:
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.last_used = 0
        self.cooldown_until = 0
    
    @property
    def health_score(self) -> float:
        total = self.success_count + self.failure_count
        if total < 5:  # Not enough data
            return 0.5
        return self.success_count / total
    
    def record_success(self):
        self.success_count += 1
        # Gradually reduce failure count on success (forgiveness)
        self.failure_count = max(0, self.failure_count - 0.5)
    
    def record_failure(self, error_type: str):
        self.failure_count += 1
        if error_type == 'rate_limit':
            self.cooldown_until = time.time() + 600  # 10 min
        elif error_type == 'timeout':
            self.cooldown_until = time.time() + 60   # 1 min
        else:
            self.cooldown_until = time.time() + 30   # 30 sec
```

### 2. Implement Weighted RPC Selection

Instead of simple round-robin, use health-weighted selection:

```python
def get_rpc(self) -> str:
    now = time.time()
    available = []
    
    for rpc, health in self.rpc_health.items():
        if now > health.cooldown_until:
            # Weight = health_score * recency_factor
            weight = health.health_score * (1 / (1 + now - health.last_used))
            available.append((rpc, weight))
    
    if not available:
        return self.helius_rpc  # All unhealthy, use Helius
    
    # Weighted random selection
    total_weight = sum(w for _, w in available)
    pick = random.uniform(0, total_weight)
    current = 0
    for rpc, weight in available:
        current += weight
        if pick <= current:
            self.rpc_health[rpc].last_used = now
            return rpc
    
    return available[-1][0]
```

### 3. Increase Retry Count & Add Exponential Backoff

```python
async def check_wallet_fast(self, wallet_dict: Dict[str, str]) -> int:
    wallet = wallet_dict['address']
    max_retries = min(len(self.public_rpcs), 6)  # Try all public RPCs
    attempted = set()
    
    for attempt in range(max_retries):
        rpc_url = self.get_rpc(exclude=attempted)
        if not rpc_url:
            break
        attempted.add(rpc_url)
        
        try:
            # ... RPC call ...
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            self.report_rpc_failure(rpc_url, type(e).__name__)
            # Exponential backoff between retries
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))
            continue
```

### 4. Adjust Cooldown Strategy

Current: Fixed 10-minute cooldown for rate limits

Recommended: Adaptive cooldown based on failure frequency:

| Failure Count | Cooldown |
|--------------|----------|
| 1st rate limit | 2 minutes |
| 2nd consecutive | 5 minutes |
| 3rd+ consecutive | 15 minutes |
| Recovery after success | Reset to 2 min |

### 5. Add RPC Usage Metrics Dashboard

Track and periodically log:

```python
def log_rpc_metrics(self):
    total_calls = sum(h.success_count + h.failure_count for h in self.rpc_health.values())
    if total_calls == 0:
        return
    
    logger.info("=== RPC Metrics ===")
    for rpc, health in self.rpc_health.items():
        total = health.success_count + health.failure_count
        if total > 0:
            success_rate = health.success_count / total * 100
            logger.info(f"  {rpc[:30]}...: {success_rate:.1f}% success ({health.success_count}/{total})")
    
    helius_pct = self.helius_usage_count / (self.helius_usage_count + self.public_usage_count) * 100
    logger.info(f"  Helius usage: {helius_pct:.1f}% ({self.helius_usage_count} calls)")
```

---

## VERIFICATION OF REQUIREMENTS

| Requirement | Status | Notes |
|------------|--------|-------|
| Cycle through ALL public RPCs before Helius | ❌ FAIL | Broken round-robin, may skip RPCs |
| Retry with different RPC on failure | ⚠️ PARTIAL | Retries don't guarantee different RPC |
| Retry logic in `check_wallet_fast()` | ⚠️ PARTIAL | Works but suboptimal |
| Efficient use of 6 public RPCs | ❌ FAIL | Uneven distribution, premature Helius fallback |

---

## PRIORITY ACTIONS

1. **IMMEDIATE (Fix Today):**
   - Fix round-robin bug (BUG #1)
   - Remove duplicate `get_rpc()` (BUG #2)
   - Report all failures, not just 429 (ISSUE #4)

2. **SHORT TERM (This Week):**
   - Implement per-RPC health tracking
   - Add RPC exclusion in retry loop (ISSUE #3)
   - Increase retry count to try all 6 RPCs

3. **MEDIUM TERM (This Month):**
   - Implement weighted RPC selection
   - Add adaptive cooldown strategy
   - Build RPC metrics dashboard

---

## CONCLUSION

The current RPC management system is **functional but inefficient**. The critical bugs cause uneven load distribution and premature Helius usage. With 51 wallets being tracked, the system is likely hitting Helius more than necessary, increasing costs.

**Estimated Impact:**
- Current: ~30-40% Helius fallback rate (estimated)
- After fixes: ~5-10% Helius fallback rate (projected)
- Cost savings: 60-75% reduction in paid RPC usage

The fixes are straightforward and can be implemented without disrupting the main transaction detection logic.
