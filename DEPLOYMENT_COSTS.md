# ShadowHunter Deployment Cost Analysis
## Complete TCO (Total Cost of Ownership) Comparison

---

## Summary Table

| Option | Upfront Cost | Monthly Cost | 1-Year TCO | 3-Year TCO | Best For |
|--------|--------------|--------------|------------|------------|----------|
| **Oracle Cloud Free Tier** | $0 | $0 | $0 | $0 | Budget-conscious, technical users |
| **Hetzner CX21** | $0 | €5.35 (~$5.80) | ~$70 | ~$210 | Best value production |
| **Hetzner CPX21** | $0 | €6.99 (~$7.60) | ~$91 | ~$273 | Production + growth room |
| **AWS Lightsail** | $0 | $12 | $144 | $432 | AWS ecosystem users |
| **DigitalOcean** | $0 | $12 | $144 | $432 | Beginners, great docs |
| **Vultr** | $0 | $10 | $120 | $360 | Global latency needs |
| **Raspberry Pi 5** | ~$150 | ~$3-5* | ~$190 | ~$260 | Home lab, privacy-focused |
| **Intel NUC** | ~$400-600 | ~$3-5* | ~$460 | ~$520 | Power users, longevity |

*Home electricity costs estimated at $3-5/month for 24/7 operation

---

## 1. Oracle Cloud Free Tier (ARM Instance)

### What You Actually Get (Always Free)
- **4 ARM Ampere vCPUs** (burstable, ~2.8GHz equivalent)
- **24GB RAM** (massive overkill)
- **200GB block storage**
- **10TB/month egress**
- **2 AMD VMs** (backup option)

### Costs
| Item | Cost | Notes |
|------|------|-------|
| Compute | $0 | Forever free tier |
| Storage | $0 | First 200GB free |
| Bandwidth | $0 | 10TB/month included |
| **Total Upfront** | **$0** | |
| **Total Monthly** | **$0** | |

### Hidden Costs / Gotchas
| Risk | Likelihood | Cost |
|------|------------|------|
| Account termination for "abuse" | Medium | Migration time (hours) |
| Support requests (no free support) | High | DIY troubleshooting only |
| Complex setup | 100% | 2-4 hours initial config |
| IPv4 exhaustion (need to request) | Medium | IPv6 only fallback |

### Real-World Experience
```
✅ Pros:
   - Actually free, no credit card games
   - Massive resources (24GB RAM!)
   - Can run 3x tracker instances
   
⚠️ Cons:
   - ARM architecture (some Docker images break)
   - "Always Free" terms can change
   - Oracle's reputation for account shutdowns
   - No human support
   - IPv4 requires request (usually approved in 24h)
```

### Best For
- Students, hobbyists
- Proof-of-concept before spending money
- Technical users comfortable with DIY

---

## 2. Hetzner Cloud (Germany/EU)

### Option A: CX21 (Shared vCPU)

| Spec | Details |
|------|---------|
| vCPUs | 2 (shared) |
| RAM | 4GB |
| Storage | 40GB NVMe |
| Traffic | 20TB/month |
| Location | Germany, Finland, USA |

**Monthly: €5.35 (~$5.80 USD)**

### Option B: CPX21 (Dedicated vCPU)

| Spec | Details |
|------|---------|
| vCPUs | 2 (dedicated) |
| RAM | 4GB |
| Storage | 80GB NVMe |
| Traffic | 20TB/month |

**Monthly: €6.99 (~$7.60 USD)**

### Costs Breakdown
| Item | CX21 | CPX21 |
|------|------|-------|
| Upfront | $0 | $0 |
| Monthly | ~$5.80 | ~$7.60 |
| Year 1 | ~$70 | ~$91 |
| Year 2 | ~$140 | ~$182 |
| Year 3 | ~$210 | ~$273 |

