# EXECUTION.md — ShadowTrader Autonomous Execution Guide

_What they need to monitor, research, decide, and execute — on their own._

---

## 🎯 The Loop

Every alert → Research → Score → Decide → Execute → Log → Reflect

---

## 1. ALERT MONITORING

### What to Monitor

| Source | What It Tells You | Frequency | Priority |
|--------|------------------|-----------|----------|
| **ShadowHunter Tracker** | Wallet clusters, large transfers, new launches | Real-time (5s checks) | Critical |
| **Helius Webhooks** | On-chain events: swaps, liquidity adds, token creation | Event-driven | High |
| **Telegram Bot** | Formatted alerts from tracker | Real-time | High |
| **Redis Queue** | Internal alert buffer | Real-time | Medium |

### Alert Types & Required Actions

#### NEW_TOKEN
**Signal:** Brand new token with initial liquidity detected
**Immediate Actions:**
- [ ] Extract token mint address
- [ ] Check liquidity lock status (must be locked/burned)
- [ ] Verify dev wallet hasn't sold any allocation
- [ ] Check initial holder distribution (not 1 wallet holding 90%)
- [ ] Check if contract is renounced (can dev modify?)
- [ ] Look up token metadata (name, symbol, socials if available)
**Decision Timer:** 30-60 seconds max
**Default:** WATCH if any red flag, PAPER TRADE if clean

#### CLUSTER_BUY
**Signal:** 3+ wallets from tracked cluster buying same token
**Immediate Actions:**
- [ ] Identify the cluster (which group? known profitable?)
- [ ] Check cluster's historical winrate (if known)
- [ ] Verify token isn't already up >3x (too late?)
- [ ] Check if cluster is buying *into* existing position or *new* token
- [ ] Check token age (launched in last 6h? vs. 3 days old?)
**Decision Timer:** 60-90 seconds
**Default:** PASS if token is >3x from launch, PAPER TRADE if early

#### LARGE_TRANSFER
**Signal:** Single wallet moved significant SOL or tokens
**Immediate Actions:**
- [ ] Identify wallet (known? tracked? new?)
- [ ] Direction: moving TO DEX or FROM DEX?
- [ ] Size relative to wallet's total holdings (% of portfolio)
- [ ] Token being moved: new launch or established?
**Decision Timer:** 2-3 minutes (lower priority)
**Default:** WATCH unless wallet is known profitable AND moving TO new token

#### VOLUME_SPIKE
**Signal:** Token volume increased >300% in short window
**Immediate Actions:**
- [ ] Check price movement vs. volume (volume up, price flat = lag)
- [ ] Check if spike is sustained or flash (1 minute vs. 10 minutes)
- [ ] Identify source of volume (1 wallet or many?)
- [ ] Check if correlated with cluster buy or transfer
**Decision Timer:** 2 minutes
**Default:** PAPER TRADE if volume precedes price by >40 seconds

---

## 2. TOKEN RESEARCH (Per Alert)

### Required Data Points

For EVERY token being considered:

#### A. Liquidity & Safety (Must Pass All)
- [ ] **Liquidity locked?** Check via SolanaFM or RugCheck
  - Locked/burned = ✅
  - Unlocked or lock expires <30 days = ❌ PASS
- [ ] **Dev wallet activity?** Check if dev sold in first hour
  - No sells = ✅
  - Any sell >5% of supply = ❌ PASS
- [ ] **Contract renounced?** Can dev still modify contract?
  - Renounced = ✅
  - Not renounced = ⚠️ higher risk, smaller size
- [ ] **Holder distribution?** Top 10 holders own what %?
  - <30% = ✅
  - >50% = ❌ PASS (whale risk)

#### B. Market Context
- [ ] **Market cap** at current price
  - <500K = early, higher risk/reward
  - 500K-5M = sweet spot for momentum
  - >10M = lower risk but less upside
- [ ] **Liquidity depth** (how much can be sold without crashing price?)
  - >50K SOL in liquidity = ✅
  - <10K SOL = ⚠️ exit will be hard
