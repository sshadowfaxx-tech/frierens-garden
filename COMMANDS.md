# 🤖 ShadowHunter Telegram Bot - Command Guide

Complete reference for all Telegram commands and how they work.

---

## 📋 Command Overview

| Command | Purpose | Requires Helius | Frequency |
|---------|---------|-----------------|-----------|
| `/start` | Welcome & help | No | Once |
| `/help` | Show all commands | No | Anytime |
| `/monitor` | Continuous ecosystem monitoring | Recommended | Background |
| `/stop` | Stop monitoring | No | On demand |
| `/hunt` | One-time comprehensive hunt | Recommended | On demand |
| `/momentum` | Quick momentum scan | No | On demand |
| `/analyze` | Deep wallet analysis | **Yes** | On demand |
| `/alpha` | Show Stealth Hunt 2.0 wallets | No | On demand |
| `/status` | System & API status | No | Anytime |
| `/signals` | Recent alerts history | No | Anytime |

---

## 🔍 Detailed Command Reference

### `/start` - Welcome & Quick Actions

**What it does:**
- Displays welcome message with bot capabilities
- Shows quick-action buttons (Start Monitor, Hunt Now, View Alpha)
- Provides overview of all available commands

**When to use:**
- First time using the bot
- Need a refresher on available commands
- Want quick access to main features via buttons

**Example Output:**
```
🎯 ShadowHunter Alpha Finder v3.0

Zero-cost programmatic wallet hunting

🎮 Available Commands:

📊 Hunting:
/monitor - Start continuous ecosystem monitoring
/hunt - Run one-time comprehensive hunt
/momentum - Scan for high-momentum tokens now
/stop - Stop monitoring

[🔥 Start Monitoring] [🎯 Hunt Now] [📊 View Alpha Wallets]
```

---

### `/monitor` - Continuous Ecosystem Monitoring

**What it does:**
- Starts a background process that scans Solana ecosystem every 5 minutes
- Automatically detects high-momentum tokens (score >60)
- Sends instant alerts when significant momentum detected
- Tracks and stores all signals for later review

**How it works:**
1. Every 5 minutes, queries DexScreener for all Solana pairs
2. Filters for tokens with >$10K liquidity
3. Calculates momentum score for each token
4. If score >= 70, sends immediate Telegram alert
5. Stores signal in history for `/signals` command

**When to use:**
- You want real-time alerts on market movements
- You're actively trading and need instant notifications
- You want to catch pumps early

**Requirements:**
- Bot must remain running (use VPS for 24/7)
- Optional: Helius API key for enhanced analysis

**Example Alert Output:**
```
🚨 HIGH-MOMENTUM ALERT!

🎯 $MOONSHOT | Score: 89.2/100
💰 Price: $0.000042
📈 1h Change: +340.0%
💎 Market Cap: $420,000
💧 Liquidity: $87,000
⏰ Age: 2h 15m
📊 Volume (24h): $1,240,000

<token_address>

Use /analyze to check early buyers
```

**Stopping:**
- Use `/stop` to pause monitoring
- Use `/status` to check if monitoring is active

---

### `/stop` - Stop Monitoring

**What it does:**
- Gracefully stops the background monitoring process
- Preserves all captured signals
- Shows summary of monitoring session

**When to use:**
- Want to pause alerts temporarily
- Done trading for the day
- Need to conserve API quota

**Example Output:**
```
🛑 Monitoring STOPPED

• Total signals generated: 12
• Monitoring duration: 3h 45m
• High-momentum tokens detected: 3

Use /signals to see all captured signals
Use /monitor to resume
```

---

### `/hunt` - Comprehensive One-Time Hunt

**What it does:**
- Runs a complete analysis in 3 phases:
  1. **Phase 1:** Scan ecosystem for high-momentum tokens
  2. **Phase 2:** Analyze token details and metrics
  3. **Phase 3:** (If Helius key available) Analyze early buyers

**How it works:**
1. Queries DexScreener for top Solana pairs
2. Filters for liquidity >$50K
3. Calculates momentum scores
4. Ranks tokens by score
5. Generates detailed report with all metrics
6. If Helius configured, attempts wallet analysis

**When to use:**
- Want a comprehensive market overview now
- Don't need continuous alerts
- Checking market before making decisions
- Prefer manual scans over automated monitoring

**Duration:** 30-120 seconds depending on market activity

