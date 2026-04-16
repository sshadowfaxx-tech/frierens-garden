# Autonomous Trading Agent Setup

## Overview
I will monitor tracker alerts directly and make autonomous trading decisions.

## Required Setup

### 1. Telegram Channel Access
I need to receive tracker alerts. Options:

**Option A: Dedicated Agent Channel (Recommended)**
- Create a new Telegram channel
- Add my bot (@shadowhuntermvpbot) as admin
- Configure tracker to forward alerts to this channel
- I will read alerts and respond with trades

**Option B: Existing Channel**
- Add my bot to existing tracker alert channel
- I'll monitor and trade from there

### 2. Add to .env
```bash
# My trading channel
CHANNEL_AGENT_TRADES=-100XXXXXXXXXX

# Which alerts to act on
AGENT_MODE=autonomous  # autonomous | assisted | passive
AGENT_RISK_LEVEL=medium  # conservative | medium | aggressive
AGENT_MAX_POSITIONS=5
AGENT_POSITION_SIZE=0.1  # 10% of balance per trade
```

### 3. Decision Framework

I will use this decision matrix:

| Signal Strength | Wallet Count | Action | Position Size |
|----------------|--------------|--------|---------------|
| Weak | 2-3 | Watch only | 0% |
| Medium | 4-5 | Buy small | 5% |
| Strong | 6-10 | Buy medium | 10% |
| Extreme | 10+ | Buy large | 15% |

### 4. Learning System

I will track:
- Which wallet clusters lead to wins
- Optimal entry timing after cluster forms
- Best take profit levels
- Stop loss effectiveness
- Market cap thresholds

This data goes into `memory/agent_trading.md` for me to reference.

## My Trading Rules

**Entry Criteria:**
1. Minimum 4 wallets in cluster
2. Entry MC < $5M (avoid pumped tokens)
3. No more than 5 positions open
4. Minimum 0.05 SOL per trade

**Exit Criteria:**
1. Take profit: +100%, +300%, +500%
2. Stop loss: -40%
3. Time stop: Exit if flat after 24h

**Risk Management:**
- Never risk more than 20% of portfolio on one token
- Cut losses quickly
- Let winners run

## How It Works

1. **Tracker detects cluster** → Sends Telegram alert
2. **I receive alert** → Parse signal strength
3. **I make decision** → Buy/Sell/Watch
4. **I execute paper trade** → Update portfolio
5. **I report trade** → Send confirmation to you
6. **I track outcome** → Update learning memory

## My Learning Loop

After each trade closes, I will:
1. Analyze what worked/didn't work
2. Update my strategy rules
3. Document in memory file
4. Apply learnings to next trade

## Your Oversight

You can:
- View all trades in real-time
- Stop me anytime with `/agent stop`
- Adjust risk parameters
- Review my learning notes

## Questions for You

1. **Which Telegram channel** should I monitor? (give me channel ID)
2. **Initial paper balance?** (recommend 1-5 SOL)
3. **Risk tolerance?** (conservative/medium/aggressive)
4. **Should I report every trade or just summary?**
5. **Any wallets to exclude from my signals?**

Once you provide the channel ID, I'll start monitoring and trading autonomously.
