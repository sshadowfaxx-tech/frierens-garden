# Solana Wallet Analyzer Configuration

## Setup Instructions

### 1. Get a Helius API Key

1. Visit https://helius.xyz/
2. Sign up for an account
3. Create a new API key
4. Copy your API key

### 2. Set Environment Variable (Recommended)

```bash
export HELIUS_API_KEY="your_api_key_here"
```

Or add to your `.bashrc` or `.zshrc` for persistence.

### 3. Usage Examples

#### Analyze a single wallet:
```bash
python solana_wallet_analyzer.py --wallets 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
```

#### Analyze multiple wallets:
```bash
python solana_wallet_analyzer.py --wallets WALLET1 WALLET2 WALLET3
```

#### Load wallets from file:
```bash
python solana_wallet_analyzer.py --wallet-file wallets.txt
```

#### Analyze last 30 days only:
```bash
python solana_wallet_analyzer.py --wallets WALLET1 --days-back 30
```

#### Output as JSON:
```bash
python solana_wallet_analyzer.py --wallets WALLET1 --output json --output-file results.json
```

#### Output as CSV for spreadsheet analysis:
```bash
python solana_wallet_analyzer.py --wallet-file wallets.txt --output csv --output-file results.csv
```

### 4. Wallet File Format

Create a file `wallets.txt`:
```
# Comments start with #
7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
8ZxKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsV
9YxKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsW
```

## Rate Limits

Helius API has rate limits based on your plan:
- Free: 10 requests/second
- Developer: 50 requests/second
- Business: 200+ requests/second

The script includes automatic retry logic with exponential backoff.

## Supported DEXes

Currently supported decentralized exchanges:
- Jupiter (JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4)
- Raydium AMM (675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8)
- Raydium CLMM (CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK)

## Understanding the Output

### Key Metrics

- **Total PnL**: Realized profit/loss in SOL
- **Total ROI**: Return on investment percentage
- **Win Rate**: Percentage of profitable trades
- **Early Bird Count**: Number of early token purchases (first 10 blocks)
- **Early Bird Success Rate**: Win rate on early purchases
- **Repeat Winner**: Wallet with consistent profits (>60% win rate, 3+ wins)
- **Consistency Score**: Combined metric of win rate, volume, and ROI

### Ranking Algorithm

Wallets are ranked using a weighted score:
- Total PnL: 30%
- ROI: 25%
- Win Rate: 20%
- Consistency Score: 15%
- Early Bird Success: 10%

## Extending the Script

### Adding New DEX Support

Edit the `DEX_PROGRAMS` dictionary in `TransactionParser`:

```python
DEX_PROGRAMS = {
    Config.JUPITER_PROGRAM_ID: DEXType.JUPITER,
    Config.RAYDIUM_PROGRAM_ID: DEXType.RAYDIUM,
    "NEW_PROGRAM_ID": DEXType.NEW_DEX,
}
```

### Custom Analysis

Create a new method in `ProfitabilityAnalyzer`:

```python
def analyze_custom_pattern(self, analysis: WalletAnalysis):
    # Your custom pattern detection logic
    pass
```

### Output Formats

Add new formatters in `OutputFormatter`:

```python
@staticmethod
def format_html(analyses: List[WalletAnalysis]) -> str:
    # Generate HTML report
    pass
```

## Troubleshooting

### "No transactions found"
- Verify the wallet address is correct
- Check if the wallet has recent activity
- Try increasing `--days-back` or removing the limit

### API rate limit errors
- Reduce `--parallel` workers
- Upgrade your Helius plan
- Add delays between requests

### Missing token data
- Some tokens may not have proper metadata
- The script uses default decimals (6 for tokens, 9 for SOL)

## Dependencies

```bash
pip install requests python-dotenv
```

## Security Notes

- Never commit your API key to version control
- Use environment variables for sensitive data
- The script only reads transaction data, never executes transactions
