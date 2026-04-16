# Cheap VPS Alternatives to AWS for ShadowHunter

**Research Date:** March 2026  
**Purpose:** Find sub-$20/month VPS alternatives for hosting ShadowHunter Discord bot  
**Comparison Period:** 1-Year Total Cost of Ownership (TCO)

---

## Executive Summary

AWS is significantly more expensive than alternative VPS providers for running a Discord bot like ShadowHunter. The cheapest comparable AWS instance (t4g.medium with 2 vCPU/4GB RAM) costs **~$24.53/month on-demand**, while alternative providers offer similar specs for **$3.50-$8/month**—a **70-85% cost reduction**.

### Key Findings
- **Best Overall Value:** Hetzner CX23 (2 vCPU/4GB) at ~$3.80/month
- **Best with Database:** Contabo VPS S (4 vCPU/8GB) at ~$6.50/month
- **Best US Performance:** Vultr High Frequency at ~$6/month
- **Avoid:** AWS for 24/7 workloads unless using Spot instances

---

## ShadowHunter Workload Requirements

Based on Discord bot hosting best practices and typical feature sets (web scraping, API calls, database storage):

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 2 GB | 4 GB |
| **vCPU** | 1 core | 2 cores |
| **Storage** | 20 GB | 40-80 GB |
| **Bandwidth** | 1 TB/mo | 2-5 TB/mo |
| **Network** | 100 Mbps+ | 500 Mbps+ |

---

## Provider Comparison

### 1. HETZNER 🇩🇪 (Winner: Best Price/Performance)

**Company:** German cloud provider, operating since 1997  
**Strengths:** Unbeatable pricing, 20TB traffic included, NVMe storage  
**Weaknesses:** EU-only locations (Germany/Finland for cheapest), limited US presence

#### Pricing Table (EU Regions - Germany/Finland)

| Plan | vCPU | RAM | Storage | Traffic | Monthly Price | $/vCPU | $/GB RAM |
|------|------|-----|---------|---------|---------------|--------|----------|
| **CX23** | 2 (shared) | 4 GB | 40 GB NVMe | 20 TB | **€3.49 (~$3.80)** | $1.90 | $0.95 |
| **CAX11** | 2 (shared ARM) | 4 GB | 40 GB NVMe | 20 TB | **€3.79 (~$4.10)** | $2.05 | $1.03 |
| **CX33** | 4 (shared) | 8 GB | 80 GB NVMe | 20 TB | **€5.49 (~$5.95)** | $1.49 | $0.74 |
| **CPX11** | 2 (shared) | 2 GB | 40 GB NVMe | 20 TB | **€4.99 (~$5.40)** | $2.70 | $2.70 |
| **CPX21** | 3 (shared) | 4 GB | 80 GB NVMe | 20 TB | **€7.55 (~$8.18)** | $2.73 | $2.05 |
| **CCX13** | 2 (dedicated) | 8 GB | 80 GB NVMe | 20 TB | **€12.49 (~$13.54)** | $6.77 | $1.69 |

#### Regional Pricing Differences

| Region | Price Premium | Traffic Included | Best For |
|--------|---------------|------------------|----------|
| Germany/Finland | Baseline | 20 TB | Maximum savings |
| USA (Ashburn/Hillsboro) | +8% to +36% | 1-8 TB | US latency requirements |
| Singapore | +40% to +67% | 0.5-8 TB | Asia-Pacific users |

#### Best for ShadowHunter
**CX23** - 2 vCPU, 4GB RAM at $3.80/month  
- Sufficient for bot + light database
- 20TB traffic more than enough
- Can upgrade to CX33 (4 vCPU/8GB) if needed for $5.95

#### Cost Analysis (1 Year)
| Metric | Cost |
|--------|------|
| Monthly | $3.80 |
| 1-Year Total | **$45.60** |
| vs AWS t3.medium | **Save $318.84/year (87%)** |

---

### 2. DIGITALOCEAN 🇺🇸 (Winner: Developer Experience)

**Company:** US-based, developer-focused since 2011  
**Strengths:** Excellent documentation, simple UI, 99.99% SLA  
**Weaknesses:** Higher prices than Hetzner, bandwidth overages at $0.01/GB

#### Pricing Table

