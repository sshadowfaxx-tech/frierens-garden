#!/bin/bash
# ShadowHunter Hetzner Deployment Script
# Copy this entire script, paste into terminal, press Enter
# Tested on Ubuntu 22.04 LTS

set -e  # Exit on any error

echo "=========================================="
echo "  ShadowHunter Tracker - Hetzner Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (use: sudo bash setup.sh)"
    exit 1
fi

# Update system
print_info "Updating system packages..."
apt update -qq && apt upgrade -y -qq
print_status "System updated"

# Install Docker
print_info "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker root
    print_status "Docker installed"
else
    print_status "Docker already installed"
fi

# Install Docker Compose
print_info "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    apt install docker-compose-plugin -y -qq
    print_status "Docker Compose installed"
else
    print_status "Docker Compose already installed"
fi

# Install Python and dependencies
print_info "Installing Python and tools..."
apt install -y -qq python3 python3-venv python3-pip git wget curl
print_status "Python installed"

# Create application directory
APP_DIR="/opt/shadowhunter"
print_info "Creating application directory at $APP_DIR..."
mkdir -p $APP_DIR
cd $APP_DIR
print_status "Directory created"

# Create docker-compose.yml
print_info "Creating Docker Compose configuration..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: timescale/timescaledb:latest-pg16
    container_name: sh-db
    environment:
      POSTGRES_USER: sh
      POSTGRES_PASSWORD: sh123
      POSTGRES_DB: shadowhunter
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sh -d shadowhunter"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: sh-cache
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
EOF
print_status "Docker Compose file created"

# Start databases
print_info "Starting PostgreSQL and Redis..."
docker compose up -d

# Wait for databases to be healthy
print_info "Waiting for databases to be ready..."
sleep 15

# Check if databases are running
if docker ps | grep -q "sh-db" && docker ps | grep -q "sh-cache"; then
    print_status "Databases are running"
else
    print_error "Databases failed to start. Checking logs..."
    docker compose logs
    exit 1
fi

# Create database tables
print_info "Creating database tables..."
docker exec -i sh-db psql -U sh -d shadowhunter << 'EOF'
-- Wallet positions table (tracks live positions)
CREATE TABLE IF NOT EXISTS wallet_positions (
    wallet_address VARCHAR(44) NOT NULL,
    token_address VARCHAR(44) NOT NULL,
    total_bought NUMERIC DEFAULT 0,
    total_sold NUMERIC DEFAULT 0,
    net_position NUMERIC DEFAULT 0,
    total_sol_invested NUMERIC DEFAULT 0,
    first_buy_time TIMESTAMP DEFAULT NOW(),
    last_buy_time TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    avg_entry_mc NUMERIC DEFAULT 0,
    PRIMARY KEY (wallet_address, token_address)
);

