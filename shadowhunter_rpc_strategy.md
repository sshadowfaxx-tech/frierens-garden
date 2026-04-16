# ShadowHunter RPC Strategy Analysis & Recommendations

## Executive Summary

With your upgraded Helius plan, you now have **staked connections** available by default. This significantly changes the optimal RPC strategy for ShadowHunter tracker. This document provides specific configuration recommendations to maximize speed while preventing credit exhaustion.

---

## 1. What Are Helius "Staked Connections"?

### Definition
**Staked connections** route your transactions directly to current and upcoming block leaders, bypassing public queues for near-guaranteed delivery during network congestion.

### Key Facts
| Aspect | Details |
|--------|---------|
| **Automatic on Paid Plans** | Yes - All paid plans use staked connections by default on the standard RPC endpoint |
| **Cost** | 1 credit per `sendTransaction` (reduced from 10 credits historically) |
| **No Code Changes Required** | Your existing Helius RPC URL automatically benefits |
| **Performance** | ~140ms average latency, higher transaction landing rates during congestion |

### Benefits vs Regular Connections
| Feature | Regular (Free) | Staked (Paid) |
|---------|----------------|---------------|
| Transaction landing rate | Standard | 80%+ during congestion |
| Queue priority | Public queue | Direct to block leaders |
| Latency | Variable | ~140ms consistent |
| Network congestion handling | May fail/timeout | Near-guaranteed delivery |

### Additional Cost?
- **No extra cost** - Staked connections are included in all paid plans
- Only costs 1 credit per `sendTransaction` call
- All other RPC calls use standard 1 credit pricing

---

## 2. Optimal RPC Strategy for ShadowHunter

### Recommended Approach: **Tiered/Hybrid Strategy**

Use different RPCs for different operation types based on speed requirements and credit costs:

| Operation Type | Recommended RPC | Reason |
|----------------|-----------------|--------|
| **Real-time tracking** (account updates, slot monitoring) | **Helius** | Lowest latency, staked for reliability |
| **Historical data fetching** | **Public RPCs** | Preserve Helius credits for critical ops |
| **Transaction submission** | **Helius** | Staked connections = higher landing rate |
| **Bulk account queries** | **Helius** | Better rate limits, consistent performance |
| **Initial sync / backfill** | **Public RPCs** | High volume, less time-sensitive |

### Why This Hybrid Approach?

1. **Helius is now primary** for time-sensitive operations
2. **Public RPCs as overflow** for high-volume, low-priority operations
3. **Prevents credit exhaustion** while maximizing speed where it matters

---

## 3. Credit Budgeting Recommendations

### Helius Plan Pricing (2025)
| Plan | Monthly Cost | Credits | RPS | Best For |
|------|--------------|---------|-----|----------|
| Free | $0 | 1M | 10 | Development only |
| **Developer** | $49 | 10M | 50 | **Small trackers** |
| **Business** | $499 | 100M | 200 | **Production trackers** |
| Professional | $999 | 200M | 500 | High-volume operations |

### Credit Costs for Common Operations
| RPC Method | Credits | Notes |
|------------|---------|-------|
| Standard RPC calls (`getAccountInfo`, etc.) | 1 | Most common |
| `getProgramAccounts` | 10 | Resource-intensive |
| `getProgramAccountsV2` | 1 | Use paginated version |
| Historical calls (`getBlock`, `getTransaction`) | 10 | Archive data |
| `sendTransaction` (staked) | 1 | Paid plans only |
| DAS API calls | 10 | NFT/token metadata |
| Enhanced Transactions | 100 | Parsed data |
| `getTransactionsForAddress` | 100 | Enhanced history |

### Daily/Hourly Budget Guidelines

**Assuming Business Plan ($499/mo, 100M credits):**

```
Total: 100M credits/month ≈ 3.3M credits/day ≈ 138K credits/hour

Recommended allocation for tracker operations:
- Critical real-time ops (Helius): 70% = 2.3M/day
- Historical/backfill (Public RPCs): 30% = 1M/day
```

**Conservative Budget (prevents exhaustion):**
```python
DAILY_HELIUS_BUDGET = 2_000_000  # 2M credits/day
HOURLY_BUDGET = DAILY_HELIUS_BUDGET // 24  # ~83K/hour
WARNING_THRESHOLD = DAILY_HELIUS_BUDGET * 0.8  # Alert at 80%
```