| Plan | vCPU | RAM | Storage | Transfer | Monthly Price | $/vCPU | $/GB RAM |
|------|------|-----|---------|----------|---------------|--------|----------|
| Basic (512MB) | 1 (shared) | 0.5 GB | 25 GB SSD | 500 GB | **$4.00** | $4.00 | $8.00 |
| Basic (1GB) | 1 (shared) | 1 GB | 25 GB SSD | 1 TB | **$6.00** | $6.00 | $6.00 |
| Basic (2GB) | 1 (shared) | 2 GB | 50 GB SSD | 2 TB | **$12.00** | $12.00 | $6.00 |
| **Basic (4GB)** | **2 (shared)** | **4 GB** | **80 GB SSD** | **4 TB** | **$24.00** | **$12.00** | **$6.00** |
| Premium Intel (4GB) | 2 (shared) | 4 GB | 120 GB NVMe | 4 TB | **$32.00** | $16.00 | $8.00 |
| Premium AMD (4GB) | 2 (shared) | 4 GB | 80 GB NVMe | 4 TB | **$28.00** | $14.00 | $7.00 |

#### Additional Costs
- **Backups:** +20% of Droplet price (~$4.80/month for 4GB plan)
- **Snapshots:** $0.05/GB/month
- **Bandwidth overage:** $0.01/GB

#### Best for ShadowHunter
**Basic 4GB** - 2 vCPU, 4GB RAM at $24/month  
- Most comparable to AWS t3.medium
- 4TB transfer included
- Premium AMD ($28) for better performance

#### Cost Analysis (1 Year)
| Metric | Cost |
|--------|------|
| Monthly (Basic 4GB) | $24.00 |
| With Backups | $28.80 |
| 1-Year Total | **$288.00 - $345.60** |
| vs AWS t3.medium | **Save $76.44/year (21%)** |

---

### 3. VULTR 🇺🇸 (Winner: Global Reach)

**Company:** Global cloud provider with 30+ data centers  
**Strengths:** 32 locations worldwide, NVMe on all plans, hourly billing  
**Weaknesses:** Bandwidth limits on cheaper plans, $2.50 plan is IPv6-only

#### Pricing Table

| Plan | vCPU | RAM | Storage | Bandwidth | Monthly Price | $/vCPU | $/GB RAM |
|------|------|-----|---------|-----------|---------------|--------|----------|
| Cloud Compute (IPv6) | 1 (shared) | 0.5 GB | 10 GB SSD | 0.5 TB | **$2.50** | $2.50 | $5.00 |
| Cloud Compute (IPv4) | 1 (shared) | 0.5 GB | 10 GB SSD | 0.5 TB | **$3.50** | $3.50 | $7.00 |
| **High Frequency** | **1 (shared)** | **1 GB** | **32 GB NVMe** | **1 TB** | **$6.00** | **$6.00** | **$6.00** |
| High Frequency (2GB) | 1 (shared) | 2 GB | 64 GB NVMe | 2 TB | **$12.00** | $12.00 | $6.00 |
| High Frequency (4GB) | 2 (shared) | 4 GB | 128 GB NVMe | 3 TB | **$24.00** | $12.00 | $6.00 |
| High Performance AMD | 1 (shared) | 1 GB | 25 GB NVMe | 2 TB | **$6.00** | $6.00 | $6.00 |
| CPU Optimized | 2 (dedicated) | 4 GB | 50 GB NVMe | 4 TB | **$28.00** | $14.00 | $7.00 |

#### Key Features
- **High Frequency:** Intel Xeon 3GHz+ CPUs (best single-thread performance)
- **High Performance:** AMD EPYC processors
- **Free snapshots** (most providers charge)
- Automated backups: +20% of instance cost

#### Best for ShadowHunter
**High Frequency 4GB** - 2 vCPU, 4GB RAM at $24/month  
- 3GHz+ Intel CPUs for fast response times
- 128GB NVMe storage
- Good for bot + database

**Budget Option:** High Frequency 2GB - 1 vCPU, 2GB at $12/month

#### Cost Analysis (1 Year)
| Metric | Cost |
|--------|------|
| Monthly (HF 4GB) | $24.00 |
| 1-Year Total | **$288.00** |
| vs AWS t3.medium | **Save $76.44/year (21%)** |

---

### 4. LINODE/AKAMAI 🇺🇸 (Winner: Support Quality)

**Company:** Acquired by Akamai in 2022, combines VPS with global CDN  
**Strengths:** 99.99% SLA, excellent support, bundled transfer  
**Weaknesses:** Higher prices, G8 dedicated plans have usage-based bandwidth

#### Pricing Table

