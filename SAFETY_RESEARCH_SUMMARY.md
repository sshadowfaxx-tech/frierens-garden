# Autonomous Trading Safety Research Summary

**Research Date:** March 28, 2026  
**Researcher:** AI Safety Engineer (Subagent)

---

## Executive Summary

This research investigated risk management and safety controls for autonomous trading systems. The findings are based on historical case studies (Knight Capital, Flash Crash, LUNA/3AC), industry best practices, and regulatory requirements.

**Key Deliverables:**
1. `SAFETY_FRAMEWORK.md` - Comprehensive 27KB safety framework document
2. `SAFETY_QUICK_REFERENCE.md` - Operator quick reference guide
3. This research summary

---

## 1. Historical Horror Stories

### Knight Capital (2012) - The $440 Million Deployment Error
**What happened:**
- Deployed new code for NYSE Retail Liquidity Program
- Updated only 7 of 8 servers; 8th server had dormant "Power Peg" test code
- Power Peg was designed to "buy high, sell low" for testing
- Broken confirmation logic meant it never stopped sending orders
- In 45 minutes: 4 million trades, $7B in unwanted positions
- Human "fix" (rollback) made it worse by deploying bad code to all 8 servers

**Key Lessons:**
1. Always remove test code from production
2. Deployments must be atomic (all-or-nothing)
3. Pre-trade risk controls would have caught this
4. Auto kill switch would have limited damage to seconds
5. Human incident response without procedures made it worse

### Flash Crash (2010) - $1 Trillion in Minutes
**What happened:**
- Waddell & Reed executed $4.1B sell order using volume-targeting algorithm
- Algorithm sold at 9% of volume without price sensitivity
- HFTs withdrew liquidity amplifying the move
- Dow Jones dropped 998 points (9%) in minutes
- Recovered 36 minutes later

**Key Lessons:**
1. Algorithms need price-sensitive execution logic
2. Market-wide circuit breakers prevent cascading failures
3. Liquidity can evaporate instantly
4. HFT feedback loops amplify market moves

### LUNA/UST Collapse (2022) - $40-60 Billion Lost
**What happened:**
- Algorithmic stablecoin UST lost peg to $1
- Death spiral: arbitrageurs minted LUNA to buy discounted UST
- Increased LUNA supply drove price down, accelerating UST selling
- Anchor Protocol's unsustainable 20% yield collapsed
- Three Arrows Capital (3AC) bankrupt 35 days later

