# Autonomous Trading Agent Decision Framework
## Quantitative Strategy System Architecture

**Version:** 1.0  
**Created:** 2026-03-28  
**Purpose:** Codified decision-making system for autonomous trading operations

---

## 1. SIGNAL GENERATION METHODOLOGY

### 1.1 Multi-Layer Signal Architecture

The signal generation system follows a **four-layer architecture** adapted from modern AI financial agent design:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNAL GENERATION PIPELINE                    │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: DATA PERCEPTION                                        │
│  ├── Market Data: OHLCV, order book, tick data                  │
│  ├── Technical Indicators: SMA, EMA, RSI, MACD, Bollinger Bands │
│  ├── Macro Signals: VIX, yield curves, economic calendar        │
│  └── Alternative: Sentiment, on-chain metrics (crypto)          │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: REASONING ENGINE                                       │
│  ├── Market Regime Classification (HMM/Threshold-based)         │
│  ├── Pattern Recognition (ML/statistical models)                │
│  ├── Confluence Scoring (multi-factor aggregation)              │
│  └── Confidence Calibration (probability estimates)             │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: STRATEGY GENERATION                                    │
│  ├── Signal Strength Calculation (0-100 scale)                  │
│  ├── Expected Value Computation (win rate × payoff ratio)       │
│  ├── Risk Assessment (volatility-adjusted)                      │
│  └── Decision Object Formation (signal + metadata)              │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: EXECUTION READINESS                                    │
│  ├── Pre-trade Risk Checks                                      │
│  ├── Position Sizing Calculation                                │
│  ├── Order Type Selection                                       │
│  └── Final Authorization Gate                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Signal Components

Each trade signal consists of the following structured data:

| Field | Description | Data Type |
|-------|-------------|-----------|
| `symbol` | Trading instrument identifier | string |
| `direction` | LONG or SHORT | enum |
| `confidence` | Signal strength (0-100) | float |
| `expected_return` | Projected return % | float |
| `win_probability` | Estimated win rate (0-1) | float |
| `regime_alignment` | Compatibility with current regime (0-1) | float |
| `time_horizon` | Expected holding period | timedelta |
| `entry_zone` | Acceptable entry price range | [float, float] |
| `stop_loss` | Mandatory exit price | float |
| `take_profit` | Target exit price | float |
| `risk_reward_ratio` | Expected R:R ratio | float |
| `volatility_forecast` | ATR or realized vol projection | float |
| `liquidity_score` | Ease of execution (0-100) | float |
| `correlation_risk` | Portfolio correlation impact | float |

### 1.3 Signal Scoring Algorithm

```python
def calculate_signal_score(signal, regime_state):
    """
    Compute composite signal score weighted by regime context
    """
    base_score = (
        signal.confidence * 0.30 +
        signal.win_probability * 25 +  # scaled to 0-25
        signal.risk_reward_ratio * 10 +  # scaled, max ~30
        signal.regime_alignment * 25 +  # scaled to 0-25
        signal.liquidity_score * 0.10
    )
    
    # Regime adjustment: reduce score in unfavorable regimes
    regime_multiplier = REGIME_MULTIPLIERS[regime_state.current_regime]
    
    # Volatility penalty: reduce score in extreme volatility
    vol_penalty = max(0, (signal.volatility_forecast - VOL_THRESHOLD) / VOL_THRESHOLD)
    
    final_score = base_score * regime_multiplier * (1 - vol_penalty * 0.5)
    
    return min(100, max(0, final_score))
```

### 1.4 Minimum Signal Thresholds

| Condition | Long Entry | Short Entry | Exit Signal |
|-----------|------------|-------------|-------------|
| **Minimum Score** | ≥ 65 | ≥ 65 | ≥ 55 (reverse) |
| **Confidence** | ≥ 60% | ≥ 60% | ≥ 50% |
| **Win Probability** | ≥ 55% | ≥ 55% | N/A |
| **Risk:Reward** | ≥ 1:2 | ≥ 1:2 | N/A |
| **Regime Alignment** | ≥ 0.6 | ≥ 0.6 | Any |

---

## 2. POSITION SIZING FORMULA

### 2.1 Core Sizing Method: Adaptive Fractional Kelly

The system uses a **volatility-adjusted fractional Kelly criterion** with safety bounds:

```
KELLY FRACTION FORMULA:
─────────────────────────────────────────────────────────────
f = (bp - q) / b

Where:
  f  = Fraction of capital to allocate
  b  = Average win / Average loss (payoff ratio)
  p  = Win probability (from backtest or forecast)
  q  = Loss probability = 1 - p
─────────────────────────────────────────────────────────────
```

