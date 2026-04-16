# UI/UX Specification v1.0
## Smart Money Trading Intelligence Platform

**Date:** 2026-03-09  
**Status:** Draft  
**References:** Nansen Token God Mode, Arkham Intelligence, GMGN Interface

---

## 1. Design Philosophy

### Core Principles
- **Information Density**: Maximize data visibility without overwhelming users
- **Visual Hierarchy**: Critical information at eye level, details on demand
- **Real-time Feel**: Subtle animations, live updates, color-coded urgency
- **Trader-First**: Everything serves decision-making speed

### Color System
```
PRIMARY PALETTE:
├── Background: #0A0B0F (Deep void)
├── Surface: #14151A (Card backgrounds)
├── Elevated: #1E1F26 (Hover states)
├── Border: #2A2D35 (Subtle dividers)
└── Text: #FFFFFF (Primary), #9CA3AF (Secondary), #6B7280 (Tertiary)

FUNCTIONAL COLORS:
├── Buy/Success: #22C55E (Green)
├── Sell/Danger: #EF4444 (Red)
├── Warning: #F59E0B (Amber)
├── Info: #3B82F6 (Blue)
├── Neutral: #8B5CF6 (Purple)
└── Highlight: #FCD34D (Yellow accent)

ALERT TIERS:
├── Critical: #EF4444 + pulse animation
├── Important: #F59E0B + subtle glow
└── Research: #3B82F6 + static indicator
```

---

## 2. Dashboard Layout

### 2.1 Overall Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LOGO    Dashboard  Wallets  Tokens  Alerts  Research        [🔍] [👤] [⚙️] │  ← Header (56px)
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌───────────────────────────────────────────────┐   │
│  │                  │  │  MARKET OVERVIEW                              │   │
│  │  PORTFOLIO       │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐│   │
│  │  SUMMARY         │  │  │ BTC     │ │ ETH     │ │ SOL     │ │ TOT  ││   │
│  │                  │  │  │ $95.2K  │ │ $3.2K   │ │ $142    │ │$300B ││   │
│  │  Total Tracked   │  │  │ +2.3%   │ │ -1.1%   │ │ +5.4%   │ │+1.2% ││   │
│  │  $1.24B          │  │  └─────────┘ └─────────┘ └─────────┘ └──────┘│   │
│  │                  │  └───────────────────────────────────────────────┘   │
│  │  Active Wallets│  ┌─────────────────────────────────────────────────┐   │
│  │  2,847         │  │  SMART MONEY HEATMAP                            │   │
│  │                  │  │                                                 │   │
│  │  Avg Position    │  │   [Bubble chart: token size = volume]          │   │
│  │  $435K         │  │                                                 │   │
│  │                  │  │        ○  ○○                                    │   │
│  │  [View All →]  │  │      ○○  $BONK  ○○                               │   │
│  │                  │  │    ○  $PEPE    ○○                                │   │
│  └──────────────────┘  │       ○○○   $SOL                                │   │
│                        │    ○○     ○○○                                    │   │
│  ┌──────────────────┐  │                                                 │   │
│  │  ALERT STREAM    │  └─────────────────────────────────────────────────┘   │
│  │  ─────────────   │  ┌─────────────────────┐ ┌─────────────────────────┐   │
│  │  🔴 CRITICAL     │  │  TOP MOVERS         │ │  RECENT SMART MOVES     │   │
│  │  $PEPE +145%   │  │  ─────────────       │ │  ────────────────────   │   │
│  │  🟡 IMPORTANT    │  │  1. $PEPE +145%    │ │  🐋 0x7a...bought $2M   │   │
│  │  $SOL breakout   │  │  2. $BONK +89%     │ │  🦈 0x3f...sold $890K   │   │
│  │  🔵 RESEARCH     │  │  3. $WIF +67%      │  │  🐋 0x9c...bought $5M   │   │
│  │  New token...    │  │  4. $FLOKI +52%    │ │  🦈 0x2a...bought $1.2M │   │
│  │                  │  │  5. $DOGE +34%     │ │                         │   │
│  │  [View All]      │  │                     │ │  [View All Activity →] │   │
│  └──────────────────┘  └─────────────────────┘ └─────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↑
                              Footer Status Bar
                    [🟢 Live] [⏱️ Last Update: 2s ago] [📊 API: OK]
