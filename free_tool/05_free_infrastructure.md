# Free Infrastructure & Hosting Guide
## Replace $3,000/mo AWS/GCP with $0

---

## Executive Summary

This guide provides a complete migration path from expensive cloud infrastructure to free/ultra-low-cost alternatives. Target monthly cost: **$0-20** vs $3,000/mo on AWS/GCP.

| Service | AWS/GCP Cost | Free Alternative | New Cost |
|---------|--------------|------------------|----------|
| Compute (servers) | $500-1500/mo | Old hardware / Oracle Free Tier | $0 |
| Container orchestration | $300-800/mo | K3s / Docker Compose | $0 |
| Message queue | $200-400/mo | NATS / RabbitMQ self-hosted | $0 |
| Monitoring | $100-300/mo | Prometheus + Grafana | $0 |
| Reverse proxy | $50-100/mo | Nginx / Caddy | $0 |
| VPN/Tunnel | $50-100/mo | Cloudflare Tunnel / Tailscale | $0 |
| **TOTAL** | **$1,200-3,200/mo** | | **$0-20/mo** |

---

## 1. Server Hardware Options

### Option A: Repurpose Old Hardware (FREE)

**What you need:**
- Old laptop/desktop with 8GB+ RAM
- 100GB+ free storage
- Working ethernet or WiFi

**Hardware Requirements by Use Case:**

| Workload | CPU | RAM | Storage | Examples |
|----------|-----|-----|---------|----------|
| Personal projects | 2 cores | 4GB | 50GB SSD | Old laptop, Intel NUC |
| Small team | 4 cores | 8GB | 100GB SSD | Old desktop, Mac Mini |
| Production (light) | 4 cores | 16GB | 250GB SSD | Used workstation |
| Production (heavy) | 8 cores | 32GB | 500GB SSD | Used server hardware |

**Setup Steps:**
1. Install Ubuntu Server LTS (headless)
2. Enable SSH: `sudo apt install openssh-server`
3. Configure static IP or use Tailscale
4. Disable sleep/suspend for laptops: `sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target`

**Pros:**
- Truly $0
- Full control
- No data transfer limits
- Learn hardware skills

**Cons:**
- Single point of failure
- Power consumption (~$5-20/mo)
- No automatic backups
- ISP may block ports

---

### Option B: Raspberry Pi Cluster ($100-300 one-time)

**Recommended Setup:**
```
┌─────────────────────────────────────────┐
│        Raspberry Pi 4/5 Cluster         │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐   │
│  │ Pi  │  │ Pi  │  │ Pi  │  │ Pi  │   │
│  │ #1  │  │ #2  │  │ #3  │  │ #4  │   │
│  │4GB  │  │4GB  │  │4GB  │  │4GB  │   │
│  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘   │
│     └─────────┴─────────┴─────────┘     │
│           Ethernet Switch               │
│              (Gigabit)                  │
└─────────────────────────────────────────┘
```

**Shopping List:**
- 4x Raspberry Pi 4/5 (4GB): $200-280
- 4x 64GB microSD cards: $40
- 5-port Gigabit switch: $15
- 4x short ethernet cables: $10
- Power supply (USB-C hub or PoE): $30
- **Total: ~$300**

**K3s Cluster Setup:**
```bash
# On master node (pi-1)
curl -sfL https://get.k3s.io | sh -
sudo cat /var/lib/rancher/k3s/server/node-token
# Copy token for workers

# On worker nodes (pi-2, pi-3, pi-4)
curl -sfL https://get.k3s.io | K3S_URL=https://<master-ip>:6443 K3S_TOKEN=<token> sh -
```

**Pros:**
- Learn Kubernetes hands-on
- Fault-tolerant (if one fails, others work)
- Low power consumption (~20W total)
- Quiet and compact

**Cons:**
- ARM architecture (some containers need adjustment)
- Limited RAM per node
- microSD cards can fail (use USB SSDs instead)

---

### Option C: Used Enterprise Hardware ($100-500 one-time)

