# ShadowHunter - Component Architecture Map

**Source File:** `trackerv2_clean.py`  
**Purpose:** Solana wallet tracker with live cluster updates, performance tracking, and Telegram alerts

---

## 1. CLASSES AND RESPONSIBILITIES

### 1.1 Config
**Responsibilities:**
- Central configuration management via environment variables
- Defines all system constants (thresholds, intervals, timeouts)
- Configures RPC endpoints (Helius, Alchemy, public RPCs)
- Database and Redis connection parameters
- Alert channel configuration

**Dependencies:** None (standalone config class)

**State:** None (static class attributes only)

---

### 1.2 ClusterDetector
**Responsibilities:**
- Detects when multiple wallets trade the same token (cluster formation)
- Updates wallet positions in database (buy/sell tracking)
- Sends VIP cluster alerts to configured channel
- Fetches token info from DexScreener API
- Implements throttling to prevent duplicate alerts (5s cooldown per token)

**Dependencies:**
- `asyncpg.Pool` - Database connection
- `redis.Redis` - Cache for throttling and token info
- `telegram.Bot` - For sending alerts
- `WalletPerformance` - For fetching wallet confidence scores

**State Maintained:**
- None directly (uses external db/cache/bot)

**Key Relationships:**
- Called by `SpeedTracker` when processing transactions
- Uses `get_token_info()` which caches in Redis

---

### 1.3 WalletPerformance
**Responsibilities:**
- Tracks wallet trading performance metrics (PnL, winrate, ROI)
- Records trades and calculates realized/unrealized PnL
- Calculates confidence scores for wallets (0-100 scale)
- Provides leaderboard and individual wallet analytics
- Calculates average hold times for positions

**Dependencies:**
- `asyncpg.Pool` - Database for performance data
- `with_db_retry()` - Retry utility function

**State Maintained:**
- None directly (all state in database)

**Key Relationships:**
- Called by `SpeedTracker` after each trade
- Used by `ClusterDetector` for confidence emojis in alerts
- Provides data for Telegram `/performance` commands

---

### 1.4 SpeedTracker (Main Application Class)
**Responsibilities:**
- Main event loop for wallet monitoring
- RPC connection management with failover and rate limiting
- Transaction fetching and parsing
- Buy/sell detection from transaction data
- Transfer detection (wallet-to-wallet, non-DEX)
- Orchestrates alerts, cluster detection, and performance tracking
- Wallet management (add/remove from file)
- HTTP session lifecycle management

**Dependencies:**
- `asyncpg.Pool` - Database
- `redis.Redis` - Transaction cache
- `telegram.Bot` - Alerts
- `aiohttp.ClientSession` - RPC and API calls
- `ClusterDetector` - Cluster alerts
- `WalletPerformance` - Performance tracking

**State Maintained:**
```python
self.wallets: List[Dict[str, str]]           # Tracked wallets (address, label)
self._wallet_labels: Dict[str, str]          # Quick lookup mapping
self.rpc_index: int                          # Round-robin RPC selector
self._shutdown_event: asyncio.Event          # Graceful shutdown
self.db_semaphore: asyncio.Semaphore(10)     # DB concurrency limit
self.wallet_check_semaphore: asyncio.Semaphore(20)  # Wallet check concurrency
self.rpc_semaphore: asyncio.Semaphore(20)    # RPC call concurrency
self.script_start_time: int                  # Unix timestamp (5 min lookback)
self.rate_limited_until: Dict[str, float]    # RPC cooldown tracking
self.current_rpc: Optional[str]              # Currently used RPC
self.helius_usage_count: int                 # Helius fallback counter
self.public_usage_count: int                 # Public RPC counter
self.wallet_check_interval: Dict[str, int]   # Adaptive intervals per wallet
self.wallet_last_activity: Dict[str, float]  # Last tx timestamp per wallet
self._wallet_last_check: Dict[str, float]    # Last check timestamp per wallet
self.public_rpcs: List[str]                  # Public RPC endpoints
self.helius_rpc: str                         # Helius RPC endpoint
self.exchange_wallets: set                   # Exchange addresses to filter
self.lp_programs: set                        # LP program addresses to filter
```

