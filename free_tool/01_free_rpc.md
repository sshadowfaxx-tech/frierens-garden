# Free Solana RPC & Data Ingestion Alternatives

> Replace Helius ($499/mo) and QuickNode ($249/mo) with $0 options

---

## Table of Contents

1. [Self-Hosted Solana RPC](#1-self-hosted-solana-rpc)
2. [Free RPC Providers](#2-free-rpc-providers)
3. [Yellowstone Geyser (Self-Hosted)](#3-yellowstone-geyser-self-hosted-grpc-streaming)
4. [Solana Lite RPC](#4-solana-lite-rpc)
5. [Public RPC Fallbacks](#5-public-rpc-fallbacks)
6. [Jito Relayer](#6-jito-relayer)

---

## 1. Self-Hosted Solana RPC

### Hardware Requirements

Running a full Solana RPC node is resource-intensive. Here are the official requirements:

| Component | Minimum Spec | Recommended for Production |
|-----------|--------------|---------------------------|
| **CPU** | 16 cores / 32 threads | 24-32 cores, high clock (3.9+ GHz base) |
| **CPU Model** | AMD EPYC 7642 / Intel Xeon Silver 4210 | AMD EPYC 9434 / Intel Xeon Gold 5412U |
| **RAM** | 256 GB | 512 GB - 1 TB ECC DDR5 |
| **Storage (Accounts)** | 1 TB NVMe SSD | 2 TB+ NVMe (high TBW) |
| **Storage (Ledger)** | 2 TB NVMe SSD | 4 TB+ NVMe (high TBW) |
| **Storage (Snapshots)** | 500 GB NVMe SSD | 1 TB+ NVMe |
| **Storage (OS)** | 500 GB SSD | 1 TB Enterprise SSD |
| **Network** | 1 Gbps symmetric | 10 Gbps symmetric, unmetered |
| **Latency** | <50ms to major clusters | <30ms to major clusters |

**Required CPU Features:**
- AVX2 instruction support (mandatory)
- AVX512f (helpful)
- SHA extensions (mandatory)
- AES-NI

### Cost Estimate (Self-Hosted)

| Approach | Upfront Cost | Monthly Cost |
|----------|--------------|--------------|
| **Buy Hardware** | $15,000 - $50,000 | $500-1,000 (power, cooling, bandwidth) |
| **Bare Metal Rental** | $0 | $400-800/month |
| **Cloud (AWS/GCP)** | $0 | $3,000-10,000/month (NOT recommended) |

**⚠️ Warning:** One user reported a $10,000 AWS bill after serving 300 TB of RPC traffic in a week. Cloud egress fees are prohibitive for Solana RPC.

### Setup Instructions (Agave Client)

**Step 1: System Preparation (Ubuntu 24.04)**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y build-essential pkg-config libssl-dev libudev-dev

# Create solana user
sudo adduser sol
sudo mkdir -p /mnt/{accounts,ledger,snapshots}
sudo chown -R sol:sol /mnt/*
```

**Step 2: System Tuning**

```bash
# Create sysctl configuration
sudo tee /etc/sysctl.d/21-solana-validator.conf <<EOF
# Increase UDP buffer sizes
net.core.rmem_default = 134217728
net.core.rmem_max = 134217728
net.core.wmem_default = 134217728
net.core.wmem_max = 134217728

# Increase memory mapping limits
vm.max_map_count = 1000000

# Increase file handles
fs.nr_open = 1000000
EOF

# Apply settings
sudo sysctl --system

# Increase file limits
sudo tee /etc/security/limits.d/90-solana.conf <<EOF
solana soft nofile 1000000
solana hard nofile 1000000
solana soft memlock unlimited
solana hard memlock unlimited
EOF
```

**Step 3: Install Solana CLI**

```bash
su - sol
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
export PATH="/home/sol/.local/share/solana/install/active_release/bin:$PATH"
echo 'export PATH="/home/sol/.local/share/solana/install/active_release/bin:$PATH"' >> ~/.bashrc
```

**Step 4: Create Identity Keypairs**

```bash
solana-keygen new --outfile ~/validator-keypair.json
solana-keygen new --outfile ~/vote-keypair.json
solana-keygen new --outfile ~/authorized-withdrawer-keypair.json
```

**Step 5: RPC Node Startup Script**

```bash
cat > ~/start-rpc.sh << 'EOF'
#!/bin/bash
exec solana-validator \
  --identity ~/validator-keypair.json \
  --vote-account ~/vote-keypair.json \
  --rpc-port 8899 \
  --entrypoint entrypoint.mainnet-beta.solana.com:8001 \
  --limit-ledger-size \
  --log ~/solana-validator.log \
  --ledger /mnt/ledger \
  --accounts /mnt/accounts \
  --snapshots /mnt/snapshots \
  --full-rpc-api \
  --rpc-bind-address 0.0.0.0 \
  --gossip-port 8001 \
  --dynamic-port-range 8002-8020 \
  --private-rpc \
  --no-voting \
  --enable-rpc-transaction-history \
  --enable-extended-tx-metadata-storage \
  --account-index program-id \
  --account-index spl-token-owner \
  --account-index spl-token-mint
EOF
chmod +x ~/start-rpc.sh
```

**Step 6: Create Systemd Service**

```bash
sudo tee /etc/systemd/system/solana-rpc.service <<EOF
[Unit]
Description=Solana RPC Node
After=network.target

[Service]
Type=simple
User=sol
WorkingDirectory=/home/sol
ExecStart=/home/sol/start-rpc.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable solana-rpc
sudo systemctl start solana-rpc
```

### Limitations

- **High upfront cost** ($15k-50k for hardware)
- **Requires DevOps expertise** for monitoring, updates, and troubleshooting
- **Must stay synced** - falling behind requires snapshot catch-up
- **No SLA** - you're responsible for 99.9% uptime
- **Storage grows continuously** - plan for expansion

---

## 2. Free RPC Providers

### Providers with Genuine Free Tiers

| Provider | Free Tier | Rate Limit | Chains | Notes |
|----------|-----------|------------|--------|-------|
| **dRPC** | ✅ Free | Up to 5,000 RPS | 95+ | PAYG available, no credit card |
| **Ankr** | ✅ Free | 1,500 RPS | 48+ | Decentralized network |
| **GetBlock** | ✅ 40,000 req/day | 60 RPS | 50+ | No credit card required |
| **Chainstack** | ✅ 3M req/month | ~100 RPS | 70+ | SOC2 certified |
| **QuickNode** | ✅ 10M credits/month | 15 RPS | 66+ | 1-month free trial only |
| **Helius** | ✅ Limited free | 500 RPS | Solana only | Best Solana-specific features |
| **NOWNodes** | ✅ 100K req/month | 15 RPS | 100+ | 1 month free only |
| **Alchemy** | ✅ 300 RPS | 300 RPS | 37+ | Requires credit card |

### Free Tier Comparison (Detailed)

| Provider | Monthly Requests | RPS | Features |
|----------|------------------|-----|----------|
| dRPC | Unlimited (rate limited) | 5,000 | WebSocket, Archive, gRPC |
| Ankr | Unlimited (rate limited) | 1,500 | Public tier, no signup |
| GetBlock | 1.2M (40k/day) | 60 | Shared nodes, 99% uptime |
| Chainstack | 3M | ~100 | Yellowstone gRPC available |
| Helius | 500K-1M CU | ~50 | Solana-only, best features |

### Recommended Free Setup

For maximum reliability, combine multiple free tiers with fallback logic:

```javascript
const RPC_ENDPOINTS = [
  { url: 'https://solana.drpc.org', name: 'dRPC' },
  { url: 'https://solana-mainnet.gateway.tatum.io/', name: 'Tatum' },
  { url: 'https://solana-rpc.publicnode.com/', name: 'Allnodes' },
  { url: 'https://api.mainnet-beta.solana.com', name: 'Solana Foundation' },
];

// Round-robin with fallback
async function getConnection() {
  for (const endpoint of RPC_ENDPOINTS) {
    try {
      const connection = new Connection(endpoint.url, 'confirmed');
      await connection.getSlot(); // Test connection
      return connection;
    } catch (e) {
      console.warn(`${endpoint.name} failed, trying next...`);
    }
  }
  throw new Error('All RPC endpoints failed');
}
```

---

## 3. Yellowstone Geyser (Self-Hosted gRPC Streaming)

Yellowstone is an open-source gRPC interface built on Solana's Geyser plugin system. It streams accounts, transactions, entries, blocks, and slots over gRPC with server-side filters.

### What You Can Build

- Live DEX monitoring (Raydium, Orca, Pump.fun)
- Real-time DeFi dashboards
- Trading bots and signal pipelines
- Token and wallet trackers
- Transaction indexers

### Hardware Requirements for Geyser Node

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 24 cores | AMD EPYC 9254 (24 cores) |
| RAM | 384 GB ECC DDR5 | 512 GB ECC DDR5 |
| Storage | 2x 1TB NVMe + 2x 2TB NVMe | Same (RAID 0 for speed) |
| Network | 1 Gbps | 3 Gbps uplink |
| Bandwidth | 50 TB/month | 200 TB/month |

### Self-Hosted Setup with SLV (Recommended)

SLV is an open-source tool that simplifies Geyser gRPC setup:

```bash
# Install SLV
curl -fsSL https://slv.dev/install.sh | bash

# Setup Geyser gRPC node
slv validator init --geyser

# Follow interactive prompts for:
# - SSH connection
# - Node identity keys
# - Jito block engine region (Frankfurt, NY, etc.)
# - RPC port configuration
# - RPC type selection (Geyser gRPC, Index RPC, SendTx RPC)
```

### Manual Setup (Yellowstone Dragon's Mouth)

**Step 1: Install Dependencies**

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install Protocol Buffers
sudo apt install -y protobuf-compiler libprotobuf-dev
```

**Step 2: Build the Geyser Plugin**

```bash
git clone https://github.com/rpcpool/yellowstone-grpc.git
cd yellowstone-grpc/yellowstone-grpc-geyser
cargo build --release
```

**Step 3: Configure Validator with Plugin**

```bash
# Add to your validator startup script
--geyser-plugin-config /path/to/yellowstone-config.json
```

**Example `yellowstone-config.json`:**

```json
{
  "libpath": "/path/to/yellowstone-grpc-geyser/release/libyellowstone_grpc_geyser.so",
  "log": {
    "level": "info"
  },
  "grpc": {
    "bind_address": "0.0.0.0:10000",
    "keepalive": {
      "max_idle": 300,
      "interval": 60
    }
  },
  "snapshot": {
    "enabled": true
  }
}
```

### Managed Yellowstone Options (If Self-Hosting Is Too Expensive)

| Provider | Starting Price | Streams | Notes |
|----------|----------------|---------|-------|
| **Chainstack** | $49/month | 1 stream / 50 accounts | Best value entry tier |
| **Helius** | $49/month | Limited | Developer-friendly |
| **QuickNode** | Add-on | Varies | Requires base plan |
| **Solana Vibe Station** | €580/month | 5 streams | Dedicated bare metal |

### Limitations

- **Requires validator node** - Must run full Solana node
- **High bandwidth usage** - ~100 Mbps per stream
- **Complex setup** - Without SLV, very technical
- **Ongoing maintenance** - Plugin updates, validator updates

---

## 4. Solana Lite RPC

Lite RPC by Mango Markets provides a more efficient method for sending and confirming transactions with **reduced hardware requirements**.

### What is Lite RPC?

Lite RPC is NOT a replacement for full RPC providers - it's a complementary solution that:
- Reduces load on RPC infrastructure
- Lowers hardware requirements for running RPC nodes
- Provides faster transaction confirmation times
- Enables more decentralized RPC networks

### Hardware Requirements (Lite RPC vs Full RPC)

| Component | Full RPC Node | Lite RPC Node |
|-----------|---------------|---------------|
| CPU | 24+ cores | 16 cores |
| RAM | 512 GB | 128-256 GB |
| Storage | 4+ TB NVMe | 1-2 TB NVMe |
| Network | 10 Gbps | 1 Gbps |

**Savings: ~60-70% reduction in hardware costs**

### Setup Instructions

```bash
# Clone Lite RPC repository
git clone https://github.com/blockworks-foundation/lite-rpc.git
cd lite-rpc

# Build
cargo build --release

# Configure
cp config.example.toml config.toml
# Edit config.toml with your settings

# Run
./target/release/lite-rpc --config config.toml
```

### Configuration Example

```toml
[rpc]
listen_address = "0.0.0.0:8890"
full_rpc_url = "https://api.mainnet-beta.solana.com"

[quic]
enable = true
listen_address = "0.0.0.0:8010"

[forwarder]
max_concurrent_connections = 100
transaction_retry_count = 3
```

### Limitations

- **Not a full RPC** - Optimized for transaction sending only
- **Limited query support** - Cannot replace full RPC for data fetching
- **Still requires upstream RPC** - Needs connection to full node
- **Experimental** - Less battle-tested than full nodes

---

## 5. Public RPC Fallbacks

### Official Solana Foundation Endpoints

| Network | Endpoint | Rate Limit |
|---------|----------|------------|
| **Mainnet** | `https://api.mainnet-beta.solana.com` | 50 RPS per 10s |
| **Devnet** | `https://api.devnet.solana.com` | 50 RPS per 10s |
| **Testnet** | `https://api.testnet.solana.com` | 50 RPS per 10s |

**Official Limits:**
- RPS: 50 per 10 seconds
- Per-method limit: 40
- Connection limit: 40
- Pubsub limit: 50
- Data transfer: 100 MB per 30 seconds

### Community Public RPC Endpoints

| Provider | Mainnet Endpoint | Rate Limit | Notes |
|----------|------------------|------------|-------|
| **dRPC** | `https://solana.drpc.org` | High | Decentralized |
| **Allnodes** | `https://solana-rpc.publicnode.com/` | Unknown | Community run |
| **BlockEden** | `https://api.blockeden.xyz/solana/KeCh6p22EX5AeRHxMSmc` | Unknown | Requires API key |
| **bloXroute** | `https://sol-protect.rpc.blxrbdn.com/` | Unknown | MEV protection |
| **Tatum** | `https://solana-mainnet.gateway.tatum.io/` | Unknown | Multi-chain |
| **OnFinality** | `https://solana.api.onfinality.io/public` | Unknown | Polkadot ecosystem |
| **Pocket Network** | `https://solana.api.pocket.network/` | Unknown | Decentralized |
| **LeoRPC** | `https://solana.leorpc.com/?api_key=FREE` | Unknown | Free tier |
| **Solana Vibe Station** | `https://public.rpc.solanavibestation.com/` | Unknown | Community |
| **SubQuery** | `https://solana.rpc.subquery.network/public` | Unknown | Indexer provider |
| **ERPC** | Check slv.dev | Varies | Devnet/Testnet free |

### Devnet/Testnet Specific

| Network | Endpoint |
|---------|----------|
| Devnet (dRPC) | `https://solana-devnet.drpc.org` |
| Devnet (Tatum) | `https://solana-devnet.gateway.tatum.io/` |
| Testnet (dRPC) | `https://solana-testnet.drpc.org` |

### Best Practices for Public RPCs

1. **Implement exponential backoff** when receiving 429 errors
2. **Rotate endpoints** - Don't hardcode a single URL
3. **Cache responses** when possible
4. **Batch requests** to reduce round trips
5. **Monitor latency** - Switch if >200ms consistently

### Fallback Implementation

```javascript
class SolanaRPCManager {
  constructor() {
    this.endpoints = [
      { url: 'https://api.mainnet-beta.solana.com', weight: 1 },
      { url: 'https://solana.drpc.org', weight: 2 },
      { url: 'https://solana-rpc.publicnode.com/', weight: 2 },
      { url: 'https://solana-mainnet.gateway.tatum.io/', weight: 1 },
    ];
    this.currentIndex = 0;
    this.failures = new Map();
  }

  async getConnection() {
    for (let i = 0; i < this.endpoints.length; i++) {
      const endpoint = this.endpoints[this.currentIndex];
      
      if (this.failures.get(endpoint.url) > 3) continue;
      
      try {
        const connection = new Connection(endpoint.url, {
          commitment: 'confirmed',
          confirmTransactionInitialTimeout: 30000,
        });
        
        // Test connection
        await connection.getSlot();
        return connection;
      } catch (error) {
        console.warn(`RPC ${endpoint.url} failed:`, error.message);
        this.failures.set(endpoint.url, (this.failures.get(endpoint.url) || 0) + 1);
        this.currentIndex = (this.currentIndex + 1) % this.endpoints.length;
      }
    }
    
    throw new Error('All RPC endpoints exhausted');
  }
}
```

---

## 6. Jito Relayer

### What is Jito Relayer?

Jito Relayer is part of the Jito MEV infrastructure that filters transactions on a separate server, allowing validators to focus on block production. It provides:

- **Spam filtering** - Reduces network spam reaching validators
- **Packet deduplication** - Removes duplicate transactions
- **Signature verification** - Offloads verification from validators
- **Bundle support** - Enables atomic transaction execution

### Free Jito Relayer Options

#### Option 1: Jito Labs Public Relayer (Free)

Jito Labs runs relayer instances as a **public good**:

```
# Public relayer endpoints (check Jito docs for current list)
https://mainnet.relayer.jito.io
https://frankfurt.relayer.jito.io
https://ny.relayer.jito.io
```

**Usage:**
```bash
# Add to validator startup
--relayer-url https://mainnet.relayer.jito.io
```

#### Option 2: Self-Hosted Relayer

The relayer logic is **open source** - anyone can run their own:

```bash
# Clone Jito repository
git clone https://github.com/jito-foundation/jito-solana.git
cd jito-solana/relayer

# Build
cargo build --release

# Configure
# Edit relayer-config.yaml

# Run
./target/release/jito-relayer --config relayer-config.yaml
```

**Self-Hosted Requirements:**

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 8 cores | 16 cores |
| RAM | 32 GB | 64 GB |
| Network | 1 Gbps | 10 Gbps |
| Location | Same DC as validator | Same DC as validator |

### Jito Bundle RPC (Free via Providers)

Several providers offer free Jito bundle submission:

| Provider | Endpoint Type | Free Tier |
|----------|---------------|-----------|
| **Jito (official)** | `https://mainnet.block-engine.jito.io` | Bundle submission |
| **Helius** | Bundled with RPC | Free plan includes |
| **QuickNode** | Add-on | Requires paid plan |

### Sending Bundles

```javascript
const { Connection, VersionedTransaction } = require('@solana/web3.js');

// Connect to Jito bundle endpoint
const jitoConnection = new Connection('https://mainnet.block-engine.jito.io');

// Create bundle (up to 5 transactions)
const bundle = [
  transaction1.serialize(),
  transaction2.serialize(),
  // ... up to 5
];

// Send bundle
const bundleId = await jitoConnection.sendBundle(bundle);
console.log('Bundle ID:', bundleId);

// Check status
const status = await jitoConnection.getBundleStatuses([bundleId]);
```

### Jito-Solana Client Setup

To fully utilize Jito infrastructure, run the Jito-Solana validator client:

```bash
# Instead of standard Agave client, use Jito-Solana
sh -c "$(curl -sSfL https://release.jito.wtf/latest/install)"

# Run with Jito features
solana-validator \
  --identity ~/validator-keypair.json \
  --vote-account ~/vote-keypair.json \
  --relayer-url https://mainnet.relayer.jito.io \
  --block-engine-url https://mainnet.block-engine.jito.io \
  # ... other standard flags
```

### Limitations

- **No guaranteed inclusion** - Bundles still compete in auction
- **Minimum tip required** - 1,000 lamports minimum for bundle priority
- **Requires Jito-Solana client** - Full benefits require client switch
- **Geographic sensitivity** - Relayer proximity matters for latency

---

## Cost Comparison Summary

| Solution | Monthly Cost | Setup Complexity | Best For |
|----------|--------------|------------------|----------|
| **Helius Paid** | $499 | Low | Production, high volume |
| **QuickNode Paid** | $249 | Low | Multi-chain projects |
| **Self-Hosted Full RPC** | $400-800 | Very High | Max control, privacy |
| **Self-Hosted Lite RPC** | $200-400 | High | Transaction sending only |
| **Free RPC Providers** | $0 | Low | Development, testing |
| **Yellowstone (Self)** | $500-600 | Very High | Real-time streaming |
| **Yellowstone (Managed)** | $49+ | Low | Production streaming |
| **Jito Relayer (Self)** | $100-200 | Medium | MEV optimization |
| **Jito Relayer (Public)** | $0 | Low | Basic MEV features |

---

## Recommended Free Stack

For a completely free setup:

1. **Primary RPC:** dRPC or Ankr (highest free limits)
2. **Fallbacks:** Public endpoints rotation
3. **Transaction Sending:** Lite RPC (if self-hosting) or Jito bundles
4. **Streaming:** Chainstack Yellowstone ($49) or WebSocket subscriptions
5. **MEV Protection:** Jito public relayer

**Total Cost: $0-49/month** (vs $499 Helius)

---

## References

- [Solana Validator Requirements](https://docs.solana.com/running-validator/validator-reqs)
- [Yellowstone gRPC GitHub](https://github.com/rpcpool/yellowstone-grpc)
- [Lite RPC GitHub](https://github.com/blockworks-foundation/lite-rpc)
- [Jito Documentation](https://jito-labs.gitbook.io/mev/)
- [SLV Toolkit](https://slv.dev)
- [CompareNodes Public RPC List](https://www.comparenodes.com/library/public-endpoints/solana/)

---

*Last Updated: March 2026*