**Best Deals:**
| Hardware | Specs | Price | Source |
|----------|-------|-------|--------|
| Dell OptiPlex 7050 | i7-6700, 16GB, 256GB SSD | $150 | eBay |
| HP EliteDesk 800 G3 | i5-7500, 16GB, 256GB SSD | $120 | eBay |
| Lenovo ThinkCentre M900 | i5-6500T, 8GB, 128GB SSD | $100 | eBay |
| Dell R620/R720 Server | 2x Xeon, 64GB+ RAM | $200-400 | eBay |

**Why enterprise desktops are perfect:**
- Built for 24/7 operation
- Easy to upgrade
- Low power (35-65W for desktops)
- Reliable

**Setup:**
```bash
# Install Proxmox VE for virtualization (optional)
# Or Ubuntu Server for bare metal

# Check hardware health
sudo apt install smartmontools
sudo smartctl -a /dev/sda
```

---

## 2. Free Cloud Hosting Tiers

### Oracle Cloud Free Tier (RECOMMENDED - Always Free)

**What you get (FOREVER FREE):**
| Resource | Allocation |
|----------|------------|
| Compute (VM.Standard.E2.1.Micro) | 2 instances |
| ARM Ampere A1 | 4 OCPUs, 24GB RAM total |
| Block Storage | 200GB total |
| Object Storage | 10GB |
| Load Balancer | 1 (10Mbps) |
| Outbound Data | 10TB/month |
| Databases | 2 autonomous (20GB each) |

**Architecture:**
```
┌─────────────────────────────────────────┐
│         Oracle Cloud Free Tier          │
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │  x86 Micro   │  │   ARM Instance │  │
│  │  (1/1 OCPU)  │  │  (4 OCPU/24GB) │  │
│  │  Reverse     │  │   Main Apps    │  │
│  │   Proxy      │  │                │  │
│  └──────────────┘  └────────────────┘  │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │      Block Storage 200GB        │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**Signup:** https://www.oracle.com/cloud/free/

**Pros:**
- Truly permanent free tier
- Generous resources
- Enterprise-grade infrastructure
- No credit card required for signup

**Cons:**
- Account termination risk if you violate terms
- Requires phone verification
- Can be complex for beginners

**Tips:**
- Create ARM instance with max resources (4 OCPUs, 24GB)
- Use x86 micro instance for lightweight services
- Set up automated backups to avoid data loss

---

### AWS Free Tier (12 Months)

**What you get (12 months):**
| Resource | Allocation |
|----------|------------|
| EC2 (t2/t3.micro) | 750 hours/month |
| S3 Storage | 5GB |
| RDS | 750 hours db.t2.micro |
| Lambda | 1M requests/month (always free) |
| CloudWatch | 10 metrics (always free) |

**Signup:** https://aws.amazon.com/free/

**Pros:**
- Industry standard
- Massive ecosystem
- Always free Lambda (great for serverless)

**Cons:**
- Only 12 months
- Easy to accidentally incur charges
- Requires credit card

---

### Google Cloud Free Tier ($300 Credit + Always Free)

**What you get:**
| Resource | Allocation |
|----------|------------|
| Credit | $300 for 90 days |
| Compute (e2-micro) | 1 instance (always free) |
| Cloud Storage | 5GB (always free) |
| BigQuery | 1TB query/month (always free) |

**Signup:** https://cloud.google.com/free

**Pros:**
- $300 credit for experimentation
- Always free e2-micro VM
- Good for learning

**Cons:**
- Credit expires in 90 days
- Always free tier is minimal
- Requires credit card

---

### Hetzner Cloud (Ultra-Cheap Alternative)

**Not free, but extremely cheap:**
| Instance | Specs | Price |
|----------|-------|-------|
| CX11 | 1 vCPU, 2GB RAM, 20GB | €3.29/mo (~$3.50) |
| CPX11 | 2 vCPU, 2GB RAM, 40GB | €4.51/mo (~$4.80) |
| CX21 | 2 vCPU, 4GB RAM, 40GB | €5.35/mo (~$5.70) |

**Why Hetzner:**
- German data centers (GDPR compliant)
- No egress fees
- Hourly billing
- Excellent performance

---

## 3. Container Orchestration

### Option A: Docker Compose (Simplest - RECOMMENDED for Beginners)

**Best for:** Single server, simple deployments

**Example `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  app:
    build: ./app
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgres://postgres:password@db:5432/myapp
    depends_on:
      - db
      - redis
    networks:
      - backend
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=myapp
    networks:
      - backend
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    networks:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  backend:
    driver: bridge
