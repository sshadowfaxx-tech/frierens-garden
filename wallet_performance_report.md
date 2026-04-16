# ShadowHunter Wallet Performance Report
**Analysis Period:** March 14-15, 2026  
**Data Source:** ShadowHunter Raw Pings Telegram exports (3 HTML files)  
**Total Trades Analyzed:** 2,027 (1,052 BUY, 975 SELL)  
**Report Generated:** March 16, 2026

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Wallets Tracked | 21 |
| Profitable Wallets | 14 (66.7%) |
| Losing Wallets | 7 (33.3%) |
| **Combined PnL** | **+1,906.09 SOL** |
| Total Volume | 3,581.47 SOL |
| **Average Return** | **+53.22%** |

**Key Insight:** Despite 1/3 of wallets being unprofitable, the portfolio as a whole is significantly profitable (+53% avg return) due to the outsized gains from top performers.

---

## Tier Rankings

### 🏆 S-TIER (Exceptional Performance)
| Wallet | PnL (SOL) | Winrate | Trades | Avg Position |
|--------|-----------|---------|--------|--------------|
| Insider5 | +1,397.53 | N/A* | 1 | 0.00 |
| GakeVector | +249.43 | N/A* | 2 | 97.52 |
| Yenni | +246.07 | 83.3% | 6 | 13.43 |
| jijo | +186.80 | 81.8% | 22 | 2.75 |

*S-TIER wallets show extraordinary returns. Insider5 and GakeVector have incomplete data (missing buy entries), but Yenni and jijo demonstrate genuine 80%+ winrates with high volume.*

### 🥇 A-TIER (Strong Performance)
| Wallet | PnL (SOL) | Winrate | Trades | Avg Position |
|--------|-----------|---------|--------|--------------|
| OGANTD | +139.96 | 50.0% | 6 | 13.96 |
| Insider6 | +86.36 | 40.0% | 5 | 14.91 |
| Cowboy | +74.78 | 71.4% | 21 | 10.08 |
| GHOSTEE | +69.68 | 17.6% | 34 | 9.07 |
| Gake1 | +65.91 | N/A* | 3 | 3.41 |
| Euris | +60.66 | 50.0% | 4 | 17.24 |
| Shy/Coyote | +53.51 | 42.9% | 21 | 10.96 |
| thedoc | +47.42 | 78.6% | 14 | 3.50 |

*A-TIER wallets are consistently profitable. Notable: GHOSTEE has only 17.6% winrate but still profitable due to large wins offsetting small losses (asymmetric risk/reward).*

### 🥈 B-TIER (Moderate Performance)
| Wallet | PnL (SOL) | Winrate | Trades | Avg Position |
|--------|-----------|---------|--------|--------------|
| Sheep | +19.27 | 43.8% | 16 | 8.91 |
| Moodeng Whale | +13.66 | N/A* | 1 | 0.00 |

*B-TIER wallets are profitable but with lower margins or incomplete data.*

### 🥉 C-TIER (Underperforming)
| Wallet | PnL (SOL) | Winrate | Trades | Avg Position |
|--------|-----------|---------|--------|--------------|
| Patty | -2.95 | N/A* | 2 | 1.58 |
| clukz | -6.31 | 28.6% | 7 | 94.56 |
| Portapog | -36.09 | N/A* | 2 | 18.05 |

*C-TIER wallets show small losses. Portapog has all open positions (no sells recorded).*

### ⚠️ D-TIER (Poor Performance - REMOVE)
| Wallet | PnL (SOL) | Winrate | Trades | Avg Position |
|--------|-----------|---------|--------|--------------|
| Insider1 | -48.70 | 0.0% | 1 | 147.38 |
| SarahMilady | -132.60 | 50.0% | 4 | 43.63 |
| Moonpie? | -197.24 | 33.3% | 15 | 30.45 |
| niggle | -381.06 | 0.0% | 1 | 586.11 |

