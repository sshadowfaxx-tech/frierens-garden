"""
ShadowHunter - Production Grade Wallet Tracker
Version: 2.0.0
Features: Circuit breakers, structured logging, graceful shutdown, health checks
"""
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
from telegram import Bot
from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log
)
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import os
import json
import time
import signal
import hashlib
import logging
import sys

# Load environment variables first
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration management"""
    
    # RPC Configuration
    HELIUS_RPC_URL = os.getenv('HELIUS_RPC_URL')
    RPC_URLS = [
        url for url in [HELIUS_RPC_URL, 
                       "https://api.mainnet-beta.solana.com",
                       "https://solana-rpc.publicnode.com"] 
        if url
    ]
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    CHANNEL_VIP = os.getenv('CHANNEL_VIP')
    
    # Birdeye API
    BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY')
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'shadowhunter')
    DB_USER = os.getenv('DB_USER', 'sh')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'sh123')
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    
    # Timing
    CHECK_INTERVAL = 5
    RPC_TIMEOUT = 3
    
    # Cache TTLs
    WALLET_STATS_TTL = 86400  # 24 hours
    TOKEN_INFO_TTL = 300      # 5 minutes
    
    # Thresholds
    NOTABLE_THRESHOLD = 1000  # $1k USD
    CLUSTER_THRESHOLD = 2     # Min wallets for cluster
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of missing critical configs"""
        missing = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
        if not cls.BIRDEYE_API_KEY:
            missing.append("BIRDEYE_API_KEY (optional but recommended)")
        
        return missing


# ============================================================================
# STRUCTURED LOGGING SETUP
# ============================================================================

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "getMessage"
            }:
                log_data[key] = value
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


def setup_logging() -> logging.Logger:
    """Configure structured logging"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger("shadowhunter")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Suppress noisy libraries
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return logger


logger = setup_logging()


# ============================================================================
# CIRCUIT BREAKER PATTERN
# ============================================================================

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent hammering failing services.
    
    CLOSED: Normal operation, requests pass through
    OPEN: Service failing, reject fast
    HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(f"Circuit {self.name} entering HALF_OPEN state")
                else:
                    raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen(f"Circuit {self.name} half-open limit reached")
                self.half_open_calls += 1
        
        # Execute outside lock
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        async with self._lock:
            self.failures = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.half_open_calls = 0
                logger.info(f"Circuit {self.name} closed after recovery")
    
    async def _on_failure(self):
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                if self.state != CircuitState.OPEN:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit {self.name} opened after {self.failures} failures"
                    )


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open"""
    pass


# ============================================================================
# CACHE WITH STAMPEDE PROTECTION
# ============================================================================

class CacheAside:
    """
    Cache-aside pattern with stampede protection.
    Prevents thundering herd when cache expires.
    """
    
    def __init__(self, redis_client: redis.Redis, lock_timeout: int = 10):
        self.redis = redis_client
        self.lock_timeout = lock_timeout
    
    async def get_or_set(
        self,
        key: str,
        factory,
        ttl: int = 300
    ) -> Any:
        """Get from cache or compute and store with stampede protection"""
        # Try cache first
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        # Generate lock key
        lock_key = f"lock:{key}"
        lock_value = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        
        # Try to acquire lock
        lock_acquired = await self.redis.set(
            lock_key,
            lock_value,
            nx=True,
            ex=self.lock_timeout
        )
        
        if not lock_acquired:
            # Someone else is fetching, wait and retry
            logger.debug(f"Cache lock contention for {key}, waiting...")
            await asyncio.sleep(0.1)
            return await self.get_or_set(key, factory, ttl)
        
        try:
            # Double-check cache (might have been set while waiting for lock)
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
            
            # Fetch data
            data = await factory()
            
            # Store in cache
            await self.redis.setex(
                key,
                ttl,
                json.dumps(data, default=str)
            )
            
            return data
        finally:
            # Release lock (only if we still own it)
            current_lock = await self.redis.get(lock_key)
            if current_lock == lock_value:
                await self.redis.delete(lock_key)


# ============================================================================
# CLUSTER DETECTOR
# ============================================================================