```

**Deployment:**
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Deploy
docker compose up -d
```

**Pros:**
- Simplest option
- Easy to learn
- Perfect for single-server setups
- Large community

**Cons:**
- No auto-scaling
- No self-healing
- Single point of failure

---

### Option B: K3s (Lightweight Kubernetes - RECOMMENDED for Production)

**Best for:** Multi-node clusters, production workloads

**What is K3s?**
- Lightweight Kubernetes distribution by Rancher
- Single binary (<100MB)
- Works on ARM and x86
- Perfect for edge/IoT/self-hosted

**Single-Node Setup:**
```bash
# Install K3s (includes containerd)
curl -sfL https://get.k3s.io | sh -

# Configure kubectl
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config

# Verify
kubectl get nodes
```

**Multi-Node Setup:**
```bash
# Master node
curl -sfL https://get.k3s.io | sh -

# Get token
sudo cat /var/lib/rancher/k3s/server/node-token

# Worker nodes
curl -sfL https://get.k3s.io | K3S_URL=https://<master-ip>:6443 K3S_TOKEN=<token> sh -
```

**Example Deployment:**
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP
```

**Deploy:**
```bash
kubectl apply -f deployment.yaml
```

**Pros:**
- Full Kubernetes compatibility
- Auto-scaling and self-healing
- Works on Raspberry Pi
- Great learning platform

**Cons:**
- Steeper learning curve
- More complex than Docker Compose

---

### Option C: Nomad (HashiCorp)

**Best for:** Mixed workloads (containers + binaries)

```bash
# Install Nomad
wget https://releases.hashicorp.com/nomad/1.6.0/nomad_1.6.0_linux_amd64.zip
unzip nomad_1.6.0_linux_amd64.zip
sudo mv nomad /usr/local/bin/
```

**Pros:**
- Lighter than K8s
- Schedules containers AND binaries
- Great for mixed workloads

**Cons:**
- Smaller community than K8s
- Requires Consul for service discovery

---

## 4. Message Queue Solutions

### Option A: NATS (Lightweight - RECOMMENDED)

**Why NATS:**
- Single binary, no dependencies
- Extremely fast (millions of messages/sec)
- Built-in streaming (JetStream)
- Native clustering

**Docker Compose Setup:**
```yaml
services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"  # Client port
      - "8222:8222"  # HTTP monitoring
    command: "--jetstream --store_dir /data"
    volumes:
      - nats_data:/data
    restart: unless-stopped

volumes:
  nats_data:
```

**Client Example (Node.js):**
```javascript
const { connect, StringCodec } = require('nats');

const nc = await connect({ servers: 'localhost:4222' });
const sc = StringCodec();

// Publish
nc.publish('orders', sc.encode('New order: #123'));

// Subscribe
const sub = nc.subscribe('orders');
for await (const msg of sub) {
  console.log('Received:', sc.decode(msg.data));
}
```

**Pros:**
- Very lightweight
- Easy to operate
- Great performance
- Built-in persistence (JetStream)

**Cons:**
- Smaller ecosystem than Kafka
- Fewer managed service options

---

### Option B: RabbitMQ

**Docker Compose:**
```yaml
services:
  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=password
    restart: unless-stopped

volumes:
  rabbitmq_data:
```

**Access UI:** http://localhost:15672 (admin/password)

**Pros:**
- Mature and battle-tested
- Excellent management UI
- Multiple protocol support
- Great documentation

**Cons:**
- Heavier than NATS
- More complex to configure

---

### Option C: Apache Kafka (Self-Hosted)

**For high-throughput scenarios:**

```yaml
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

**Pros:**
- Industry standard for streaming
- Massive throughput
- Excellent ecosystem

**Cons:**
- Complex to operate
- Resource hungry
- Requires ZooKeeper (or KRaft)

---

### Comparison

