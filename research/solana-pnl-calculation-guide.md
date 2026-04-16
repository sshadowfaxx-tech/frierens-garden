# Solana Wallet PnL & Winrate Calculation Guide

## Executive Summary

This guide covers the complete methodology for calculating Profit and Loss (PnL) and winrate from raw Solana transaction data, including cost basis tracking, handling complex trade scenarios, and implementation code examples.

---

## 1. Formula for Calculating Realized PnL from Buy/Sell Transactions

### Basic PnL Formula

**Realized PnL = Proceeds from Sale - Cost Basis of Tokens Sold**

Where:
- **Proceeds** = Amount received from selling (in USD or SOL terms)
- **Cost Basis** = Original purchase price of the tokens being sold

### Example Calculation

```
Buy 1 SOL at $100
Buy 1 SOL at $120
Sell 1 SOL at $150

Using FIFO (see section 3):
Cost Basis = $100 (first purchase)
Proceeds = $150
Realized PnL = $150 - $100 = $50 profit
```

### Multi-Token PnL Formula

**Total Realized PnL = Σ (Sell Price × Quantity Sold) - Σ (Cost Basis × Quantity Sold)**

---

## 2. How to Determine Winrate

### Winrate Formula

```
Winrate (%) = (Number of Profitable Trades / Total Number of Closed Trades) × 100
```

### Key Definitions

- **Profitable Trade**: Any closed position where Realized PnL > 0
- **Losing Trade**: Any closed position where Realized PnL < 0
- **Breakeven Trade**: Realized PnL = 0 (typically excluded or counted separately)
- **Closed Trade**: A complete round-trip (buy + sell) for a token position

### Example

```
Total Trades: 100
Profitable Trades: 55
Losing Trades: 42
Breakeven Trades: 3

Winrate = (55 / 100) × 100 = 55%
```

### Important Considerations

1. **Winrate Alone Is Misleading**: A 90% winrate with small gains and large losses can be unprofitable
2. **Risk-Reward Ratio**: Combine winrate with average profit/loss per trade
3. **Expectancy**: (Win% × Avg Win) - (Loss% × Avg Loss) = Expected value per trade

---

## 3. How to Track Token Cost Basis for PnL Calculation

### Cost Basis Methods

#### 3.1 FIFO (First-In, First-Out) - Most Common
- Assumes oldest purchased tokens are sold first
- Required by IRS (US) for 2026+ tax reporting
- Matches physical inventory logic

**Example:**
```
Buy 100 TOKEN_A at $1.00 (Batch 1)
Buy 50 TOKEN_A at $1.50 (Batch 2)
Sell 75 TOKEN_A at $2.00

FIFO Cost Basis:
- 75 from Batch 1 @ $1.00 = $75
Proceeds: 75 × $2.00 = $150
PnL: $150 - $75 = $75 profit
```

#### 3.2 LIFO (Last-In, First-Out)
- Assumes most recently purchased tokens are sold first
- Can reduce taxes in rising markets
- Not allowed in all jurisdictions

**Example:**
```
Same purchases as above
LIFO Cost Basis:
- 50 from Batch 2 @ $1.50 = $75
- 25 from Batch 1 @ $1.00 = $25
Total Cost = $100
PnL: $150 - $100 = $50 profit
```

#### 3.3 Weighted Average Cost
- Calculates average price of all holdings
- Simpler but less precise

**Example:**
```
Total Cost = (100 × $1.00) + (50 × $1.50) = $175
Total Quantity = 150
Average Cost = $175 / 150 = $1.167 per token

Sell 75 @ $2.00:
Cost Basis = 75 × $1.167 = $87.50
PnL = $150 - $87.50 = $62.50 profit
```

#### 3.4 Specific Identification
- Explicitly choose which tokens to sell
- Requires detailed tracking and real-time identification
- Most flexible but record-keeping intensive

---

## 4. Handling Complex Scenarios

### 4.1 Partial Sells

When selling fewer tokens than purchased:

```typescript
// FIFO Partial Sell Example
interface TokenLot {
  quantity: number;
  price: number;        // price per token in USD
  timestamp: number;
  remaining: number;    // unsold quantity
}

class CostBasisTracker {
  private lots: Map<string, TokenLot[]> = new Map(); // tokenMint -> lots

  addPurchase(tokenMint: string, quantity: number, price: number, timestamp: number) {
    if (!this.lots.has(tokenMint)) {
      this.lots.set(tokenMint, []);
    }
    this.lots.get(tokenMint)!.push({
      quantity,
      price,
      timestamp,
      remaining: quantity
    });
  }

  // Returns array of { quantity, costBasis } for the sale
  calculateSaleCostBasis(tokenMint: string, sellQuantity: number): { quantity: number; costBasis: number }[] {
    const lots = this.lots.get(tokenMint);
    if (!lots) throw new Error("No purchase history for token");

    const consumedLots: { quantity: number; costBasis: number }[] = [];
    let remainingToSell = sellQuantity;

    // FIFO: Process oldest lots first
    for (const lot of lots) {
      if (remainingToSell <= 0) break;
      if (lot.remaining <= 0) continue;

      const quantityFromLot = Math.min(remainingToSell, lot.remaining);
      consumedLots.push({
        quantity: quantityFromLot,
        costBasis: lot.price
      });

      lot.remaining -= quantityFromLot;
      remainingToSell -= quantityFromLot;
    }

    if (remainingToSell > 0) {
      throw new Error("Attempting to sell more than owned");
    }

    return consumedLots;
  }
}
```

### 4.2 Multiple Buys at Different Prices

Track each purchase as a separate "lot" with its own cost basis:

```typescript
interface Position {
  tokenMint: string;
  lots: Lot[];
  totalQuantity: number;
  totalCost: number;  // in USD
}

interface Lot {
  id: string;
  quantity: number;
  pricePerToken: number;
  purchaseTx: string;
  timestamp: number;
  remainingQuantity: number;
}

// Add to position
function addToPosition(position: Position, lot: Lot) {
  position.lots.push(lot);
  position.totalQuantity += lot.quantity;
  position.totalCost += lot.quantity * lot.pricePerToken;
}
```

### 4.3 Token Swaps (DEX Trades)

Solana DEX swaps (Jupiter, Raydium, Orca, Meteora) are atomic transactions:

```typescript
interface SwapEvent {
  signature: string;
  timestamp: number;
  inputMint: string;      // Token being sold
  inputAmount: number;    // Raw amount (consider decimals)
  outputMint: string;     // Token being bought
  outputAmount: number;   // Raw amount (consider decimals)
  dex: 'Jupiter' | 'Raydium' | 'Orca' | 'Meteora' | 'PumpSwap';
  priceUsd?: number;      // USD price at time of swap
}

// For PnL: Swaps are TWO events
// 1. Sell input token (realize PnL if had position)
// 2. Buy output token (establish new cost basis)

function processSwap(swap: SwapEvent, tracker: CostBasisTracker): TradeResult {
  // Step 1: Calculate PnL on the token being sold
  const inputLots = tracker.calculateSaleCostBasis(
    swap.inputMint,
    swap.inputAmount
  );

  const inputCostBasis = inputLots.reduce(
    (sum, lot) => sum + (lot.quantity * lot.costBasis),
    0
  );

  // Get USD value of input at swap time
  const inputValueUsd = getUsdValue(swap.inputMint, swap.inputAmount, swap.timestamp);
  const realizedPnL = inputValueUsd - inputCostBasis;

  // Step 2: Record new purchase (output token)
  const outputPriceUsd = inputValueUsd / swap.outputAmount;
  tracker.addPurchase(
    swap.outputMint,
    swap.outputAmount,
    outputPriceUsd,
    swap.timestamp
  );

  return {
    realizedPnL,
    isProfitable: realizedPnL > 0,
    inputToken: swap.inputMint,
    outputToken: swap.outputMint
  };
}
```

### 4.4 SOL/WSOL Wrapping

When swapping SOL (native) for SPL tokens, it first wraps to WSOL:

```typescript
function isWrapUnwrap(tx: ParsedTransaction): boolean {
  // Detect WSOL account creation + closure in same tx
  const hasWsolCreate = tx.meta?.innerInstructions?.some(ix =>
    ix.instructions.some(i =>
      i.programId.equals(TOKEN_PROGRAM_ID) &&
      i.parsed?.type === 'createAccount'
    )
  );

  const hasWsolClose = tx.meta?.innerInstructions?.some(ix =>
    ix.instructions.some(i =>
      i.parsed?.type === 'closeAccount'
    )
  );

  return hasWsolCreate && hasWsolClose;
}

// For PnL: Treat SOL→WSOL→TOKEN as direct SOL→TOKEN
// Use SOL price as cost basis for the purchased token
```