### 2.2 Practical Implementation

```python
def calculate_position_size(account_equity, signal, portfolio_state):
    """
    Calculate optimal position size using adaptive fractional Kelly
    """
    # Step 1: Calculate Kelly percentage
    p = signal.win_probability
    b = signal.risk_reward_ratio
    q = 1 - p
    
    kelly_pct = (b * p - q) / b if b > 0 else 0
    
    # Step 2: Apply fractional Kelly (conservative: 1/4 Kelly)
    fractional_kelly = kelly_pct * KELLY_FRACTION  # Default: 0.25
    
    # Step 3: Volatility adjustment (reduce size in high vol)
    vol_adjustment = BASE_VOLATILITY / signal.volatility_forecast
    vol_adjustment = max(0.5, min(2.0, vol_adjustment))  # Cap between 0.5x - 2x
    
    # Step 4: Regime-based scaling
    regime_multiplier = REGIME_POSITION_MULTIPLIERS[regime_state.current_regime]
    
    # Step 5: Portfolio heat adjustment (reduce size as portfolio heat increases)
    heat_factor = 1 - (portfolio_state.current_heat / MAX_PORTFOLIO_HEAT)
    heat_factor = max(0.25, heat_factor)  # Never below 25%
    
    # Step 6: Drawdown protection (reduce size during drawdowns)
    dd_factor = drawdown_position_modifier(portfolio_state.drawdown_pct)
    
    # Final calculation
    risk_per_trade = fractional_kelly * vol_adjustment * regime_multiplier * heat_factor * dd_factor
    
    # Apply absolute limits
    risk_per_trade = min(risk_per_trade, MAX_RISK_PER_TRADE)  # 2% hard cap
    risk_per_trade = max(risk_per_trade, MIN_RISK_PER_TRADE)  # 0.1% floor
    
    # Calculate dollar risk and position size
    dollar_risk = account_equity * risk_per_trade
    stop_distance = abs(signal.entry_price - signal.stop_loss)
    
    position_size = dollar_risk / stop_distance
    position_value = position_size * signal.entry_price
    
    # Final constraint: max position value as % of equity
    max_position_value = account_equity * MAX_POSITION_PCT
    if position_value > max_position_value:
        position_size = max_position_value / signal.entry_price
    
    return {
        'shares': position_size,
        'value': position_size * signal.entry_price,
        'risk_pct': risk_per_trade,
        'risk_dollars': dollar_risk
    }
```

### 2.3 Position Sizing Parameters

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `KELLY_FRACTION` | 0.25 (Quarter Kelly) | Reduces volatility vs full Kelly |
| `MAX_RISK_PER_TRADE` | 0.02 (2%) | Absolute maximum risk per trade |
| `MIN_RISK_PER_TRADE` | 0.001 (0.1%) | Minimum meaningful position |
| `MAX_POSITION_PCT` | 0.10 (10%) | Max position as % of equity |
| `BASE_VOLATILITY` | 20% annualized | Reference volatility for sizing |
| `MAX_PORTFOLIO_HEAT` | 0.06 (6%) | Max portfolio risk at any time |

### 2.4 Drawdown-Based Position Scaling

| Drawdown Level | Position Multiplier | Action |
|----------------|---------------------|--------|
| 0% - 5% | 1.00 | Normal sizing |
| 5% - 10% | 0.75 | Reduce to 75% |
| 10% - 15% | 0.50 | Reduce to 50% |
| 15% - 20% | 0.25 | Reduce to 25% |
| > 20% | 0.00 | Stop new positions |

---

## 3. ENTRY/EXIT RULES

### 3.1 Entry Strategy Matrix

| Market Condition | Primary Entry | Secondary Entry | Order Type |
|------------------|---------------|-----------------|------------|
| **Trending Up** | Pullback to 20 EMA | Breakout above resistance | Limit / Stop-Limit |
| **Trending Down** | Rally to resistance | Breakdown below support | Limit / Stop-Limit |
| **Range-Bound** | Support bounce | Resistance rejection | Limit |
| **High Volatility** | Volatility contraction | Momentum continuation | Limit with wide stops |
| **Low Volatility** | Breakout entry | Range expansion | Stop-Entry |

### 3.2 Entry Execution Algorithm

