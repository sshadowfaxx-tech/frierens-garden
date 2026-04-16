# Paper Trading Bot Setup

Autonomous paper trading system for ShadowHunter.

## Features

- Starts with **1 SOL paper balance**
- **0.01 SOL fee** per trade (simulates real gas costs)
- **Autonomous decisions** based on wallet cluster signals
- **Telegram alerts** for every trade
- Tracks portfolio, PnL, winrate

## Setup Instructions

### 1. Create Database Tables

Run the schema file:
```bash
psql -U postgres -d shadowhunter -f paper_trading_schema.sql
```

Or if using Windows:
```cmd
psql -U postgres -d shadowhunter -f paper_trading_schema.sql
```

### 2. Add Environment Variables

Add to your `.env` file:
```bash
# Paper Trading Settings
CHANNEL_PAPER_TRADES=-1001234567890  # Your Telegram channel ID for paper trade alerts
```

To get your channel ID:
1. Add @userinfobot to your channel
2. Send any message in the channel
3. The bot will reply with the channel ID (including the `-`)

### 3. Run the Paper Trader

```bash
python paper_trader.py
```

## Trading Strategy

The bot operates autonomously with these rules:

### Entry (BUY)
- Triggers when **3+ tracked wallets** enter a token cluster
- Invests **1-20% of balance** based on conviction (wallet count)
- **Min:** 0.05 SOL, **Max:** 0.5 SOL per trade
- **Max positions:** 5 concurrent holdings
- Skips if market cap > $10M (already pumped)
- **Fee:** 0.01 SOL deducted per buy

### Exit (SELL)
- **Take Profit:** 2x, 5x, 10x price targets
- **Stop Loss:** -50%
- **Fee:** 0.01 SOL deducted per sell

### Monitoring
- Checks for opportunities every 30 seconds
- Updates position prices every 30 seconds
- Sends portfolio summary every 5 minutes
- Saves state to database (survives restarts)

## Commands

No Telegram commands - the bot is fully autonomous. It will:
- Buy when it detects strong wallet clusters
- Sell when targets or stops are hit
- Alert you of every action

## Reset

To reset the paper portfolio (start fresh with 1 SOL):
```bash
psql -U postgres -d shadowhunter -c "UPDATE paper_portfolio SET data = '{\"sol_balance\": 1.0, \"total_trades\": 0, \"winning_trades\": 0, \"losing_trades\": 0, \"total_fees_paid\": 0, \"realized_pnl\": 0}' WHERE id = 1;"
```

## Logs

Watch the bot in action:
```bash
tail -f logs/paper_trader.log
```

Or on Windows:
```cmd
python paper_trader.py > paper_trader.log 2>&1
type paper_trader.log
```

## Alert Format

Every trade sends a Telegram alert like:

```
🟢 PAPER TRADE: BUY

*CAPTCHA*
`FtSRgyCEhKTc1PPgEAXvuHN3NyiP6LS9uyB28KCN3CAP`

💰 Amount: `0.15` SOL
🪙 Tokens: `12345.67`
📊 Price: `$0.00001234`
💎 Market Cap: `$250.5K`
💸 Fee: `0.01` SOL
📝 Cluster of 5 wallets

💼 Portfolio: `0.84` SOL
📈 Winrate: `66.7%` (2W/1L)
📊 Total PnL: `+0.23` SOL

[📊 DexScreener] [⚡ Photon]
```

## Customization

Edit these variables in `paper_trader.py`:

```python
self.max_positions = 5          # Max concurrent positions
self.min_signal_strength = 3    # Min wallets to trigger buy
self.take_profit_levels = [2.0, 5.0, 10.0]  # TP levels
self.stop_loss = -0.50          # -50% stop loss
```

## Next Steps

Once the paper trader proves profitable over a period of time, we can:
1. Increase paper balance to test with larger amounts
2. Add more sophisticated position sizing
3. Eventually connect to a real wallet for live trading