### 4.5 Airdrops and Transfers

**Airdrops**: Typically $0 cost basis (income at fair market value)
**Transfers In**: Exclude from PnL (not a trade)
**Transfers Out**: May trigger disposal event

```typescript
enum TransactionType {
  BUY = 'buy',           // Acquire token with SOL/USDC
  SELL = 'sell',         // Sell token for SOL/USDC
  SWAP = 'swap',         // Token-to-token exchange
  TRANSFER_IN = 'transfer_in',
  TRANSFER_OUT = 'transfer_out',
  AIRDROP = 'airdrop',
  IGNORE = 'ignore'      // MEV, dust, etc.
}

function classifyTransaction(tx: ParsedTransaction, walletAddress: string): TransactionType {
  // Check for DEX program IDs
  const dexPrograms = [
    'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4', // Jupiter v6
    'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB', // Jupiter v4
    '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', // Raydium AMM
    '9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP', // Orca
    'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo', // Meteora
    '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P', // Pump.fun
  ];

  const programIds = tx.transaction.message.instructions.map(
    ix => ix.programId.toBase58()
  );

  if (programIds.some(id => dexPrograms.includes(id))) {
    return TransactionType.SWAP;
  }

  // Check for transfers
  // ... logic to detect transfers vs trades

  return TransactionType.IGNORE;
}
```

---

## 5. Code Example: Complete Wallet Performance Calculator

### TypeScript Implementation

```typescript
import { Connection, PublicKey, ParsedTransactionWithMeta } from '@solana/web3.js';
import { TOKEN_PROGRAM_ID } from '@solana/spl-token';

// ==================== TYPES ====================

interface TokenLot {
  id: string;
  quantity: number;
  priceUsd: number;
  timestamp: number;
  txSignature: string;
  remaining: number;
}

interface TokenPosition {
  mint: string;
  symbol: string;
  decimals: number;
  lots: TokenLot[];
  totalRemaining: number;
}

interface Trade {
  id: string;
  signature: string;
  timestamp: number;
  type: 'buy' | 'sell';
  tokenMint: string;
  tokenSymbol: string;
  quantity: number;
  priceUsd: number;
  totalValueUsd: number;
  costBasisUsd: number;
  realizedPnL: number;
  isProfitable: boolean;
}

interface WalletPerformance {
  walletAddress: string;
  totalRealizedPnL: number;
  totalTrades: number;
  profitableTrades: number;
  losingTrades: number;
  winrate: number;
  averageProfitPerTrade: number;
  averageLossPerTrade: number;
  largestProfit: number;
  largestLoss: number;
  trades: Trade[];
  openPositions: TokenPosition[];
}

// ==================== PRICE ORACLE ====================

interface PriceOracle {
  getPrice(tokenMint: string, timestamp: number): Promise<number>;
}

class BirdeyePriceOracle implements PriceOracle {
  private apiKey: string;
  private cache: Map<string, number> = new Map();

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async getPrice(tokenMint: string, timestamp: number): Promise<number> {
    const cacheKey = `${tokenMint}_${timestamp}`;
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)!;
    }

    // Call Birdeye API for historical price
    // Fallback to current price if historical not available
    const price = await this.fetchPrice(tokenMint, timestamp);
    this.cache.set(cacheKey, price);
    return price;
  }

  private async fetchPrice(tokenMint: string, timestamp: number): Promise<number> {
    // Implementation using Birdeye or DexScreener API
    // https://docs.birdeye.so/docs/prices
    const response = await fetch(
      `https://public-api.birdeye.so/defi/history_price?` +
      `address=${tokenMint}&` +
      `address_type=token&` +
      `type=1m&` +
      `time_from=${timestamp - 60}&` +
      `time_to=${timestamp + 60}`,
      {
        headers: {
          'X-API-KEY': this.apiKey,
          'accept': 'application/json'
        }
      }
    );

    const data = await response.json();
    if (data.data?.items?.length > 0) {
      return data.data.items[0].value;
    }

    // Fallback: try current price
    const currentResponse = await fetch(
      `https://public-api.birdeye.so/defi/price?address=${tokenMint}`,
      { headers: { 'X-API-KEY': this.apiKey, 'accept': 'application/json' } }
    );
    const currentData = await currentResponse.json();
    return currentData.data?.value || 0;
  }
}