**Example Output:**
```
🎯 HUNT COMPLETE
Found 5 high-momentum tokens

1. $MOONSHOT | Score: 89.2/100
├ 💰 Price: $0.000042
├ 📈 1h: +340.0% | 5m: +45.0%
├ 💎 MC: $420,000 | 💧 Liq: $87,000
├ 📊 Vol: $1,240,000 | 🔄 Txns: 89 buys
├ ⏰ Age: 2h 15m
└ 🔗 <token_address>

2. $ROCKET | Score: 76.4/100
...

💡 Next Steps:
• Use /monitor for continuous tracking
• Use /analyze <wallet> to check specific wallets
• Use /alpha to see our premium wallet list
```

---

### `/momentum` - Quick Momentum Scan

**What it does:**
- Fast scan for high-momentum tokens only
- Shows top 5 tokens with highest momentum scores
- Provides quick market snapshot
- Includes interactive buttons for next actions

**Difference from /hunt:**
- Faster (10-20 seconds vs 30-120)
- Less detailed (top 5 only vs all)
- Shows action buttons for follow-up
- No wallet analysis phase

**When to use:**
- Quick market check
- Don't need full details
- Want to see if anything is happening right now

**Example Output:**
```
🚀 HIGH-MOMENTUM TOKENS DETECTED

1. $MOONSHOT | Score: 89.2/100
├ Price: $0.000042
├ Market Cap: $420,000
├ 1h Change: +340.0%
├ Volume: $1,240,000
├ Liquidity: $87,000
└ Age: 2h 15m

2. $ROCKET | Score: 76.4/100
...

...and 3 more tokens

💡 Use /hunt for full wallet analysis of these tokens

[🎯 Full Hunt] [📊 Monitor]
```

---

### `/analyze <wallet>` - Deep Wallet Analysis

**What it does:**
- Comprehensive analysis of a specific wallet
- Calculates 30-day performance metrics
- Determines win rate, profitability, trade frequency
- Assigns alpha score (0-100)
- Detects bot patterns
- Shows favorite tokens and trading patterns

**Requires:** Helius API key (free tier)

**How it works:**
1. Fetches last 100 transactions via Helius
2. Parses DEX swaps (Jupiter, Raydium, Pump.fun)
3. Calculates entry/exit prices
4. Determines PnL for each trade
5. Aggregates statistics
6. Scores wallet quality

**Parameters:**
- `<wallet>`: Solana wallet address (required)

**When to use:**
- Found an interesting wallet from /hunt or alerts
- Want to verify if a wallet is worth tracking
- Checking your own wallet performance
- Due diligence before copy-trading

**Example Usage:**
```
/analyze 4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6
```

**Example Output:**
```
🟢 WALLET ANALYSIS
<code>4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6</code>

📊 Performance (30D):
├ Alpha Score: 87.5/100
├ Total Trades: 156
├ Win Rate: 58.3%
├ Total PnL: 247.5 SOL
├ Avg Trade Size: 2.3 SOL
└ Quality: ✅ HIGH

👤 Behavior: Human-like trading

🎯 Favorite Tokens:
1. <code>7xK3m...P9zL2...</code>
2. <code>9nL2p...M4xK8...</code>
3. <code>2mP8x...K7nL3...</code>

Last active: 2 days ago
```

**Error Cases:**
- ❌ Invalid wallet address: "Please provide a valid Solana wallet address"
- ❌ No Helius key: "Wallet analysis requires a free Helius API key"
- ❌ Inactive wallet: "Could not fetch wallet data. The wallet may be inactive."

---

### `/alpha` - Stealth Hunt 2.0 Wallet List

**What it does:**
- Displays all 25+ wallets discovered during Stealth Hunt 2.0
- Organized by tier (Legendary, Tier 1, Tier 2)
- Shows profits, specialty, and source
- Wallets are copy-paste ready

**When to use:**
- Want our best discovered wallets
- Building a tracking list
- Looking for high-quality wallets to analyze
- Quick reference during trading

**Example Output:**
```
🎯 STEALTH HUNT 2.0 - DISCOVERED WALLETS

Premium wallets from 515K token research across 5 parallel agents

👑 LEGENDARY
• <code>G5nxEXuFMfV74DSnsrSatqCW32F34XUnBeq3PfDS7w5E</code>
  LeBron | $17.6M+
  MELANIA/LIBRA/TRUMP sniper

• <code>4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6</code>
  Nansen Smart Trader | $44.24M
  90D top performer

🤖👑 MEV_LEGENDARY
• <code>E6YoRP3adE5XYneSseLee15wJshDxCsmyD2WtLvAmfLi</code>
  E6Y Sandwich Bot | $300K/day
  42% sandwich market share

💎 TIER_1
• <code>HWdeCUjBvPP1HJ5oCJt7aNsvMWpWoDgiejUWvfFX6T7R</code>
  FARTCOIN Whale | $4.38M
  Memecoins, 73% win rate

...

💡 Usage:
Click any address to copy, then use:
/analyze <wallet> for deep analysis

Add these to your wallets.txt for live tracking

[🎯 Hunt All] [📊 Start Monitoring]
```