```

### 2.2 Layout Specifications

| Component | Position | Size | Behavior |
|-----------|----------|------|----------|
| Header | Fixed top | 100% × 56px | Always visible |
| Sidebar | Fixed left | 280px × 100vh | Collapsible to 64px |
| Main Content | Scrollable | flex: 1 | Padding: 24px |
| Status Bar | Fixed bottom | 100% × 32px | System indicators |

### 2.3 Responsive Breakpoints

```
Desktop Large: ≥ 1920px (4K optimized)
Desktop: 1280px - 1919px (Default)
Tablet: 768px - 1279px (Sidebar collapses)
Mobile: < 768px (Stacked layout)
```

---

## 3. Real-Time Alert System

### 3.1 Alert Tier System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ALERT CONFIGURATION PANEL                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🔴 CRITICAL ALERTS (Immediate Notification)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [✓] Whale wallet activation (>$10M movement)                       │   │
│  │  [✓] New token smart money accumulation (>5 whales in 1h)           │   │
│  │  [✓] Exchange outflow spike (>1000% avg)                            │   │
│  │  [✓] Token unlock / vesting cliff                                     │   │
│  │  [ ] Liquidation cascade detected                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  🟡 IMPORTANT ALERTS (In-App + Push)                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [✓] Wallet cluster formation (3+ related wallets)                  │   │
│  │  [✓] Significant position increase (>50% of avg)                    │   │
│  │  [✓] Token breaking key resistance level                            │   │
│  │  [✓] Large DEX swap (>100 ETH equivalent)                           │   │
│  │  [✓] New CEX listing detected                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  🔵 RESEARCH ALERTS (In-App Only)                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [✓] New wallet with high win rate discovered                       │   │
│  │  [✓] Unusual token holding pattern detected                         │   │
│  │  [✓] Correlation analysis complete                                    │   │
│  │  [✓] Funding rate anomaly                                             │   │
│  │  [ ] Social sentiment spike                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Alert Card Design

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔴 CRITICAL                                    2 min ago    [×]   │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  🐋 WHALE ACTIVITY DETECTED                                         │
│                                                                     │
│  Wallet: 0x7a8b...3f9e                    [View Wallet →]          │
│  Label: 🏷️ Jump Trading                                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ACTION:  BUY $PEPE                                        │   │
│  │  AMOUNT:  $12,450,000 (2.1B tokens)                        │   │
│  │  PRICE:   $0.00000592 (+15% impact)                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [📊 Chart]  [🔔 Set Alert]  [💾 Save]  [↗️ Share]                 │
└─────────────────────────────────────────────────────────────────────┘

ANIMATION: Subtle pulse glow on border (red: 0.4s pulse, 2s interval)
```

### 3.3 Alert Feed Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LIVE ALERTS                                    [🔔 Mute] [⚙️ Filter]      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🔴 19:32  Whale Buy: 0x7a... purchased $15M PEPE                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🟡 19:28  Cluster Alert: 5 wallets accumulating $WIF               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🔵 19:15  Research: High correlation between 0x3f... and 0x9c...  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🔴 19:08  Exchange Alert: $200M USDT withdrawn from Binance       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ── Earlier Today ─────────────────────────────────────────────────────   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🟡 18:45  Position Alert: Smart wallet 0x2a... increased SOL 300%  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Wallet Cluster Visualization