**Key Relationships:**
- Initializes and owns `ClusterDetector` and `WalletPerformance`
- Contains all Telegram command handlers (via functions passed to bot)
- Reads/writes `wallets.txt`, `exchanges.txt`, `lpools.txt`

---

## 2. METHODS GROUPED BY FUNCTIONALITY

### 2.1 RPC Handling Methods (SpeedTracker)

| Method | Purpose |
|--------|---------|
| `_setup_rpc_routing()` | Initialize RPC endpoint lists and health tracking |
| `get_rpc(force_public=False)` | Get next available RPC URL with failover logic |
| `_get_rpc_excluding(excluded_rpcs)` | Get RPC excluding already-tried endpoints |
| `report_rpc_failure(rpc, error_type)` | Mark RPC as failed with cooldown period |
| `get_adaptive_interval(wallet)` | Calculate check interval based on wallet activity |
| `get_token_supply(token)` | Get token supply via RPC |
| `get_token_supply_alchemy(token)` | Get supply via Alchemy API with decimals |
| `_get_token_supply_public(token)` | Fallback supply fetch via public RPC |
| `get_token_balance(wallet, token)` | Get token balance for wallet (with retries) |
| `get_token_balance_alchemy(wallet, token)` | Get balance via Alchemy API |

**RPC Failover Strategy:**
- Primary: Public RPCs (free tier)
- Fallback: Helius (paid, credits preserved)
- Error-based cooldowns: rate_limit (10min), timeout (2min), server_error (1min), connection_error (30s)

---

### 2.2 Database Methods

| Method | Class | Purpose |
|--------|-------|---------|
| `with_db_retry(func, *args, **kwargs)` | Global | Execute DB function with exponential backoff |
| `_execute_update_position(...)` | ClusterDetector | Raw SQL for position upsert |
| `update_position(...)` | ClusterDetector | Update position with retry wrapper |
| `_execute_check_cluster(token)` | ClusterDetector | Raw SQL for cluster fetch |
| `check_cluster(...)` | ClusterDetector | Check cluster with retry wrapper |
| `_execute_buy_record(...)` | WalletPerformance | Raw SQL for buy recording |
| `_execute_sell_record(...)` | WalletPerformance | Raw SQL for sell with PnL calc |
| `record_trade(...)` | WalletPerformance | Record trade with retry wrapper |
| `_fetch_performance(wallet)` | WalletPerformance | Fetch single wallet performance |
| `get_performance(wallet)` | WalletPerformance | Get performance with retry |
| `_fetch_all_performance()` | WalletPerformance | Fetch all wallet performance |
| `get_all_performance()` | WalletPerformance | Get all with retry |
| `get_performance_timeframe(days)` | WalletPerformance | Get performance for N days |
| `get_token_analysis(token, wallets)` | WalletPerformance | Analyze token across wallets |
| `cleanup_removed_wallets(active_wallets)` | WalletPerformance | Delete data for removed wallets |
| `get_recent_trades(wallet, limit)` | WalletPerformance | Get recent trades with PnL |
| `_fetch_hold_percentage(wallet, token)` | SpeedTracker | Get hold % from position |
| `_fetch_avg_entry_mc(wallet, token)` | SpeedTracker | Get avg entry market cap |

**Database Retry Logic:**
- Max retries: 5 (from Config.DB_MAX_RETRIES)
- Base delay: 0.5s, doubles each retry
- Retryable: Connection errors, pool exhaustion
- Non-retryable: Syntax errors, constraint violations

---

### 2.3 Transaction Parsing Methods

| Method | Class | Purpose |
|--------|-------|---------|
| `_is_dex_program(program_id)` | SpeedTracker | Check if program is known DEX |
| `_is_lp_or_exchange(address)` | SpeedTracker | Check if address is LP/exchange |
| `_detect_transfers(tx, wallet, account_keys)` | SpeedTracker | Detect wallet-to-wallet transfers |
| `check_wallet_fast(wallet_dict)` | SpeedTracker | Main wallet monitoring loop |
| `_mark_processed(sig)` | SpeedTracker | Mark tx as processed in Redis (30d TTL) |

