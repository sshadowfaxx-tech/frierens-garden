# Claude Trading Agent - Cloud VPS Setup

Run Claude on a cheap VPS while keeping FX 6300 lightweight.

## Architecture

```
Hetzner VPS (€5/mo)          FX 6300 (Home)
├─ OpenClaw Gateway    ←────┼─ PostgreSQL (port 5432)
├─ Claude Agent      VPN    ├─ Tracker (writes positions)
└─ Sol CLI wallet           └─ Redis (port 6379)
```

## Step 1: Create Hetzner VPS

1. Go to [hetzner.com/cloud](https://hetzner.com/cloud)
2. Create project → Add server
3. **Type:** CX21 (2 vCPU, 4GB, 40GB) - €5.35/mo
4. **Location:** US East (Ashburn) for low latency
5. **Image:** Ubuntu 24.04
6. **SSH Key:** Add your public key

## Step 2: Connect VPS to FX 6300 Database

Option A: **SSH Tunnel (Simplest)**

On Hetzner VPS, create tunnel:
```bash
ssh -L 5432:localhost:5432 -N -f user@fx6300-ip
```

Option B: **VPN (More Secure)**

Install Tailscale on both:
```bash
# On both VPS and FX 6300
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Then FX 6300 PostgreSQL listens on Tailscale IP.

## Step 3: Configure PostgreSQL on FX 6300

Allow VPS to connect:

```bash
# Edit postgresql.conf
listen_addresses = '*'

# Edit pg_hba.conf
host all all 0.0.0.0/0 md5

# Restart PostgreSQL
```

**Security:** Use VPN (Tailscale) instead of exposing port 5432 to internet.

## Step 4: Install OpenClaw on VPS

```bash
# SSH into Hetzner VPS
ssh root@vps-ip

# Install Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install OpenClaw
npm install -g openclaw

# Create config directory
mkdir -p ~/.openclaw
```

## Step 5: Configure OpenClaw

Create `~/.openclaw/config.yaml`:

```yaml
gateway:
  port: 8080
  host: 0.0.0.0

models:
  default: anthropic/claude-4-6
  anthropic:
    api_key: ${CLAUDE_API_KEY}

sessions:
  claude-trader:
    agent: main
    model: anthropic/claude-4-6
    thinking: high

channels:
  telegram:
    token: ${TELEGRAM_BOT_TOKEN}

database:
  postgresql:
    host: ${DB_HOST}  # FX 6300 Tailscale IP or localhost if tunneled
    port: 5432
    database: shadowhunter
    user: postgres
    password: sh123

redis:
  host: ${REDIS_HOST}  # FX 6300 Tailscale IP
  port: 6379
```

## Step 6: Set Environment Variables

```bash
# ~/.bashrc
export CLAUDE_API_KEY=sk-ant-api03-your-key
export TELEGRAM_BOT_TOKEN=your-bot-token
export DB_HOST=100.x.x.x  # FX 6300 Tailscale IP
export REDIS_HOST=100.x.x.x

source ~/.bashrc
```

## Step 7: Install Sol CLI on VPS

```bash
npm install -g @solana-compass/cli

# Create trading wallet
sol wallet create --name claude-trader
sol config set rpc.url https://mainnet.helius-rpc.com/?api-key=your-key

# Security settings
sol config set permissions.canTransfer false
sol config set permissions.canExportWallet false
sol config set limits.maxTransactionUsd 500
sol config set limits.maxDailyUsd 2000
sol config lock
```

## Step 8: Start Claude Trader

```bash
# Start OpenClaw gateway
openclaw gateway start

# In another terminal, spawn Claude session
openclaw sessions spawn \
  --agent claude-trader \
  --model anthropic/claude-4-6 \
  --task "You are an autonomous Solana memecoin trader. Monitor the ShadowHunter database on FX 6300 for wallet positions. When clusters appear (2+ wallets on same token), analyze performance data, research tokens, and execute paper trades. Start with 2 SOL. Report all decisions to Telegram."
```

## Step 9: Fund the Wallet (When Ready)

```bash
# Get wallet address
sol wallet address

# Send SOL from your main wallet
# Start with 2-5 SOL for paper trading simulation
# Or 10-20 SOL for live trading (when proven)
```

## Monitoring

**Check VPS resources:**
```bash
htop
free -h
df -h
```

**Check OpenClaw status:**
```bash
openclaw gateway status
openclaw sessions list
```

**View logs:**
```bash
tail -f ~/.openclaw/logs/gateway.log
tail -f ~/.openclaw/logs/claude-trader.log
```

**Telegram notifications:**
- Channel: -1003778576771
- All trades and decisions reported there

## Security Checklist

- [ ] VPS has UFW/firewall enabled (only SSH + OpenClaw port)
- [ ] PostgreSQL not exposed to internet (Tailscale only)
- [ ] Sol CLI wallet locked (can't export keys)
- [ ] Transaction limits configured
- [ ] Claude API key stored securely

## Costs

| Service | Monthly Cost |
|---------|-------------|
| Hetzner CX21 | €5.35 (~$6) |
| Claude API | ~$20-50 (depends on usage) |
| Helius RPC | Free tier (or $49 for more) |
| **Total** | **~$30-60/month** |

## Advantages

1. **FX 6300 stays lightweight** - Only tracker + DB
2. **Claude has dedicated resources** - 4GB RAM just for trading
3. **24/7 uptime** - VPS doesn't sleep
4. **Remote access** - SSH in from anywhere
5. **Easy to scale** - Upgrade VPS if needed

## Troubleshooting

**Can't connect to FX 6300 database:**
```bash
# Test connection
psql -h fx6300-tailscale-ip -U postgres -d shadowhunter

# Check if PostgreSQL listening on all interfaces
netstat -tlnp | grep 5432
```

**Claude API rate limits:**
- Claude Max plan should handle it
- If hitting limits, reduce polling frequency (30s → 60s)

**VPS running slow:**
- Upgrade to CX31 (4 vCPU, 8GB) for €10/mo
- Or optimize queries (add database indexes)

## Backup Plan

If VPS fails:
1. All data is on FX 6300 PostgreSQL (safe)
2. Spin up new VPS in 10 minutes
3. Restore config, reconnect to DB
4. Resume trading

## Next Steps

1. Sign up for Hetzner
2. Create CX21 VPS
3. Install Tailscale on FX 6300 and VPS
4. Follow setup steps
5. Fund wallet with 2 SOL (test)
6. Let Claude trade autonomously

You'll have a professional trading setup for ~$30/month with zero load on FX 6300.