// ==================== PnL CALCULATOR ====================

class SolanaPnLCalculator {
  private positions: Map<string, TokenPosition> = new Map();
  private trades: Trade[] = [];
  private priceOracle: PriceOracle;

  constructor(priceOracle: PriceOracle) {
    this.priceOracle = priceOracle;
  }

  /**
   * Process a parsed Solana transaction
   */
  async processTransaction(
    tx: ParsedTransactionWithMeta,
    walletAddress: string
  ): Promise<void> {
    if (!tx.meta || tx.meta.err) return; // Skip failed transactions

    const signature = tx.transaction.signatures[0];
    const timestamp = tx.blockTime || Date.now() / 1000;

    // Extract token balance changes
    const tokenChanges = this.extractTokenChanges(tx, walletAddress);

    for (const change of tokenChanges) {
      if (change.change > 0) {
        // Token received (buy)
        await this.processBuy(
          signature,
          timestamp,
          change.mint,
          change.change,
          change.priceUsd || await this.priceOracle.getPrice(change.mint, timestamp)
        );
      } else if (change.change < 0) {
        // Token sent (sell)
        await this.processSell(
          signature,
          timestamp,
          change.mint,
          Math.abs(change.change),
          change.priceUsd || await this.priceOracle.getPrice(change.mint, timestamp)
        );
      }
    }
  }

  /**
   * Extract token balance changes from transaction
   */
  private extractTokenChanges(
    tx: ParsedTransactionWithMeta,
    walletAddress: string
  ): Array<{ mint: string; change: number; priceUsd?: number }> {
    const changes: Array<{ mint: string; change: number; priceUsd?: number }> = [];
    const preBalances = tx.meta?.preTokenBalances || [];
    const postBalances = tx.meta?.postTokenBalances || [];

    // Build lookup maps
    const preMap = new Map<string, number>();
    const postMap = new Map<string, number>();

    for (const bal of preBalances) {
      if (bal.owner === walletAddress) {
        const key = `${bal.accountIndex}_${bal.mint}`;
        preMap.set(key, bal.uiTokenAmount.uiAmount || 0);
      }
    }

    for (const bal of postBalances) {
      if (bal.owner === walletAddress) {
        const key = `${bal.accountIndex}_${bal.mint}`;
        postMap.set(key, bal.uiTokenAmount.uiAmount || 0);
      }
    }

    // Calculate deltas
    const allKeys = new Set([...preMap.keys(), ...postMap.keys()]);

    for (const key of allKeys) {
      const [_, mint] = key.split('_');
      const pre = preMap.get(key) || 0;
      const post = postMap.get(key) || 0;
      const delta = post - pre;

      if (delta !== 0) {
        changes.push({ mint, change: delta });
      }
    }

    return changes;
  }

  /**
   * Process a buy transaction
   */
  private async processBuy(
    signature: string,
    timestamp: number,
    mint: string,
    quantity: number,
    priceUsd: number
  ): Promise<void> {
    if (!this.positions.has(mint)) {
      this.positions.set(mint, {
        mint,
        symbol: mint.slice(0, 4) + '...' + mint.slice(-4),
        decimals: 9, // Fetch from token metadata
        lots: [],
        totalRemaining: 0
      });
    }

    const position = this.positions.get(mint)!;

    const lot: TokenLot = {
      id: `${signature}_${Date.now()}`,
      quantity,
      priceUsd,
      timestamp,
      txSignature: signature,
      remaining: quantity
    };

    position.lots.push(lot);
    position.totalRemaining += quantity;

    // Record trade
    this.trades.push({
      id: lot.id,
      signature,
      timestamp,
      type: 'buy',
      tokenMint: mint,
      tokenSymbol: position.symbol,
      quantity,
      priceUsd,
      totalValueUsd: quantity * priceUsd,
      costBasisUsd: quantity * priceUsd,
      realizedPnL: 0,
      isProfitable: false
    });
  }