- [ ] **24h volume** trend
  - Increasing = ✅
  - Flat/decreasing = ⚠️ momentum fading

#### C. Social Signal (If Available)
- [ ] **Twitter/X mentions** (scraped or API)
  - Growing organically = ✅
  - Bot-filled, no real engagement = ⚠️
- [ ] **Telegram group** activity
  - Active, organic = ✅
  - Dead or botted = ⚠️
- [ ] **Website** exists and not template
  - Professional/unique = ✅
  - Generic template = ⚠️

#### D. Time Context
- [ ] **Token age**
  - <1 hour = highest risk, highest reward
  - 1-6 hours = momentum window
  - 6-24 hours = fading momentum, more info available
  - >24 hours = only trade if new catalyst
- [ ] **Alert timing**
  - Alert within 2 min of event = ✅
  - Alert >10 min old = ⚠️ may be too late

### Research APIs & Tools

| Data Point | Source | Endpoint/Tool |
|------------|--------|--------------|
| Liquidity lock | RugCheck API | `https://api.rugcheck.xyz/v1/tokens/{mint}` |
| Holder distribution | Helius | `getTokenHolders` |
| Market cap / price | Jupiter | `https://price.jup.ag/v4/price?ids={mint}` |
| Volume | Birdeye | `https://public-api.birdeye.so/public/history?address={mint}` |
| Contract info | SolanaFM | `https://api.solana.fm/v0/accounts/{mint}` |
| DexScreener | Social + chart | `https://api.dexscreener.com/latest/dex/tokens/{mint}` |

---

## 3. DECISION FRAMEWORK

### Scoring Matrix

Rate each trade opportunity on 4 dimensions (1-10):

#### Signal Strength (1-10)
| Score | Meaning |
|-------|---------|
| 9-10 | Multiple confirming signals (cluster + volume + early) |
| 7-8 | Strong single signal (large cluster, very early launch) |
| 5-6 | Moderate signal (some activity, but not overwhelming) |
| 3-4 | Weak signal (single wallet, older token) |
| 1-2 | Noise (unclear what triggered the alert) |

#### Timing Quality (1-10)
| Score | Meaning |
|-------|---------|
| 9-10 | First 2 minutes of launch or first cluster detection |
| 7-8 | Within 5 minutes, clear early momentum |
| 5-6 | Within 15 minutes, still early but more info priced in |
| 3-4 | 30+ minutes, chasing |
| 1-2 | >1 hour, definitely too late |

#### Risk Level (1-10, lower = riskier)
| Score | Meaning |
|-------|---------|
| 9-10 | Liquidity locked, dev renounced, clean distribution |
| 7-8 | Mostly clean, minor concerns |
| 5-6 | Some red flags but manageable with small size |
| 3-4 | Significant risk (unlocked, dev active, weird distribution) |
| 1-2 | Likely rug (obvious honeypot, unlocked, dev selling) |

#### Conviction (1-10)
| Score | Meaning |
|-------|---------|
| 9-10 | "This matches a pattern that worked 5+ times" |
| 7-8 | "Strong signal, good timing, manageable risk" |
| 5-6 | "Interesting but not sure, worth a small bet" |
| 3-4 | "Something about this doesn't feel right" |
| 1-2 | "Just FOMO or curiosity, no real edge" |

### Decision Rules

```
IF Signal Strength >= 7 AND Timing >= 7 AND Risk >= 5 AND Conviction >= 6:
    → PAPER TRADE (full size: 5% portfolio)

ELIF Signal Strength >= 5 AND Timing >= 5 AND Risk >= 7 AND Conviction >= 5:
    → PAPER TRADE (reduced size: 2% portfolio)

ELIF Signal Strength >= 6 AND Timing >= 6 BUT Risk < 5:
    → WATCH (wait for confirmation or better entry)

ELIF Timing < 5 OR Conviction < 4:
    → PASS (too late or not enough confidence)

ELSE:
    → WATCH (gather more data)
```

---

## 4. EXECUTION

### Paper Trade Execution