**Transaction Flow in `check_wallet_fast`:**
1. Fetch signatures via `getSignaturesForAddress` (20 most recent)
2. Sort by blockTime (oldest first)
3. Check Redis cache for each signature
4. Fetch full transaction via `getTransaction`
5. Extract pre/post token balances
6. Calculate token changes per mint
7. Detect transfers (non-DEX)
8. For each change: update position, check cluster, record trade, send alert
9. Mark transaction as processed

---

### 2.4 Alert Methods

| Method | Class | Purpose |
|--------|-------|---------|
| `send_alert(wallet, token, tx_type, sol_amount, token_amount, sig)` | SpeedTracker | Send buy/sell alert to CHANNEL_PINGS |
| `send_transfer_alert(wallet, token, amount, is_sol, sig, counterparty, direction)` | SpeedTracker | Send transfer alert to CHANNEL_TRANSFERS |
| `send_cluster_alert(token, wallets, wallet_labels, trigger_tx_type, trigger_wallet)` | ClusterDetector | Send VIP cluster alert to CHANNEL_VIP |
| `get_token_info(token, use_cache=True)` | ClusterDetector | Fetch token metadata from DexScreener |

**Alert Channels:**
- `CHANNEL_PINGS` - Individual buy/sell alerts
- `CHANNEL_VIP` - Cluster formation alerts
- `CHANNEL_TRANSFERS` - Wallet-to-wallet transfer alerts

**Alert Throttling:**
- Cluster alerts: 5-second cooldown per token (Redis NX)
- Transfer alerts: Fire-and-forget (async tasks)
- Buy/sell alerts: Fire-and-forget with 0.1s sleep

---

### 2.5 Utility Methods

| Method | Class | Purpose |
|--------|-------|---------|
| `_load_exchange_wallets()` | SpeedTracker | Load exchanges.txt into set |
| `_load_lp_programs()` | SpeedTracker | Load lpools.txt into set |
| `load_wallets()` | SpeedTracker | Parse wallets.txt into list |
| `reload_wallets()` | SpeedTracker | Reload and update internal state |
| `add_wallet(address, label)` | SpeedTracker | Add wallet to file |
| `remove_wallet(query)` | SpeedTracker | Remove wallet by address/label |
| `_signal_handler(signum, frame)` | SpeedTracker | Handle SIGTERM/SIGINT |
| `connect()` | SpeedTracker | Initialize all connections |
| `close()` | SpeedTracker | Cleanup connections |
| `_create_session()` | SpeedTracker | Create aiohttp session with SSL |

---

## 3. EXTERNAL DEPENDENCIES

### 3.1 Files Read

| File | Purpose | Format |
|------|---------|--------|
| `wallets.txt` | Tracked wallet addresses and labels | `address\|label` per line, comments with `#` |
| `exchanges.txt` | Exchange wallet addresses to filter | One address per line, comments with `#` |
| `lpools.txt` | LP program addresses to filter | One address per line, comments with `#` |

**File Operations:**
- Read on startup and `/reload`
- Append on `/add` command
- Filter & rewrite on `/remove` command

---

### 3.2 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `HELIUS_RPC_URL` | Premium RPC endpoint | None |
| `ALCHEMY_API_KEY` | Alchemy API access | None |
| `TELEGRAM_BOT_TOKEN` | Bot authentication | None |
| `TELEGRAM_CHAT_ID` | Default alert channel | None |
| `CHANNEL_PINGS` | Buy/sell alert channel | None |
| `CHANNEL_VIP` | Cluster alert channel | None |
| `CHANNEL_TRANSFERS` | Transfer alert channel | None |
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `DB_NAME` | Database name | shadowhunter |
| `DB_USER` | Database user | sh |
| `DB_PASSWORD` | Database password | sh123 |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `ADMIN_USERS` | Comma-separated Telegram user IDs | "" |

---

### 3.3 Database Tables

#### wallet_positions
```sql
-- Tracks current and historical positions per wallet/token
wallet_address (text, PK)
token_address (text, PK)
total_bought (numeric)
total_sold (numeric)
net_position (numeric)
total_sol_invested (numeric)
total_sol_returned (numeric)
first_buy_time (timestamp)
last_buy_time (timestamp)
is_active (boolean)
avg_entry_mc (numeric)
```