  /**
   * Process a sell transaction with FIFO cost basis
   */
  private async processSell(
    signature: string,
    timestamp: number,
    mint: string,
    quantity: number,
    priceUsd: number
  ): Promise<void> {
    const position = this.positions.get(mint);
    if (!position || position.totalRemaining < quantity) {
      console.warn(`Insufficient balance for ${mint}`);
      return;
    }

    let remainingToSell = quantity;
    let totalCostBasis = 0;
    let totalValue = 0;

    // FIFO: Sell oldest lots first
    for (const lot of position.lots) {
      if (remainingToSell <= 0) break;
      if (lot.remaining <= 0) continue;

      const sellFromLot = Math.min(remainingToSell, lot.remaining);
      const lotCostBasis = sellFromLot * lot.priceUsd;
      const lotValue = sellFromLot * priceUsd;

      totalCostBasis += lotCostBasis;
      totalValue += lotValue;
      lot.remaining -= sellFromLot;
      position.totalRemaining -= sellFromLot;
      remainingToSell -= sellFromLot;
    }

    const realizedPnL = totalValue - totalCostBasis;

    // Record trade
    this.trades.push({
      id: `${signature}_${Date.now()}_sell`,
      signature,
      timestamp,
      type: 'sell',
      tokenMint: mint,
      tokenSymbol: position.symbol,
      quantity,
      priceUsd,
      totalValueUsd: totalValue,
      costBasisUsd: totalCostBasis,
      realizedPnL,
      isProfitable: realizedPnL > 0
    });
  }

  /**
   * Calculate final wallet performance metrics
   */
  calculatePerformance(walletAddress: string): WalletPerformance {
    const closedTrades = this.trades.filter(t => t.type === 'sell');
    const profitableTrades = closedTrades.filter(t => t.realizedPnL > 0);
    const losingTrades = closedTrades.filter(t => t.realizedPnL < 0);

    const totalPnL = closedTrades.reduce((sum, t) => sum + t.realizedPnL, 0);
    const totalProfits = profitableTrades.reduce((sum, t) => sum + t.realizedPnL, 0);
    const totalLosses = losingTrades.reduce((sum, t) => sum + t.realizedPnL, 0);

    return {
      walletAddress,
      totalRealizedPnL: totalPnL,
      totalTrades: closedTrades.length,
      profitableTrades: profitableTrades.length,
      losingTrades: losingTrades.length,
      winrate: closedTrades.length > 0
        ? (profitableTrades.length / closedTrades.length) * 100
        : 0,
      averageProfitPerTrade: profitableTrades.length > 0
        ? totalProfits / profitableTrades.length
        : 0,
      averageLossPerTrade: losingTrades.length > 0
        ? totalLosses / losingTrades.length
        : 0,
      largestProfit: profitableTrades.length > 0
        ? Math.max(...profitableTrades.map(t => t.realizedPnL))
        : 0,
      largestLoss: losingTrades.length > 0
        ? Math.min(...losingTrades.map(t => t.realizedPnL))
        : 0,
      trades: this.trades,
      openPositions: Array.from(this.positions.values())
    };
  }
}

// ==================== MAIN EXECUTION ====================

async function analyzeWallet(
  walletAddress: string,
  rpcUrl: string,
  birdeyeApiKey: string
): Promise<WalletPerformance> {
  const connection = new Connection(rpcUrl, 'confirmed');
  const priceOracle = new BirdeyePriceOracle(birdeyeApiKey);
  const calculator = new SolanaPnLCalculator(priceOracle);

  // Fetch transaction signatures
  const pubKey = new PublicKey(walletAddress);
  const signatures = await connection.getSignaturesForAddress(pubKey, { limit: 1000 });

  console.log(`Found ${signatures.length} transactions`);

  // Process transactions in batches
  const batchSize = 10;
  for (let i = 0; i < signatures.length; i += batchSize) {
    const batch = signatures.slice(i, i + batchSize);
    const txs = await connection.getParsedTransactions(
      batch.map(s => s.signature),
      { maxSupportedTransactionVersion: 0 }
    );

    for (const tx of txs) {
      if (tx) {
        await calculator.processTransaction(tx, walletAddress);
      }
    }

    console.log(`Processed ${Math.min(i + batchSize, signatures.length)}/${signatures.length}`);
  }

  return calculator.calculatePerformance(walletAddress);
}

// ==================== USAGE EXAMPLE ====================