| Feature | NATS | RabbitMQ | Kafka |
|---------|------|----------|-------|
| Memory Usage | ~50MB | ~200MB | ~1GB+ |
| Setup Complexity | Easy | Medium | Hard |
| Throughput | Millions/sec | Thousands/sec | Millions/sec |
| Persistence | Yes (JetStream) | Yes | Yes |
| Learning Curve | Low | Medium | High |
| Best For | General purpose | Enterprise | Big data |

---

## 5. Monitoring & Observability

### Option A: Prometheus + Grafana (RECOMMENDED)

**Architecture:**
```
┌─────────────────────────────────────────┐
│           Your Services                 │
│  ┌────────┐ ┌────────┐ ┌────────┐      │
│  │  App   │ │  DB    │ │ Cache  │      │
│  │Metrics │ │Metrics │ │Metrics │      │
│  └───┬────┘ └───┬────┘ └───┬────┘      │
│      └─────────┬┴─────────┘             │
│                │                        │
│      ┌─────────▼─────────┐              │
│      │    Prometheus     │              │
│      │   (Time Series)   │              │
│      └─────────┬─────────┘              │
│                │                        │
│      ┌─────────▼─────────┐              │
│      │      Grafana      │              │
│      │   (Dashboards)    │              │
│      └───────────────────┘              │
└─────────────────────────────────────────┘
```

**docker-compose.yml:**
```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
    restart: unless-stopped

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro
    ports:
      - "8080:8080"
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

**prometheus.yml:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'myapp'
    static_configs:
      - targets: ['app:3000']
```

**Access:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

**Pre-built Dashboards:**
- Node Exporter Full: ID 1860
- Docker Monitoring: ID 193
- Kubernetes Cluster: ID 7249

---

### Option B: Uptime Kuma (Uptime Monitoring)

**For simple uptime/health checks:**

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    ports:
      - "3001:3001"
    volumes:
      - uptime_kuma_data:/app/data
    restart: unless-stopped

volumes:
  uptime_kuma_data:
```

**Features:**
- HTTP/HTTPS/Ping/DNS monitoring
- TCP/UDP port monitoring
- Push monitoring
- Email/Discord/Slack notifications
- Beautiful status pages

**Access:** http://localhost:3001

---

## 6. Reverse Proxy & Load Balancer

### Option A: Caddy (RECOMMENDED for Simplicity)

**Why Caddy:**
- Automatic HTTPS (Let's Encrypt)
- Simple configuration
- HTTP/2 and HTTP/3 support
- Built-in metrics

**Caddyfile:**
```
{
    email your-email@example.com
    auto_https off  # Use Cloudflare SSL instead
}

# Main site
app.example.com {
    reverse_proxy localhost:3000
    
    # Enable compression
    encode gzip zstd
    
    # Security headers
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}

# API subdomain
api.example.com {
    reverse_proxy localhost:8080
    
    # CORS headers
    header Access-Control-Allow-Origin "*"
    header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
}

# Static files
static.example.com {
    root * /var/www/static
    file_server
    encode gzip
}
```

**Docker Compose:**
```yaml
services:
  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

---

### Option B: Nginx (Most Popular)

**nginx.conf:**
```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Upstream for load balancing
    upstream app_servers {
        server localhost:3000;
        server localhost:3001;
    }

    server {
        listen 80;
        server_name app.example.com;

        location / {
            proxy_pass http://app_servers;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

---

### Option C: Traefik (Cloud-Native)

**Best for:** Kubernetes/Docker environments

```yaml
services:
  traefik:
    image: traefik:v3.0
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
    restart: unless-stopped

  whoami:
    image: traefik/whoami
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.rule=Host(`whoami.example.com`)"
      - "traefik.http.routers.whoami.entrypoints=web"
```

---

## 7. VPN & Tunnel Solutions

### Option A: Cloudflare Tunnel (RECOMMENDED)

**Why Cloudflare Tunnel:**
- **Completely free**
- No open ports needed
- DDoS protection included
- Automatic SSL
- Works behind CGNAT

**Architecture:**
```
Internet → Cloudflare Edge → Cloudflare Tunnel → Your Server
                ↑                                    ↑
           (SSL/TLS)                         (Outbound only)
```

**Setup:**
```bash
# Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Login (opens browser)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create my-tunnel