### Warning Thresholds
| Threshold | Action |
|-----------|--------|
| 50% daily budget used | Log notice |
| 80% daily budget used | **Alert + switch to public RPCs for non-critical ops** |
| 95% daily budget used | **Emergency mode: Helius only for sends** |
| 100% budget exceeded | Fall back to public RPCs entirely |

---

## 4. Specific Configuration Recommendations

### 4.1 Recommended RPC_URLS Ordering

```python
RPC_URLS = {
    # Primary: Helius for time-sensitive operations
    "primary": os.getenv('HELIUS_RPC_URL', ''),
    
    # Secondary: Alchemy as backup premium
    "secondary": os.getenv('ALCHEMY_RPC_URL', ''),
    
    # Fallback: Public RPCs for overflow/low-priority
    "fallback": [
        "https://api.mainnet-beta.solana.com",
        "https://solana-rpc.publicnode.com",
    ]
}
```

### 4.2 Operation-Based Routing

```python
from enum import Enum
from typing import Optional

class OperationType(Enum):
    REAL_TIME_TRACKING = "real_time"      # Use Helius
    TRANSACTION_SEND = "transaction"       # Use Helius (staked)
    HISTORICAL_FETCH = "historical"        # Use Public
    BULK_QUERY = "bulk"                    # Use Helius
    BACKFILL = "backfill"                  # Use Public

class RPCRouter:
    def __init__(self):
        self.helius_url = os.getenv('HELIUS_RPC_URL')
        self.alchemy_url = os.getenv('ALCHEMY_RPC_URL')
        self.public_urls = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-rpc.publicnode.com",
        ]
        self.credit_tracker = CreditTracker(daily_budget=2_000_000)
    
    def get_rpc_for_operation(self, op_type: OperationType) -> str:
        """Route operations to appropriate RPC based on type and credit budget."""
        
        # Always use Helius for transaction sends (staked connections)
        if op_type == OperationType.TRANSACTION_SEND:
            return self.helius_url
        
        # Use Helius for real-time if credits available
        if op_type == OperationType.REAL_TIME_TRACKING:
            if self.credit_tracker.has_budget():
                return self.helius_url
            return self.alchemy_url or self._get_public_rpc()
        
        # Use public RPCs for historical/backfill to save credits
        if op_type in (OperationType.HISTORICAL_FETCH, OperationType.BACKFILL):
            return self._get_public_rpc()
        
        # Default: Helius if budget allows
        if self.credit_tracker.has_budget():
            return self.helius_url
        return self._get_public_rpc()
    
    def _get_public_rpc(self) -> str:
        """Round-robin through public RPCs."""
        # Implement round-robin logic
        pass
```

### 4.3 Credit Monitoring Implementation

```python
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CreditMetrics:
    used_today: int
    daily_budget: int
    last_reset: datetime
    
    @property
    def remaining(self) -> int:
        return self.daily_budget - self.used_today
    
    @property
    def usage_percent(self) -> float:
        return (self.used_today / self.daily_budget) * 100

class CreditTracker:
    """Track Helius credit usage with automatic reset."""
    
    # Credit costs per method
    CREDIT_COSTS = {
        'getAccountInfo': 1,
        'getBalance': 1,
        'getLatestBlockhash': 1,
        'sendTransaction': 1,  # Staked connection
        'getProgramAccounts': 10,
        'getProgramAccountsV2': 1,
        'getBlock': 10,
        'getTransaction': 10,
        'getSignaturesForAddress': 10,
        'getTransactionsForAddress': 100,
        'getAsset': 10,  # DAS API
        'getAssetsByOwner': 10,
    }
    
    def __init__(self, daily_budget: int = 2_000_000):
        self.daily_budget = daily_budget
        self.used_today = 0
        self.last_reset = datetime.now()
        self.warning_threshold = 0.8  # 80%
        self.critical_threshold = 0.95  # 95%
    
    def record_call(self, method: str):
        """Record an RPC call and deduct credits."""
        cost = self.CREDIT_COSTS.get(method, 1)
        self.used_today += cost
        self._check_thresholds()
    
    def _check_thresholds(self):
        """Check budget thresholds and trigger alerts."""
        usage = self.usage_percent
        
        if usage >= self.critical_threshold:
            self._alert_critical()
        elif usage >= self.warning_threshold:
            self._alert_warning()
    
    def _alert_warning(self):
        """Log warning at 80% usage."""
        print(f"⚠️  WARNING: Helius credit usage at {self.usage_percent:.1f}%")
        print(f"   Remaining today: {self.remaining:,} credits")
    
    def _alert_critical(self):
        """Log critical alert at 95% usage."""
        print(f"🚨 CRITICAL: Helius credit usage at {self.usage_percent:.1f}%!")
        print(f"   Switching to fallback RPCs for non-critical operations.")
    
    def has_budget(self, buffer_percent: float = 0.1) -> bool:
        """Check if we have budget remaining (with safety buffer)."""
        effective_budget = self.daily_budget * (1 - buffer_percent)
        return self.used_today < effective_budget
    
    def reset_if_needed(self):
        """Reset counter if it's a new day."""
        now = datetime.now()
        if now.date() != self.last_reset.date():
            self.used_today = 0
            self.last_reset = now
```