### Hidden Costs
| Item | Cost | When |
|------|------|------|
| Backups | 20% of server cost | Optional, ~$1.20/month |
| Snapshots | €0.01/GB/month | Manual only |
| Floating IP | €1.08/month | If you need static IP |
| Extra traffic | €1.07/TB | Only after 20TB |
| Windows license | +€5.35/month | Don't use Windows |

### Real-World Experience
```
✅ Pros:
   - Cheapest reliable option
   - NVMe storage (fast PostgreSQL)
   - No "surprise" bills ever
   - Excellent network (German backbone)
   - Easy Docker setup
   
⚠️ Cons:
   - EU servers (100-150ms latency from US)
   - No free tier to test
   - Basic support (tickets only)
   - 19% VAT for EU customers (included in price above)
```

### Best For
- Production deployment on a budget
- Privacy-conscious users (EU GDPR)
- Users who value predictable costs

---

## 3. AWS Lightsail

### Instance Options

| Plan | Specs | Price | Suitable? |
|------|-------|-------|-----------|
| 512MB | 1 vCPU, 512MB RAM | $3.50 | ❌ Too small |
| 1GB | 1 vCPU, 1GB RAM | $5 | ⚠️ Minimum, tight |
| **2GB** | **1 vCPU, 2GB RAM** | **$8** | ✅ **Minimum** |
| **4GB** | **2 vCPU, 4GB RAM** | **$12** | ✅ **Recommended** |
| 8GB | 2 vCPU, 8GB RAM | $24 | ✅ Overkill |

### Costs Breakdown (4GB Plan)
| Item | Cost |
|------|------|
| Upfront | $0 |
| Monthly | $12 |
| Year 1 | $144 |
| Year 2 | $288 |
| Year 3 | $432 |

### Hidden Costs
| Item | Cost | Notes |
|------|------|-------|
| Snapshots | $0.05/GB/month | 40GB = $2/month |
| Extra storage | $0.10/GB/month | First 40GB included |
| Data transfer | First 2TB free, then $0.09/GB | Rarely hit |
| Static IP | Free when attached | $0.005/hr if detached |
| Support | $29/month (Developer) | DIY only without |

### Free Tier Quirks
- 750 hours/month free for 3 months (any size)
- 12 months of "free tier" (t2.micro only, too small)
- After 3 months: full price

### Real-World Experience
```
✅ Pros:
   - AWS ecosystem (S3, CloudWatch, etc.)
   - 3-month free trial (any size!)
   - Easy snapshots/backups
   - One-click apps (Docker preinstalled)
   - US regions (low latency)
   
⚠️ Cons:
   - 50% more expensive than Hetzner
   - "AWS complexity tax" (learning curve)
   - Egress fees if you exceed limits
   - Support costs extra
```

### Best For
- Already using AWS
- Want managed backups
- Need US-based servers
- Corporate/compliance requirements

---

## 4. DigitalOcean (DO)

### Droplet Options

| Plan | Specs | Price |
|------|-------|-------|
| Basic 1GB | 1 vCPU, 1GB RAM | $6 |
| **Basic 2GB** | **1 vCPU, 2GB RAM** | **$12** |
| Basic 4GB | 2 vCPU, 4GB RAM | $24 |
| Premium AMD/Intel | 1 vCPU, 2GB RAM | $15 |

### Costs Breakdown (Basic 2GB)
| Item | Cost |
|------|------|
| Upfront | $0 |
| Monthly | $12 |
| Year 1 | $144 |
| Year 3 | $432 |

### Credit Offers
- **$200 free credit for 60 days** (new users)
- Effectively: 16 months free on 2GB plan
- After credit: $144/year

### Hidden Costs
| Item | Cost | Notes |
|------|------|-------|
| Backups | 20% of droplet cost | ~$2.40/month |
| Snapshots | $0.05/GB/month | Manual, billed hourly |
| Block storage | $0.10/GB/month | Add volumes |
| Extra bandwidth | $0.01/GB | First 500GB-1TB included |
| Managed DB | $15/month+ | Don't use for tracker |