```python
def execute_entry(signal, market_data):
    """
    Determine optimal entry execution strategy
    """
    # Select execution algorithm based on order size and urgency
    order_value = signal.target_position_value
    avg_daily_volume = market_data.adv_20d
    participation_rate = order_value / (avg_daily_volume * market_data.price)
    
    if participation_rate > 0.10:  # > 10% of ADV
        # Use TWAP/VWAP for large orders
        return {
            'algorithm': 'TWAP',
            'duration_minutes': 60,
            'slices': 12,
            'order_type': 'LIMIT',
            'limit_price': signal.entry_zone[1]  # Upper bound
        }
    elif signal.urgency == 'HIGH':
        # Quick execution with market impact awareness
        return {
            'algorithm': 'SNIPER',
            'order_type': 'LIMIT',
            'limit_price': signal.entry_zone[1],
            'timeout_seconds': 300
        }
    else:
        # Standard limit order with patience
        return {
            'algorithm': 'PASSIVE',
            'order_type': 'LIMIT',
            'limit_price': signal.entry_zone[0],  # Lower bound for better fill
            'time_in_force': 'GTC',
            'cancel_after': '30 min'
        }
```

### 3.3 Exit Rules Framework

#### 3.3.1 Stop Loss Exit (Mandatory)

| Stop Type | Trigger Condition | Execution |
|-----------|-------------------|-----------|
| **Initial Stop** | Price hits stop_loss level | Market order immediately |
| **Trailing Stop** | Price moves favorably, stop trails | Adjust stop dynamically |
| **Time Stop** | Position held > max_time | Exit at market close |
| **Volatility Stop** | ATR expands > 2x entry | Tighten stop to breakeven |

**Trailing Stop Formula:**
```
trail_distance = max(ATR(14) * ATR_MULTIPLIER, min_trail_distance)
new_stop = max(current_stop, price - trail_distance)  # for longs
```

#### 3.3.2 Profit Target Exit

| Exit Method | Condition | R:R Target |
|-------------|-----------|------------|
| **Full Target** | Price hits take_profit | Close 100% |
| **Scale Out 1** | +1R profit | Close 25% |
| **Scale Out 2** | +2R profit | Close 50% |
| **Scale Out 3** | +3R profit | Close 25% (runner) |
| **Trailing Exit** | Trailing stop hit | Close remainder |

#### 3.3.3 Conditional Exits

```python
EXIT_TRIGGERS = {
    'stop_loss_hit': {
        'priority': 1,  # Highest
        'action': 'CLOSE_ALL',
        'order_type': 'MARKET'
    },
    'target_hit_full': {
        'priority': 2,
        'action': 'CLOSE_ALL',
        'order_type': 'LIMIT'
    },
    'signal_reversal': {
        'priority': 3,
        'condition': 'opposite_signal_confidence > 70',
        'action': 'CLOSE_ALL'
    },
    'regime_change': {
        'priority': 4,
        'condition': 'regime_changed AND new_regime_unfavorable',
        'action': 'REDUCE_50'
    },
    'time_expiration': {
        'priority': 5,
        'condition': 'hold_time > max_hold_time',
        'action': 'CLOSE_ALL'
    },
    'correlation_spike': {
        'priority': 6,
        'condition': 'portfolio_correlation > 0.8',
        'action': 'REDUCE_25'
    }
}
```

### 3.4 Order Type Selection Logic

```
ENTRY ORDERS:
├── Size < 1% ADV → Limit Order (passive, GTC)
├── Size 1-5% ADV → Limit Order (aggressive, IOC)
├── Size 5-10% ADV → TWAP over 15-30 min
└── Size > 10% ADV → VWAP over 1-4 hours

EXIT ORDERS:
├── Stop Loss → Stop-Market (guaranteed execution)
├── Profit Target → Limit Order (price control)
├── Trailing Stop → Trailing Stop-Market
└── Emergency Exit → Market Order (immediate)
```

---

## 4. RISK MANAGEMENT PARAMETERS