### 4.4 Health Tracking Strategy

```python
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class RPCEndpoint:
    url: str
    name: str
    is_premium: bool
    priority: int  # Lower = higher priority
    
    # Health metrics
    last_response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0
    is_healthy: bool = True
    last_check: float = 0.0

class RPCHealthMonitor:
    """Monitor health of all RPC endpoints."""
    
    HEALTH_CHECK_INTERVAL = 30  # seconds
    ERROR_THRESHOLD = 5  # consecutive errors before marking unhealthy
    TIMEOUT_THRESHOLD = 2.0  # seconds
    
    def __init__(self):
        self.endpoints: Dict[str, RPCEndpoint] = {}
        self._setup_endpoints()
    
    def _setup_endpoints(self):
        """Initialize endpoint configurations."""
        self.endpoints['helius'] = RPCEndpoint(
            url=os.getenv('HELIUS_RPC_URL', ''),
            name='Helius',
            is_premium=True,
            priority=1
        )
        self.endpoints['alchemy'] = RPCEndpoint(
            url=os.getenv('ALCHEMY_RPC_URL', ''),
            name='Alchemy',
            is_premium=True,
            priority=2
        )
        self.endpoints['public1'] = RPCEndpoint(
            url='https://api.mainnet-beta.solana.com',
            name='Public (Solana Labs)',
            is_premium=False,
            priority=3
        )
        self.endpoints['public2'] = RPCEndpoint(
            url='https://solana-rpc.publicnode.com',
            name='Public (PublicNode)',
            is_premium=False,
            priority=4
        )
    
    async def health_check(self, endpoint: RPCEndpoint) -> bool:
        """Perform health check on an endpoint."""
        try:
            start = time.time()
            # Simple health check: get latest blockhash
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint.url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getHealth"
                    },
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_THRESHOLD)
                ) as resp:
                    await resp.json()
                    
            endpoint.last_response_time = time.time() - start
            endpoint.success_count += 1
            endpoint.error_count = 0
            endpoint.is_healthy = True
            endpoint.last_check = time.time()
            return True
            
        except Exception as e:
            endpoint.error_count += 1
            endpoint.last_check = time.time()
            
            if endpoint.error_count >= self.ERROR_THRESHOLD:
                endpoint.is_healthy = False
                print(f"❌ {endpoint.name} marked unhealthy after {endpoint.error_count} errors")
            
            return False
    
    def get_best_endpoint(self, require_premium: bool = False) -> Optional[str]:
        """Get the best available endpoint based on health and priority."""
        candidates = [
            ep for ep in self.endpoints.values()
            if ep.is_healthy and (not require_premium or ep.is_premium)
        ]
        
        if not candidates:
            # Fallback: return first endpoint even if unhealthy
            return list(self.endpoints.values())[0].url
        
        # Sort by priority (lower = better) then by response time
        candidates.sort(key=lambda e: (e.priority, e.last_response_time))
        return candidates[0].url
    
    async def run_health_checks(self):
        """Background task to continuously check endpoint health."""
        while True:
            tasks = [
                self.health_check(ep) 
                for ep in self.endpoints.values()
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
```