| Plan | vCPU | RAM | Storage | Transfer | Monthly Price | $/vCPU | $/GB RAM |
|------|------|-----|---------|----------|---------------|--------|----------|
| **Nanode** | **1 (shared)** | **1 GB** | **25 GB SSD** | **1 TB** | **$5.00** | **$5.00** | **$5.00** |
| Linode 2GB | 1 (shared) | 2 GB | 50 GB SSD | 2 TB | **$12.00** | $12.00 | $6.00 |
| **Linode 4GB** | **2 (shared)** | **4 GB** | **80 GB SSD** | **4 TB** | **$24.00** | **$12.00** | **$6.00** |
| Dedicated 4GB (G7) | 2 (dedicated) | 4 GB | 80 GB SSD | 4 TB | **$36.00** | $18.00 | $9.00 |
| Premium 4GB (G8) | 2 (dedicated) | 4 GB | 80 GB NVMe | Pay-per-use | **$43.00** | $21.50 | $10.75 |

#### Additional Costs
- **Backups:** ~$5/month for Linode 4GB
- **Block Storage:** $0.10/GB/month (NVMe)
- **Snapshots:** $0.10/GB/month

#### Best for ShadowHunter
**Linode 4GB** - 2 vCPU, 4GB RAM at $24/month  
- Same specs as DigitalOcean
- Excellent support reputation
- 4TB transfer included

#### Cost Analysis (1 Year)
| Metric | Cost |
|--------|------|
| Monthly (Linode 4GB) | $24.00 |
| With Backups | $29.00 |
| 1-Year Total | **$288.00 - $348.00** |
| vs AWS t3.medium | **Save $76.44/year (21%)** |

---

### 5. OVHcloud 🇫🇷 (Winner: Unlimited Bandwidth)

**Company:** European hosting giant since 1999  
**Strengths:** Unlimited traffic, strong EU presence, anti-DDoS included  
**Weaknesses:** Older interface, SATA SSD on entry plans, limited US support

#### Pricing Table (VPS 2026 Line)

| Plan | vCPU | RAM | Storage | Traffic | Monthly Price | $/vCPU | $/GB RAM |
|------|------|-----|---------|---------|---------------|--------|----------|
| VPS Starter | 1 (shared) | 2 GB | 20 GB SATA | Unlimited | **€3.50 (~$3.80)** | $3.80 | $1.90 |
| VPS Value | 1 (shared) | 2 GB | 40 GB NVMe | Unlimited | **€5.80 (~$6.30)** | $6.30 | $3.15 |
| VPS Essential | 2 (shared) | 4 GB | 80 GB NVMe | Unlimited | **€12.50 (~$13.60)** | $6.80 | $3.40 |
| **VPS-1** | **4 (shared)** | **8 GB** | **75 GB SSD** | **Unlimited** | **$4.90** | **$1.23** | **$0.61** |
| VPS-3 | 8 (shared) | 24 GB | 200 GB SSD | Unlimited | **$15.00** | $1.88 | $0.63 |

#### Older VPS Line (Public Cloud)

| Plan | vCPU | RAM | Storage | Traffic | Monthly Price |
|------|------|-----|---------|---------|---------------|
| D2-2 | 1 | 2 GB | 25 GB | Unlimited | ~$6.57 |
| D2-4 | 2 | 4 GB | 50 GB | Unlimited | ~$13.15 |

#### Best for ShadowHunter
**VPS-1** - 4 vCPU, 8GB RAM at $4.90/month ⭐ **EXCEPTIONAL VALUE**  
- 4x the vCPUs of competitors at same price
- 8GB RAM for database-heavy workloads
- Unlimited traffic

#### Cost Analysis (1 Year)
| Metric | Cost |
|--------|------|
| Monthly (VPS-1) | $4.90 |
| 1-Year Total | **$58.80** |
| vs AWS t3.medium | **Save $305.64/year (84%)** |

---

### 6. CONTABO 🇩🇪 (Winner: Raw Specs)

**Company:** German provider since 2003, known for generous allocations  
**Strengths:** Massive RAM/vCPU for price, huge storage, 32TB traffic  
**Weaknesses:** Oversold/shared CPUs (CPU steal up to 40%), slow support, slow provisioning

#### Pricing Table

| Plan | vCPU | RAM | Storage | Traffic | Monthly Price | $/vCPU | $/GB RAM |
|------|------|-----|---------|---------|---------------|--------|----------|
| **Cloud VPS S NVMe** | **4 (shared)** | **8 GB** | **100 GB NVMe** | **32 TB** | **$6.99** | **$1.75** | **$0.87** |
| Cloud VPS M NVMe | 6 (shared) | 16 GB | 200 GB NVMe | 32 TB | **$11.99** | $2.00 | $0.75 |
| Cloud VPS L NVMe | 8 (shared) | 30 GB | 200 GB NVMe | 32 TB | **$19.99** | $2.50 | $0.67 |
| Cloud VPS XL NVMe | 10 (shared) | 60 GB | 400 GB NVMe | 32 TB | **$34.99** | $3.50 | $0.58 |
| Storage VPS 10 | 2 (shared) | 4 GB | 300 GB SATA | 32 TB | **€5.36 (~$5.80)** | $2.90 | $1.45 |