### 4.1 Multi-Level Risk Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RISK CONTROL HIERARCHY                        │
├─────────────────────────────────────────────────────────────────┤
│  LEVEL 1: TRADE-LEVEL RISK                                       │
│  ├── Max risk per trade: 2% of equity                           │
│  ├── Mandatory stop-loss on every position                      │
│  ├── Position sizing based on stop distance                     │
│  └── Single position max: 10% of portfolio                      │
├─────────────────────────────────────────────────────────────────┤
│  LEVEL 2: SESSION-LEVEL RISK                                     │
│  ├── Daily loss limit: 3% of equity                             │
│  ├── Consecutive loss limit: 5 trades                           │
│  ├── Max trades per day: 20                                     │
│  └── Trading hours restriction (market hours only)              │
├─────────────────────────────────────────────────────────────────┤
│  LEVEL 3: PORTFOLIO-LEVEL RISK                                   │
│  ├── Max portfolio heat: 6% (aggregate risk)                    │
│  ├── Correlation limit: No two positions > 0.7 correlation      │
│  ├── Sector concentration: Max 30% per sector                   │
│  └── Cash reserve: Minimum 10% uninvested                       │
├─────────────────────────────────────────────────────────────────┤
│  LEVEL 4: SYSTEM-LEVEL RISK                                      │
│  ├── Maximum drawdown: 20% (hard stop)                          │
│  ├── Monthly loss limit: 10%                                    │
│  ├── Volatility filter: Pause if VIX > 40                       │
│  └── Emergency kill switch: Manual + automatic triggers         │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Circuit Breaker Implementation

```python
class CircuitBreaker:
    """
    Multi-tier circuit breaker system
    """
    RISK_LEVELS = {
        'NORMAL': {'can_trade': True, 'position_mult': 1.0},
        'REDUCED': {'can_trade': True, 'position_mult': 0.5},
        'PAUSED': {'can_trade': False, 'position_mult': 0.0},
        'HALTED': {'can_trade': False, 'position_mult': 0.0, 'close_all': True}
    }
    
    def evaluate(self, portfolio_state):
        """Determine current risk level based on all metrics"""
        
        # Check HALTED conditions (most severe)
        if portfolio_state.drawdown_pct >= 0.20:
            return self._halt("Maximum drawdown (20%) breached")
            
        if portfolio_state.monthly_loss_pct >= 0.10:
            return self._halt("Monthly loss limit (10%) reached")
        
        # Check PAUSED conditions
        if portfolio_state.daily_loss_pct >= 0.03:
            return self._pause("Daily loss limit (3%) reached")
            
        if portfolio_state.consecutive_losses >= 5:
            return self._pause("Consecutive loss limit (5) reached")
            
        if portfolio_state.vix > 40:
            return self._pause("Extreme volatility (VIX > 40)")
        
        # Check REDUCED conditions
        if portfolio_state.drawdown_pct >= 0.10:
            return self._reduce(f"Drawdown ({portfolio_state.drawdown_pct:.1%}) > 10%")
            
        if portfolio_state.portfolio_heat >= 0.05:
            return self._reduce(f"Portfolio heat ({portfolio_state.portfolio_heat:.1%}) elevated")
        
        return 'NORMAL'
```

### 4.3 Risk Parameter Summary

| Risk Category | Parameter | Value | Action on Breach |
|---------------|-----------|-------|------------------|
| **Trade** | Max Risk/Trade | 2% | Reject trade |
| **Trade** | Max Position Size | 10% | Reduce to limit |
| **Trade** | Max Slippage | 0.5% | Switch to limit |
| **Session** | Daily Loss Limit | 3% | Pause trading |
| **Session** | Consecutive Losses | 5 | Pause trading |
| **Session** | Max Daily Trades | 20 | Reject new orders |
| **Portfolio** | Max Heat | 6% | Reduce positions |
| **Portfolio** | Max Correlation | 0.70 | Reject correlated trade |
| **Portfolio** | Sector Limit | 30% | Reject new sector position |
| **System** | Max Drawdown | 20% | Halt, manual restart |
| **System** | Monthly Loss | 10% | Halt for review |
| **System** | Volatility Pause | VIX > 40 | Pause new entries |

### 4.4 Dynamic Risk Adjustment

```python
def adjust_risk_for_regime(base_params, regime_state):
    """
    Dynamically adjust risk parameters based on market regime
    """
    adjustments = {
        'TRENDING_UP': {
            'risk_per_trade_mult': 1.0,
            'position_size_mult': 1.0,
            'trailing_stop_enabled': True,
            'pyramiding_allowed': True
        },
        'TRENDING_DOWN': {
            'risk_per_trade_mult': 0.75,
            'position_size_mult': 0.75,
            'trailing_stop_enabled': True,
            'short_bias': True
        },
        'RANGE_BOUND': {
            'risk_per_trade_mult': 0.75,
            'position_size_mult': 0.75,
            'tighter_stops': True,
            'profit_target_scalar': 0.8
        },
        'HIGH_VOLATILITY': {
            'risk_per_trade_mult': 0.50,
            'position_size_mult': 0.50,
            'wider_stops': True,
            'reduce_hold_time': True
        },
        'CRISIS': {
            'risk_per_trade_mult': 0.25,
            'position_size_mult': 0.25,
            'only_high_conviction': True,
            'hedge_required': True
        }
    }
    
    return apply_adjustments(base_params, adjustments[regime_state.current_regime])
```

