# 🤖 ShadowHunter Auto-Hunter
## Continuous Momentum Detection + Automatic Scanning

This system continuously monitors the Solana ecosystem for high-momentum tokens and **automatically scans them** for early buyer analysis.

---

## 🎯 What It Does

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Every X mins   │────→│  Check momentum │────→│  Score > 60?    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                YES                      ▼
                               ┌──────────────────────────────────┐
                               │  1. Send Telegram alert          │
                               │  2. Auto-scan early buyers       │
                               │  3. Send scan results            │
                               │  4. Save to report               │
                               └──────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Run Locally
```bash
cd /root/.openclaw/workspace
./start_auto_hunter.sh
```

### Option 2: Run with Custom Settings
```bash
# Check every 3 minutes, alert on score > 50
python3 auto_hunter.py --interval 3 --threshold 50
```

### Option 3: Run Once (Testing)
```bash
python3 auto_hunter.py --once --threshold 60
```

---

## 📊 How It Works

### 1. Momentum Detection
- Queries DexScreener every X minutes
- Calculates momentum score for each token:
  ```
  score = (price_change_1h × 2) + (volume_24h / 10,000)
  max score = 100
  ```
- Filters tokens with score ≥ threshold (default: 60)

### 2. Duplicate Prevention
- Tracks recently analyzed tokens (4-hour cooldown)
- Avoids spamming same token repeatedly
- Auto-cleans tracking after 24 hours

### 3. Auto-Scanning
When high-momentum token detected:
1. **Sends momentum alert** to Telegram
2. **Fetches early buyers** from DexCheck
3. **Filters quality wallets** (ROI > 100%, PnL ≥ $20)
4. **Sends scan report** with top early birds
5. **Saves to JSON report** for history

---

## 🔔 Alert Format

### Momentum Alert
```
🚨 HIGH-MOMENTUM TOKEN DETECTED!

🎯 $MOONSHOT | Score: 89.2/100
💰 Price: $0.00004200
📈 1h Change: +340.0%
📊 5m Change: +45.0%
💎 Market Cap: $420K
💧 Liquidity: $87K
📊 Volume 24h: $1.24M
⏰ Age: 2h 15m

🔗 Pair: 7xK3m...P9zL2

🔍 Auto-scanning for early buyers...
```

### Scan Report (Auto-generated)
```
🔎 EARLY BUYER ANALYSIS: $MOONSHOT

📊 Found 8 high-quality early buyers
Filters: ROI > 100% | PnL ≥ $20 USD

🐣 TOP EARLY BIRDS:

🚀 #1 7xK3m...P9zL2
   💰 PnL: $2,450 | ROI: 580%
   📊 💎 HOLDING

📈 #2 9nL2p...M4xK8
   💰 PnL: $1,890 | ROI: 420%
   📊 💎 HOLDING

💡 Use /scan 7xK3m...P9zL2 for full analysis
```

---

## ⚙️ Configuration

### Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token

# Optional (but recommended)
CHANNEL_ALERTS=@your_channel    # Where to send alerts
DEXCHECK_API_KEY=your_key       # For early buyer scanning
HELIUS_API_KEY=your_key         # For hidden exit detection
```

### Command Line Options
```bash
python3 auto_hunter.py [options]

Options:
  --interval, -i    Minutes between scans (default: 5)
  --threshold, -t   Momentum score threshold (default: 60)
  --once, -o        Run once and exit (for testing)
```

### Recommended Settings

| Market Condition | Interval | Threshold | Use Case |
|------------------|----------|-----------|----------|
| Active/Bull      | 3 min    | 70        | Catch pumps early |
| Normal           | 5 min    | 60        | Balanced |
| Slow/Bear        | 10 min   | 50        | Reduce noise |
| Testing          | N/A      | 40        | See more tokens |

---

## 📁 Output Files

### JSON Report
File: `auto_hunt_report_YYYYMMDD.json`

```json
{
  "timestamp": "2026-03-15T04:14:50",
  "total_scans": 144,
  "total_hits": 12,
  "signals": [
    {
      "timestamp": "2026-03-15T04:14:50",
      "symbol": "MOONSHOT",
      "pair": "7xK3m...",
      "score": 89.2,
      "early_birds": 8,
      "price_change": 340.0
    }
  ]
}
```

---

## 🐳 Docker Integration

### Add to docker-compose.yml
```yaml
version: '3.8'

services:
  tracker:
    # ... your existing tracker config
    
  auto-hunter:
    build: .
    container_name: shadowhunter-auto
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - CHANNEL_ALERTS=${CHANNEL_ALERTS}
      - DEXCHECK_API_KEY=${DEXCHECK_API_KEY}
      - HELIUS_API_KEY=${HELIUS_API_KEY}
    command: python3 auto_hunter.py --interval 5 --threshold 60
    restart: unless-stopped
    volumes:
      - ./reports:/app/reports
```

### Or run manually in container
```bash
docker exec -it shadowhunter-tracker python3 auto_hunter.py --interval 5
```

---

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| Scan frequency | Every 3-10 minutes |
| API cost | $0/month |
| Detection latency | 3-10 minutes after pump starts |
| False positive rate | ~20% (market dependent) |
| Memory usage | ~30MB |
| CPU usage | Low |

---

## 🎯 Workflow Example

```bash
# Terminal 1: Start auto-hunter
./start_auto_hunter.sh

# Terminal 2: Watch logs
docker logs -f shadowhunter-auto

# Terminal 3: Monitor Telegram alerts
# (In your Telegram channel)

# Later: Check report
cat auto_hunt_report_20260315.json | jq '.signals'
```

---

## 🔧 Troubleshooting

### "No high-momentum tokens detected"
- Market is slow - normal during off-peak hours
- Lower threshold: `--threshold 40`
- Check during peak hours (UTC 14:00-23:00)

### "Telegram alerts not sending"
- Verify `TELEGRAM_BOT_TOKEN` is set
- Verify `CHANNEL_ALERTS` is correct
- Check bot has permissions in channel

### "DexCheck API errors"
- API key may be rate limited
- Free tier has limits
- Wait a few minutes and retry

### "Too many alerts"
- Increase threshold: `--threshold 70`
- Increase interval: `--interval 10`
- This reduces noise in slow markets

---

## 💡 Pro Tips

1. **Start with `--once` flag** to test configuration
2. **Use `--threshold 50`** during bear markets
3. **Use `--threshold 70`** during bull markets
4. **Check reports daily** to analyze hit rate
5. **Combine with tracker** for full pipeline

---

## 🔄 Full Automation Pipeline

```
Auto-Hunter              Tracker              You
     |                       |                 |
     ├─ Detects momentum ────┤                 |
     ├─ Sends alert ─────────┼────────────────►|
     │                       |                 |
     ├─ Auto-scans ──────────┤                 |
     │   finds wallets       |                 |
     ├─ Sends wallets ───────┼────────────────►|
     │                       |                 |
     │                       ├─ Monitors wallets|
     │                       │  live activity   |
     │                       ├─ Sends cluster   |
     │                       │  alerts ────────►|
```

---

## 📈 Success Metrics

After running for 24 hours, check:
```bash
# Total scans
python3 -c "import json; d=json.load(open('auto_hunt_report_20260315.json')); print(f\"Scans: {d['total_scans']}, Hits: {d['total_hits']}\")"

# Hit rate
# Good: 5-15% hit rate (5-15 high-momentum tokens per 100 scans)
# Excellent: >20% hit rate
```

---

**Version:** 1.0  
**Last Updated:** March 15, 2026  
**Status:** Production Ready