1. **Log intent** BEFORE executing (prevents post-hoc rationalization)
   - Token, signal type, scores, planned entry, planned exit
2. **Calculate position size**
   - Full size: 5% of current SOL balance
   - Reduced size: 2% of current SOL balance
   - Max single trade: 0.05 SOL (during paper testing)
3. **Execute simulated buy**
   - Record entry price, market cap, timestamp
   - Deduct SOL + fee (0.01 SOL) from paper balance
4. **Set monitoring**
   - Add to active positions list
   - Set stop-loss (usually -30% or -50% for memecoins)
   - Set take-profit ladder (50% at 2x, 25% at 5x, 25% hold)
5. **Log to database**
   - All trade details, reasoning, expected outcome

### Position Monitoring (Every 5 Minutes)

For each open position:
- [ ] Current price vs. entry
- [ ] Current market cap vs. entry
- [ ] Unrealized PnL
- [ ] Volume trend (increasing = hold, decreasing = consider exit)
- [ ] Any new alerts for this token? (cluster selling? dev moving?)
- [ ] Time held (memecoins peak fast, usually within 2-6 hours)

### Exit Rules

| Condition | Action |
|-----------|--------|
| Hit 2x take-profit | Sell 50% of position |
| Hit 5x take-profit | Sell 25% of remaining (total 75% sold) |
| Hit -30% stop-loss | Sell 100% immediately |
| No volume for 4+ hours | Consider exit (momentum dead) |
| Dev wallet sells any amount | Sell 100% immediately |
| Liquidity unlocks | Sell 100% immediately |
| Cluster that bought starts selling | Sell 50-100% (follow smart money out) |
| New token launched by same dev | Sell 100% (dev left for new project) |

---

## 5. LOGGING & REFLECTION

### Every Trade (Win or Loss)

Log to `trader/trade_log.md` or database:

```
## Trade: [TOKEN_SYMBOL] — [DateTime]

**Signal:** [Cluster/Volume/Transfer/New]
**Scores:** Signal=[X] Timing=[X] Risk=[X] Conviction=[X]
**Research:**
- Liquidity locked: [Yes/No]
- Dev sold: [Yes/No]
- Holder distribution: [clean/concentrated]
- Market cap at entry: [X]

**Execution:**
- Entry: [X SOL at $Y price]
- Size: [Z% portfolio]
- Exit: [A SOL at $B price / or still holding]
- PnL: [+/- X SOL, +/- Y%]

**Why I took it:** [reasoning]
**What happened:** [outcome]
**Lesson:** [what to do differently next time]
```

### Daily Reflection (End of Session)

Answer:
1. What pattern worked today?
2. What pattern failed?
3. Did I follow my position sizing rules?
4. Did I chase any FOMO trades?
5. What will I do differently tomorrow?

Update `trader/MEMORY.md` with answers.

---

## 6. AUTONOMOUS DECISION CHECKLIST

Before executing ANY trade without human input, confirm:

- [ ] Alert is fresh (<5 minutes old)
- [ ] Liquidity is locked
- [ ] Dev hasn't sold
- [ ] Position size is ≤5% portfolio
- [ ] I can articulate WHY this trade has edge
- [ ] I have a clear exit plan (stop-loss + take-profit)
- [ ] This isn't FOMO (token hasn't pumped >3x already)
- [ ] Total open positions ≤5 (don't over-diversify)

**If ANY check fails → PASS or WATCH, never trade.**

---

## 7. HUMAN OVERRIDE PROTOCOLS

### When to Alert Human Immediately
- Portfolio drawdown >15% in single session
- Unclear if token is honeypot/rug (can't verify liquidity)
- Tracker producing impossible data (likely bug)
- Want to exceed 5% position size for "special opportunity"
- Emotional state compromised (tired, frustrated, overconfident after big win)

### When Human Can Override You
- Any time, no questions asked
- Force sell any position
- Pause all trading
- Change position sizing rules
- Ban specific tokens or wallets from trading

---

*Execute with discipline. Research with skepticism. Decide with conviction. Log with honesty.*
