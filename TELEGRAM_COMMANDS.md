# 🤖 ShadowHunter Telegram Bot - Command Guide v3.0

Complete reference for all commands in your integrated scanner + momentum hunter.

---

## 📋 Command Overview

| Command | Purpose | Requires API Key | Response Time |
|---------|---------|------------------|---------------|
| `/scan <pair>` | Analyze early buyers | DexCheck (free) | 10-30s |
| `/momentum` | Quick momentum scan | None | 5-10s |
| `/hunt` | Comprehensive hunt | None | 10-20s |
| `/alpha` | Show discovered wallets | None | Instant |
| `/status` | System status | None | Instant |
| `/help` | Show all commands | None | Instant |

---

## 🔍 Detailed Command Reference

### `/scan <pair_address>` - Early Buyer Analysis

**What it does:**
Your original scanner function - analyzes a specific token pair for early buyers and insider activity.

**Parameters:**
- `pair_address` (required): The Solana pair address to analyze

**How it works:**
1. Fetches token info from DexScreener
2. Gets early birds from DexCheck (first 100 buyers)
3. Gets top traders from DexCheck (highest PnL)
4. Finds overlaps (wallets in both lists)
5. Calculates insider scores (0-100)
6. Detects hidden exits (if Helius configured)
7. Ranks wallets by conviction

**Example:**
```
/scan 7xK3m...P9zL2...
```

**Example Output:**
```
🔎 SHADOWHUNTER SCAN

💎 MoonShotToken ($MOON)
📍 Pair: 7xK3m...P9zL2...
💰 Market Cap: $420K
💵 Price: $0.000042
⏰ 2026-03-14 14:30

🐣 TOP INSIDER WALLETS (Dual Source)
Filters: ROI > 100% | PnL ≥ $20 USD
⭐ Overlaps: 3 wallets

🚀 #1 | 7xK3m...P9zL2...
   🎯 Score: 87/100 🟠 HIGH
   💰 PnL: $2,450 | ROI: 580%
   📊 Trades: 3B/0S | 💎 HOLDING
   📡 🔥 DUAL SOURCE

⭐ #2 | 9nL2p...M4xK8...
...

📊 SUMMARY
• Token: MoonShotToken ($MOON)
• Wallets: 15
• ⭐ Dual Source: 3
• 🔴 Critical: 2 | 🟠 High: 5 | 🟡 Medium: 8
```

---

### `/momentum` - Quick Market Scan

**What it does:**
Scans all Solana tokens and identifies those with high momentum (price change + volume).

**How it works:**
1. Queries DexScreener for top Solana pairs
2. Filters for >$10K liquidity
3. Calculates momentum score:
   - Price change 1h × 2 (max 50 points)
   - Volume / 10K (max 50 points)
4. Shows top 5 highest scoring tokens

**When to use:**
- Quick market check
- Find hot tokens without specifying a pair
- Discover new opportunities

**Example Output:**
```
🚀 HIGH-MOMENTUM TOKENS DETECTED

1. $MOONSHOT | Score: 89.2/100
├ Price: $0.00004200
├ 1h Change: +340.0%
├ Volume: $1,240,000
├ Liquidity: $87,000
└ /scan 7xK3m...P9zL2...

2. $ROCKET | Score: 76.4/100
├ Price: $0.00001500
├ 1h Change: +180.0%
...
```

**Next step:** Click the `/scan` link for any token to analyze its early buyers.

---

### `/hunt` - Comprehensive Hunt

**What it does:**
Full ecosystem scan combining momentum detection + analysis. Similar to `/momentum` but more detailed.

**How it works:**
Same as `/momentum` but:
- Shows more details (liquidity, volume, price)
- Provides next-step guidance
- Formatted as a complete hunt report

**When to use:**
- Want a comprehensive market overview
- Prefer detailed output over quick scan
- Building a watchlist

**Example Output:**
```
🎯 HUNT COMPLETE
Found 5 high-momentum tokens

1. $MOONSHOT | Score: 89.2/100
├ 💰 Price: $0.00004200
├ 📈 1h: +340.0%
├ 💧 Liquidity: $87,000
├ 📊 Volume: $1,240,000
└ 🔗 /scan 7xK3m...P9zL2...

2. $ROCKET | Score: 76.4/100
...

💡 Next Steps:
• Use `/scan <pair>` for full early buyer analysis
• Use `/alpha` to see our premium wallet list
• Use `/momentum` for quick updates
```

---

### `/alpha` - Stealth Hunt 2.0 Wallets

**What it does:**
Displays all wallets discovered during Stealth Hunt 2.0 (515K token research).

**Wallets included:**
- **Legendary tier**: LeBron ($17.6M), Nansen Smart Trader ($44.24M)
- **MEV tier**: E6Y Sandwich Bot ($300K/day)
- **Tier 1**: FARTCOIN Whale, TRUMP Millionaire
- **Tier 2**: RIF Sniper, AI16Z Leader

**When to use:**
- Want our best discovered wallets
- Building tracking lists
- Looking for high-quality targets

