# TOOLS.md — ShadowTrader Tool Configuration

_What you have, how to use it, where the keys live._

---

## Data Sources

### Primary: ShadowHunter Tracker
**File:** `trackerv2_clean.py`
**What it does:** Monitors Solana wallets for large transfers, new token launches, and wallet clustering
**Output:** Telegram alerts + database records
**Status:** Must be running for system to function

**Alert Types:**
- `NEW_TOKEN` — New token detected with liquidity
- `CLUSTER_BUY` — Multiple wallets from same cluster buying
- `LARGE_TRANSFER` — Single wallet moving significant SOL/tokens
- `VOLUME_SPIKE` — Token volume increases dramatically

**Configuration:**
```bash
# These must be set in environment or .env
HELIUS_RPC_URL=       # Premium RPC for speed
ALCHEMY_API_KEY=       # Backup RPC
TELEGRAM_BOT_TOKEN=    # Bot for alerts
TELEGRAM_CHAT_ID=      # Channel for public alerts
CHANNEL_PINGS=         # Channel for ping alerts
CHANNEL_VIP=           # Channel for high-confidence alerts
CHANNEL_TRANSFERS=     # Channel for transfer alerts
```

### Secondary: RPC Endpoints
- Helius (primary, paid) — Fast, reliable, enhanced APIs
- Alchemy (backup) — Fallback if Helius fails
- Public RPCs (last resort) — Slow but free

### Price Data
- Jupiter API — Current token prices, route finding
- DexScreener — Market cap, liquidity, holder count
- Birdeye — Volume, price history

---

## Trading Infrastructure

### Paper Trader
**File:** `paper_trader.py`
**What it does:** Simulates trades using real market data, tracks PnL, winrate, portfolio
**Balance:** 1 SOL (paper, not real)
**Fee per trade:** 0.01 SOL

**Database Schema:**
- `paper_trades` — All executed trades
- `paper_positions` — Current holdings
- `portfolio_snapshots` — Daily balance records
- `alert_log` — All tracker alerts received

### Live Trading (Future)
**Wallet:** TBD (human will provide)
**DEX:** Jupiter Aggregator (best routes, lowest slippage)
**Priority:** High fee for fast execution (speed matters)

---

## Communication

### Telegram Channels
| Channel | Purpose | Priority |
|---------|---------|----------|
| Admin (you) | System issues, major decisions | Critical |
| VIP Alerts | High-confidence trade signals | High |
| Pings | General tracker activity | Medium |
| Paper Trades | All paper trading activity | Log |

### Commands You Can Send
- `/status` — Portfolio summary, open positions, today's PnL
- `/pause` — Stop taking new trades (maintain positions)
- `/resume` — Resume normal operation
- `/summary` — Weekly performance report
- `/force_sell <token>` — Exit position immediately (emergency)

---

## Environment Variables

### Required for Operation
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shadowhunter
DB_USER=sh
DB_PASSWORD=sh123

# Redis (alert queue)
REDIS_HOST=localhost
REDIS_PORT=6379

# RPC
HELIUS_RPC_URL=https://your-helius-url
ALCHEMY_API_KEY=your-key

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
CHANNEL_PINGS=ping-channel-id
CHANNEL_VIP=vip-channel-id
CHANNEL_TRANSFERS=transfer-channel-id
CHANNEL_PAPER_TRADES=paper-trades-channel-id

# Trading
TRANSFER_SOL_THRESHOLD=0.5
TRANSFER_TOKEN_THRESHOLD=100
```

### Files That Must Exist
- `.env` — All secrets (NEVER commit to git)
- `trackerv2_clean.py` — Tracker (running)
- `paper_trader.py` — Trader (can be started/stopped)

---

## Key Locations

| What | Where |
|------|-------|
| Agent identity | `trader/SOUL.md` |
| Session protocol | `trader/AGENTS.md` |
| Trading goals | `trader/GOAL.md` |
| Trading memory | `trader/MEMORY.md` |
| Periodic checks | `trader/HEARTBEAT.md` |
| Tracker code | `trackerv2_clean.py` |
| Paper trader | `paper_trader.py` |
| Database | PostgreSQL `shadowhunter` |
| Alert queue | Redis |
| Logs | Telegram channels + local files |

---

## Quick Commands

```bash
# Start tracker
python trackerv2_clean.py

# Start paper trader
python paper_trader.py

# Check database
psql -U sh -d shadowhunter -c "SELECT * FROM paper_positions;"

# Check Redis queue
redis-cli LRANGE alerts 0 10

# View recent trades
tail -f logs/paper_trades.log
```

---

*Keep tools sharp. Know where everything lives. Trust the system, verify the outputs.*
