# Autonomous Trading Safety Quick Reference
## Keep This Visible During All Trading Operations

---

## 🚨 EMERGENCY KILL SWITCH

**TO HALT ALL TRADING IMMEDIATELY:**
1. Click [KILL SWITCH] button on dashboard, OR
2. Send SMS "STOP ALL" to emergency number, OR
3. Call Risk Manager: [PHONE NUMBER]

**Kill switch activates in <1 second and:**
- Cancels ALL open orders
- Prevents ANY new orders
- Sends alerts to all team members
- Logs incident for review

---

## ⚠️ CIRCUIT BREAKER TRIGGERS

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Daily Loss | ≥2% of portfolio | AUTO-HALT 24 hours |
| Weekly Loss | ≥5% of portfolio | AUTO-HALT + Review |
| Max Drawdown | ≥15% from peak | AUTO-HALT |
| Consecutive Losses | 5 in a row | PAUSE 15 min |
| API Error Rate | >5% in 1 hour | PAUSE + Investigate |
| Unauthorized Access | Any attempt | KILL SWITCH |

---

## 📊 HARD LIMITS (Cannot Override)

| Limit | Value | What It Means |
|-------|-------|---------------|
| Per-Trade Risk | 1% of capital | Max loss per position |
| Position Size | 5% of capital | Max $ in single trade |
| Single Asset | 10% of capital | Max exposure to one symbol |
| Leverage | 3x max | Never exceed 3x leverage |
| Daily Trades | 50 max | Prevents overtrading |
| Open Positions | 20 max | Manageable monitoring |

---

## 🔐 SECURITY CHECKLIST

### Before Trading:
- [ ] API keys have NO withdrawal permissions
- [ ] IP whitelisting is active
- [ ] 2FA enabled on all accounts
- [ ] Kill switch tested and functional
- [ ] Dashboard monitoring is live

### Daily:
- [ ] Review overnight P&L
- [ ] Check all positions match system
- [ ] Verify no unauthorized API access
- [ ] Test kill switch responsiveness

### Weekly:
- [ ] Rotate API keys if >60 days old
- [ ] Review access logs
- [ ] Update emergency contacts if needed
- [ ] Test backup systems

---

## 📋 INCIDENT RESPONSE (5 Steps)

### 1. DETECT (0-30 sec)
- Alert fires or anomaly noticed
- Acknowledge immediately

### 2. ASSESS (30 sec - 2 min)
- What happened?
- How bad is it?
- Who needs to know?

### 3. CONTAIN (2-5 min)
- **If in doubt, HIT KILL SWITCH**
- Cancel open orders
- Document state

### 4. COMMUNICATE (5-15 min)
- Notify team via emergency channel
- Update every 30 min until resolved

### 5. RESOLVE (15-60 min)
- Find root cause
- Fix or rollback
- Test before resuming

---

## 🔄 RECOVERY PROCEDURES

### After Kill Switch:
1. **DO NOT** resume immediately
2. Review what triggered it
3. Paper trade 24 hours to verify
4. Resume with 25% size
5. Gradually scale up over 3-5 days

### After Bad Trade:
1. Don't revenge trade
2. Stick to position sizing rules
3. Review strategy if pattern emerges
4. Take break if emotional

### After Code Issue:
1. Rollback to last stable version
2. Verify system health
3. Fix in staging first
4. Deploy with enhanced monitoring

---

## 📈 POSITION SIZING FORMULA

```
Position Size = (Risk % × Capital) ÷ (Entry - Stop)

Example (1% risk on $100K, $50 entry, $48 stop):
= (0.01 × $100,000) ÷ ($50 - $48)
= $1,000 ÷ $2
= 500 shares ($25,000 position)
```

**NEVER risk more than 1-2% per trade!**

---

## 🎯 KEY PHONE NUMBERS

| Role | Name | Phone | When to Call |
|------|------|-------|--------------|
| Risk Manager | [NAME] | [PHONE] | Kill switch, major losses |
| Tech Lead | [NAME] | [PHONE] | System issues, bugs |
| Exchange | [NAME] | [PHONE] | API issues, account problems |
| Emergency | [NAME] | [PHONE] | After hours critical |

---

## ⚡ QUICK DECISIONS

| Situation | Decision |
|-----------|----------|
| Down 2% in one day | STOP - Daily limit hit |
| System acting weird | PAUSE - Investigate |
| Unusual API activity | KILL SWITCH - Security |
| Market crashing | Reduce size 50% |
| Slippage >1% | Alert + reduce size |
| 5 losses in row | Pause + review |

---

## 📝 DAILY CHECKLIST

### Morning (Before Market Open):
- [ ] Check overnight news/events
- [ ] Review positions and P&L
- [ ] Verify system health
- [ ] Confirm kill switch functional
- [ ] Check API connectivity

### During Trading:
- [ ] Monitor dashboard continuously
- [ ] Watch for alerts
- [ ] Verify fills match expectations
- [ ] Track daily P&L vs limit

### Evening (After Close):
- [ ] Reconcile all positions
- [ ] Review day's trades
- [ ] Check for errors or anomalies
- [ ] Prepare for next day

---

## 🎓 LESSONS FROM HISTORY

### Knight Capital ($440M loss in 45 min)
- Test code in production = DISASTER
- Incomplete deployments = DANGER
- No auto kill switch = CATASTROPHE

### Flash Crash ($1T temporarily lost)
- Liquidity can VANISH instantly
- HFTs amplify moves
- Circuit breakers are essential

### LUNA Collapse ($40-60B lost)
- Algorithmic stability is FRAGILE
- High yields = high risk
- Diversification is critical

---

**Remember: The goal is to survive to trade another day.**

*Preserve capital. Detect anomalies. Act decisively.*