**Example Output:**
```
🎯 STEALTH HUNT 2.0 - DISCOVERED WALLETS

Premium wallets from 515K token research across 5 parallel agents

👑 LEGENDARY
• G5nxEXuFMfV74DSnsrSatqCW32F34XUnBeq3PfDS7w5E
  LeBron | $17.6M+
  MELANIA/LIBRA/TRUMP sniper

• 4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6
  Nansen Smart Trader | $44.24M
  90D top performer

🤖👑 MEV_LEGENDARY
• E6YoRP3adE5XYneSseLee15wJshDxCsmyD2WtLvAmfLi
  E6Y Sandwich Bot | $300K/day
  42% sandwich market share

💎 TIER_1
• HWdeCUjBvPP1HJ5oCJt7aNsvMWpWoDgiejUWvfFX6T7R
  FARTCOIN Whale | $4.38M
  Memecoins, 73% win rate

...

💡 Usage: Click any address to copy
Add these to wallets.txt for live tracking
```

**Using these wallets:**
1. Click an address in Telegram to copy it
2. Add to your `wallets.txt` file for the tracker
3. Or use with other tools (Bubblemaps, Nansen, etc.)

---

### `/status` - System Status

**What it does:**
Shows current operational status of all systems and APIs.

**Example Output:**
```
⚙️ SHADOWHUNTER SYSTEM STATUS

APIs:
├ DexScreener: ✅ Unlimited
├ DexCheck: ✅
└ Helius: ✅

Systems:
├ Scanner (/scan): ✅ Active
├ Momentum Hunter (/momentum): ✅ Ready
├ Full Hunt (/hunt): ✅ Ready
├ Alpha List (/alpha): ✅ Ready
└ Hidden Exits: ✅

Wallets Tracked: 7 from Stealth Hunt 2.0

💡 Tip: Use `/momentum` to scan for hot tokens
```

**When to use:**
- Troubleshooting
- Verify APIs are working
- Check configuration

---

### `/help` - Command Help

**What it does:**
Shows all available commands and quick start guide.

**Example Output:**
```
🎯 ShadowHunter Scanner v3.0

📊 Hunting Commands:
/momentum - Quick scan for high-momentum tokens
/hunt - Comprehensive hunt with full analysis
/scan <pair_address> - Analyze token early buyers

🔍 Analysis Commands:
/alpha - Show Stealth Hunt 2.0 wallet list
/status - System status and API configuration

💡 Quick Start:
1. Type /momentum to see hot tokens now
2. Find interesting token → /scan <pair_address>
3. Get early buyer analysis with insider scoring
4. Check /alpha for our premium wallet list

Zero cost using free APIs only
```

---

## 🎮 Workflows

### Workflow 1: Find New Tokens
```
1. Type: /momentum
2. See hot tokens in output
3. Click /scan link for interesting token
4. Review early buyer analysis
5. Add high-conviction wallets to tracking
```

### Workflow 2: Research Specific Token
```
1. Get pair address from DexScreener
2. Type: /scan <pair_address>
3. Review early buyer list
4. Look for ⭐ DUAL SOURCE wallets
5. Copy wallet addresses for further analysis
```

### Workflow 3: Build Wallet List
```
1. Type: /alpha
2. Review tier list
3. Click addresses to copy
4. Add to wallets.txt
5. Use with tracker for live monitoring
```

---

## 💡 Tips

1. **Use `/momentum` frequently** - Market changes fast
2. **Focus on DUAL SOURCE wallets** - In both early birds AND top traders
3. **Check scores >60** - High conviction indicator
4. **Watch for hidden exits** - 🥷 emoji indicates potential manipulation
5. **Combine with tracker** - Add discovered wallets to wallets.txt

---

## 🔧 Configuration

### Required (Free)
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `DEXCHECK_API_KEY` - Free tier works

### Optional (Enhanced Features)
- `HELIUS_API_KEY` - Enables hidden exit detection
- `CHANNEL_SCANNER` - Channel for startup notifications

### Environment File
```bash
# .env file
TELEGRAM_BOT_TOKEN=your_bot_token
DEXCHECK_API_KEY=BostDZLJBBPu44iXpiOneGprXhTpSFCg
HELIUS_API_KEY=your_helius_key  # Optional
CHANNEL_SCANNER=@your_channel  # Optional
```

---

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| `/scan` time | 10-30 seconds |
| `/momentum` time | 5-10 seconds |
| `/alpha` time | Instant |
| API cost | $0/month |
| Momentum detection | ~70% accuracy |
| Signal quality | High during active markets |

---

## 🚨 Troubleshooting

### "No high-momentum tokens detected"
- Market is slow - normal during off-peak hours
- Try again in 30-60 minutes
- Use `/scan` on specific tokens you're watching

### "Failed to fetch market data"
- DexScreener API temporarily down
- Wait 1-2 minutes and retry
- Check `/status` for API health

### Commands not working
- Ensure bot is running: `docker ps`
- Check logs: `docker logs shadowhunter-tracker`
- Verify token hasn't expired

---

**Version:** 3.0  
**Last Updated:** March 14, 2026  
**Status:** Production Ready