### 4.1 Network Graph View (Arkham-style)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WALLET CLUSTER: Meme Coin Whales                          [🔍] [⛶] [📷] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                           ╭──────────╮                                     │
│                          ╱   0x7a    ╲                                    │
│                         │  $45.2M    │                                    │
│                         │   🏷️ JUMP  │                                    │
│                          ╲   ████   ╱                                     │
│                           ╰────┬───╯                                      │
│                                │                                          │
│                ┌───────────────┼───────────────┐                          │
│                │               │               │                          │
│           ╭────┴───╮      ╭───┴────╮     ╭────┴───╮                     │
│          ╱  0x3f   ╲    ╱   0x9c    ╲   ╱  0x2a   ╲                    │
│         │  $12.5M   │  │   $8.9M    │  │   $6.2M   │                    │
│         │   ███     │  │    ██      │  │    █      │                    │
│          ╲  🏷️ MM  ╱    ╲   🏷️ ?   ╱    ╲  🏷️ ?  ╱                     │
│           ╰───┬────╯      ╰────┬───╯      ╰────┬───╯                     │
│               │                │               │                          │
│          ╭────┴───╮      ╭────┴───╮     ╭────┴───╮                     │
│         ╱  0x8d   ╲    ╱  0x1e   ╲   ╱  0x4b   ╲                    │
│        │  $890K   │  │   $450K   │  │   $320K   │                    │
│        │     █    │  │      █    │  │      █    │                    │
│         ╲  🏷️ ?  ╱    ╲   🏷️ ?  ╱    ╲  🏷️ ?  ╱                     │
│          ╰────────╯      ╰────────╯      ╰────────╯                     │
│                                                                             │
│  LEGEND:                                                                    │
│  ━━━━ Strong connection (>50% same tokens)                                 │
│  ━━━  Medium connection (20-50% overlap)                                   │
│  ━━   Weak connection (<20% overlap)                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Cluster Analysis Panel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLUSTER METRICS                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CLUSTER SIZE                    PRIMARY TOKENS                              │
│  ┌─────────────────────────┐    ┌──────────────────────────────────────┐   │
│  │  Total Wallets:     12  │    │  1. $PEPE    ████████████████████  │   │
│  │  Labeled:           3   │    │  2. $WIF     ████████████████░░░░  │   │
│  │  Anonymous:         9   │    │  3. $BONK    ██████████░░░░░░░░░░  │   │
│  │  Combined AUM:  $73.1M  │    │  4. $DOGE    ███████░░░░░░░░░░░░░  │   │
│  │  Avg Win Rate:    67%   │    │  5. $FLOKI   █████░░░░░░░░░░░░░░░  │   │
│  └─────────────────────────┘    └──────────────────────────────────────┘   │
│                                                                             │
│  CONNECTION MATRIX                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │         │ 0x7a │ 0x3f │ 0x9c │ 0x2a │ 0x8d │ 0x1e │ 0x4b │         │   │
│  │  0x7a   │  --  │  85% │  72% │  45% │  23% │  12% │   8% │         │   │
│  │  0x3f   │  85% │  --  │  91% │  38% │  67% │  15% │  11% │         │   │
│  │  0x9c   │  72% │  91% │  --  │  29% │  54% │   9% │   6% │         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ACTIVITY TIMELINE                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [Mini sparkline: coordinated buys/sells over time]                 │   │
│  │  ████░░░░████░░░░░░████░░░░░░████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    │   │
│  │  Last coordinated activity: 2 hours ago                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Wallet Detail Card

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WALLET PROFILE                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────┐  0x7a8b...3f9e                                      [📋]  │
│  │            │  ─────────────────────────────────────────────────         │
│  │   🐋       │  🏷️ Jump Trading (95% confidence)                          │
│  │  AVATAR    │  📊 Win Rate: 78% | 📈 Avg ROI: +145% | ⏱️ Active: 234d   │
│  │            │                                                             │
│  └────────────┘  CURRENT HOLDINGS                                          │
│                  ┌─────────────────────────────────────────────────────┐   │
│                  │ Token      │  Amount    │ Value      │  24h    P&L │   │
│  PERFORMANCE     │────────────│────────────│────────────│─────────────│   │
│  ┌──────────┐    │ $PEPE      │ 45.2B      │ $12.4M    │ +23%  +$2.3M│   │
│  │  7D P&L  │    │ $WIF       │ 2.1M       │ $4.8M     │ +45%  +$1.5M│   │
│  │  +$8.2M  │    │ $BONK      │ 12.5B      │ $890K     │ -5%   -$47K │   │
│  │   +23%   │    │ $SOL       │ 1,250      │ $178K     │ +12%  +$19K │   │
│  └──────────┘    └─────────────────────────────────────────────────────┘   │
│                                                                             │
│  RECENT ACTIVITY (Last 7 Days)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Mar 09  BUY  $PEPE    $2.1M   @ $0.0000051    [+15% unrealized]   │   │
│  │  Mar 08  SELL $WIF     $890K   @ $2.34         [+34% realized]     │   │
│  │  Mar 07  BUY  $BONK    $450K   @ $0.000071     [-5% unrealized]    │   │
│  │  Mar 06  BUY  $PEPE    $3.2M   @ $0.0000048    [+22% unrealized]   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [📊 Full History]  [🔔 Track This Wallet]  [🔗 View on Explorer]         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Token Screener Interface