-- Wallet performance table (tracks historical stats)
CREATE TABLE IF NOT EXISTS wallet_performance (
    wallet_address VARCHAR(44) PRIMARY KEY,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_sol_invested NUMERIC DEFAULT 0,
    total_sol_returned NUMERIC DEFAULT 0,
    realized_pnl NUMERIC DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_positions_token ON wallet_positions(token_address);
CREATE INDEX IF NOT EXISTS idx_positions_wallet ON wallet_positions(wallet_address);
EOF
print_status "Database tables created"

# Create Python virtual environment
print_info "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q aiohttp asyncpg redis "python-telegram-bot>=20.0" python-dotenv
print_status "Python dependencies installed"

# Create .env template
print_info "Creating environment configuration template..."
cat > .env.example << 'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
CHANNEL_PINGS=-100your_channel_id
CHANNEL_VIP=-100your_vip_channel_id

# Database Configuration (leave defaults if using Docker)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shadowhunter
DB_USER=sh
DB_PASSWORD=sh123

# Redis Configuration (leave defaults if using Docker)
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: Helius RPC (for fallback)
# HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_key
EOF
print_status ".env.example created"

# Create wallets.txt template
print_info "Creating wallets template..."
cat > wallets.txt.example << 'EOF'
# Add your wallets here
# Format: address|label (optional)
# Example:
# 7xR9...k3mP|AlphaTrader
# 9HCT...hp9z|WhaleWatcher

EOF
print_status "wallets.txt.example created"

# Create startup script
cat > start.sh << 'EOF'
#!/bin/bash
cd /opt/shadowhunter
source venv/bin/activate
python trackerv2_clean.py
EOF
chmod +x start.sh

# Create systemd service
print_info "Creating systemd service..."
cat > /etc/systemd/system/shadowhunter.service << 'EOF'
[Unit]
Description=ShadowHunter Tracker Bot
After=docker.service network.target
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/shadowhunter
Environment=PATH=/opt/shadowhunter/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/shadowhunter/venv/bin/python /opt/shadowhunter/trackerv2_clean.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=shadowhunter

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload
systemctl enable shadowhunter
print_status "Systemd service created and enabled"

# Create helper scripts
print_info "Creating helper scripts..."

# View logs script
cat > /opt/shadowhunter/logs.sh << 'EOF'
#!/bin/bash
journalctl -u shadowhunter -f
EOF
chmod +x /opt/shadowhunter/logs.sh

# Restart script
cat > /opt/shadowhunter/restart.sh << 'EOF'
#!/bin/bash
systemctl restart shadowhunter
echo "ShadowHunter restarted"
EOF
chmod +x /opt/shadowhunter/restart.sh

# Status script
cat > /opt/shadowhunter/status.sh << 'EOF'
#!/bin/bash
systemctl status shadowhunter --no-pager
EOF
chmod +x /opt/shadowhunter/status.sh

# Backup script
cat > /opt/shadowhunter/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/shadowhunter/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
docker exec sh-db pg_dump -U sh shadowhunter > $BACKUP_DIR/shadowhunter_backup_$DATE.sql
echo "Backup created: $BACKUP_DIR/shadowhunter_backup_$DATE.sql"
# Keep only last 10 backups
ls -t $BACKUP_DIR/*.sql | tail -n +11 | xargs -r rm
echo "Old backups cleaned up"
EOF
chmod +x /opt/shadowhunter/backup.sh
print_status "Helper scripts created"

# Create update script
cat > /opt/shadowhunter/update.sh << 'EOF'
#!/bin/bash
cd /opt/shadowhunter
echo "Pulling latest code..."
git pull 2>/dev/null || echo "Not a git repository, skipping git pull"
echo "Restarting service..."
systemctl restart shadowhunter
echo "Update complete"
EOF
chmod +x /opt/shadowhunter/update.sh

# Create README
cat > /opt/shadowhunter/README.txt << 'EOF'
SHADOWHUNTER TRACKER - DEPLOYMENT GUIDE
========================================

SETUP CHECKLIST:
□ 1. Upload trackerv2_clean.py to /opt/shadowhunter/
□ 2. Create .env file: cp .env.example .env && nano .env
□ 3. Create wallets.txt: cp wallets.txt.example wallets.txt && nano wallets.txt
□ 4. Start the tracker: systemctl start shadowhunter

COMMANDS:
- Start:    systemctl start shadowhunter
- Stop:     systemctl stop shadowhunter
- Restart:  ./restart.sh
- Status:   ./status.sh
- Logs:     ./logs.sh
- Backup:   ./backup.sh
- Update:   ./update.sh

TROUBLESHOOTING:
- Check logs:        journalctl -u shadowhunter -n 50
- Check databases:   docker ps
- Restart DB:        docker compose restart
- View DB logs:      docker logs sh-db
- Reset DB (DANGER): docker compose down -v && docker compose up -d

FILES:
- Application:    /opt/shadowhunter/
- Tracker code:   /opt/shadowhunter/trackerv2_clean.py
- Config:         /opt/shadowhunter/.env
- Wallets:        /opt/shadowhunter/wallets.txt
- Database:       Docker volume postgres_data
- Logs:           journalctl -u shadowhunter

SUPPORT:
- Check ShadowHunter documentation
- Review deployment guide
EOF

print_status "README created"

echo ""
echo "=========================================="
echo "  SETUP COMPLETE!"
echo "=========================================="
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo ""
echo "1. Upload your files:"
echo "   - trackerv2_clean.py"
echo "   - .env (environment variables)"
echo "   - wallets.txt (your wallet list)"
echo ""
echo "   Use SCP:"
echo "   scp trackerv2_clean.py .env wallets.txt root@YOUR_SERVER_IP:/opt/shadowhunter/"
echo ""
echo "   Or use FileZilla/WinSCP to connect via SFTP"
echo ""
echo "2. Configure environment:"
echo "   cd /opt/shadowhunter"
echo "   nano .env          # Add your Telegram bot token"
echo "   nano wallets.txt   # Add your wallets"
echo ""
echo "3. Start the tracker:"
echo "   systemctl start shadowhunter"
echo ""
echo "4. View logs:"
echo "   ./logs.sh"
echo "   (or: journalctl -u shadowhunter -f)"
echo ""
echo "5. Check status:"
echo "   ./status.sh"
echo ""
echo "HELPER SCRIPTS:"
echo "   ./start.sh     - Manual start"
echo "   ./restart.sh   - Restart service"
echo "   ./logs.sh      - View live logs"
echo "   ./status.sh    - Check service status"
echo "   ./backup.sh    - Backup database"
echo "   ./update.sh    - Update and restart"
echo ""
echo "SERVER IP: $(curl -s ifconfig.me 2>/dev/null || echo 'Check Hetzner console')"
echo ""
echo -e "${YELLOW}Your databases are running at:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
