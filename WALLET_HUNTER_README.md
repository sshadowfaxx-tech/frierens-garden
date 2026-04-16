# Smart Money Wallet Hunter

A script to discover and analyze profitable Solana wallets for copy-trading research.

## Quick Start

### 1. Set API Keys (Required)

```bash
export HELIUS_API_KEY="your_helius_key_here"
export BIRDEYE_API_KEY="your_birdeye_key_here"  # Optional
```

### 2. Run the Hunter

**Basic hunt (default settings):**
```bash
python3 wallet_hunter.py
```

**Hunt from a specific token:**
```bash
python3 wallet_hunter.py --seed 4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R
```

**Custom filters:**
```bash
python3 wallet_hunter.py \
  --seed YOUR_TOKEN_ADDRESS \
  --min-win-rate 0.6 \
  --min-trades 10 \
  --top 20 \
  --output my_wallets.json
```

## How It Works

1. **Discovery Phase**: Finds wallets that traded a given token
2. **Analysis Phase**: Fetches transaction history for each wallet
3. **Scoring Phase**: Calculates profitability metrics
4. **Filtering**: Returns wallets meeting your criteria

## Metrics Calculated

- **Win Rate**: % of profitable trades
- **Total Trades**: Activity level
- **Profit Factor**: Wins/Losses ratio
- **Composite Score**: Combined ranking metric
- **PnL Estimate**: Approximate profit/loss in SOL

## Limitations

- **PnL is estimated** - True PnL requires historical price data at trade time
- **Rate limits apply** - Helius free tier has limits
- **Analysis depth** - Limited to ~20 wallets per run (respects API limits)

## Requirements

```bash
pip install aiohttp
```

## Output Format

```json
{
  "timestamp": "2026-03-12T12:00:00",
  "seed_token": "...",
  "profitable_wallets": [
    {
      "address": "ABC123...",
      "score": 85.5,
      "win_rate": 72.3,
      "total_trades": 15,
      "estimated_pnl_sol": 45.2
    }
  ]
}
```

## API Keys

### Helius (Required)
- Sign up: https://www.helius.dev/
- Free tier: 1M credits/month
- No credit card required

### Birdeye (Optional)
- Sign up: https://birdeye.so/
- Free tier: 30K CU/month
- Better for token metadata

## Tips for Better Results

1. **Start with hot tokens** - Use recently successful memecoins as seeds
2. **Adjust filters gradually** - Start loose, tighten based on results
3. **Cross-reference** - Verify wallets on solscan.fm before following
4. **Check recency** - Ensure wallets are still active

## Disclaimer

This tool is for **research purposes only**. 
- Past performance ≠ future results
- DYOR before copy-trading any wallet
- Never invest more than you can afford to lose