### 5.1 Main Screener Grid (GMGN-style)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TOKEN SCREENER                                          [🔍] [⚙️] [💾]    │
├─────────────────────────────────────────────────────────────────────────────┤
│  FILTERS:  [All Chains ▼]  [Market Cap: >$1M ▼]  [Smart Score: >70 ▼]     │
│                                                                             │
│  ┌────────┬──────────┬──────────┬──────────┬──────────┬──────────┬────────┐ │
│  │  #     │  TOKEN   │  PRICE   │   24H    │  SMART   │  HOLDER  │ ACTION │ │
│  │        │          │          │  CHANGE  │  MONEY   │  ANALYSIS│        │ │
│  ├────────┼──────────┼──────────┼──────────┼──────────┼──────────┼────────┤ │
│  │   1    │ 🐸 PEPE  │ $0.0000..│  ▲ +23%  │  🟢 92   │  🟢 Bull │  [👁️] │ │
│  │        │ MC: $4.2B│ +15% 1h  │  Vol $2B │  12 🐋   │  78% in  │        │ │
│  │        │          │          │          │  34 🦈   │  24h     │        │ │
│  ├────────┼──────────┼──────────┼──────────┼──────────┼──────────┼────────┤ │
│  │   2    │ 🐕 WIF   │ $2.34    │  ▲ +45%  │  🟢 88   │  🟢 Bull │  [👁️] │ │
│  │        │ MC: $2.1B│ +8% 1h   │  Vol $890M│  8 🐋    │  85% in  │        │ │
│  │        │          │          │          │  56 🦈   │  24h     │        │ │
│  ├────────┼──────────┼──────────┼──────────┼──────────┼──────────┼────────┤ │
│  │   3    │ 🦴 BONK  │ $0.0000..│  ▼ -5%   │  🟡 72   │  🟡 Neut │  [👁️] │ │
│  │        │ MC: $1.8B│ -2% 1h   │  Vol $450M│  6 🐋    │  45% in  │        │ │
│  │        │          │          │          │  23 🦈   │  24h     │        │ │
│  ├────────┼──────────┼──────────┼──────────┼──────────┼──────────┼────────┤ │
│  │   4    │ 🐶 DOGE  │ $0.18    │  ▲ +12%  │  🟢 85   │  🟢 Bull │  [👁️] │ │
│  │        │ MC: $26B │ +3% 1h   │  Vol $5B │  45 🐋   │  65% in  │        │ │
│  │        │          │          │          │  234 🦈  │  24h     │        │ │
│  ├────────┼──────────┼──────────┼──────────┼──────────┼──────────┼────────┤ │
│  │   5    │ 🔥 FLOKI │ $0.0002  │  ▲ +18%  │  🟡 68   │  🟡 Neut │  [👁️] │ │
│  │        │ MC: $1.9B│ +5% 1h   │  Vol $320M│  4 🐋    │  52% in  │        │ │
│  │        │          │          │          │  18 🦈   │  24h     │        │ │
│  └────────┴──────────┴──────────┴──────────┴──────────┴──────────┴────────┘ │
│                                                                             │
│  [◀ Prev]  Page 1 of 24  [Next ▶]           Showing 5 of 1,247 tokens      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Smart Money Score Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SMART MONEY SCORE: PEPE (92/100)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │              ╭──────────────────────────────╮                      │   │
│  │             ╱         92                   ╲                     │   │
│  │            │      ████████████████          │                     │   │
│  │            │      █  EXCELLENT   █          │                     │   │
│  │             ╲     ████████████████         ╱                     │   │
│  │              ╰──────────────────────────────╯                      │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  SCORE COMPONENTS                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Whale Accumulation    ████████████████████░░░░░  85/100            │   │
│  │  (12 whales buying in last 24h)                                     │   │
│  │                                                                     │   │
│  │  Holder Quality        ████████████████████████░░  92/100           │   │
│  │  (High win-rate wallets entering)                                   │   │
│  │                                                                     │   │
│  │  Volume Momentum       ██████████████████████░░░░  88/100           │   │
│  │  (Volume up 234% vs 7d avg)                                         │   │
│  │                                                                     │   │
│  │  Price Action          ██████████████████████████  95/100           │   │
│  │  (Breaking resistance, strong trend)                                │   │
│  │                                                                     │   │
│  │  Liquidity Score       ██████████████████░░░░░░░░  82/100           │   │
│  │  (Adequate DEX liquidity)                                           │   │
│  │                                                                     │   │
│  │  Social Sentiment      ██████████████░░░░░░░░░░░░  72/100           │   │
│  │  (Positive Twitter mentions)                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  OVERALL: EXCELLENT buying opportunity with strong smart money backing     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Token Detail View (Nansen Token God Mode style)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  $PEPE / PEPE                            [🌐 Website] [📊 Chart] [📋 Copy] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────────────────────┐ │
│  │  PRICE CHART (Live)               │  │  HOLDER DISTRIBUTION            │ │
│  │                                   │  │                                 │ │
│  │    $0.00001 ┤    ╱╲               │  │  🐋 Whales (>$1M)   12 wallets │ │
│  │    $0.00008 ┤   ╱  ╲    ╱╲       │  │     Avg Entry: $0.0000045      │ │
│  │    $0.00006 ┤  ╱    ╲  ╱  ╲      │  │     Unrealized: +145%          │ │
│  │    $0.00004 ┤ ╱      ╲╱    ╲     │  │                                 │ │
│  │    $0.00002 ┤╱              ╲    │  │  🦈 Sharks ($100K-$1M) 45 wal  │ │
│  │         $0  ┼────────────────    │  │     Avg Entry: $0.0000062      │ │
│  │            1D  7D  30D  MAX      │  │     Unrealized: +78%           │ │
│  │                                   │  │                                 │ │
│  │  [1H] [4H] [1D] [1W] [1M]        │  │  🐟 Fish (<$100K)    12,450 wal│ │
│  │                                   │  │     Avg Entry: $0.0000089      │ │
│  └───────────────────────────────────┘  │     Unrealized: +24%           │ │
│                                         └─────────────────────────────────┘ │
│  ┌───────────────────────────────────┐  ┌─────────────────────────────────┐ │
│  │  SMART MONEY FLOWS (24H)          │  │  TOP HOLDERS                    │ │
│  │                                   │  │                                 │ │
│  │  BUYING          SELLING          │  │  #1  0x7a8b...  $12.4M   🏷️ JT │ │
│  │  ████████████    ████             │  │  #2  0x3f2a...  $4.2M    🏷️ MM │ │
│  │  $45.2M          $8.9M            │  │  #3  0x9c4d...  $2.1M    🏷️ ?  │ │
│  │                                   │  │  #4  0x2a8f...  $1.8M    🏷️ ?  │ │
│  │  Net Flow: +$36.3M 🟢             │  │  #5  0x8d3e...  $1.2M    🏷️ ?  │ │
│  │                                   │  │                                 │ │
│  │  [View All Transactions →]        │  │  [View All 12,507 Holders →]   │ │
│  └───────────────────────────────────┘  └─────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EXCHANGE FLOWS                                                     │   │
│  │  Binance:   +$12M inflow   🟢  |  Coinbase:  -$3M outflow   🔴     │   │
│  │  OKX:       +$8M inflow    🟢  |  Bybit:     +$2M inflow    🟢     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Mobile Alert Design