# Configure (~/.cloudflared/config.yml)
tunnel: <tunnel-id>
credentials-file: /home/user/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: app.example.com
    service: http://localhost:3000
  - hostname: api.example.com
    service: http://localhost:8080
  - hostname: grafana.example.com
    service: http://localhost:3000
  - service: http_status:404

# Run
cloudflared tunnel run my-tunnel

# Install as service
sudo cloudflared service install
sudo systemctl start cloudflared
```

**Pros:**
- No port forwarding needed
- Works on any network
- Free SSL certificates
- DDoS protection

**Cons:**
- Requires Cloudflare account
- Tunnels through their network
- Some latency added

---

### Option B: Tailscale (Mesh VPN)

**Why Tailscale:**
- WireGuard-based
- Free for personal use (20 devices)
- No configuration needed
- MagicDNS for easy hostnames

**Setup:**
```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh

# Connect
sudo tailscale up

# Check status
tailscale status

# Get your Tailscale IP
ip addr show tailscale0
```

**Use Cases:**
- Access home server from anywhere
- Secure database connections
- Remote development

**Pros:**
- Zero-config VPN
- NAT traversal works everywhere
- Free for personal use
- Fast (WireGuard)

**Cons:**
- Requires client on all devices
- 20 device limit on free tier

---

### Option C: ngrok (Quick Tunnels)

**For quick sharing/testing:**

```bash
# Install
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Authenticate (free signup required)
ngrok config add-authtoken <your-token>

# Expose local port
ngrok http 3000

# Expose with custom subdomain (paid feature)
ngrok http --subdomain=myapp 3000
```

**Pros:**
- Instant public URLs
- Great for testing webhooks
- Request inspection UI

**Cons:**
- Free tier URLs change every restart
- Limited connections on free tier
- Not for production

---

## Complete Architecture Example

### Single Desktop Server Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                    Single Desktop Server                         │
│                    (Ubuntu Server LTS)                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Cloudflare Tunnel (daemon)                  │   │
│  │     Exposes: app.example.com, api.example.com            │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                     │
│  ┌─────────────────────────▼───────────────────────────────┐   │
│  │                    Caddy (Reverse Proxy)                 │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│  │  │  App 1  │  │  App 2  │  │ Grafana │  │ Uptime  │    │   │
│  │  │ :3000   │  │ :3001   │  │ :3002   │  │ :3003   │    │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └─────────┘    │   │
│  └───────┼────────────┼────────────┼──────────────────────┘   │
│          │            │            │                            │
│  ┌───────▼────────────▼────────────▼──────────────────────┐   │
│  │              K3s / Docker Compose                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Supporting Services:                                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │  NATS    │ │Postgres  │ │  Redis   │ │Prometheus│   │   │
│  │  │ Message  │ │  SQL DB  │ │  Cache   │ │ Metrics  │   │   │
│  │  │ Queue    │ │          │ │          │ │          │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Storage:                                               │   │
│  │  - NVMe SSD (OS + containers)                           │   │
│  │  - HDD (backups, logs)                                  │   │
│  │  - Automated backups to external drive                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Tailscale (optional)
                              ▼
                   ┌─────────────────────┐
                   │   Your Laptop/Phone │
                   │   (Remote Access)   │
                   └─────────────────────┘
```

---

## Docker Compose All-in-One

```yaml
version: '3.8'

services:
  # Applications
  app:
    build: ./app
    environment:
      - DATABASE_URL=postgres://postgres:password@postgres:5432/app
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    depends_on:
      - postgres
      - redis
      - nats
    restart: unless-stopped

  # Database
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=app
    restart: unless-stopped

  # Cache
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # Message Queue
  nats:
    image: nats:latest
    command: "--jetstream --store_dir /data"
    volumes:
      - nats_data:/data
    restart: unless-stopped

  # Reverse Proxy
  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    restart: unless-stopped

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro
    restart: unless-stopped

  uptime-kuma:
    image: louislam/uptime-kuma:latest
    volumes:
      - uptime_kuma_data:/app/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  nats_data:
  caddy_data:
  caddy_config:
  prometheus_data:
  grafana_data:
  uptime_kuma_data:
```