### Real-World Experience
```
✅ Pros:
   - $200 free credit (massive!)
   - Best documentation/tutorials
   - Simple, no-nonsense UI
   - "One-click Docker" apps
   - Active community
   - Good balance price/performance
   
⚠️ Cons:
   - Same price as AWS Lightsail
   - 50% pricier than Hetzner
   - Basic plan = shared CPU
   - Support costs extra
```

### Best For
- Beginners (best tutorials)
- Learning Docker/cloud
- Maximize free credit period
- Community support

---

## 5. Vultr

### Cloud Compute Options

| Plan | Specs | Price |
|------|-------|-------|
| Cloud 1GB | 1 vCPU, 1GB RAM | $5 |
| **Cloud 2GB** | **1 vCPU, 2GB RAM** | **$10** |
| Cloud 4GB | 2 vCPU, 4GB RAM | $20 |
| High Frequency | 1 vCPU, 2GB RAM | $12 |

### Costs Breakdown (Cloud 2GB)
| Item | Cost |
|------|------|
| Upfront | $0 |
| Monthly | $10 |
| Year 1 | $120 |
| Year 3 | $360 |

### Credit Offers
- $100 free credit (30 days)
- Less generous than DO

### Hidden Costs
| Item | Cost | Notes |
|------|------|-------|
| Backups | 20% of server cost | ~$2/month |
| Snapshots | $0.05/GB/month | |
| Extra bandwidth | $0.01/GB | First 2TB included |
| DDoS protection | $10/month | Usually not needed |

### Real-World Experience
```
✅ Pros:
   - Cheaper than DO/AWS ($10 vs $12)
   - 2TB bandwidth (most generous)
   - Multiple US/EU/Asia locations
   - Bitcoin payment accepted
   - Fast provisioning
   
⚠️ Cons:
   - Smaller community than DO
   - Documentation not as good
   - "You get what you pay for" support
```

### Best For
- Global latency optimization
- Accepting crypto payments
- Bandwidth-heavy applications
- $2/month matters

---

## 6. Raspberry Pi 5 (8GB)

### Upfront Costs

| Item | Cost | Notes |
|------|------|-------|
| Raspberry Pi 5 (8GB) | $80 | Official price |
| Power supply (27W USB-C) | $15 | Official required |
| MicroSD 64GB (boot) | $15 | SanDisk Extreme |
| **NVMe SSD 256GB** | **$40** | **Required, not optional** |
| NVMe HAT (M.2 adapter) | $25 | Pimoroni or official |
| Case with cooling | $15 | Passive + fan recommended |
| Ethernet cable | $5 | Cat6 |
| **Total Upfront** | **~$195** | Can trim to ~$150 with deals |

### Monthly Operating Costs

| Item | Monthly | Notes |
|------|---------|-------|
| Electricity | ~$2-4 | 15W average, $0.15/kWh |
| Internet | $0 | Uses existing connection |
| Dynamic DNS | $0-5 | If no static IP |
| **Total Monthly** | **~$2-4** | |

### TCO Over Time
| Period | Cost |
|--------|------|
| Year 1 | ~$240 (hardware + electricity) |
| Year 2 | ~$40 (electricity only) |
| Year 3 | ~$55 (electricity + 1 SSD replacement) |
| **3-Year TCO** | **~$335** |

### Hidden Costs
| Item | Cost | When |
|------|------|------|
| SSD replacement | $40 | Every 2-3 years (wear) |
| SD card replacement | $15 | Every 1-2 years (if used) |
| Cooling upgrades | $10-20 | If thermal throttling |
| UPS (power backup) | $50-80 | Optional but recommended |
| Time investment | 10-20 hours | Setup, maintenance |