---

## 5. PORTFOLIO CONSTRAINTS

### 5.1 Portfolio Construction Rules

```
DIVERSIFICATION CONSTRAINTS:
├── Maximum Positions: 15 concurrent positions
├── Minimum Positions: 3 (ensures diversification)
├── Sector Concentration: ≤ 30% in any sector
├── Asset Class: ≤ 50% in single asset class
├── Geographic: ≤ 60% in single region
└── Market Cap: ≤ 40% in single cap tier

CORRELATION CONSTRAINTS:
├── Pairwise Correlation: No two positions with |ρ| > 0.7
├── Portfolio Beta: Target 0.8-1.2 vs benchmark
├── Sector Correlation: Monitor rolling 30-day correlations
└── Market Correlation: Reduce exposure if portfolio ρ > 0.9 with SPY

LIQUIDITY CONSTRAINTS:
├── Minimum ADV: Position ≤ 5% of 20-day ADV
├── Maximum Spread: ≤ 0.5% bid-ask spread for entry
├── Position Size: ≤ 10% of average daily dollar volume
└── Exit Planning: Must be able to exit within 1 day at ≤ 1% slippage
```

### 5.2 Portfolio Balance Targets

| Metric | Target | Minimum | Maximum |
|--------|--------|---------|---------|
| Long Exposure | 70% | 30% | 100% |
| Short Exposure | 20% | 0% | 50% |
| Cash Reserve | 10% | 5% | 30% |
| Portfolio Beta | 0.9 | 0.5 | 1.3 |
| Active Positions | 8 | 3 | 15 |
| Avg Position Size | 6.25% | 2% | 10% |

### 5.3 Rebalancing Rules

```python
def check_rebalancing_needs(portfolio):
    """
    Check if portfolio requires rebalancing
    """
    triggers = []
    
    # 1. Drift-based rebalancing
    for position in portfolio.positions:
        target_weight = position.target_weight
        current_weight = position.current_value / portfolio.equity
        drift = abs(current_weight - target_weight)
        
        if drift > REBALANCE_DRIFT_THRESHOLD:  # 5%
            triggers.append({
                'type': 'DRIFT',
                'symbol': position.symbol,
                'action': 'REDUCE' if current_weight > target_weight else 'INCREASE',
                'amount': abs(current_weight - target_weight) * portfolio.equity
            })
    
    # 2. Correlation-based rebalancing
    corr_matrix = calculate_correlation_matrix(portfolio.positions)
    high_corr_pairs = find_correlations_above(corr_matrix, 0.7)
    
    for pair in high_corr_pairs:
        triggers.append({
            'type': 'CORRELATION',
            'symbols': pair,
            'action': 'REDUCE_BOTH',
            'amount': 'MIN_POSITION_SIZE'
        })
    
    # 3. Stop-based rebalancing (position hit stop but not closed)
    for position in portfolio.positions:
        if position.unrealized_pnl_pct < -0.05:  # Down 5%
            triggers.append({
                'type': 'STOP_VIOLATION',
                'symbol': position.symbol,
                'action': 'REVIEW_STOP'
            })
    
    return triggers
```

### 5.4 Cash Management

```
CASH ALLOCATION STRATEGY:
├── Minimum Operating Cash: 5% of equity
├── Opportunity Reserve: 5% (for sudden opportunities)
├── Defensive Cash: Scales with drawdown
│   ├── 0-5% DD: 0% additional cash
│   ├── 5-10% DD: +5% cash
│   ├── 10-15% DD: +10% cash
│   └── >15% DD: +15% cash (total 25%)
└── Cash Deployment Rules:
    ├── Deploy 2% per day when signal quality > 70
    ├── Deploy 1% per day when signal quality 60-70
    └── Hold when signal quality < 60
```

---

## 6. DECISION TREE / FLOWCHART

### 6.1 Master Decision Tree

