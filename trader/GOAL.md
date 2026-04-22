# GOAL.md — Himmel the Trader Trading System

_What we're building, why, and how we know it's working._

---

## 🎯 Mission

Build a profitable memecoin trading system on Solana through:
1. Detecting whale/cluster movement before the crowd
2. Paper trading to prove edge without risking capital
3. Systematic execution that removes emotion from decision-making
4. Continuous learning from every trade, win or lose

**Current Phase:** Paper Trading Proof-of-Concept
**Next Phase:** Live Trading (human-approved, risk-limited)
**Ultimate Goal:** Autonomous trading with human oversight, not permission

---

## 📊 Success Metrics

### Paper Trading Targets (Phase 1)
| Metric | Target | Minimum | Timeframe |
|--------|--------|---------|-----------|
| Winrate | >55% | >50% | 100 trades |
| Average Win | >2x Average Loss | >1.5x | 100 trades |
| Max Drawdown | <20% | <30% | Rolling |
| Portfolio Return | >20% | >10% | 30 days |
| Trades per week | 5-15 | >3 | Weekly |

### Live Trading Targets (Phase 2)
| Metric | Target | Risk Limit |
|--------|--------|------------|
| Position size | <5% portfolio | Hard cap at 10% |
| Daily loss limit | <5% portfolio | Auto-stop for day |
| Monthly loss limit | <20% portfolio | Human review required |
| Winrate | >50% | Reassess strategy if <45% |

---

## 🧠 Strategy Framework

### Signal Types We Trade

1. **Cluster Launch** (Highest Priority)
   - 3+ wallets from tracked cluster buy new token within 5 minutes
   - Signal strength: 8-10
   - Entry: Immediate (within 30 seconds of alert)
   - Exit: 50% at 2x, 25% at 5x, 25% hold with trailing stop

2. **Volume Spike + Price Lag**
   - Token volume increases >300% but price hasn't moved yet
   - Signal strength: 6-8
   - Entry: Within 2 minutes
   - Exit: 100% at 3x or 24h timeout

3. **Large Wallet Rotation**
   - Known profitable wallet moves >50% of position into new token
   - Signal strength: 7-9
   - Entry: Within 1 minute
   - Exit: Follow their pattern (usually quick flip)

4. **Transfer Alert (Secondary)**
   - Large SOL or token transfer between wallets
   - Signal strength: 3-5
   - Action: Usually watch, rarely trade
   - Used for: Pattern building, not direct profit

### Signal Types We Ignore
- Tokens with <5 holders
- Tokens with no liquidity locked
- Tokens where dev wallet sells within 1 hour of launch
- Anything Jonathan says "no" to
- Your own FOMO

---

## 📋 Active Checklist

### Infrastructure
- [x] ShadowHunter tracker operational (`trackerv2_clean.py`)
- [x] Paper trading system (`paper_trader.py`)
- [x] Database schema (PostgreSQL)
- [x] Telegram alert channels configured
- [ ] **Identity files created** (SOUL, AGENTS, GOAL, TOOLS, HEARTBEAT)
- [ ] **Agent workspace initialized**
- [ ] Backup tracker data source (in case primary fails)
- [ ] Automated position monitoring (check positions every minute)

### Strategy Development
- [ ] Define cluster scoring algorithm (how to rank which clusters matter)
- [ ] Backtest cluster signals on historical data
- [ ] Define "too late" threshold (how old can an alert be?)
- [ ] Build rug pull detection (dev selling, liquidity removal)
- [ ] Define take-profit ladder (when to sell what %)
- [ ] Build stop-loss system (hard stops + time-based exits)

### Performance Tracking
- [ ] Daily PnL snapshot to Telegram
- [ ] Weekly performance report (winrate, avg win/loss, max drawdown)
- [ ] Monthly strategy review (what's working, what isn't)
- [ ] Trade journal with reasoning (why did you take each trade?)

### Risk Management
- [x] Position sizing rules (coded into paper_trader.py)
- [ ] Daily loss circuit breaker
- [ ] Weekly max drawdown hard stop
- [ ] Correlation check (don't hold 5 memecoins that all move together)

### Transition to Live
- [ ] 30 days of profitable paper trading
- [ ] Human review of all 30 days of trades
- [ ] Risk limits confirmed by human
- [ ] Small live test: 0.5 SOL max for first week
- [ ] Scale up gradually based on live performance

---

## ⚠️ What Will Make Us Stop

1. Paper trading unprofitable for 30+ days
2. Live trading hits monthly loss limit
3. System bugs causing missed stops or double execution
4. Human says "stop" (no questions asked)
5. Market conditions fundamentally change (e.g., all memecoins die for 6 months)

---

## 🔄 Learning Loop

After every trade, document:
- What was the signal?
- Why did you take it?
- What happened?
- What did you learn?
- What will you do differently next time?

Review weekly. Update strategy. Never stop learning.

---

*This is a living document. Strategy evolves. Markets change. We adapt or we die.*
