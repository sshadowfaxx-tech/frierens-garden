# ShadowHunter Modular Architecture Proposal

## Executive Summary

This document proposes a module structure for ShadowHunter that separates concerns into Infrastructure, Domain Logic, and Application layers while maintaining backward compatibility and supporting future autonomous trading extensions.

---

## Core Design Decisions

### 1. Dependency Management: Simple Imports + Factory Pattern

**Decision:** Use simple imports with a lightweight factory pattern, NOT full DI framework.

**Rationale:**
- Solo developer context - no need for complex DI containers
- Python's import system is sufficient
- Factory pattern gives us testability without overhead
- Easy to understand and debug

```python
# Instead of:
@inject
class Tracker:
    def __init__(self, rpc: RPCClient, db: DBPool): ...

# We use:
class Tracker:
    def __init__(self, rpc: RPCClient, db: DBPool): ...

# Created via factory:
def create_tracker():
    config = load_config()
    rpc = RPCClient(config.rpc_urls)
    db = create_db_pool(config.db)
    return Tracker(rpc=rpc, db=db)
```

### 2. Shared State: Repository Pattern + Event Bus

**Decision:** Use Repository pattern for persistence state, EventBus for ephemeral state.

**Repositories** (for DB-backed state):
- `WalletPositionRepository` - positions, trades
- `WalletPerformanceRepository` - performance metrics
- `TokenInfoRepository` - cached token metadata

**EventBus** (for in-memory coordination):
- Wallet activity events
- New transaction events  
- Alert trigger events

```python
# Event-driven state updates
class WalletPositionRepository:
    def __init__(self, db_pool, event_bus):
        self.db = db_pool
        event_bus.subscribe('trade_executed', self._on_trade)
    
    async def _on_trade(self, event: TradeEvent):
        await self.update_position(event.wallet, event.token, ...)
```

### 3. Module Granularity: 9 Modules (The "Goldilocks" Number)

Not too few (5 = tight coupling), not too many (20 = cognitive overload).

---

## Proposed Directory Structure

```
shadowhunter/
├── __init__.py
├── __main__.py              # Entry point: python -m shadowhunter
│
├── config/                  # INFRASTRUCTURE - Configuration
│   ├── __init__.py
│   ├── settings.py          # Pydantic-based config with env var binding
│   └── logging_config.py    # Structured logging setup
│
├── infrastructure/          # INFRASTRUCTURE - External services
│   ├── __init__.py
│   ├── rpc/                 # RPC management
│   │   ├── __init__.py
│   │   ├── client.py        # RPCClient with retry, failover
│   │   ├── routing.py       # Public vs Helius routing logic
│   │   └── rate_limiter.py  # Rate limiting per endpoint
│   ├── db/                  # Database
│   │   ├── __init__.py
│   │   ├── pool.py          # Connection pool management
│   │   ├── retries.py       # with_db_retry decorator
│   │   └── migrations/      # Schema migrations
│   ├── cache/               # Redis/cache layer
│   │   ├── __init__.py
│   │   ├── client.py        # Redis client wrapper
│   │   └── keys.py          # Cache key naming conventions
│   └── messaging/           # Telegram bot
│       ├── __init__.py
│       ├── bot.py           # Bot initialization
│       └── formatters.py    # Message formatting utilities
│
├── domain/                  # DOMAIN LOGIC - Core business rules
│   ├── __init__.py
│   ├── models/              # Domain models (dataclasses)
│   │   ├── __init__.py
│   │   ├── wallet.py        # Wallet, WalletPosition
│   │   ├── token.py         # TokenInfo
│   │   ├── trade.py         # Trade, TradeType
│   │   └── performance.py   # PerformanceMetrics
│   ├── parsers/             # Transaction parsing
│   │   ├── __init__.py
│   │   ├── base.py          # Parser interface
│   │   ├── swap_detector.py # Buy/sell detection
│   │   └── transfer_detector.py  # Wallet-to-wallet transfer detection
│   └── repositories/        # Data access abstraction
│       ├── __init__.py
│       ├── wallet_positions.py
│       ├── wallet_performance.py
│       └── token_info.py
│
├── services/                # DOMAIN SERVICES - Orchestration
│   ├── __init__.py
│   ├── wallet_tracker.py    # Core tracking logic (was check_wallet_fast)
│   ├── cluster_detector.py  # Cluster detection & alerts
│   ├── performance_tracker.py  # Performance calculation
│   └── market_data.py       # Token info from DexScreener
│
├── application/             # APPLICATION LAYER - Use cases
│   ├── __init__.py
│   ├── tracker.py           # Main SpeedTracker orchestration
│   ├── alert_manager.py     # Alert dispatching
│   └── commands/            # Telegram bot commands
│       ├── __init__.py
│       ├── base.py          # Command interface
│       ├── performance.py   # /performance, /recent
│       ├── analysis.py      # /analyze, /trackhold, /suggest
│       ├── admin.py         # /add, /remove
│       └── status.py        # /status, /start
│
└── trading/                 # FUTURE: Autonomous trading extension
    ├── __init__.py
    ├── signals.py           # Trading signal generation
    ├── risk_manager.py      # Position sizing, stop-loss
    ├── executor.py          # Trade execution
    └── strategies/          # Strategy implementations
        ├── __init__.py
        └── base.py
```