```
                         ┌─────────────────────────────────────┐
                         │     MARKET DATA & SIGNALS RECEIVED   │
                         └──────────────┬──────────────────────┘
                                        │
                                        ▼
                    ┌──────────────────────────────────────────┐
                    │  STEP 1: SYSTEM HEALTH CHECK              │
                    │  ├── Circuit breaker status?              │
                    │  ├── Trading hours?                       │
                    │  ├── Data quality OK?                     │
                    │  └── All systems operational?             │
                    └──────────────┬───────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                   FAIL                         PASS
                    │                             │
                    ▼                             ▼
         ┌─────────────────┐        ┌──────────────────────────────┐
         │  LOG & NOTIFY   │        │  STEP 2: REGIME DETECTION    │
         │  Skip cycle     │        │  ├── Classify market regime  │
         └─────────────────┘        │  └── Update regime parameters│
                                    └──────────────┬───────────────┘
                                                   │
                                                   ▼
                           ┌───────────────────────────────────────┐
                           │  STEP 3: SIGNAL GENERATION             │
                           │  ├── Run strategy algorithms          │
                           │  ├── Calculate signal scores          │
                           │  ├── Apply regime filters             │
                           │  └── Generate candidate signals       │
                           └──────────────┬────────────────────────┘
                                          │
                           ┌──────────────┴──────────────┐
                           │                             │
                         SIGNAL                       NO SIGNAL
                           │                             │
                           ▼                             ▼
                ┌────────────────────┐      ┌────────────────────────┐
                │ STEP 4: VALIDATE   │      │ STEP 8: PORTFOLIO      │
                │  ├── Score >= 65?  │      │      MONITORING        │
                │  ├── R:R >= 2:1?   │      │  ├── Check stops       │
                │  ├── Win% >= 55%?  │      │  ├── Update trailing   │
                │  └── Liquidity OK? │      │  ├── Check targets     │
                └──────────┬─────────┘      │  └── Rebalance check   │
                           │                └────────────────────────┘
              ┌────────────┴────────────┐
              │                         │
            REJECT                    VALIDATE
              │                         │
              ▼                         ▼
    ┌──────────────────┐    ┌──────────────────────────────────┐
    │ LOG: Signal      │    │  STEP 5: RISK CHECKS              │
    │ rejected - reason│    │  ├── Position size OK?            │
    └──────────────────┘    │  ├── Portfolio heat OK?           │
                            │  ├── Correlation OK?              │
                            │  ├── Daily loss limit OK?         │
                            │  └── Drawdown OK?                 │
                            └──────────────┬───────────────────┘
                                           │
                            ┌──────────────┴──────────────┐
                            │                             │
                          REJECT                         PASS
                            │                             │
                            ▼                             ▼
                  ┌──────────────────┐       ┌──────────────────────────┐
                  │ REDUCE SIZE OR   │       │  STEP 6: EXECUTION        │
                  │ SKIP TRADE       │       │  ├── Select order type    │
                  │ (log reason)     │       │  ├── Calculate size       │
                  └──────────────────┘       │  ├── Set stops/targets    │
                                             │  └── Submit order         │
                                             └──────────────┬────────────┘
                                                            │
                                                            ▼
                                               ┌────────────────────────┐
                                               │  STEP 7: POST-TRADE    │
                                               │  ├── Monitor fill      │
                                               │  ├── Update portfolio  │
                                               │  ├── Log performance   │
                                               │  └── Alert if anomaly  │
                                               └────────────────────────┘
```

### 6.2 Trade Execution Decision Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ENTRY EXECUTION DECISION                         │
└─────────────────────────────────────────────────────────────────────┘

START: Validated entry signal received
│
├─→ Calculate optimal position size (Kelly + adjustments)
│   │
│   ├─→ Check: Size > 10% of ADV?
│   │   ├─→ YES: Use VWAP over 2-4 hours
│   │   └─→ NO: Continue
│   │
│   ├─→ Check: Urgency = HIGH?
│   │   ├─→ YES: Use aggressive limit (IOC)
│   │   └─→ NO: Continue
│   │
│   └─→ Check: Spread < 0.1%?
│       ├─→ YES: Use market order (small size)
│       └─→ NO: Use limit order at bid/ask
│
├─→ Submit primary order
│   │
│   ├─→ Fill within 5 minutes?
│   │   ├─→ YES: Position opened, set stops
│   │   └─→ NO: Adjust limit price (cancel/replace)
│   │
│   └─→ Partial fill?
│       ├─→ YES: Hold remaining, update size
│       └─→ NO: Complete
│
└─→ END: Position active, monitoring started


┌─────────────────────────────────────────────────────────────────────┐
│                      EXIT EXECUTION DECISION                         │
└─────────────────────────────────────────────────────────────────────┘