---

### `/status` - System Status

**What it does:**
- Shows current operational status
- Displays API configuration status
- Shows monitoring state
- Lists systems ready/available
- Shows captured signal count

**When to use:**
- Check if everything is working
- Verify API keys are configured
- See monitoring status
- Troubleshooting

**Example Output:**
```
⚙️ SHADOWHUNTER SYSTEM STATUS

APIs:
├ DexScreener: ✅ Unlimited
├ Jupiter: ✅ 600 req/min
└ Helius: ✅ Configured

Services:
├ Monitoring: 🟢 Active
├ Signals Captured: 12
└ Wallets Tracked: 25

Systems:
├ First Blood (Real-time): ✅ Ready
├ Shadow Network (Graph): ✅ Ready
└ Momentum Hunter (Signals): ✅ Active

💡 Tip: Use /stop to pause monitoring
```

---

### `/signals` - Recent Alert History

**What it does:**
- Shows history of all alerts generated
- Displays last 10 signals
- Includes timestamp, type, score, token
- Helps track market activity over time

**When to use:**
- Review what you missed while away
- Analyze alert patterns
- Check if alerts were accurate
- Historical market analysis

**Example Output:**
```
🔔 RECENT SIGNALS (12 total)

⏰ 14:32:15
🎯 HIGH_MOMENTUM
📊 Score: 89.2/100
<code>7xK3m...P9zL2...</code>

⏰ 14:27:03
🎯 HIGH_MOMENTUM
📊 Score: 76.4/100
<code>9nL2p...M4xK8...</code>

...
```

---

## 🎮 Workflows & Use Cases

### Workflow A: Intraday Trading
```
1. Morning: /momentum → Check overnight activity
2. See interesting token → /hunt → Deep analysis
3. Find good setup → /monitor → Get entry alerts
4. Trade active → Watch for /signals alerts
5. End of day → /stop → Review signals
```

### Workflow B: Research Mode
```
1. /alpha → Get premium wallet list
2. Copy wallet addresses
3. /analyze <wallet> → Check each wallet
4. Find high-scoring wallets → Add to tracking
5. /hunt → Cross-reference with market activity
```

### Workflow C: Passive Monitoring
```
1. Set up bot on VPS (24/7)
2. /monitor → Start continuous scanning
3. Wait for /signals alerts
4. When alert fires → Quick analysis
5. Take action or ignore
```

---

## ⚙️ Setup Requirements

### Minimum Setup (Free)
- Telegram bot token (from @BotFather)
- No API keys needed for basic functionality
- Can use: `/start`, `/help`, `/momentum`, `/alpha`, `/status`

### Full Setup (Still Free)
- Telegram bot token
- Helius API key (free tier, 10M credits/month)
- Enables: `/analyze`, enhanced `/hunt`, early buyer detection

### Configuration File (.env.hunter)
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
HELIUS_API_KEY=your_helius_key_here  # Optional but recommended
```

---

## 🐛 Troubleshooting

### "No high-momentum tokens detected"
- **Cause:** Market is slow, no significant pumps
- **Solution:** Try again in 30-60 minutes, or use /monitor to wait for activity

### "Wallet analysis requires Helius API key"
- **Cause:** HELIUS_API_KEY not set in .env.hunter
- **Solution:** Get free key at https://helius.xyz

### Bot not responding
- **Cause:** Bot stopped or crashed
- **Solution:** Restart with `python3 shadowhunter_bot.py`

### No alerts during /monitor
- **Cause:** Threshold too high (score >= 70 required)
- **Solution:** Normal during slow markets, lower threshold in config if needed

---

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| Scan speed | 100 tokens/minute |
| Alert latency | 5-10 seconds after detection |
| Memory usage | ~50MB |
| API cost | $0/month |
| Signal accuracy | ~70% (market dependent) |

---

## 🎯 Best Practices

1. **Always verify** before trading
2. **Start with paper trading** (test mode)
3. **Use small amounts** first
4. **Set stop losses** (memecoins volatile)
5. **Combine signals** (don't rely on single indicator)
6. **Monitor during active hours** (UTC 14:00-23:00 typically most active)

---

**Last Updated:** March 14, 2026
**Version:** 3.0
**Status:** Production Ready