---

## 5. Complete Implementation Example

```python
"""
Optimized RPC Manager for ShadowHunter Tracker
Maximizes speed using Helius staked connections while preventing credit exhaustion.
"""

import os
import time
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class OperationType(Enum):
    REAL_TIME = "real_time"
    TRANSACTION = "transaction"
    HISTORICAL = "historical"
    BACKFILL = "backfill"

@dataclass
class RPCConfig:
    """Configuration for RPC manager."""
    helius_url: str
    alchemy_url: Optional[str] = None
    daily_credit_budget: int = 2_000_000
    warning_threshold: float = 0.8
    critical_threshold: float = 0.95

class OptimizedRPCManager:
    """
    Smart RPC manager that:
    1. Uses Helius staked connections for critical operations
    2. Falls back to public RPCs for high-volume/low-priority ops
    3. Monitors credit usage to prevent exhaustion
    4. Tracks endpoint health for automatic failover
    """
    
    CREDIT_COSTS = {
        'getAccountInfo': 1,
        'getBalance': 1,
        'getLatestBlockhash': 1,
        'sendTransaction': 1,
        'getProgramAccounts': 10,
        'getBlock': 10,
        'getTransaction': 10,
        'getSignaturesForAddress': 10,
        'getTransactionsForAddress': 100,
        'getAsset': 10,
    }
    
    def __init__(self, config: RPCConfig):
        self.config = config
        self.credits_used_today = 0
        self.last_reset = datetime.now()
        
        # Endpoint health tracking
        self.endpoint_health = {
            'helius': {'healthy': True, 'latency': 0.0, 'errors': 0},
            'alchemy': {'healthy': True, 'latency': 0.0, 'errors': 0},
            'public1': {'healthy': True, 'latency': 0.0, 'errors': 0},
            'public2': {'healthy': True, 'latency': 0.0, 'errors': 0},
        }
        
        self.public_endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-rpc.publicnode.com",
        ]
    
    def _should_use_helius(self, operation: OperationType) -> bool:
        """Determine if operation should use Helius based on type and budget."""
        # Always use Helius for transactions (staked connections critical)
        if operation == OperationType.TRANSACTION:
            return True
        
        # Use Helius for real-time if we have budget
        if operation == OperationType.REAL_TIME:
            return self._has_credit_budget()
        
        # Use public for historical/backfill to save credits
        if operation in (OperationType.HISTORICAL, OperationType.BACKFILL):
            return False
        
        # Default: use Helius if budget allows
        return self._has_credit_budget()
    
    def _has_credit_budget(self, buffer: float = 0.1) -> bool:
        """Check if we have credits remaining."""
        self._reset_if_new_day()
        effective_budget = self.config.daily_credit_budget * (1 - buffer)
        return self.credits_used_today < effective_budget
    
    def _reset_if_new_day(self):
        """Reset credit counter on new day."""
        now = datetime.now()
        if now.date() != self.last_reset.date():
            self.credits_used_today = 0
            self.last_reset = now
    
    def get_rpc_url(self, operation: OperationType = OperationType.REAL_TIME) -> str:
        """Get the optimal RPC URL for the operation type."""
        
        if self._should_use_helius(operation):
            if self.endpoint_health['helius']['healthy']:
                return self.config.helius_url
            # Fallback to Alchemy if Helius unhealthy
            if self.config.alchemy_url and self.endpoint_health['alchemy']['healthy']:
                return self.config.alchemy_url
        
        # Use public RPCs
        healthy_publics = [
            url for url, name in zip(
                self.public_endpoints, 
                ['public1', 'public2']
            )
            if self.endpoint_health[name]['healthy']
        ]
        
        if healthy_publics:
            # Simple round-robin
            return healthy_publics[int(time.time()) % len(healthy_publics)]
        
        # Last resort: return any
        return self.public_endpoints[0]
    
    async def call(self, method: str, params: List[Any] = None, 
                   operation: OperationType = OperationType.REAL_TIME) -> Dict[str, Any]:
        """Make an RPC call with automatic routing and credit tracking."""
        
        url = self.get_rpc_url(operation)
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=30) as resp:
                    result = await resp.json()
                    
            # Track credit usage if using Helius
            if 'helius' in url:
                cost = self.CREDIT_COSTS.get(method, 1)
                self.credits_used_today += cost
                self._check_budget_alerts()
            
            # Update health metrics
            latency = time.time() - start_time
            self._update_health(url, latency, success=True)
            
            return result
            
        except Exception as e:
            self._update_health(url, 0, success=False)
            raise
    
    def _check_budget_alerts(self):
        """Check credit budget and emit alerts."""
        usage = self.credits_used_today / self.config.daily_credit_budget
        
        if usage >= self.config.critical_threshold:
            print(f"🚨 CRITICAL: {usage*100:.1f}% of daily Helius credits used!")
        elif usage >= self.config.warning_threshold:
            print(f"⚠️  WARNING: {usage*100:.1f}% of daily Helius credits used")
    
    def _update_health(self, url: str, latency: float, success: bool):
        """Update endpoint health metrics."""
        # Map URL to endpoint name
        name = 'helius' if 'helius' in url else \
               'alchemy' if url == self.config.alchemy_url else \
               'public1' if 'mainnet-beta' in url else 'public2'
        
        if success:
            self.endpoint_health[name]['latency'] = latency
            self.endpoint_health[name]['errors'] = 0
            self.endpoint_health[name]['healthy'] = True
        else:
            self.endpoint_health[name]['errors'] += 1
            if self.endpoint_health[name]['errors'] > 5:
                self.endpoint_health[name]['healthy'] = False


# Usage Example
if __name__ == "__main__":
    config = RPCConfig(
        helius_url=os.getenv('HELIUS_RPC_URL'),
        alchemy_url=os.getenv('ALCHEMY_RPC_URL'),
        daily_credit_budget=2_000_000
    )
    
    rpc = OptimizedRPCManager(config)
    
    # Real-time tracking - uses Helius (staked, fast)
    # asyncio.run(rpc.call('getAccountInfo', [pubkey], OperationType.REAL_TIME))
    
    # Historical backfill - uses public RPCs (saves credits)
    # asyncio.run(rpc.call('getBlock', [slot], OperationType.HISTORICAL))
    
    # Transaction send - ALWAYS uses Helius (staked connections)
    # asyncio.run(rpc.call('sendTransaction', [tx], OperationType.TRANSACTION))
```

