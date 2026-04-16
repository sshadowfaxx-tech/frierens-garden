# Claude Autonomous Trader Setup on FX 6300

## Goal
Run Claude as an autonomous trading agent on FX 6300 that:
- Monitors all tracker alerts
- Learns from every trade
- Executes autonomously
- Adapts strategy over time

## Architecture

```
FX 6300
├── Tracker (trackerv2.py) → Writes to PostgreSQL
├── PostgreSQL (port 5432) → Shared database
├── Redis (port 6379) → Shared cache
└── OpenClaw Gateway + Claude Agent → The trader
```

## Prerequisites

1. **Node.js 20+** installed
2. **OpenClaw** installed globally: `npm install -g openclaw`
3. **Claude API key** from Anthropic console

## Step 1: Configure OpenClaw Gateway

Create/edit `~/.openclaw/config.yaml`:

```yaml
# ~/.openclaw/config.yaml
gateway:
  port: 8080
  host: 0.0.0.0
  
models:
  default: anthropic/claude-4-6
  anthropic:
    api_key: ${CLAUDE_API_KEY}
    
sessions:
  claude-trader:
    agent: main
    model: anthropic/claude-4-6
    thinking: high
    
channels:
  telegram:
    token: ${TELEGRAM_BOT_TOKEN}
    
database:
  postgresql:
    host: localhost
    port: 5432
    database: shadowhunter
    user: postgres
    password: sh123
    
redis:
  host: localhost
  port: 6379
```

## Step 2: Set Environment Variables

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export CLAUDE_API_KEY=sk-ant-api03-your-key-here
export TELEGRAM_BOT_TOKEN=your-bot-token
export ANTHROPIC_API_KEY=$CLAUDE_API_KEY
```

Then reload:
```bash
source ~/.bashrc
```

## Step 3: Create Claude Trader Agent

Create `~/claude-trader/SKILL.md`:

```markdown
# Claude Trader Skill

## Purpose
Autonomous Solana memecoin trader running on FX 6300.

## Capabilities
- Query PostgreSQL for wallet positions and performance
- Execute trades via Sol CLI
- Learn from trade outcomes
- Adapt strategy weights
- Report decisions to Telegram

## Tools
- PostgreSQL database access
- Sol CLI for trading
- Telegram notifications
- File system for strategy persistence

## Strategy Guidelines
1. Paper trade initially (2 SOL balance)
2. Log every decision with reasoning
3. Track win/loss rates per wallet
4. Adjust weights based on performance
5. Conservative approach - quality over quantity

## Database Schema
- wallet_positions: token holdings
- wallet_performance: winrate, PnL
- paper_trades: trade history
- paper_portfolio: current balance
```

## Step 4: Optimize PostgreSQL for Multiple Connections

Since both tracker and Claude will connect:

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Increase max connections
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '4GB';

-- Restart PostgreSQL
-- On Windows: services.msc → Restart PostgreSQL
-- On Linux: sudo systemctl restart postgresql
```

## Step 5: Start the Gateway

```bash
# Start OpenClaw gateway with Claude
openclaw gateway start --config ~/.openclaw/config.yaml

# Or if already configured
openclaw gateway start
```

## Step 6: Spawn Claude Trader Session

```bash
# Create a named session for the trader
openclaw sessions spawn \
  --agent claude-trader \
  --model anthropic/claude-4-6 \
  --task "Monitor ShadowHunter database for wallet positions. When new positions appear, analyze wallet performance data and make paper trading decisions. Log all trades and outcomes. Adapt strategy based on results."
```

## Step 7: Give Claude the Trading Prompt

Send this to Claude once running:

```
You are now an autonomous Solana memecoin trader running on FX 6300.

Your job:
1. Poll database every 15 seconds for new wallet_positions
2. When you see new activity (2+ wallets on same token = cluster):
   - Query wallet_performance for each wallet
   - Research token (DexScreener API)
   - Calculate weighted confidence
   - Decide: BUY / WATCH / SKIP
3. Execute paper trades (2 SOL starting balance)
4. Log every decision with reasoning
5. Track outcomes and adjust weights

Database credentials:
- Host: localhost:5432
- Database: shadowhunter
- User: postgres
- Password: sh123

Trading rules:
- Max position: 0.5 SOL
- Stop loss: -30%
- Take profit: +50%, +100%, +200% (ladder out)
- Only trade if confidence > 60%

Report all trades to Telegram channel: -1003778576771

Start monitoring now.
```

## Monitoring

**Check if running:**
```bash
openclaw gateway status
openclaw sessions list
```

**View logs:**
```bash
tail -f ~/.openclaw/logs/gateway.log
tail -f ~/.openclaw/logs/claude-trader.log
```

## Resource Management

**If FX 6300 gets slow:**

1. **Reduce Claude polling frequency** (30s instead of 15s)
2. **Limit PostgreSQL connections** in config
3. **Use nice/renice** to prioritize tracker
4. **Consider upgrading** PostgreSQL connection pool

## Troubleshooting

**"Too many connections" error:**
```sql
-- Check current connections
SELECT count(*) FROM pg_stat_activity;

-- Increase max_connections (edit postgresql.conf)
max_connections = 100
```

**Gateway won't start:**
```bash
# Check port availability
netstat -ano | findstr 8080

# Kill existing process or change port in config
```

**Claude not responding:**
- Check API key validity
- Verify rate limits (Claude Max should be fine)
- Check gateway logs for errors

## Integration with Existing Infrastructure

The existing tracker (trackerv2.py) continues running independently.
Claude reads from the same database but doesn't interfere with writes.

Both share:
- PostgreSQL (wallet_positions, wallet_performance)
- Redis (processed transaction cache)
- wallets.txt (read-only for Claude)

## Next Steps

1. Install and configure OpenClaw gateway
2. Set Claude API key
3. Start gateway
4. Spawn Claude trader session
5. Give trading prompt
6. Monitor via Telegram and logs

Claude will now trade autonomously while the tracker continues monitoring.
```

## Important Notes

- **Start with paper trading** - Don't fund live wallet until profitable
- **Monitor resource usage** - FX 6300 has limits
- **Keep Kimi (me) for infrastructure** - I'll help with code, bugs, optimization
- **Claude handles trading logic** - Strategy, decisions, learning

This setup gives you the best of both: Claude's reasoning for trading, my building for infrastructure.
