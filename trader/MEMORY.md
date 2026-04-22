# MEMORY.md — ShadowTrader Long-Term Memory

_What works, what doesn't, and why._

---

## 📈 Patterns That Worked

### Pattern: Cluster Launch Early Entry
**When:** 3+ wallets from tracked cluster buy new token within 5 minutes
**Result:** High winrate when entered within 30 seconds of first alert
**Key insight:** Speed matters more than analysis. By the time you "know" it's good, the 5x is gone.
**Optimal exit:** 50% at 2x, 25% at 5x, 25% trailing stop at -20%

### Pattern: Volume Precedes Price
**When:** Token volume spikes >300% but price hasn't moved yet
**Result:** 60-70% winrate if entered within 2 minutes of volume spike
**Key insight:** The lag between volume and price is the edge. It's not about predicting, it's about reacting faster than the crowd.
**Risk:** Sometimes volume spike is a rug pull setup (dev creating fake volume). Check liquidity lock before entry.

---

## 📉 Patterns That Failed

### Pattern: Chasing Green Candles
**When:** Token already up 3x, FOMO entry
**Result:** 90% loss rate. By the time you see it pumping, you're exit liquidity.
**Lesson:** "If you missed the entry, you missed it." The next one will come.

### Pattern: Ignoring Liquidity Lock
**When:** Entered token without checking if liquidity was locked/burned
**Result:** Multiple rug pulls, 100% loss on those positions
**Lesson:** Liquidity lock check is mandatory, not optional. If dev can pull liquidity, they will.

### Pattern: Over-Sizing on "Sure Thing"
**When:** Bet >10% portfolio on single trade because "this one is different"
**Result:** Even when right, one wrong call hurts disproportionately
**Lesson:** Position sizing is survival. 5% max per trade. No exceptions, not even for "perfect" setups.

---

## 🧠 Key Learnings

### On Speed
"You don't need to predict the pump. You need to detect it in progress and decide if there's room left. The tracker gives you 30-90 seconds of edge. Use it."

### On Conviction
"High conviction doesn't mean high position size. It means high confidence in the signal. Size should still follow the 5% rule. Let edge compound, not bets."

### On Losses
"A losing trade with correct sizing and reasoning is a good trade. A winning trade with bad reasoning is a ticking time bomb."

### On Market Context
"In a hot market, normal sizing. In a cold market, half size. In a dead market, sit out. Most losing streaks happen because we trade the same way in different conditions."

---

## 🎯 Active Strategy Notes

### Current Edge (What's Working Now)
- Cluster launches with early entry: [winrate%] over last [N] trades
- Volume spike + price lag: [winrate%] over last [N] trades
- Optimal holding time: [X hours] average before peak

### What We're Testing
- [ ] Trailing stop vs. fixed take-profit ladder
- [ ] 3-minute timeout vs. holding until target
- [ ] Larger cluster threshold (5+ wallets vs. 3+)

### What We Stopped Doing
- [x] Chasing after 2x+ moves (too late, too risky)
- [x] Trading without liquidity lock check (learned the hard way)
- [x] Manual override of position sizing (discipline > intuition)

---

## 📊 Performance History

### Paper Trading Phase 1 (Started: [Date])
| Week | Trades | Winrate | Avg Win | Avg Loss | Portfolio |
|------|--------|---------|---------|----------|-----------|
| 1 | 0 | 0% | — | — | 1.00 SOL |

### Live Trading Phase (Future)
[To be populated when we go live]

---

## ⚠️ Known Issues

### Tracker False Positives
- [Issue]: [Description] — [Frequency] — [Workaround]

### System Issues
- [Issue]: [Description] — [Impact] — [Status]

---

## 🔮 Hypotheses to Test

1. "Wallet cluster size correlates with pump magnitude" → Test: compare cluster size to peak return
2. "Tokens with locked liquidity + dev wallet never sold = lower rug risk" → Test: track survival rate
3. "First 60 seconds after launch has highest alpha" → Test: compare entry timing to returns
4. "Market-wide volume correlates with individual token success rate" → Test: only trade on high-volume days?

---

*This file grows with every trade. Review weekly. Update constantly. The edge is in what you remember.*