#### wallet_performance
```sql
-- Tracks trading performance metrics per wallet
wallet_address (text, PK)
total_trades (int)
winning_trades (int)
losing_trades (int)
realized_pnl (numeric)
total_sol_invested (numeric)
total_sol_returned (numeric)
total_hold_time_seconds (numeric)
created_at (timestamp)
updated_at (timestamp)
```

---

### 3.4 Redis Keys

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `tx:{signature}` | Processed transaction deduplication | 30 days (2592000s) |
| `token_info:{token_address}` | Token metadata cache | 5 minutes (300s) |
| `cluster_throttle:{token}` | Cluster alert cooldown | 5 seconds |
| `trackhold:{token_address}` | Trackhold command result cache | 5 minutes (300s) |

---

### 3.5 API Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `https://api.dexscreener.com/latest/dex/tokens/{token}` | Token price, market cap, metadata | None |
| `https://api.mainnet-beta.solana.com` | Solana RPC | None |
| `https://solana-rpc.publicnode.com` | Public Solana RPC | None |
| `https://rpc.ankr.com/solana` | Public Solana RPC | None |
| `https://solana-mainnet.g.alchemy.com/v2/{key}` | Alchemy RPC | API Key |
| `{HELIUS_RPC_URL}` | Helius enhanced RPC | URL contains key |

**RPC Methods Used:**
- `getSignaturesForAddress` - Get transaction signatures for wallet
- `getTransaction` - Get full transaction details
- `getTokenSupply` - Get token total supply
- `getTokenAccountsByOwner` - Get token balances for wallet

---

## 4. DATA FLOW

### 4.1 Transaction Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TRANSACTION FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────────┐     ┌─────────────────────────────────┐
│  Solana RPC │────▶│ check_wallet_   │────▶│  1. getSignaturesForAddress    │
│  (Network)  │     │ fast()          │     │     (20 most recent)           │
└─────────────┘     └─────────────────┘     └─────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  2. Sort by     │
                    │     blockTime   │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  3. Redis Cache │
                    │     Check       │◀─────────┐
                    │  (tx:{sig})     │          │
                    └─────────────────┘          │
                              │                  │
                    ┌─────────┴─────────┐        │
                    │                   │        │
                   HIT                 MISS     │
                    │                   │        │
                    ▼                   ▼        │
              [Skip tx]      ┌────────────────┐  │
                             │ getTransaction │  │
                             │ (full details) │  │
                             └────────────────┘  │
                                      │           │
                                      ▼           │
                             ┌────────────────┐   │
                             │ Parse Balances │   │
                             │ pre/post token │   │
                             │ + SOL balances │   │
                             └────────────────┘   │
                                      │           │
                                      ▼           │
                             ┌────────────────┐   │
                             │ Detect Changes │   │
                             │ per mint       │   │
                             └────────────────┘   │
                                      │           │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌───────────┐    ┌─────────────┐    ┌────────────┐
            │   BUY     │    │    SELL     │    │ TRANSFER   │
            └─────┬─────┘    └──────┬──────┘    └─────┬──────┘
                  │                 │                 │
                  ▼                 ▼                 ▼
         ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
         │ update_      │   │ update_      │   │ send_        │
         │ position()   │   │ position()   │   │ transfer_    │
         │ (buy)        │   │ (sell)       │   │ alert()      │
         └──────┬───────┘   └──────┬───────┘   └──────────────┘
                │                  │
                ▼                  ▼
         ┌──────────────┐   ┌──────────────┐
         │ record_trade │   │ record_trade │
         │ (buy record) │   │ (sell w/ PnL)│
         └──────┬───────┘   └──────┬───────┘
                │                  │
                └────────┬─────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ check_cluster() │
                │ (if >threshold  │
                │  send VIP alert)│
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  send_alert()   │
                │  (buy/sell)     │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ _mark_processed │───────────────┐
                │ (tx:{sig})      │               │
                └─────────────────┘               │
                                                  │
                                                  ▼
                                        ┌─────────────────┐
                                        │ 30-day TTL set  │
                                        └─────────────────┘