---

## Module Responsibilities

### 1. `config/settings.py`
```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """All configuration in one place with env var binding."""
    
    # RPC
    helius_rpc_url: str | None = None
    alchemy_api_key: str | None = None
    rpc_timeout: int = 5
    
    # DB
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "shadowhunter"
    db_user: str = "sh"
    db_password: str = "sh123"
    db_max_retries: int = 5
    
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    channel_pings: str | None = None
    channel_vip: str | None = None
    channel_transfers: str | None = None
    
    # Tracking
    check_interval: int = 5
    min_sol_threshold: float = 0.02
    cluster_threshold: int = 2
    
    class Config:
        env_file = ".env"
        env_prefix = ""  # Keep existing env var names
```

### 2. `infrastructure/rpc/client.py`
```python
class RPCClient:
    """Unified RPC client with failover and rate limiting."""
    
    def __init__(self, urls: list[str], helius_url: str | None = None):
        self.router = RPCRouter(urls, helius_url)
        self.rate_limiter = RateLimiter()
        self.session: aiohttp.ClientSession | None = None
    
    async def get_signatures(self, wallet: str, limit: int = 20) -> list[dict]:
        """Get signatures with automatic retry on different endpoints."""
        
    async def get_transaction(self, signature: str) -> dict | None:
        """Get transaction with session affinity."""
        
    async def get_token_supply(self, token: str) -> float | None:
        """Get token supply via Alchemy or public RPC."""
```

### 3. `domain/parsers/swap_detector.py`
```python
class SwapDetector:
    """Detects buy/sell transactions."""
    
    DEX_PROGRAMS = {...}  # Moved from SpeedTracker
    
    def detect(self, tx: dict, wallet: str) -> list[Trade]:
        """
        Returns list of trades (buys/sells) in the transaction.
        Empty list if no trades detected.
        """
        
    def _is_dex_program(self, program_id: str) -> bool:
        """Check if program is a known DEX."""
```

### 4. `domain/parsers/transfer_detector.py`
```python
class TransferDetector:
    """Detects wallet-to-wallet transfers (not DEX swaps)."""
    
    def detect(self, tx: dict, wallet: str) -> list[Transfer]:
        """
        Returns list of transfers (SOL or token).
        Empty list if this is a DEX swap.
        """
```

### 5. `domain/repositories/wallet_positions.py`
```python
class WalletPositionRepository:
    """Repository for wallet position data."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def update_position(
        self, 
        wallet: str, 
        token: str, 
        trade_type: TradeType,
        token_amount: float,
        sol_amount: float,
        market_cap: float = 0
    ) -> None:
        """Update position after a trade."""
        
    async def get_positions(self, wallet: str) -> list[WalletPosition]:
        """Get all positions for a wallet."""
        
    async def get_cluster_positions(self, token: str) -> list[WalletPosition]:
        """Get positions for cluster detection."""
```