*D-TIER wallets are significant drags on portfolio performance. Immediate removal recommended.*

---

## Data Quality Assessment

### Completeness Issues
| Issue Type | Count | Impact |
|------------|-------|--------|
| Missing BUY entries | ~25% | Inflated PnL for some wallets |
| Open positions (no SELL) | ~30% | Unrealized PnL unknown |
| Complete positions | ~45% | Reliable winrate calculations |

**Interpretation:** Many wallets show "N/A" winrates due to incomplete position data. This is expected when:
- Logs started mid-position (sell without prior buy)
- Positions still open (buy without sell yet)

**Recommendation:** Focus on wallets with 5+ complete positions for reliable metrics.

---

## Key Insights

### 1. Winrate ≠ Profitability
- GHOSTEE: Only 17.6% winrate but +69.68 SOL profit
- clukz: 28.6% winrate and -6.31 SOL loss
- **Lesson:** Position sizing and risk management matter more than winrate

### 2. High-Volume Consistency
- **Yenni:** 6 trades, 83.3% winrate - most consistent
- **jijo:** 22 trades, 81.8% winrate - high volume + consistency
- **thedoc:** 14 trades, 78.6% winrate - methodical approach

### 3. Whale Wallets Show Mixed Results
- Large position sizes don't guarantee success
- niggle: $586 SOL position → total loss
- clukz: $661 SOL invested → small loss despite massive position in UHI (-449 SOL)

### 4. Insider Cluster Performance
| Wallet | PnL | Status |
|--------|-----|--------|
| Insider5 | +1,397.53 | 🟢 Legendary (incomplete data) |
| Insider6 | +86.36 | 🟢 Profitable |
| Insider1 | -48.70 | 🔴 Remove |

*Mixed performance from related accounts suggests different strategies or operators.*

---

## Recommendations

### ✅ KEEP TRACKING (High Priority)
1. **Yenni** - 83.3% winrate, consistent profits
2. **jijo** - 81.8% winrate, high volume
3. **thedoc** - 78.6% winrate, methodical
4. **Cowboy** - 71.4% winrate, good volume
5. **OGANTD** - High absolute profits despite 50% winrate
6. **Insider6** - Solid performance in Insider cluster
7. **GHOSTEE** - Asymmetric returns, worth studying

### 📝 MONITOR CLOSELY (Medium Priority)
- Shy/Coyote, Euris, Sheep - Profitable but lower margins
- GakeVector, Gake1 - Need more complete data

### 🗑️ REMOVE FROM TRACKER (Immediate)
1. **niggle** - Massive loss (-381 SOL), 0% winrate
2. **Moonpie?** - Consistent losses (-197 SOL), 33% winrate
3. **SarahMilady** - Losing despite 50% winrate (-133 SOL)
4. **Insider1** - Complete loss on single trade
5. **clukz** - Underperforming, high capital usage
6. **Portapog** - No profitable closes recorded

### 🎯 ADD NEW WALLETS
See `alpha_wallets.txt` for Stealth Hunt 2.0 discoveries:
- LeBron ($17.6M profits)
- Nansen Smart Trader ($44.24M)
- E6Y MEV Bot ($300K/day)
- FARTCOIN Whale ($4.38M)
- TRUMP Millionaire ($4.8M)

---

## Action Items

- [x] Parse tracker logs (2,027 trades analyzed)
- [x] Calculate PnL and winrate for each wallet
- [x] Identify underperformers for removal
- [ ] Remove D-TIER wallets from wallets.txt
- [ ] Add S-TIER wallets from alpha_wallets.txt
- [ ] Set up alerts for Yenni/jijo/thedoc cluster buys
- [ ] Investigate GHOSTEE's asymmetric win strategy
- [ ] Replenish Helius API credits for himmel.py

---

## Appendix: Complete Wallet Data

```json
Full data available in: tracker_analysis.json
```

---

*Report generated by ShadowHunter Analytics*  
*For questions, refer to memory/2026-03-16.md*