async function main() {
  const WALLET_ADDRESS = 'YourWalletAddressHere';
  const RPC_URL = 'https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY';
  const BIRDEYE_API_KEY = 'YOUR_BIRDEYE_API_KEY';

  const performance = await analyzeWallet(WALLET_ADDRESS, RPC_URL, BIRDEYE_API_KEY);

  console.log('\n========== WALLET PERFORMANCE ==========\n');
  console.log(`Wallet: ${performance.walletAddress}`);
  console.log(`Total Realized PnL: $${performance.totalRealizedPnL.toFixed(2)}`);
  console.log(`Total Trades: ${performance.totalTrades}`);
  console.log(`Profitable Trades: ${performance.profitableTrades}`);
  console.log(`Losing Trades: ${performance.losingTrades}`);
  console.log(`Winrate: ${performance.winrate.toFixed(2)}%`);
  console.log(`Average Profit: $${performance.averageProfitPerTrade.toFixed(2)}`);
  console.log(`Average Loss: $${performance.averageLossPerTrade.toFixed(2)}`);
  console.log(`Largest Profit: $${performance.largestProfit.toFixed(2)}`);
  console.log(`Largest Loss: $${performance.largestLoss.toFixed(2)}`);
  console.log(`Open Positions: ${performance.openPositions.length}`);

  // Print trade history
  console.log('\n========== TRADE HISTORY ==========\n');
  for (const trade of performance.trades.slice(-10)) {
    console.log(
      `${new Date(trade.timestamp * 1000).toISOString()} | ` +
      `${trade.type.toUpperCase()} | ` +
      `${trade.tokenSymbol} | ` +
      `${trade.quantity.toFixed(4)} @ $${trade.priceUsd.toFixed(4)} | ` +
      `PnL: $${trade.realizedPnL.toFixed(2)}`
    );
  }
}

main().catch(console.error);
```

---

## 6. Key Considerations & Best Practices

### 6.1 Data Sources

| Data Type | Recommended Source |
|-----------|-------------------|
| Transaction History | Helius API, QuickNode |
| Token Prices | Birdeye, DexScreener, CoinGecko |
| Token Metadata | Metaplex, Jupiter Token List |
| Real-time Updates | Helius Webhooks, Yellowstone gRPC |

### 6.2 Performance Optimization

1. **Batch RPC calls**: Process transactions in batches (10-50 at a time)
2. **Cache price data**: Store fetched prices to avoid redundant API calls
3. **Use connection pooling**: For high-throughput applications
4. **Index by token**: Organize lots by token mint for fast lookups
5. **Database persistence**: Store processed data in PostgreSQL/MongoDB

### 6.3 Common Edge Cases

1. **Failed transactions**: Skip transactions where `meta.err` is not null
2. **MEV/arbitrage**: Filter out sandwich attacks and bot transactions
3. **Decimal precision**: Always use token decimals for raw amount conversion
4. **Stablecoin pairs**: USDC/SOL swaps need special handling for USD valuation
5. **Multi-hop swaps**: Jupiter routes through multiple DEXs - treat as single trade

### 6.4 Tax Considerations

- **FIFO is mandatory** for US taxpayers from 2026 (per-wallet basis)
- Track holding periods for short-term vs long-term capital gains
- Record gas/fees as adjustments to cost basis
- Airdrops may be taxable as ordinary income at receipt

---

## 7. Summary

To calculate PnL and winrate from Solana transaction data:

1. **Parse transactions** using `getSignaturesForAddress` + `getParsedTransactions`
2. **Extract token changes** from `preTokenBalances` and `postTokenBalances`
3. **Classify transactions** (buy/sell/swap/transfer/airdrop)
4. **Track cost basis** using FIFO (recommended) or other method
5. **Calculate realized PnL** on each sell: `Proceeds - Cost Basis`
6. **Track closed trades** to compute winrate: `Profitable Trades / Total Trades`
7. **Fetch USD prices** at transaction time for consistent valuation

**Key Formula Recap:**
- Realized PnL = Σ(Sell Value) - Σ(Cost Basis)
- Winrate = (Profitable Trades / Total Closed Trades) × 100
- Cost Basis (FIFO) = Price of oldest unsold tokens

---

## References

1. Birdeye Wallet PnL API: https://bds.birdeye.so/blog/detail/track-realized-and-unrealized-gains-on-solana-with-wallet-pnl-api
2. Solana Transaction Parsing: https://baransel.dev/post/parse-solana-transactions-efficiently/
3. FIFO Trading Model: https://code.activestate.com/recipes/579024-simple-fifo-trading-model-for-pnl/
4. Helius Documentation: https://docs.helius.dev/
5. Jupiter Swap Decoding: https://stackoverflow.com/questions/79400728/how-to-correctly-decode-a-jupiter-swap-event-on-solana