### 6. `services/cluster_detector.py`
```python
class ClusterDetector:
    """Detects wallet clusters and sends cluster alerts."""
    
    def __init__(
        self,
        position_repo: WalletPositionRepository,
        token_repo: TokenInfoRepository,
        alert_manager: AlertManager,
        performance_tracker: PerformanceTracker,
        cache: CacheClient
    ):
        ...
    
    async def check_cluster(
        self, 
        token: str, 
        new_wallet: str, 
        tx_type: TradeType
    ) -> bool:
        """Check if cluster alert should fire."""
        
    async def send_cluster_alert(
        self, 
        token: str, 
        positions: list[WalletPosition]
    ) -> None:
        """Send the actual cluster alert."""
```

### 7. `application/tracker.py`
```python
class ShadowHunterTracker:
    """Main orchestration class (refactored SpeedTracker)."""
    
    def __init__(
        self,
        config: Settings,
        rpc: RPCClient,
        wallet_repo: WalletRepository,
        position_repo: WalletPositionRepository,
        wallet_tracker: WalletTrackerService,
        cluster_detector: ClusterDetector,
        alert_manager: AlertManager,
        event_bus: EventBus
    ):
        self.config = config
        self.rpc = rpc
        self.wallet_repo = wallet_repo
        self.position_repo = position_repo
        self.wallet_tracker = wallet_tracker
        self.cluster_detector = cluster_detector
        self.alert_manager = alert_manager
        self.event_bus = event_bus
        
        self._shutdown_event = asyncio.Event()
    
    async def run(self) -> None:
        """Main tracking loop with adaptive intervals."""
        
    async def check_wallet(self, wallet: Wallet) -> int:
        """Check a single wallet for new transactions."""
```

### 8. `application/commands/performance.py`
```python
class PerformanceCommandHandler:
    """Handles /performance command."""
    
    def __init__(
        self,
        performance_tracker: PerformanceTracker,
        wallet_repo: WalletRepository
    ):
        ...
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Main command handler."""
        
    async def show_leaderboard(self, update: Update, page: int = 0) -> None:
        """Show paginated performance leaderboard."""
        
    async def show_wallet_detail(self, update: Update, wallet: str) -> None:
        """Show detailed performance for a single wallet."""
```

### 9. `trading/signals.py` (Future Extension)
```python
class SignalGenerator:
    """Generate trading signals from cluster data."""
    
    def __init__(
        self,
        cluster_detector: ClusterDetector,
        performance_tracker: PerformanceTracker
    ):
        ...
    
    async def evaluate_opportunity(self, token: str) -> Signal | None:
        """Evaluate if a token presents a trading opportunity."""
```

---

## Interface Definitions

### EventBus Interface
```python
from typing import Callable, Awaitable

THandler = Callable[[Event], Awaitable[None]]

class EventBus:
    """Simple async event bus for decoupled communication."""
    
    def subscribe(self, event_type: str, handler: THandler) -> None:
        """Subscribe to an event type."""
        
    def unsubscribe(self, event_type: str, handler: THandler) -> None:
        """Unsubscribe from an event type."""
        
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
```

### Repository Interface
```python
from typing import Protocol

class WalletPositionRepository(Protocol):
    """Interface for wallet position storage."""
    
    async def update_position(self, wallet: str, token: str, ...) -> None: ...
    async def get_positions(self, wallet: str) -> list[WalletPosition]: ...
    async def get_cluster_positions(self, token: str) -> list[WalletPosition]: ...
```

### AlertManager Interface
```python
class AlertManager:
    """Centralized alert dispatch."""
    
    async def send_trade_alert(self, alert: TradeAlert) -> None:
        """Send buy/sell alert."""
        
    async def send_cluster_alert(self, alert: ClusterAlert) -> None:
        """Send cluster alert."""
        
    async def send_transfer_alert(self, alert: TransferAlert) -> None:
        """Send wallet-to-wallet transfer alert."""
```