---

## 6. Summary Checklist

### Immediate Actions
- [ ] **Update RPC_URLS** to prioritize Helius for time-sensitive operations
- [ ] **Implement credit tracking** with daily budget and warning thresholds
- [ ] **Add operation-based routing** (real-time vs historical vs transaction)
- [ ] **Deploy health monitoring** for automatic failover

### Configuration Changes
- [ ] Set `DAILY_HELIUS_BUDGET` based on your plan (recommend 2M for Business)
- [ ] Set `WARNING_THRESHOLD` to 80%
- [ ] Set `CRITICAL_THRESHOLD` to 95%
- [ ] Configure `HELIUS_RPC_URL` with your mainnet endpoint

### Monitoring Setup
- [ ] Log credit usage per hour
- [ ] Alert at 80% daily usage
- [ ] Auto-switch to public RPCs at 95% usage
- [ ] Track endpoint health (latency, errors)
- [ ] Monitor transaction landing rates

### Best Practices
1. **Always use Helius for `sendTransaction`** - Staked connections are critical
2. **Use `getProgramAccountsV2`** instead of `getProgramAccounts` (1 vs 10 credits)
3. **Batch historical requests** and route to public RPCs
4. **Cache aggressively** to reduce repeat calls
5. **Monitor credit usage** and adjust budget monthly based on actual usage

---

## 7. Expected Performance Improvements

With this optimized strategy:

| Metric | Before (Round-Robin) | After (Optimized) |
|--------|---------------------|-------------------|
| Transaction landing rate | ~60-70% (congestion) | **80%+** (staked) |
| Avg latency | Variable (200-500ms) | **~140ms** |
| Credit exhaustion risk | High | **Managed** |
| Failover capability | None | **Automatic** |
| Cost predictability | Low | **High** |

---

*Document generated for ShadowHunter tracker RPC optimization*
*Helius paid plan with staked connections - March 2025*