### Failure Modes
| Component | Lifespan | Replacement Cost |
|-----------|----------|------------------|
| MicroSD card | 1-2 years | $15 |
| NVMe SSD | 3-5 years | $40 |
| Power supply | 5+ years | $15 |
| Pi board | 10+ years | $80 |

### Real-World Experience
```
✅ Pros:
   - One-time cost
   - Complete privacy (data stays home)
   - No recurring bills
   - Fun to build/maintain
   - Can repurpose for other projects
   - No "cloud provider" risks (shutdowns, billing issues)
   
⚠️ Cons:
   - $195 upfront vs $0 for cloud
   - Home internet reliability
   - No DDoS protection
   - Power outages = downtime
   - You are the sysadmin
   - ARM architecture (minor compatibility issues)
   - Not truly "production grade"
```

### Best For
- Privacy paranoid
- Learning/hobby projects
- Already have internet + power
- Want zero monthly bills
- Home automation enthusiasts

---

## 7. Intel NUC / Mini PC

### Upfront Costs

| Option | Specs | Price |
|--------|-------|-------|
| **Budget: Beelink SER5** | Ryzen 5, 8GB, 256GB SSD | ~$300 |
| **Mid: Intel NUC 11** | i3, 8GB, 256GB SSD | ~$450 |
| **High: Intel NUC 13 Pro** | i5, 16GB, 512GB SSD | ~$650 |

### Recommended Config (Beelink SER5)
| Item | Cost |
|------|------|
| Beelink SER5 (barebones) | $250 |
| 16GB DDR4 RAM | $40 |
| 512GB NVMe SSD | $50 |
| **Total** | **~$340** |

### Monthly Operating Costs
| Item | Monthly |
|------|---------|
| Electricity | ~$4-6 | 25W average |
| Internet | $0 | Existing |
| **Total** | **~$4-6** |

### TCO Over Time
| Period | Cost |
|--------|------|
| Year 1 | ~$400 |
| Year 2 | ~$60 |
| Year 3 | ~$75 |
| **3-Year TCO** | **~$535** |

### Advantages Over Raspberry Pi
| Feature | NUC | Pi 5 |
|---------|-----|------|
| CPU performance | 3-4x faster | Baseline |
| x86 compatibility | ✅ Native | ❌ Emulation |
| NVMe slot | ✅ Built-in | ❌ Adapter needed |
| Thermal management | ✅ Active cooling | ⚠️ Needs case |
| Expansion | ✅ RAM, SSD, USB | Limited |
| Lifespan | 5-10 years | 3-5 years |

### Real-World Experience
```
✅ Pros:
   - x86 architecture (no compatibility issues)
   - Upgradeable RAM/storage
   - Professional reliability
   - Can run Windows if needed
   - Multiple Docker containers
   - Silent operation (most models)
   
⚠️ Cons:
   - $300-600 upfront
   - 3-year TCO > cloud options
   - Overkill for just tracker
   - Still need backup power
   - You are the sysadmin
```

### Best For
- Power users
- Multiple services (tracker + web + ML)
- Long-term 5+ year deployment
- Professional home lab
- x86 Docker image compatibility

---

## Detailed Cost Comparison (3-Year TCO)

### Scenario: 40 wallets, 24/7 operation

| Option | Year 1 | Year 2 | Year 3 | 3-Year Total | Monthly Avg |
|--------|--------|--------|--------|--------------|-------------|
| **Oracle Free** | $0 | $0 | $0 | **$0** | **$0** |
| Hetzner CX21 | $70 | $70 | $70 | $210 | $5.83 |
| Vultr 2GB | $120 | $120 | $120 | $360 | $10.00 |
| DO 2GB | $144 | $144 | $144 | $432 | $12.00 |
| AWS Lightsail 4GB | $144 | $144 | $144 | $432 | $12.00 |
| **Pi 5** | $240 | $40 | $55 | **$335** | **$9.31** |
| **Intel NUC** | $400 | $60 | $75 | **$535** | **$14.86** |

---

## Cost Per Wallet (3-Year)