class ClusterDetector:
    """Detect wallet clusters and send alerts"""
    
    def __init__(self, db_pool: asyncpg.Pool, cache: redis.Redis, bot: Bot):
        self.db = db_pool
        self.cache = cache
        self.bot = bot
        self.vip_channel = Config.CHANNEL_VIP
        self.cache_helper = CacheAside(cache)
    
    async def update_position(
        self,
        wallet: str,
        token: str,
        tx_type: str,
        amount: float,
        price_usd: float = 0
    ):
        """Track wallet position with cost basis"""
        try:
            if tx_type == "buy":
                await self.db.execute(
                    """
                    INSERT INTO wallet_positions 
                    (wallet_address, token_address, total_bought, net_position, 
                     avg_buy_price, total_cost_usd, last_buy_time)
                    VALUES ($1, $2, $3::numeric, $3::numeric, $4::numeric, 
                            ($3::numeric * $4::numeric), NOW())
                    ON CONFLICT (wallet_address, token_address) 
                    DO UPDATE SET 
                        total_bought = wallet_positions.total_bought + $3::numeric,
                        net_position = wallet_positions.net_position + $3::numeric,
                        avg_buy_price = CASE 
                            WHEN (wallet_positions.total_bought + $3::numeric) > 0 
                            THEN (wallet_positions.total_cost_usd + ($3::numeric * $4::numeric)) 
                                 / (wallet_positions.total_bought + $3::numeric)
                            ELSE $4::numeric 
                        END,
                        total_cost_usd = wallet_positions.total_cost_usd + ($3::numeric * $4::numeric),
                        last_buy_time = NOW(),
                        is_active = TRUE
                    """,
                    wallet, token, amount, price_usd
                )
            else:  # sell
                await self.db.execute(
                    """
                    UPDATE wallet_positions 
                    SET total_sold = total_sold + $3::numeric,
                        net_position = GREATEST(0, net_position - $3::numeric),
                        is_active = (net_position - $3::numeric) > 0.0001
                    WHERE wallet_address = $1 AND token_address = $2
                    """,
                    wallet, token, amount
                )
        except asyncpg.PostgresError as e:
            logger.error("Database error updating position", 
                        error=str(e), wallet=wallet[:10], token=token[:10])
            raise
    
    async def check_cluster(self, token: str, new_wallet: str) -> bool:
        """Check if multiple wallets hold this token"""
        try:
            rows = await self.db.fetch(
                """
                SELECT 
                    wallet_address,
                    first_buy_time,
                    net_position,
                    total_bought,
                    total_sold,
                    total_cost_usd,
                    avg_buy_price,
                    CASE 
                        WHEN total_bought > 0 THEN 
                            ROUND((net_position / total_bought * 100)::numeric, 1)
                        ELSE 0 
                    END as hold_percentage
                FROM wallet_positions 
                WHERE token_address = $1 
                  AND is_active = TRUE 
                  AND net_position > 0.001
                ORDER BY first_buy_time ASC
                """,
                token
            )
            
            if len(rows) >= Config.CLUSTER_THRESHOLD:
                cluster_key = f"cluster:{token}"
                already_alerted = await self.cache.get(cluster_key)
                
                if not already_alerted:
                    await self.cache.setex(cluster_key, 3600, str(len(rows)))
                    await self.send_cluster_alert(token, rows)
                    return True
            
            return False
            
        except asyncpg.PostgresError as e:
            logger.error("Database error checking cluster", error=str(e), token=token[:10])
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def get_token_info(self, token: str) -> Dict[str, Any]:
        """Fetch token metadata from DexScreener with caching"""
        cache_key = f"token_info:{token}"
        
        async def fetch_token():
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        logger.warning("DexScreener rate limited", token=token[:10])
                        raise aiohttp.ClientError("Rate limited")
                    
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get('pairs', [])
                        
                        if pairs:
                            # Prefer Solana pairs
                            solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                            if solana_pairs:
                                pairs = solana_pairs
                            
                            best = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                            
                            return {
                                'ticker': best.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                                'name': best.get('baseToken', {}).get('name', 'Unknown'),
                                'market_cap': float(best.get('marketCap', 0) or 0),
                                'price': float(best.get('priceUsd', 0) or 0),
                                'liquidity': float(best.get('liquidity', {}).get('usd', 0) or 0),
                                'volume_24h': float(best.get('volume', {}).get('h24', 0) or 0),
                                'dexscreener': f"https://dexscreener.com/solana/{token}",
                                'dex': best.get('dexId', 'Unknown')
                            }
            
            return self._fallback_token_info(token)
        
        return await self.cache_helper.get_or_set(
            cache_key, fetch_token, ttl=Config.TOKEN_INFO_TTL
        )
    
    def _fallback_token_info(self, token: str) -> Dict[str, Any]:
        """Return fallback when DexScreener fails"""
        return {
            'ticker': 'NEW',
            'name': 'New Token',
            'market_cap': 0,
            'price': 0,
            'liquidity': 0,
            'volume_24h': 0,
            'dexscreener': f"https://dexscreener.com/solana/{token}",
            'dex': 'Unknown'
        }
    
    async def send_cluster_alert(self, token: str, wallets: List[asyncpg.Record]):
        """Send VIP cluster alert"""
        if not self.vip_channel:
            return
        
        try:
            info = await self.get_token_info(token)
            current_price = info['price']
            wallet_lines = []
            now = datetime.utcnow()
            
            for row in wallets:
                wallet = row['wallet_address']
                first_buy = row['first_buy_time']
                net_pos = float(row['net_position'] or 0)
                total_cost = float(row['total_cost_usd'] or 0)
                hold_pct = float(row['hold_percentage'] or 0)
                
                current_value = net_pos * current_price if current_price else 0
                pnl = current_value - total_cost
                pnl_emoji = "🟢+" if pnl >= 0 else "🔴"
                
                time_diff = now - first_buy
                if time_diff.days > 0:
                    time_str = f"{time_diff.days}d"
                elif time_diff.seconds > 3600:
                    time_str = f"{time_diff.seconds // 3600}h"
                else:
                    time_str = f"{time_diff.seconds // 60}m"
                
                if hold_pct >= 90:
                    status = "Holding"
                elif hold_pct >= 50:
                    status = "Partial"
                else:
                    status = f"Sold {100-hold_pct:.0f}%"
                
                wallet_lines.append(
                    f"`{wallet[:10]}...` | {time_str} | "
                    f"${total_cost:.0f}→${current_value:.0f} | "
                    f"{pnl_emoji}${abs(pnl):.0f} | {status}"
                )
            
            mc_str = (
                f"${info['market_cap']/1_000_000:.2f}M" 
                if info['market_cap'] >= 1_000_000 
                else f"${info['market_cap']/1000:.1f}K"
            )
            
            message = f"""
🚨 *WALLET CLUSTER DETECTED* 🚨

*{info['ticker']}* ({info['name']})
`{token}`

*Market Cap:* `{mc_str}`
*Price:* `${info['price']:.8f}`
*Liquidity:* `${info['liquidity']:,.0f}`
*DEX:* {info['dex']}

👥 *{len(wallets)} Wallets Coordinated:*

Wallet | Time | Cost→Value | P&L | Status
------|------|-----------|-----|-------
{chr(10).join(wallet_lines)}

[📊 DexScreener]({info['dexscreener']})
[🔗 Solscan](https://solscan.io/token/{token})
            """
            
            await self.bot.send_message(
                chat_id=self.vip_channel,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(
                "Cluster alert sent",
                token=info['ticker'],
                wallets=len(wallets),
                market_cap=info['market_cap']
            )
            
        except Exception as e:
            logger.error("Failed to send cluster alert", error=str(e), token=token[:10])


# ============================================================================
# SPEED TRACKER
# ============================================================================

class SpeedTracker:
    """Main tracker class with all resilience patterns"""
    
    def __init__(self):
        self.db: Optional[asyncpg.Pool] = None
        self.cache: Optional[redis.Redis] = None
        self.bot: Optional[Bot] = None
        self.chat_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.cluster_detector: Optional[ClusterDetector] = None
        
        self.rpc_urls = Config.RPC_URLS
        self.rpc_index = 0
        
        # Circuit breakers for external services
        self.birdeye_circuit = CircuitBreaker("birdeye", failure_threshold=3, recovery_timeout=300)
        
        # Graceful shutdown
        self._shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
    
    def _signal_handler(self, signum: int, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutdown_event.set()
    
    async def connect(self):
        """Initialize all connections with validation"""
        # Database
        try:
            self.db = await asyncpg.create_pool(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                min_size=5,
                max_size=20,
                command_timeout=10,
                server_settings={'jit': 'off'}
            )
            logger.info("Database connected")
        except asyncpg.PostgresError as e:
            logger.error("Failed to connect to database", error=str(e))
            raise
        
        # Redis
        try:
            self.cache = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                decode_responses=True,
                max_connections=20
            )
            await self.cache.ping()
            logger.info("Redis connected")
        except redis.ConnectionError as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
        
        # Telegram
        try:
            self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
            self.chat_id = Config.TELEGRAM_CHAT_ID
            me = await self.bot.get_me()
            logger.info("Telegram bot connected", username=me.username)
        except Exception as e:
            logger.error("Failed to connect to Telegram", error=str(e))
            raise
        
        # HTTP Session
        timeout = aiohttp.ClientTimeout(total=Config.RPC_TIMEOUT, connect=2)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        logger.info("HTTP session created")
        
        # Cluster detector
        self.cluster_detector = ClusterDetector(self.db, self.cache, self.bot)
        
        # Test Birdeye if key provided
        if Config.BIRDEYE_API_KEY:
            await self._test_birdeye()
        else:
            logger.warning("Birdeye API key not configured")
    
    async def _test_birdeye(self):
        """Test Birdeye API connectivity"""
        try:
            headers = {"X-API-KEY": Config.BIRDEYE_API_KEY, "accept": "application/json"}
            url = "https://public-api.birdeye.so/wallet/v2/net-worth-details"
            params = {"wallet": "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVbAW5qr5n6LTZ", "type": "1d", "limit": 1}
            
            async with self.session.get(url, headers=headers, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('success'):
                        logger.info("Birdeye API validated")
                    else:
                        logger.warning("Birdeye API returned error", message=data.get('message'))
                elif resp.status == 401:
                    logger.error("Birdeye API key invalid")
        except Exception as e:
            logger.warning("Birdeye API test failed", error=str(e))
    
    async def close(self):
        """Cleanup all resources"""
        logger.info("Closing connections...")
        
        if self.session:
            await self.session.close()
            logger.info("HTTP session closed")
        
        if self.db:
            await self.db.close()
            logger.info("Database pool closed")
        
        if self.cache:
            await self.cache.close()
            logger.info("Redis connection closed")
        
        logger.info("Shutdown complete")
    
    def get_rpc(self) -> str:
        """Get next RPC URL in rotation"""
        url = self.rpc_urls[self.rpc_index % len(self.rpc_urls)]
        self.rpc_index += 1
        return url
    
    async def get_wallet_stats(self, wallet: str, token: str = None) -> Dict[str, Any]:
        """Fetch wallet stats with circuit breaker and caching"""
        if not Config.BIRDEYE_API_KEY:
            return self._empty_stats()
        
        cache_key = f"wallet_stats:{wallet}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for wallet stats", wallet=wallet[:10])
            return json.loads(cached)
        
        # Only fetch on transaction trigger
        if not token:
            return self._empty_stats()
        
        try:
            # Use circuit breaker
            stats = await self.birdeye_circuit.call(
                self._fetch_wallet_stats, wallet, cache_key
            )
            return stats
        except CircuitBreakerOpen:
            logger.warning("Birdeye circuit open, using empty stats")
            return self._empty_stats()
        except Exception as e:
            logger.error("Failed to fetch wallet stats", error=str(e), wallet=wallet[:10])
            return self._empty_stats()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _fetch_wallet_stats(self, wallet: str, cache_key: str) -> Dict[str, Any]:
        """Fetch from Birdeye API"""
        headers = {"X-API-KEY": Config.BIRDEYE_API_KEY, "accept": "application/json"}
        url = "https://public-api.birdeye.so/wallet/v2/net-worth-details"
        params = {"wallet": wallet, "type": "1d", "sort_type": "desc", "limit": 50}
        
        async with self.session.get(url, headers=headers, params=params, timeout=10) as resp:
            if resp.status == 429:
                logger.warning("Birdeye rate limited")
                raise aiohttp.ClientError("Rate limited")
            
            if resp.status != 200:
                error_text = await resp.text()
                logger.error("Birdeye API error", status=resp.status, error=error_text[:100])
                return self._empty_stats()
            
            data = await resp.json()
            
            if data.get('success') and data.get('data'):
                items = data['data'].get('items', [])
                
                total_value = sum(float(item.get('valueUsd', 0) or 0) for item in items)
                active_positions = sum(1 for item in items if float(item.get('valueUsd', 0) or 0) > 1)
                
                # Extract notable tokens
                notable_tokens = []
                for item in items:
                    value = float(item.get('valueUsd', 0) or 0)
                    if value >= Config.NOTABLE_THRESHOLD:
                        notable_tokens.append({
                            'address': item.get('address', ''),
                            'symbol': item.get('symbol', 'UNKNOWN'),
                            'name': item.get('name', 'Unknown'),
                            'value_usd': value,
                            'balance': float(item.get('balance', 0) or 0),
                        })
                
                notable_tokens.sort(key=lambda x: x['value_usd'], reverse=True)
                
                stats = {
                    'active_positions': active_positions,
                    'total_value_usd': total_value,
                    'pnl_30d': 0.0,  # Not available in v2 endpoint
                    'invested': total_value * 0.8,
                    'notable_tokens': notable_tokens,
                    'notable_count': len(notable_tokens),
                    'last_updated': datetime.now().isoformat()
                }
                
                # Cache for 24 hours
                await self.cache.setex(cache_key, Config.WALLET_STATS_TTL, json.dumps(stats))
                
                logger.info(
                    "Wallet stats fetched",
                    wallet=wallet[:10],
                    value=total_value,
                    notables=len(notable_tokens)
                )
                
                return stats
            else:
                return self._empty_stats()
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure"""
        return {
            'active_positions': 0,
            'total_value_usd': 0.0,
            'pnl_30d': 0.0,
            'invested': 0.0,
            'notable_tokens': [],
            'notable_count': 0
        }
    
    def _format_notable(self, tokens: List[Dict]) -> str:
        """Format notable tokens for display"""
        if not tokens:
            return "None"
        
        lines = []
        for t in tokens[:5]:
            v = t['value_usd']
            v_str = f"${v/1000:.1f}K" if v >= 1000 else f"${v:.0f}"
            lines.append(f"• {t['symbol']}: {v_str}")
        
        if len(tokens) > 5:
            lines.append(f"• ... and {len(tokens)-5} more")
        
        return "\n".join(lines)
    
    async def send_alert(self, wallet: str, token: str, tx_type: str, amount: float, sig: str):
        """Send transaction alert"""
        try:
            emoji = "🟢" if tx_type == "buy" else "🔴"
            
            # Get token info (with caching)
            token_info = await self.cluster_detector.get_token_info(token)
            
            # Get wallet stats
            wallet_stats = await self.get_wallet_stats(wallet, token)
            
            # Format market cap
            mc = token_info['market_cap']
            mc_str = f"${mc/1_000_000:.2f}M" if mc >= 1_000_000 else f"${mc/1000:.1f}K"
            
            # Format wallet value
            w_val = wallet_stats.get('total_value_usd', 0)
            w_str = (
                f"${w_val/1_000_000:.2f}M" if w_val >= 1_000_000 
                else f"${w_val/1000:.1f}K" if w_val >= 1000 
                else f"${w_val:.0f}"
            )
            
            notable = self._format_notable(wallet_stats.get('notable_tokens', []))
            
            message = f"""
{emoji} *{tx_type.upper()} ALERT*

*{token_info['ticker']}* ({token_info['name']})
`{token}`

*Market Cap:* `{mc_str}`
*Price:* `${token_info['price']:.8f}`

*Wallet:*
• Value: `{w_str}`
• Positions: `{wallet_stats.get('active_positions', 0)}`

*Notable (>${Config.NOTABLE_THRESHOLD}):*
{notable}

*Tx:* `{amount:.4f} SOL` at `{datetime.now().strftime('%H:%M:%S')}`

[📊 DexScreener]({token_info['dexscreener']})
[🔗 Solscan](https://solscan.io/tx/{sig})
            """
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(
                "Alert sent",
                token=token_info['ticker'],
                type=tx_type,
                amount=amount,
                wallet=wallet[:10]
            )
            
        except Exception as e:
            logger.error("Failed to send alert", error=str(e), wallet=wallet[:10], token=token[:10])
    
    async def check_wallet_fast(self, wallet: str) -> int:
        """Fast wallet check with error isolation"""
        rpc_url = self.get_rpc()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": 5}]
        }
        
        try:
            async with self.session.post(rpc_url, json=payload) as resp:
                if resp.status != 200:
                    return 0
                
                data = await resp.json()
                signatures = data.get('result', [])
                
                if not signatures:
                    return 0
                
                new_count = 0
                
                for sig_info in signatures[:5]:
                    sig = sig_info['signature']
                    
                    if await self.cache.get(f"tx:{sig}"):
                        continue
                    
                    await self.cache.setex(f"tx:{sig}", 3600, "1")
                    
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
                    }
                    
                    async with self.session.post(rpc_url, json=tx_payload) as tx_resp:
                        if tx_resp.status != 200:
                            continue
                        
                        tx_data = await tx_resp.json()
                        tx = tx_data.get('result')
                        
                        if not tx:
                            continue
                        
                        # Parse transaction
                        message = tx.get('transaction', {}).get('message', {})
                        account_keys = message.get('accountKeys', [])
                        
                        wallet_index = None
                        for i, key in enumerate(account_keys):
                            addr = key if isinstance(key, str) else key.get('pubkey', '')
                            if addr == wallet:
                                wallet_index = i
                                break
                        
                        if wallet_index is None:
                            continue
                        
                        meta = tx.get('meta', {})
                        pre = meta.get('preBalances', [])
                        post = meta.get('postBalances', [])
                        
                        if wallet_index >= len(pre) or wallet_index >= len(post):
                            continue
                        
                        change = (post[wallet_index] - pre[wallet_index]) / 1e9
                        
                        if abs(change) < 0.0001:
                            continue
                        
                        tx_type = "buy" if change < 0 else "sell"
                        amount = abs(change)
                        
                        token = "unknown"
                        if len(account_keys) > 1:
                            tk = account_keys[1]
                            token = tk if isinstance(tk, str) else tk.get('pubkey', 'unknown')
                        
                        # Update position and check cluster
                        await self.cluster_detector.update_position(wallet, token, tx_type, amount, 0)
                        
                        if tx_type == "buy":
                            await self.cluster_detector.check_cluster(token, wallet)
                        
                        await self.send_alert(wallet, token, tx_type, amount, sig)
                        new_count += 1
                        
                        logger.debug(f"Detected {tx_type} {amount:.4f} SOL", wallet=wallet[:10])
                
                return new_count
                
        except asyncio.TimeoutError:
            logger.warning("RPC timeout", wallet=wallet[:10])
            return 0
        except Exception as e:
            logger.error("Error checking wallet", error=str(e), wallet=wallet[:10])
            return 0
    
    def load_wallets(self) -> List[str]:
        """Load wallets from file"""
        wallets = []
        try:
            with open('wallets.txt', 'r') as f:
                for line in f:
                    wallet = line.strip()
                    if wallet and not wallet.startswith('#'):
                        wallets.append(wallet)
        except FileNotFoundError:
            logger.error("wallets.txt not found")
        
        return wallets
    
    async def run(self):
        """Main loop with graceful shutdown"""
        await self.connect()
        wallets = self.load_wallets()
        
        if not wallets:
            logger.error("No wallets loaded, exiting")
            return
        
        logger.info(
            "Starting tracker",
            wallets=len(wallets),
            vip=bool(self.cluster_detector.vip_channel),
            birdeye=bool(Config.BIRDEYE_API_KEY)
        )
        
        cycle_count = 0
        
        while not self._shutdown_event.is_set():
            cycle_start = time.time()
            cycle_count += 1
            
            try:
                # Check all wallets in parallel
                tasks = [self.check_wallet_fast(w) for w in wallets]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                total_new = sum(
                    r for r in results 
                    if isinstance(r, int)
                )
                
                elapsed = time.time() - cycle_start
                
                logger.info(
                    "Cycle complete",
                    cycle=cycle_count,
                    elapsed=f"{elapsed:.2f}s",
                    new_transactions=total_new
                )
                
                # Sleep with shutdown check
                sleep_time = max(0, Config.CHECK_INTERVAL - elapsed)
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=sleep_time
                    )
                except asyncio.TimeoutError:
                    pass
                    
            except Exception as e:
                logger.error("Cycle error", error=str(e))
                await asyncio.sleep(1)
        
        logger.info("Shutdown signal received, stopping...")


# ============================================================================
# TELEGRAM COMMANDS
# ============================================================================

async def start_command(update, context):
    """Handle /start command"""
    await update.message.reply_text("⚡ ShadowHunter Bot Online")


async def status_command(update, context):
    """Handle /status command"""
    await update.message.reply_text("✅ Bot running")


async def ping_command(update, context):
    """Handle /ping command"""
    await update.message.reply_text("🏓 Pong!")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Entry point with full lifecycle management"""
    # Validate config
    missing = Config.validate()
    if missing:
        for m in missing:
            logger.error(f"Missing config: {m}")
        if any("TELEGRAM" in m or "BIRDEYE" in m for m in missing):
            raise RuntimeError("Critical configuration missing")
    
    tracker = SpeedTracker()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, tracker._signal_handler)
    signal.signal(signal.SIGINT, tracker._signal_handler)
    
    # Setup Telegram bot
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("ping", ping_command))
    
    # Start bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("ShadowHunter initialized")
    
    try:
        # Run tracker
        await tracker.run()
    finally:
        # Cleanup
        await app.stop()
        await tracker.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical("Fatal error", error=str(e))
        raise