START: Exit condition triggered
│
├─→ Identify exit type
│   │
│   ├─→ Stop Loss Hit?
│   │   ├─→ YES: Market order immediately (no limit)
│   │   └─→ NO: Continue
│   │
│   ├─→ Profit Target?
│   │   ├─→ YES: Limit order at target price
│   │   └─→ NO: Continue
│   │
│   ├─→ Trailing Stop?
│   │   ├─→ YES: Market order immediately
│   │   └─→ NO: Continue
│   │
│   └─→ Time/Signal Exit?
│       ├─→ YES: Limit order with patience (GTC)
│       └─→ NO: Manual review
│
├─→ Check position size
│   │
│   ├─→ Size > 5% of ADV?
│   │   ├─→ YES: Scale out over time (TWAP)
│   │   └─→ NO: Single order
│   │
│   └─→ Check urgency
│       ├─→ URGENT: Market order
│       └─→ PATIENT: Limit order
│
└─→ END: Position closed, log P&L
```

### 6.3 Risk Management Decision Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RISK MANAGEMENT CHECKPOINTS                       │
└─────────────────────────────────────────────────────────────────────┘

EVERY 60 SECONDS:
│
├─→ Update portfolio metrics
│   ├── Current equity
│   ├── Unrealized P&L
│   ├── Realized P&L (today)
│   ├── Current drawdown
│   └── Portfolio heat (aggregate risk)
│
├─→ Check Circuit Breakers
│   │
│   ├─→ Drawdown > 20%?
│   │   └─→ HALT ALL: Close positions, notify, manual restart required
│   │
│   ├─→ Daily loss > 3%?
│   │   └─→ PAUSE: No new entries, monitor existing
│   │
│   ├─→ Consecutive losses >= 5?
│   │   └─→ PAUSE: Cool-off period (30 min minimum)
│   │
│   └─→ VIX > 40?
│       └─→ PAUSE: No new entries, tighten stops
│
├─→ Check Position-Level Risk
│   │
│   ├─→ Any position down > 5%?
│   │   └─→ REVIEW: Check stop placement, consider early exit
│   │
│   ├─→ Any position up > 3R?
│   │   └─→ TRAIL: Activate/ tighten trailing stop
│   │
│   └─→ Position held > max time?
│       └─→ TIME EXIT: Close at market
│
├─→ Check Portfolio-Level Risk
│   │
│   ├─→ Portfolio heat > 6%?
│   │   └─→ REDUCE: No new positions, scale down existing
│   │
│   ├─→ Correlation spike detected?
│   │   └─→ DIVERSIFY: Reduce correlated positions
│   │
│   └─→ Cash < 5%?
│       └─→ CONSOLIDATE: Close weakest position
│
└─→ Log status, continue monitoring
```

---

## 7. MARKET REGIME DETECTION

### 7.1 Regime Classification System

```python
REGIME_DEFINITIONS = {
    'TRENDING_UP': {
        'conditions': [
            'price > 200_SMA',
            'ADX > 25',
            '+DI > -DI',
            'price > 20_EMA'
        ],
        'favored_strategies': ['trend_following', 'momentum'],
        'position_mult': 1.0,
        'stop_type': 'trailing'
    },
    'TRENDING_DOWN': {
        'conditions': [
            'price < 200_SMA',
            'ADX > 25',
            '-DI > +DI',
            'price < 20_EMA'
        ],
        'favored_strategies': ['trend_following', 'short_bias'],
        'position_mult': 0.75,
        'stop_type': 'trailing'
    },
    'RANGE_BOUND': {
        'conditions': [
            'ADX < 20',
            'RSI between 40 and 60',
            'BB_width < percentile_20'
        ],
        'favored_strategies': ['mean_reversion', 'range_trading'],
        'position_mult': 0.75,
        'stop_type': 'fixed_tight'
    },
    'HIGH_VOLATILITY': {
        'conditions': [
            'ATR > 1.5x_average',
            'VIX > 25',
            'realized_vol > percentile_80'
        ],
        'favored_strategies': ['volatility_breakout', 'volatility_mean_reversion'],
        'position_mult': 0.50,
        'stop_type': 'wide'
    },
    'CRISIS': {
        'conditions': [
            'VIX > 40',
            'correlation_spike > 0.9',
            'liquidity_stress_indicator = True'
        ],
        'favored_strategies': ['defensive', 'hedging'],
        'position_mult': 0.25,
        'stop_type': 'tight'
    },
    'TRANSITION': {
        'conditions': [
            'ADX between 20-25',
            'regime_probability < 0.70 for any regime'
        ],
        'favored_strategies': ['reduced_activity'],
        'position_mult': 0.50,
        'stop_type': 'tight'
    }
}
```