Assuming 40 wallets monitored:

| Option | 3-Year TCO | Cost Per Wallet |
|--------|------------|-----------------|
| Oracle Free | $0 | **$0.00** |
| Hetzner CX21 | $210 | **$1.75** |
| Pi 5 | $335 | **$2.79** |
| Vultr 2GB | $360 | **$3.00** |
| DO 2GB | $432 | **$3.60** |
| AWS Lightsail 4GB | $432 | **$3.60** |
| Intel NUC | $535 | **$4.46** |

---

## Hidden Cost Analysis

### Time Investment (Setup)

| Option | Setup Time | Learning Curve |
|--------|------------|----------------|
| Oracle Free | 4-6 hours | Steep |
| Hetzner | 30 min | Easy |
| DO | 20 min | Easiest |
| AWS | 45 min | Moderate |
| Vultr | 30 min | Easy |
| Pi 5 | 3-4 hours | Moderate |
| Intel NUC | 2-3 hours | Moderate |

**Your time value:** If you bill $50/hour, Oracle Free's 5 hours = $250 in time cost, making it more expensive than Hetzner!

### Maintenance Time (Per Year)

| Option | Updates/Month | Annual Maintenance |
|--------|---------------|-------------------|
| Cloud VPS | 1-2 hours | ~20 hours |
| Pi 5 | 3-4 hours | ~40 hours |
| Intel NUC | 2-3 hours | ~30 hours |

Cloud providers handle hardware, security patches, DDoS. Home labs = you're the sysadmin.

---

## Risk-Adjusted Cost

### Failure Probability (Annual)

| Option | Hardware Fail | Provider Shutdown | Your Error |
|--------|--------------|-------------------|------------|
| Oracle Free | N/A | 15% | 5% |
| Hetzner | 1% | 0.1% | 5% |
| DO | 1% | 0.1% | 5% |
| AWS | 0.5% | 0.01% | 5% |
| Pi 5 | 10% | N/A | 10% |
| Intel NUC | 3% | N/A | 8% |

### Downtime Cost (If Tracking 40 Alpha Wallets)

Missing a 10x memecoin call because of downtime:
- Conservative: $1,000 opportunity cost
- Realistic: $5,000-10,000+

**Reliability is worth paying for.**

---

## My Recommendations by Use Case

### 💰 Absolute Cheapest (Accept Risk)
**Oracle Cloud Free Tier**
- $0 forever
- Accept 15% chance of account issues
- Only if you're technical

### 🏆 Best Value (Production)
**Hetzner CX21**
- $5.80/month
- German reliability
- 99.9% uptime
- TCO: $210 / 3 years

### 🎓 Beginner Friendliest
**DigitalOcean with $200 Credit**
- 16 months free
- Best tutorials
- $144/year after
- Great learning experience

### 🇺🇸 US-Based (Low Latency)
**AWS Lightsail 4GB**
- $12/month
- US regions
- 3-month free trial
- Managed backups

### 🔒 Privacy Paranoid
**Raspberry Pi 5**
- $195 upfront
- $3/month electricity
- No cloud = no surveillance
- Data never leaves home

### 🚀 Future-Proof / Growth
**Intel NUC + Hetzner Backup**
- NUC for primary (performance)
- Hetzner CX21 as hot backup ($5.80/month)
- Total: ~$20/month
- Zero downtime architecture

---

## The "Just Tell Me What To Do" Answer

**Starting out (< 6 months):**
→ DigitalOcean with $200 credit (16 months free)

**Production, budget-conscious:**
→ Hetzner CX21 ($5.80/month)

**Production, enterprise:**
→ AWS Lightsail 4GB ($12/month)

**Privacy-first:**
→ Raspberry Pi 5 ($195 upfront)

**Maximum savings, accept risk:**
→ Oracle Cloud Free ($0)

---

*Prices current as of March 2026. Exchange rates: €1 = $1.09 USD*