### 6.1 Mobile Layout (Portrait)

```
┌─────────────────────────────┐
│ ≡  SmartMoney    [🔔] [👤] │  ← Header (48px)
├─────────────────────────────┤
│                             │
│  ┌───────────────────────┐  │
│  │ 🔴 CRITICAL           │  │
│  │ Whale Alert!          │  │
│  │ $PEPE +23%            │  │
│  │ 0x7a... bought $12M   │  │
│  └───────────────────────┘  │
│                             │
│  ┌───────────────────────┐  │
│  │ 🟡 IMPORTANT          │  │
│  │ Cluster Formation     │  │
│  │ 5 wallets $WIF        │  │
│  └───────────────────────┘  │
│                             │
│  ── TODAY ───────────────── │
│                             │
│  ┌───────────────────────┐  │
│  │ 19:32  🔴  Whale Buy  │  │
│  │        $PEPE $12M    │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │ 19:28  🟡  Cluster    │  │
│  │        $WIF accum     │  │
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │ 19:15  🔵  Research   │  │
│  │        New high WR    │  │
│  └───────────────────────┘  │
│                             │
└─────────────────────────────┘
│  [🏠]  [🔍]  [🔔]  [👤]    │  ← Bottom Nav (56px)
└─────────────────────────────┘
```