```

### 4.2 Position Update Logic

**BUY:**
```sql
INSERT ... ON CONFLICT UPDATE
- total_bought += token_amount
- net_position += token_amount
- total_sol_invested += sol_amount
- last_buy_time = NOW()
- is_active = TRUE
- avg_entry_mc = weighted_average(old_mc * old_amount + new_mc * new_amount) / total
```

**SELL:**
```sql
UPDATE
- total_sold += token_amount
- net_position = MAX(0, net_position - token_amount)
- is_active = net_position > 0.0001
- total_sol_returned += sol_amount
```

### 4.3 Performance Calculation Flow

```
Trade Recorded
      │
      ▼
┌─────────────┐
│ Buy Record  │ ──▶ total_trades++, total_sol_invested += amount
└─────────────┘
      │
      ▼
┌─────────────┐
│ Sell Record │ ──▶ Get position data (cost basis)
└─────────────┘
      │
      ▼
┌─────────────────┐
│ Calculate PnL   │
│ trade_pnl =     │
│   sol_received  │
│   - (token_sold │
│      * avg_cost │
│      _per_token)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update Stats    │ ──▶ realized_pnl += trade_pnl
│                 │     winning_trades++ (if win)
│                 │     losing_trades++ (if loss)
│                 │     total_hold_time_seconds += hold_time
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Derived Metrics │ ──▶ winrate = wins / total * 100
│                 │     avg_roi = pnl / invested * 100
│                 │     confidence = (winrate * 0.6) + (min(roi,100) * 0.4)
└─────────────────┘
```

---

## 5. CONFIGURATION CONSTANTS

### 5.1 Core Config (from environment)

| Constant | Purpose | Typical Value |
|----------|---------|---------------|
| `HELIUS_RPC_URL` | Premium RPC with higher rate limits | `https://mainnet.helius-rpc.com/?api-key=xxx` |
| `ALCHEMY_API_KEY` | Alchemy API access | `xxx...` |
| `ALCHEMY_RPC_URL` | Full Alchemy endpoint | `https://solana-mainnet.g.alchemy.com/v2/{key}` |
| `TELEGRAM_BOT_TOKEN` | Bot authentication | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | Default channel ID | `-1001234567890` |
| `CHANNEL_PINGS` | Alert channel | `-100...` |
| `CHANNEL_VIP` | Cluster alerts | `-100...` |
| `CHANNEL_TRANSFERS` | Transfer alerts | `-100...` |

### 5.2 Thresholds & Intervals

| Constant | Purpose | Value |
|----------|---------|-------|
| `TRANSFER_SOL_THRESHOLD` | Min SOL for transfer alert | 0.5 SOL |
| `TRANSFER_TOKEN_THRESHOLD` | Min tokens for transfer alert | 100 tokens |
| `CHECK_INTERVAL` | Legacy interval (not used with adaptive) | 5 seconds |
| `RPC_TIMEOUT` | HTTP timeout for RPC calls | 5 seconds |
| `TOKEN_INFO_TTL` | DexScreener cache duration | 300 seconds (5 min) |
| `CLUSTER_THRESHOLD` | Min wallets to trigger cluster alert | 2 wallets |
| `MIN_SOL_THRESHOLD` | Min SOL for buy/sell alert | 0.02 SOL |

### 5.3 Performance Tuning

| Constant | Purpose | Value |
|----------|---------|-------|
| `DB_MAX_RETRIES` | Max DB retry attempts | 5 |
| `DB_BASE_RETRY_DELAY` | Initial retry delay | 0.5 seconds |
| `PERFORMANCE_SNAPSHOT_INTERVAL` | Performance stats save interval | 3600 seconds (1 hour) |
| `HELIUS_TX_LIMIT` | Max transactions per RPC call | 100 |
| `HELIUS_PRIORITY_FEE` | Priority fee for tracking (unused) | 10000 micro-lamports |

### 5.4 Filter Lists

| Constant | Value |
|----------|-------|
| `IGNORED_TOKENS` | `["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"]` (USDC) |
| `ADMIN_USERS` | Parsed from `ADMIN_USERS` env var (comma-separated integers) |

### 5.5 RPC Endpoints (Hardcoded)