#### ⚠️ Important Considerations
- **CPU Performance:** Shared cores, expect 20-40% CPU steal during peak
- **Network:** 200-500 Mbps ports (slower than competitors' 1-10 Gbps)
- **Provisioning:** Can take 1-3 hours (others are instant)
- **Support:** Email-only, 24h+ response times

#### Best for ShadowHunter
**Cloud VPS S NVMe** - 4 vCPU, 8GB RAM at $6.99/month  
- Double the RAM of competitors
- Great if running bot + PostgreSQL + Redis
- Tolerate inconsistent CPU for the price

#### Cost Analysis (1 Year)
| Metric | Cost |
|--------|------|
| Monthly (VPS S) | $6.99 |
| 1-Year Total | **$83.88** |
| vs AWS t3.medium | **Save $280.56/year (77%)** |

---

## AWS Baseline Comparison

### AWS EC2 Pricing (us-east-1)

| Instance | vCPU | RAM | Storage | Bandwidth | Monthly Price |
|----------|------|-----|---------|-----------|---------------|
| t3.micro | 2 (burstable) | 1 GB | EBS only | Pay per GB | **~$8.50** |
| t3.small | 2 (burstable) | 2 GB | EBS only | Pay per GB | **~$15.18** |
| **t3.medium** | **2 (burstable)** | **4 GB** | **EBS only** | **Pay per GB** | **~$30.37** |
| t4g.medium (ARM) | 2 (burstable) | 4 GB | EBS only | Pay per GB | **~$24.53** |
| t3.large | 2 (burstable) | 8 GB | EBS only | Pay per GB | **~$60.74** |

### Additional AWS Costs
- **EBS Storage:** gp3 is $0.08/GB/month (~$3.20 for 40GB)
- **Data Transfer:** $0.09/GB outbound (first 10TB)
- **Public IPv4:** $0.005/hour (~$3.65/month) since Feb 2024
- **Estimated total for t3.medium + 40GB + 1TB transfer:** **~$37/month**

### AWS Reserved Instances (1-Year)
| Instance | Upfront | Monthly | Effective Monthly |
|----------|---------|---------|-------------------|
| t3.medium | None | $19.05 | **$19.05** |
| t3.medium | Partial | Varies | ~$15-17 |
| t4g.medium | None | $15.80 | **$15.80** |

---

## Total Cost of Ownership Comparison (1 Year)

### Scenario: 2 vCPU, 4GB RAM, 40GB Storage, 2TB Bandwidth

| Provider | Plan | Monthly | 1-Year Cost | vs AWS Savings |
|----------|------|---------|-------------|----------------|
| **Hetzner** | CX23 | $3.80 | **$45.60** | **87%** |
| **OVHcloud** | VPS-1 | $4.90 | **$58.80** | **84%** |
| **Contabo** | VPS S NVMe | $6.99 | **$83.88** | **77%** |
| **Vultr** | HF 4GB | $24.00 | **$288.00** | **21%** |
| **DigitalOcean** | Basic 4GB | $24.00 | **$288.00** | **21%** |
| **Linode** | Linode 4GB | $24.00 | **$288.00** | **21%** |
| **AWS** | t3.medium (On-Demand) | $37.00* | **$444.00** | Baseline |
| **AWS** | t3.medium (Reserved 1Y) | $22.00* | **$264.00** | - |
| **AWS** | t4g.medium (Reserved 1Y) | $19.00* | **$228.00** | - |

*Includes estimated $7/month for EBS + bandwidth + IPv4

---

## Recommendations by Use Case

### For ShadowHunter (Recommended)

| Priority | Provider | Plan | Monthly | Why |
|----------|----------|------|---------|-----|
| 🥇 **Best Value** | Hetzner | CX23 | $3.80 | Cheapest reliable option |
| 🥈 **Most RAM** | OVHcloud | VPS-1 | $4.90 | 4 vCPU + 8GB RAM |
| 🥉 **Balanced** | Contabo | VPS S | $6.99 | 8GB RAM for growth |

### By Workload Type

| Workload | Recommendation |
|----------|----------------|
| **Bot Only (No DB)** | Hetzner CX23 or OVHcloud VPS Starter |
| **Bot + SQLite** | Hetzner CX23 or CAX11 |
| **Bot + PostgreSQL** | Contabo VPS S or OVHcloud VPS-1 |
| **Bot + Redis + DB** | Contabo VPS S (8GB RAM) |
| **High Traffic Bot** | Vultr High Frequency (better CPU) |
| **Global Audience** | Vultr (30+ locations) |

---

## Detailed Analysis: Best Instance for ShadowHunter

### Recommended: Hetzner CX23

**Specs:**
- 2 shared vCPU (Intel Xeon Gold)
- 4 GB RAM
- 40 GB NVMe SSD (RAID10)
- 20 TB traffic/month
- 10 Gbit network
- DDoS protection included

**Why it's ideal:**
1. **Price:** At $3.80/month, it's 87% cheaper than AWS
2. **Traffic:** 20TB is effectively unlimited for a Discord bot
3. **Storage:** NVMe ensures fast database queries
4. **Network:** 10 Gbit with low latency to Discord's EU servers
5. **Upgrade path:** Easy upgrade to CX33 (4 vCPU/8GB) if needed

**Limitations:**
- Germany/Finland only for best pricing
- Shared CPU (noisy neighbors possible, but rare)

### Alternative: OVHcloud VPS-1

**Specs:**
- 4 shared vCPU
- 8 GB RAM
- 75 GB SSD storage
- Unlimited traffic
- $4.90/month

**Why consider it:**
- Double the RAM for database caching
- 4 vCPUs for concurrent operations
- Slightly better network port speed
- More locations available

---

## Bandwidth Comparison

| Provider | Included | Overage Cost | Notes |
|----------|----------|--------------|-------|
| **Hetzner** | 20 TB | €1.00/TB | Very generous |
| **DigitalOcean** | 1-4 TB | $0.01/GB | Monitor usage |
| **Vultr** | 0.5-3 TB | $0.01/GB | Can get expensive |
| **Linode** | 1-4 TB | $0.005/GB | Cheapest overage |
| **OVHcloud** | Unlimited | - | Truly unlimited |
| **Contabo** | 32 TB | - | Effectively unlimited |
| **AWS** | None | $0.09/GB | Major cost factor |

---

## CPU Performance Notes

| Provider | CPU Type | Dedicated Option | Notes |
|----------|----------|------------------|-------|
| **Hetzner** | Intel Xeon / AMD EPYC / ARM Ampere | CCX series | Good consistent performance |
| **DigitalOcean** | Intel Xeon / AMD EPYC | CPU-Optimized droplets | Premium AMD is fastest |
| **Vultr** | Intel 3GHz+ / AMD EPYC | Optimized Cloud | High Frequency best single-thread |
| **Linode** | AMD EPYC (various gens) | Dedicated CPU plans | G8 uses latest Zen 5 |
| **OVHcloud** | Intel / AMD | Public Cloud instances | Varies by plan |
| **Contabo** | Shared (unknown) | VDS available | CPU steal can be 20-40% |
| **AWS** | Intel / AMD / Graviton (ARM) | All instance types | Burstable credits system |

---

## Final Verdict

### For ShadowHunter Discord Bot

**Primary Recommendation: Hetzner CX23**
- **Cost:** $3.80/month ($45.60/year)
- **Savings:** $318/year vs AWS on-demand
- **Specs:** Perfect for a Discord bot with web scraping
- **Reliability:** 99.9%+ uptime, German engineering

**If you need more RAM: OVHcloud VPS-1**
- **Cost:** $4.90/month ($58.80/year)
- **Advantage:** 8GB RAM for $1 more than Hetzner
- **Good for:** Running database + cache alongside bot

**If CPU consistency matters: Vultr High Frequency**
- **Cost:** $24/month ($288/year)
- **Advantage:** 3GHz+ Intel, NVMe, 32 global locations
- **Good for:** Latency-sensitive operations

### Avoid
- **AWS** for 24/7 workloads unless using Spot instances or 3-year RIs
- **Contabo** if you need consistent CPU performance

### Migration Checklist
1. [ ] Export ShadowHunter database
2. [ ] Set up new VPS with Hetzner/OVHcloud
3. [ ] Install Node.js/Python dependencies
4. [ ] Configure systemd service for auto-restart
5. [ ] Update Discord bot token environment variables
6. [ ] Test thoroughly before DNS cutover
7. [ ] Monitor first 48 hours for any issues

---

*Document generated: March 2026*  
*Prices subject to change. Verify current pricing before purchase.*