---

## Monthly Cost Comparison

| Component | AWS/GCP | Free Alternative | Monthly Cost |
|-----------|---------|------------------|--------------|
| **Compute** | EC2/GCE instances | Old desktop / Oracle Free Tier | $0-10 (power) |
| **Container Orchestration** | EKS/GKE | K3s / Docker Compose | $0 |
| **Message Queue** | SQS/Cloud Pub/Sub | NATS self-hosted | $0 |
| **Database** | RDS/Cloud SQL | PostgreSQL self-hosted | $0 |
| **Monitoring** | CloudWatch/Monitoring | Prometheus + Grafana | $0 |
| **CDN/SSL** | CloudFront/Load Balancer | Cloudflare Tunnel | $0 |
| **VPN** | VPN Gateway | Tailscale free / WireGuard | $0 |
| **Domain** | Route 53 | Cloudflare / Namecheap | $10-15/year |
| **Backups** | S3/GCS | External HDD / rclone | $0-5 |
| **TOTAL** | **$1,200-3,000/mo** | | **$0-20/mo** |

---

## Migration Checklist

### Phase 1: Foundation (Week 1)
- [ ] Set up hardware (old laptop/desktop)
- [ ] Install Ubuntu Server LTS
- [ ] Configure SSH access
- [ ] Install Docker and Docker Compose
- [ ] Set up Cloudflare Tunnel
- [ ] Configure DNS records

### Phase 2: Core Services (Week 2)
- [ ] Deploy PostgreSQL
- [ ] Deploy Redis
- [ ] Deploy NATS message queue
- [ ] Set up Caddy reverse proxy
- [ ] Deploy applications

### Phase 3: Monitoring (Week 3)
- [ ] Deploy Prometheus
- [ ] Deploy Grafana
- [ ] Import dashboards
- [ ] Set up alerts
- [ ] Deploy Uptime Kuma

### Phase 4: Optimization (Week 4)
- [ ] Configure automated backups
- [ ] Set up log rotation
- [ ] Document everything
- [ ] Test disaster recovery
- [ ] Monitor resource usage

---

## Backup Strategy

### Local Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/mnt/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Database backup
docker exec postgres pg_dumpall -U postgres > $BACKUP_DIR/postgres.sql

# Volume backup
docker run --rm -v postgres_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
docker run --rm -v app_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/app_data.tar.gz -C /data .

# Config backup
tar czf $BACKUP_DIR/configs.tar.gz /etc/nginx /opt/app/docker-compose.yml

# Sync to external/cloud
rclone sync $BACKUP_DIR remote:backups
```

### Automated with Cron
```bash
# Edit crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /opt/backup/backup.sh >> /var/log/backup.log 2>&1

# Weekly cleanup (keep 30 days)
0 3 * * 0 find /mnt/backup -type d -mtime +30 -exec rm -rf {} +
```

---

## Security Checklist

- [ ] Disable password authentication (use SSH keys only)
- [ ] Configure UFW firewall
- [ ] Enable automatic security updates
- [ ] Use strong passwords for databases
- [ ] Enable fail2ban
- [ ] Regular backups (tested!)
- [ ] Use Tailscale for admin access
- [ ] Keep containers updated
- [ ] Scan for vulnerabilities (Trivy)

```bash
# Security hardening
sudo apt install fail2ban ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Auto updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Conclusion

You can replace a $3,000/month AWS/GCP setup with a $0-20/month self-hosted solution using:

1. **Free hardware** you already have
2. **Oracle Cloud Free Tier** for cloud resources
3. **Docker Compose** or **K3s** for orchestration
4. **NATS** for messaging
5. **Prometheus + Grafana** for monitoring
6. **Caddy** for reverse proxy
7. **Cloudflare Tunnel** for secure access

**Expected savings:** $35,000+ per year

**Trade-offs:**
- You are responsible for maintenance
- Single point of failure (unless clustered)
- Learning curve for self-hosting

**Resources:**
- [K3s Documentation](https://docs.k3s.io/)
- [Caddy Documentation](https://caddyserver.com/docs/)
- [NATS Documentation](https://docs.nats.io/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