**Public RPCs (Primary):**
- `https://api.mainnet-beta.solana.com`
- `https://solana-rpc.publicnode.com`
- `https://solana-api.instantnodes.io`
- `https://rpc.ankr.com/solana`
- `https://solana-mainnet.rpc.extrnode.com`
- `https://solana.public-rpc.com`

**DEX Programs (for filtering):**
- Jupiter: `JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4`
- Raydium: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`
- Orca: `whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc`
- Meteora: `LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo`
- Pump.fun: `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`
- Moonshot: `MoonCVVNZFSYkqNXP6bxHLPL6QQJiMagDL3qcE14FZp`

### 5.6 Adaptive Intervals

| Inactivity | Check Interval |
|------------|----------------|
| < 1 hour | 15 seconds |
| 1-6 hours | 30 seconds |
| 6-12 hours | 60 seconds |
| 12-24 hours | 90 seconds |
| 24+ hours | 120 seconds |

---

## 6. TELEGRAM COMMANDS

| Command | Handler | Access | Description |
|---------|---------|--------|-------------|
| `/start` | `start_cmd` | All | Show available commands |
| `/status` | `status_cmd` | All | Show tracker status |
| `/performance` | `performance_cmd` | All | Show leaderboard or wallet stats |
| `/performance 7d/30d` | `performance_timeframe_cmd` | All | Time-filtered performance |
| `/performance <wallet>` | `_show_wallet_performance` | All | Specific wallet stats |
| `/trackhold <token>` | `trackhold_cmd` | All | Check live token holdings |
| `/analyze <token>` | `analyze_token_cmd` | All | Token analysis across wallets |
| `/suggest` | `suggest_wallets_cmd` | All | Find similar wallets |
| `/recent <wallet>` | `recent_cmd` | All | Recent trades for wallet |
| `/add <addr> [label]` | `add_wallet_cmd` | Admin | Add wallet to tracking |
| `/remove <query>` | `remove_wallet_cmd` | Admin | Remove wallet from tracking |

**Callback Handlers:**
- `perf:page:N` - Pagination for performance leaderboard
- `perf:wallet:address` - Show specific wallet from leaderboard

---

## 7. KEY ARCHITECTURAL PATTERNS

### 7.1 Concurrency Management
- **Semaphores:** Limit concurrent DB (10), wallet checks (20), and RPC calls (20)
- **Adaptive Intervals:** Reduce RPC load for inactive wallets
- **Staggered Startup:** Spread initial checks over 60 seconds

### 7.2 Caching Strategy
- **Redis:** Transaction deduplication (30d), token info (5min), trackhold results (5min)
- **In-Memory:** Wallet labels mapping for O(1) lookups

### 7.3 Error Handling
- **RPC Failover:** Automatic fallback with cooldown tracking
- **DB Retry:** Exponential backoff for connection errors
- **Fail-Open:** Redis throttle failures allow alerts (don't block)

### 7.4 Resource Lifecycle
- **Session Refresh:** HTTP session recreated every 5000 cycles
- **Graceful Shutdown:** SIGTERM/SIGINT handling with event flag
- **Connection Pooling:** asyncpg and Redis connection limits

---

## 8. REFACTORING CONSIDERATIONS

### 8.1 High Cohesion Modules
Based on this analysis, the code could be split into:

1. **config/** - Configuration management
2. **rpc/** - RPC client with failover and rate limiting
3. **database/** - All DB operations and models
4. **tracker/** - Core transaction processing logic
5. **alerts/** - Telegram alert formatting and sending
6. **analytics/** - Performance tracking and cluster detection
7. **bot/** - Telegram bot command handlers
8. **models/** - Data classes for positions, trades, etc.

### 8.2 Current Tight Couplings
- `SpeedTracker` directly instantiates `ClusterDetector` and `WalletPerformance`
- Telegram handlers are closures that capture `tracker` instance
- File I/O mixed with business logic
- Database SQL embedded in method bodies

### 8.3 Data Flow Boundaries
- **Input:** Solana RPC → Transaction JSON
- **Transform:** Parse → Calculate changes → Update positions
- **Output:** Database updates + Telegram alerts

---

*Generated for modular refactoring planning*
