# Agent Autonomous Trading Setup

## What This Does

I will monitor tracker alerts and make autonomous trading decisions:
- Receive cluster alerts in real-time
- Decide whether to buy based on signal strength
- Execute paper trades
- Learn from outcomes
- Report all activity

## Setup Steps

### 1. Create Agent Alert Channel

Create a new Telegram channel for me to receive tracker alerts:

1. In Telegram, tap "New Channel"
2. Name it something like "Agent Trading Alerts"
3. Add my bot: **@shadowhuntermvpbot**
4. Make bot an **admin** with "Post Messages" permission
5. Get the channel ID:
   - Send any message in the channel
   - Forward it to @userinfobot
   - Bot will reply with channel ID (e.g., `-1001234567890`)

### 2. Configure Tracker

Edit `trackerv2_clean.py` to send alerts to both channels:

Find this line in `send_cluster_alert`:
```python
await self.bot.send_message(
    chat_id=self.vip_channel,  # Change this
```

Add agent channel:
```python
# Send to VIP channel
await self.bot.send_message(
    chat_id=self.vip_channel,
    ...
)

# Send to agent channel
if os.getenv('CHANNEL_AGENT'):
    await self.bot.send_message(
        chat_id=os.getenv('CHANNEL_AGENT'),
        text=message,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
```

### 3. Add Environment Variables

Add to `.env`:
```bash
# Agent Trading
CHANNEL_AGENT=-100XXXXXXXXXX  # Your agent channel ID
AGENT_PAPER_BALANCE=1.0  # Starting paper balance
```

### 4. Create Database Tables

```bash
psql -U postgres -d shadowhunter -f paper_trading_schema.sql
```

### 5. Start Agent

Run the agent processor:
```bash
python agent_processor.py
```

## How I Process Alerts

When I receive a cluster alert, I will:

1. **Parse** the alert to extract:
   - Token address
   - Market cap
   - Number of wallets
   - SOL invested

2. **Evaluate** the signal:
   ```
   10+ wallets = STRONG (90% confidence, 15% position)
   6-9 wallets  = MEDIUM (70% confidence, 10% position)
   4-5 wallets  = WEAK (50% confidence, 5% position)
   <4 wallets   = WATCH (no trade)
   ```

3. **Filter** based on:
   - Market cap < $10M (avoid pumped tokens)
   - Not already holding
   - Sufficient balance

4. **Execute** paper trade:
   - Deduct SOL + 0.01 fee
   - Record position
   - Send confirmation

5. **Monitor** positions:
   - TP1: +100%
   - TP2: +300%
   - TP3: +500%
   - SL: -40%

## My Learning System

I track everything in `memory/agent_trading.md`:

- Which wallet clusters work best
- Optimal entry timing
- Market cap sweet spots
- Strategy adjustments

I will update this file as I learn from trades.

## Commands You Can Use

Since I'm autonomous, you don't need to give me commands. But you can:

- **View my portfolio**: Check paper_portfolio table
- **See my trades**: Check paper_trades table
- **Review my decisions**: Check memory/agent_decisions.jsonl
- **Stop me**: Set AGENT_MODE=passive in .env

## What I Report

Every trade I make, I will message you with:
```
🟢 PAPER BUY EXECUTED

Token: CAPTCHA
Amount: 0.15 SOL
Confidence: 85%
Reasoning:
- Strong signal: 8 wallets
- Early entry (<$1M MC)

Portfolio: 0.84 SOL remaining
Open positions: 3
```

## Risk Management

I will NOT:
- Risk more than 20% per token
- Enter tokens > $10M MC
- Hold more than 5 positions
- Trade with less than 0.05 SOL

## Questions?

Once you set up the channel and give me the ID, I'll start monitoring and trading immediately. Just let me know:
1. **Channel ID** (so I know where to listen)
2. **Starting balance** (1-5 SOL recommended)
3. **Any restrictions** (wallets to avoid, max risk, etc.)