---

## Migration Strategy

### Phase 1: Preparation (No code changes)
1. Create new directory structure alongside existing file
2. Set up `__init__.py` files with exports
3. Create `shadowhunter/__main__.py` entry point

### Phase 2: Extract Infrastructure (Week 1)
```
Steps:
1. Create infrastructure/rpc/ - copy RPC logic from SpeedTracker
2. Create infrastructure/db/ - copy DB logic
3. Create infrastructure/cache/ - copy Redis logic
4. Create config/settings.py - consolidate all Config class values
5. Test each module independently with unit tests
```

### Phase 3: Extract Domain Logic (Week 2)
```
Steps:
1. Create domain/models/ - define dataclasses for Wallet, Trade, Token
2. Create domain/parsers/ - extract _detect_transfers, _is_dex_program
3. Create domain/repositories/ - extract DB queries from classes
4. Verify parsers work identically to original
```

### Phase 4: Extract Services (Week 3)
```
Steps:
1. Create services/wallet_tracker.py - move check_wallet_fast logic
2. Create services/cluster_detector.py - move ClusterDetector class
3. Create services/performance_tracker.py - move WalletPerformance class
4. Create services/market_data.py - move get_token_info logic
```

### Phase 5: Application Layer (Week 4)
```
Steps:
1. Create application/tracker.py - new orchestrator using extracted modules
2. Create application/commands/ - move all command handlers
3. Create application/alert_manager.py - consolidate alert logic
4. Create factory.py - wire everything together
```

### Phase 6: Cutover (Week 5)
```
Steps:
1. Keep trackerv2_clean.py as backup
2. Create shadowhunter/main.py that uses new structure
3. Run both in parallel (compare outputs)
4. Switch entry point when confident
5. Keep old file for 2 weeks, then delete
```

### Backward Compatibility During Transition

```python
# shadowhunter/compat.py
"""Compatibility layer during migration."""

from trackerv2_clean import SpeedTracker, Config
from .infrastructure.rpc import RPCClient
from .infrastructure.db import create_pool

class CompatTracker:
    """Wraps old tracker to provide new interface."""
    
    def __init__(self):
        self._old_tracker = SpeedTracker()
    
    async def run(self):
        # Can gradually replace components
        await self._old_tracker.run()
```

---

## Key Benefits

### 1. Easier to Change One Piece
- Change RPC provider? Only touch `infrastructure/rpc/`
- Change alert format? Only touch `application/alert_manager.py`
- Add new command? Create file in `application/commands/`

### 2. Testability
```python
# Can mock RPC for tests
@pytest.fixture
def rpc_client():
    return MockRPCClient([
        {"signature": "abc123", ...},
    ])

async def test_swap_detection(rpc_client):
    tracker = WalletTrackerService(rpc=rpc_client, ...)
    trades = await tracker.check_wallet(wallet)
    assert len(trades) == 1
    assert trades[0].type == TradeType.BUY
```

### 3. Future Trading Extension
```python
# In application/tracker.py, add:
if self.config.trading_enabled:
    await self.trading_executor.evaluate_signals()

# trading/ module is already structured and ready
```

### 4. No Business Logic Rewrite
- All SQL queries moved as-is to repositories
- All parsing logic moved as-is to parsers
- All alert formatting moved as-is to formatters
- Only structural changes, no algorithm changes

---

## Estimated Effort

| Phase | Duration | Risk |
|-------|----------|------|
| Preparation | 1 day | Low |
| Infrastructure | 3 days | Low |
| Domain Logic | 3 days | Medium |
| Services | 3 days | Medium |
| Application | 3 days | Low |
| Cutover | 2 days | Low |
| **Total** | **~2.5 weeks** | Manageable |

---

## Success Criteria

1. ✅ All existing functionality preserved
2. ✅ Can run unit tests on individual modules
3. ✅ Can swap RPC implementation without touching domain logic
4. ✅ Can add new Telegram command without touching tracker logic
5. ✅ Clear path to add trading module
6. ✅ Old code can be deleted (no lingering dependencies)