### 6.2 Mobile Push Notification Specs

```
┌─────────────────────────────┐
│ 🔴 SmartMoney Alert         │
├─────────────────────────────┤
│ 🐋 Whale Activity: $PEPE   │
│ $12.4M purchased by Jump  │
│ Trading                   │
│                             │
│ [View] [Dismiss]            │
└─────────────────────────────┘

TAP BEHAVIOR:
- Single Tap → Open app to alert detail
- Swipe Right → Mark as read
- Swipe Left → Dismiss & mute similar

RICH NOTIFICATION (expandable):
┌─────────────────────────────┐
│ 🔴 SmartMoney Alert         │
├─────────────────────────────┤
│ 🐋 Whale Activity: $PEPE   │
│ $12.4M purchased           │
│                             │
│ Price: $0.00000592         │
│ Impact: +15%               │
│ Time: 2 min ago            │
│                             │
│ [Chart Preview Sparkline]  │
│                             │
│ [View] [Track] [Share]     │
└─────────────────────────────┘
```

### 6.3 Mobile Token View

```
┌─────────────────────────────┐
│ [←] $PEPE          [⋮]     │
├─────────────────────────────┤
│                             │
│  $0.00000592               │
│  ▲ +23.4% (24h)            │
│  MC: $4.2B | Vol: $2.1B    │
│                             │
│  ┌───────────────────────┐  │
│  │    [Price Chart]      │  │
│  │      📈               │  │
│  └───────────────────────┘  │
│                             │
│  SMART SCORE: 92 🟢         │
│  ████████████████████░░     │
│                             │
│  ─────────────────────────  │
│  HOLDER ANALYSIS            │
│  ─────────────────────────  │
│                             │
│  🐋 Whales: 12              │
│  └─ Net buy: +$45M 🟢       │
│                             │
│  🦈 Sharks: 45              │
│  └─ Net buy: +$12M 🟢       │
│                             │
│  🐟 Retail: 12,450          │
│  └─ Mixed activity          │
│                             │
│  ─────────────────────────  │
│  TOP MOVES (24H)            │
│  ─────────────────────────  │
│                             │
│  BUY  0x7a...  $12.4M  🏷️  │
│  BUY  0x3f...  $4.2M   🏷️  │
│  SELL 0x9c...  $2.1M       │
│                             │
│  [View All 234 Moves →]    │
│                             │
└─────────────────────────────┘
```

### 6.4 Mobile Navigation

```
BOTTOM NAVIGATION BAR (56px height)

┌─────────────────────────────┐
│  🏠    🔍    🔔    👤       │
│ Home  Search Alerts Profile │
└─────────────────────────────┘

TAB BEHAVIOR:
- Home: Dashboard overview
- Search: Token screener with filters
- Alerts: Full alert history (badge count)
- Profile: Settings, tracked wallets, saved alerts

BADGE SYSTEM:
- 🔴 Red badge for Critical alerts (count)
- 🟡 Yellow badge for Important + Critical
- No badge for Research-only
```

---