**Key Lessons:**
1. Algorithmic stability mechanisms fail under stress
2. High yields often mask unsustainable economics
3. Concentrated positions (3AC's LUNA holdings) create systemic risk
4. DeFi protocols need circuit breakers

---

## 2. Risk Taxonomy Summary

### Technical Failures
- Code deployment errors (Knight Capital)
- Logic errors and bugs
- Integration failures (API, data feeds)
- Infrastructure failures
- Race conditions in concurrent processing

### Market Risks
- Flash crashes and extreme volatility
- Liquidity evaporation
- Correlation breakdowns (diversification fails)
- Gap risk (price jumps past stops)
- Oracle failures (stale/manipulated prices)

### Operational Risks
- API key compromise
- Human error in overrides
- Over-leverage
- Concentration risk
- Cascading failures

### Model/Strategy Risks
- Overfitting (backtest vs. live performance gap)
- Regime changes (strategy stops working)
- Data snooping bias
- Alpha decay (edge erodes)
- Black swan events

---

## 3. Essential Safety Controls

### Hard Limits (Non-Negotiable)
| Limit | Recommendation |
|-------|----------------|
| Daily Loss Limit | 2% of portfolio - HALT 24h |
| Weekly Loss Limit | 5% of portfolio - HALT + review |
| Max Drawdown | 15% from peak - HALT |
| Per-Trade Risk | 1% of capital |
| Position Size | 5% of capital max |
| Leverage | 3x maximum |

### Circuit Breakers
| Trigger | Response |
|---------|----------|
| 5 consecutive losses | Pause 15 min |
| Volatility spike (>50%) | Reduce size 50% |
| API error rate >5% | PAUSE + investigate |
| Slippage >1% | ALERT + reduce size |
| Unauthorized access | KILL SWITCH |

### Kill Switch Requirements
1. **Independence**: Separate infrastructure from trading system
2. **Speed**: <1 second from trigger to halt
3. **Completeness**: Cancels all orders, prevents new ones
4. **Notification**: Immediate alerts to all stakeholders
5. **Audit Trail**: Log all activations
6. **Recovery**: Tested, documented procedures

---

## 4. Monitoring Dashboard Requirements

### Real-Time Metrics (<1 second update)
- Total equity and P&L
- Open positions and exposure
- Maximum drawdown
- Win rate (rolling)
- Active alerts status

### Risk Metrics (<5 second update)
- Value at Risk (VaR)
- Expected Shortfall (CVaR)
- Portfolio Greeks (Delta, Gamma, Theta, Vega)
- Leverage and margin utilization

### Execution Quality (Per trade)
- Slippage analysis
- Fill rates
- Rejected order rate
- Average execution time

---

## 5. Human Oversight Framework

### Three Governance Models

**Human-in-the-Loop (HITL)**
- Use: High-stakes decisions, new strategies, large orders
- Flow: Signal → Human review → Approval → Execution
- Latency: Minutes to hours
- Examples: Strategy deployment, positions >$10K

**Human-on-the-Loop (HOTL)**
- Use: Routine trading within parameters
- Flow: Auto-execution + Real-time monitoring + Override capability
- Latency: Milliseconds to seconds
- Examples: Standard operations, approved strategies

**Human-over-the-Loop**
- Use: Mature strategies with strict boundaries
- Flow: Humans set rules → Bot operates → Periodic review
- Latency: None (fully automated)
- Examples: Well-tested strategies, stable markets

### Decisions Requiring Human Approval
1. New strategy deployment
2. Parameter changes >20%
3. New asset classes
4. Leverage increases
5. Kill switch overrides
6. Daily loss limit increases
7. API key regeneration

---

## 6. Operational Safeguards

### API Security Best Practices
- **Principle of Least Privilege**: Trade-only, NO WITHDRAWALS
- **IP Whitelisting**: Restrict to known server IPs
- **Key Rotation**: Every 60-90 days
- **Separate Keys**: Different keys for trading/monitoring/data
- **Encrypted Storage**: Never hardcode in source

### Infrastructure Security
- Dedicated VPS/cloud (no shared hosting)
- Firewall configured
- SSH key authentication (no passwords)
- Regular security updates
- DDoS protection
- VPN for remote access

### Deployment Safety
- Version control with signed commits
- Mandatory code review
- Automated testing (unit + integration)
- Staging environment mirroring production
- Canary deployments (gradual rollout)
- Feature flags for easy rollback

---

## 7. Regulatory Compliance Requirements

### Key Regulations
| Regulation | Jurisdiction | Requirements |
|------------|--------------|--------------|
| SEC Market Access Rule | US | Pre-trade risk controls, credit checks |
| MiFID II | EU | Algorithm testing, kill switches, monitoring |
| CFTC Automated Trading | US | Risk controls, compliance reports |
| EU AI Act | EU | Human oversight for high-risk AI |

### Required Documentation
- Algorithm description and logic
- Risk management procedures
- Testing and validation results
- Incident response procedures
- Audit trails (retain 7+ years)
- Model governance documentation
- Change management logs

---

## 8. Testing Requirements

### Backtesting
- Minimum 5 years historical data
- 20% out-of-sample holdout
- Include realistic slippage + fees
- No look-ahead bias
- Monte Carlo simulations (10,000+ paths)

### Paper Trading
- Minimum 30 days
- Include volatile market periods
- Match live position sizing
- Realistic fill simulation

### Stress Testing Scenarios
- Flash crash: 10% drop in 10 minutes
- Corruption stress: All correlations = 1.0
- Liquidity stress: 50% reduction
- Volatility stress: 3x normal sustained
- Gap risk: 20% overnight gap

---

## 9. Key Statistics from Research

| Metric | Value | Source |
|--------|-------|--------|
| Knight Capital loss | $440M in 45 min | Case study |
| Flash Crash value loss | $1 trillion (temporary) | SEC report |
| LUNA/UST collapse | $40-60B lost | Market data |
| 3AC bankruptcy | 35 days after LUNA | News reports |
| HFT volume (2009 peak) | 61% of trading | Research |
| Minor flash crashes/day | ~14 daily | Research |

---

## 10. Critical Recommendations

### Priority 1: Must Have Before Trading
1. ✅ Kill switch with <1 second response
2. ✅ Daily loss limit (2%) with auto-halt
3. ✅ Position limits (5% max per position)
4. ✅ API security (no withdrawals, IP whitelist)
5. ✅ Real-time monitoring dashboard

### Priority 2: Critical for Safety
1. ✅ Circuit breakers for volatility/errors
2. ✅ Human oversight framework
3. ✅ Incident response procedures
4. ✅ Audit logging system
5. ✅ Paper trading period (30+ days)

### Priority 3: Important for Robustness
1. ✅ Stress testing
2. ✅ Multiple kill switch types
3. ✅ Code deployment safeguards
4. ✅ Regular security audits
5. ✅ Regulatory compliance documentation

---

## Conclusion

The research clearly shows that autonomous trading systems require a defense-in-depth approach to safety. No single control is sufficient - multiple layers of protection are necessary.

**The most important principles:**
1. **Preserve capital** - Hard limits are non-negotiable
2. **Detect early** - Real-time monitoring is essential
3. **Act fast** - Kill switches must be automatic
4. **Trust but verify** - Human oversight remains critical
5. **Learn from history** - The same mistakes keep happening

**The goal is not to eliminate risk, but to survive to trade another day.**

---

**Documents Created:**
- `/workspace/SAFETY_FRAMEWORK.md` (27KB) - Comprehensive safety framework
- `/workspace/SAFETY_QUICK_REFERENCE.md` (5KB) - Operator quick reference
