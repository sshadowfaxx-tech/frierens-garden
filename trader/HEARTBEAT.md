# HEARTBEAT.md — ShadowTrader Periodic Checks

_What to check, when, and what to do about it._

---

## Every 5 Minutes (During Active Trading)

### 1. Position Monitor
- Check all open positions against current prices
- Any hit stop-loss? → Execute exit, log reason
- Any hit take-profit? → Execute partial/full exit per ladder
- Any token with no volume for >6 hours? → Consider exit

### 2. Alert Queue
- Process new tracker alerts from Redis queue
- Score each alert (signal strength, timing, risk)
- Execute paper trades that meet criteria
- Log all decisions with reasoning

### 3. System Health
- Tracker still running? (process check)
- Database responsive? (ping query)
- RPC endpoints working? (quick test call)
- Telegram bot sending? (heartbeat ping to admin)

---

## Every 30 Minutes

### Portfolio Snapshot
- Current SOL balance
- Total portfolio value (SOL + positions)
- Unrealized PnL on open positions
- Day's realized PnL
- Win/loss count for current session

Send to admin channel if significant change (>5% portfolio value).

### Tracker Quality Check
- Alerts received in last 30 min vs. expected rate
- False positive rate (alerts that led to no trade)
- Missed signals (tracker saw something you didn't act on)

---

## Every 4 Hours

### Market Context
- SOL price movement (trending up/down/sideways?)
- Overall memecoin market activity (volume, new launches)
- Any major news/events affecting Solana ecosystem?
- Are we in a "hot" market or "cold" market?

Adjust position sizing:
- Hot market: Normal size (opportunities are real)
- Cold market: Reduce size by 50% (most signals will be noise)
- Uncertain: Maintain current size, tighten stops

### Performance Tracking
- Update rolling 24h metrics
- Compare to yesterday's same time
- Flag if metrics deteriorating (winrate dropping, drawdown increasing)

---

## Daily (Session Wrap)

### End-of-Day Report (send to admin)
```
ShadowTrader Daily — [Date]

Trades: [X] executed
Win/Loss: [Y]/[Z] ([winrate]%)
Realized PnL: [+/- X.XX SOL]
Portfolio Value: [X.XX SOL] ([+/- X.X]% from start)
Open Positions: [N] ([tokens])

Best Trade: [token] [+X.X SOL] — [reason]
Worst Trade: [token] [-X.X SOL] — [lesson learned]

System Status: [healthy/issues]
Notes: [anything unusual]
```

### Memory Update
- Add today's key learnings to `MEMORY.md`
- Update "Patterns That Worked" and "Patterns That Failed"
- Note any system issues or tracker false positives

---

## Weekly (Every 7 Days)

### Strategy Review
1. Pull all trades from database
2. Calculate:
   - Overall winrate
   - Average win size vs. average loss size
   - Max drawdown
   - Sharpe ratio (if enough data)
3. Analyze by signal type:
   - Cluster launches: [winrate%, avg return]
   - Volume spikes: [winrate%, avg return]
   - Wallet rotations: [winrate%, avg return]
4. Identify:
   - What's working? → Do more of it
   - What's not? → Do less or fix it
   - What's missing? → New opportunities

### Memory Consolidation
- Review daily `MEMORY.md` entries
- Distill into weekly summary
- Update `GOAL.md` if targets need adjustment

### System Maintenance
- Database backup
- Log rotation (archive old logs)
- Tracker config review (thresholds still appropriate?)
- API key rotation check (do any need renewing?)

---

## Monthly (Every 30 Days)

### Major Review
- Full performance analysis vs. GOAL targets
- Strategy effectiveness: Are we hitting our metrics?
- Risk management: Did we ever violate position sizing? Circuit breakers work?
- Live trading readiness assessment

### Decision Point
- Metrics green across the board? → Prepare live trading proposal for human
- Metrics yellow? → Continue paper, adjust strategy
- Metrics red? → Stop and reassess fundamentally

---

## Emergency Triggers (Immediate Action)

**Immediate halt + alert human:**
- Portfolio drops >10% in one trade
- Tracker reports rug pull on held token
- Database corruption or data loss
- Suspicious activity on wallet (if live)
- Human sends `/stop` command

**Immediate halt + self-investigate:**
- Three consecutive losing trades (check for strategy breakdown)
- Tracker producing 10x normal alert rate (probably broken)
- Can't connect to RPC for >5 minutes (flying blind)
- Telegram bot unresponsive for >10 minutes (can't communicate)

---

## Heartbeat State File

Track last checks in `trader/heartbeat-state.json`:
```json
{
  "lastChecks": {
    "positionMonitor": "2026-04-22T11:45:00Z",
    "alertQueue": "2026-04-22T11:45:00Z",
    "systemHealth": "2026-04-22T11:45:00Z",
    "portfolioSnapshot": "2026-04-22T11:30:00Z",
    "trackerQuality": "2026-04-22T11:30:00Z",
    "marketContext": "2026-04-22T08:00:00Z",
    "dailyReport": "2026-04-22T00:00:00Z",
    "weeklyReview": "2026-04-20T00:00:00Z"
  }
}
```

---

*Check systematically. Act decisively. Log everything.*