## 7. Component Library

### 7.1 Common UI Elements

```
BUTTONS:
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   PRIMARY   │  │  SECONDARY  │  │    GHOST    │  │    ICON     │
│   [Save]    │  │  [Cancel]   │  │   [View]    │  │    [👁️]     │
│  #3B82F6    │  │  #1E1F26    │  │   transparent │   transparent │
│  white text │  │  white text │  │  #3B82F6    │  │  #9CA3AF    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

BADGES:
┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
│ NEW │  │ HOT │  │ 🐋  │  │ 🦈  │  │ 🟢  │  │ 🔴  │
│ #8B5│  │ #F59│  │ Whale│  │Shark│  │ Bull│  │ Bear│
└─────┘  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘

DATA CELLS:
┌─────────────────────────────────────────────────────────┐
│  TOKEN          │  PRICE    │  CHANGE  │  SIGNAL       │
│  🐸 PEPE        │  $0.000.. │  ▲ +23%  │  🟢 STRONG BUY│
│  $4.2B MC       │  +15% 1h  │  Vol $2B │  92 Score     │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Animation Specifications

```
TRANSITIONS:
├── Page Load: 200ms fade-in, ease-out
├── Modal Open: 150ms scale(0.95→1) + fade
├── Data Update: 300ms number count-up
├── Alert Pulse: 2s infinite (critical only)
├── Hover States: 100ms color/border transition
└── Chart Updates: 500ms smooth transition

LOADING STATES:
├── Skeleton: Shimmer animation (1.5s loop)
├── Spinner: 360° rotate (1s linear infinite)
├── Progress: Smooth width transition
└── Data Fetch: Pulsing opacity on stale data
```

---

## 8. Accessibility

### 8.1 Visual Standards

```
CONTRAST RATIOS:
├── White text on dark bg: 15.8:1 ✓
├── Green/Red indicators: 4.6:1 ✓
├── Secondary text: 7.2:1 ✓
└── Interactive elements: 4.5:1 ✓

COLOR INDEPENDENCE:
├── Always pair color with icon/shape
├── Green ▲ vs Red ▼ (not just color)
├── Whale 🐋 vs Shark 🦈 (not just size)
└── Score displayed as number + bar

FOCUS STATES:
├── Visible focus ring: 2px #3B82F6
├── Tab order follows visual hierarchy
└── Skip to content link available
```

---

## 9. Responsive Behavior Summary

| Feature | Desktop | Tablet | Mobile |
|---------|---------|--------|--------|
| Sidebar | Fixed 280px | Collapsible icon | Hidden (drawer) |
| Charts | Full interactive | Simplified | Sparkline only |
| Tables | Full columns | 4 columns | Card list |
| Alerts | Side panel | Bottom sheet | Full screen |
| Wallet Graph | Force-directed | Simplified | List view |
| Navigation | Header only | Header only | Bottom bar |

---

## 10. Reference Implementations

### 10.1 Nansen Token God Mode
- **Strengths**: Rich on-chain metrics, holder distribution charts
- **Adopted**: Token detail layout, smart money scores
- **Improved**: Real-time updates, mobile responsiveness

### 10.2 Arkham Intelligence
- **Strengths**: Entity labeling, network graph visualization
- **Adopted**: Wallet clustering, entity relationships
- **Improved**: Performance (60fps graphs), alert integration

### 10.3 GMGN Interface
- **Strengths**: Clean screener, fast filtering
- **Adopted**: Grid layout, quick filters
- **Improved**: More data density, advanced analytics

---

## Appendix: ASCII Chart Reference

```
Color codes in ASCII:
🔴 Red/Critical    🟡 Yellow/Important  🔵 Blue/Research
🟢 Green/Bullish   🟣 Purple/Neutral    ⚪ Gray/Info

Icons:
🐋 Whale (>$10M)   🦈 Shark ($1M-$10M)  🐟 Fish (<$1M)
📈 Chart up        📉 Chart down        ⏱️ Time
🔔 Alert           👁️ View              📊 Analytics
```

---

*Document Version: 1.0*  
*Last Updated: 2026-03-09*  
*Next Review: On implementation start*