### 7.2 Regime Detection Algorithm

```python
def detect_market_regime(market_data):
    """
    Multi-factor regime detection using HMM and rule-based confirmation
    """
    # 1. Calculate indicator values
    adx = calculate_adx(market_data.high, market_data.low, market_data.close, 14)
    atr = calculate_atr(market_data.high, market_data.low, market_data.close, 14)
    sma200 = market_data.close.rolling(200).mean()
    ema20 = market_data.close.ewm(span=20).mean()
    bb_width = calculate_bollinger_band_width(market_data.close, 20)
    
    # 2. Get regime probabilities from Hidden Markov Model
    features = pd.DataFrame({
        'returns': market_data.close.pct_change(),
        'volatility': market_data.close.pct_change().rolling(20).std(),
        'range': (market_data.high - market_data.low) / market_data.close
    }).dropna()
    
    hmm_probs = hmm_model.predict_proba(features.iloc[-1:])
    
    # 3. Rule-based confirmation
    if adx.iloc[-1] > 25:
        if market_data.close.iloc[-1] > ema20.iloc[-1]:
            regime = 'TRENDING_UP'
        else:
            regime = 'TRENDING_DOWN'
    elif market_data['VIX'].iloc[-1] > 40:
        regime = 'CRISIS'
    elif atr.iloc[-1] > atr.rolling(50).mean().iloc[-1] * 1.5:
        regime = 'HIGH_VOLATILITY'
    elif adx.iloc[-1] < 20:
        regime = 'RANGE_BOUND'
    else:
        regime = 'TRANSITION'
    
    # 4. Confidence score
    regime_confidence = max(hmm_probs[0])
    
    # 5. Transition detection
    regime_changed = (regime != previous_regime)
    
    return {
        'current_regime': regime,
        'confidence': regime_confidence,
        'changed': regime_changed,
        'hmm_probabilities': dict(zip(hmm_model.states, hmm_probs[0]))
    }
```

---

## 8. IMPLEMENTATION CHECKLIST

### 8.1 Pre-Trade System Checklist

- [ ] All data feeds operational
- [ ] Circuit breaker status: NORMAL
- [ ] Current regime identified
- [ ] Portfolio metrics calculated
- [ ] Correlation matrix updated
- [ ] Risk parameters within limits
- [ ] Signal validation passed

### 8.2 Signal Validation Checklist

- [ ] Signal score ≥ 65
- [ ] Confidence ≥ 60%
- [ ] Win probability ≥ 55%
- [ ] Risk:Reward ≥ 1:2
- [ ] Regime alignment ≥ 0.6
- [ ] Liquidity score ≥ 50
- [ ] Correlation risk acceptable

### 8.3 Post-Trade Checklist

- [ ] Position opened successfully
- [ ] Stop-loss order placed
- [ ] Take-profit order placed (if applicable)
- [ ] Position logged in portfolio
- [ ] Risk metrics updated
- [ ] Alert thresholds set
- [ ] Trade logged for analysis

---

## 9. APPENDIX: KEY FORMULAS

### 9.1 Position Sizing

```
Position Size = (Account Equity × Risk Per Trade) / (Entry Price - Stop Loss)

Where Risk Per Trade = Fractional Kelly × Volatility Adjust × Regime Multiplier × Heat Factor
```

### 9.2 Kelly Criterion

```
f = (bp - q) / b

Where:
  f = Optimal fraction of capital
  b = Average win / Average loss
  p = Win probability
  q = 1 - p
```

### 9.3 Portfolio Heat

```
Portfolio Heat = Σ (Position Size × Stop Distance / Account Equity)
               = Sum of all position risks as % of equity
```

### 9.4 Drawdown

```
Current Drawdown = (Peak Equity - Current Equity) / Peak Equity

Max Drawdown = max over time of Current Drawdown
```

### 9.5 Risk-Adjusted Returns

```
Sharpe Ratio = (Return - Risk Free Rate) / Volatility

Sortino Ratio = (Return - Risk Free Rate) / Downside Deviation

Calmar Ratio = Annual Return / Max Drawdown
```

---

**Document End**

*This framework provides the complete decision-making architecture for an autonomous trading system. All rules are codifiable and designed to operate without human discretion while maintaining safety through layered risk controls.*
