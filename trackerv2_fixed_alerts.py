"""
ShadowHunter - Wallet Tracker with Token Scanner (Fixed - Fresh Market Cap for Alerts)
"""
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
import os
import json
import time
import signal
import hashlib
import logging
import sys
import re

load_dotenv()

class Config:
    HELIUS_RPC_URL = os.getenv('HELIUS_RPC_URL')
    RPC_URLS = [
        url for url in [HELIUS_RPC_URL, 
                       "https://api.mainnet-beta.solana.com",
                       "https://solana-rpc.publicnode.com"] 
        if url
    ]
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    CHANNEL_PINGS = os.getenv('CHANNEL_PINGS')
    CHANNEL_VIP = os.getenv('CHANNEL_VIP')
    CHANNEL_SCANNER = os.getenv('CHANNEL_SCANNER')
    BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY')
    BITQUERY_API_KEY = os.getenv('BITQUERY_API_KEY')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'shadowhunter')
    DB_USER = os.getenv('DB_USER', 'sh')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'sh123')
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    CHECK_INTERVAL = 5
    RPC_TIMEOUT = 3
    TOKEN_INFO_TTL = 300
    NOTABLE_THRESHOLD = 1000
    CLUSTER_THRESHOLD = 2
    MIN_SOL_THRESHOLD = 0.02

class JSONFormatter(logging.Formatter):
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
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "getMessage"
            }:
                log_data[key] = value
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, default=str)

def setup_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger = logging.getLogger("shadowhunter")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    return logger

logger = setup_logging()

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, 
                 recovery_timeout: float = 60.0, half_open_max_calls: int = 3):
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
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    raise Exception(f"Circuit {self.name} is OPEN")
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise Exception(f"Circuit {self.name} half-open limit reached")
                self.half_open_calls += 1
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
    
    async def _on_failure(self):
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold and self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN

class CacheAside:
    def __init__(self, redis_client: redis.Redis, lock_timeout: int = 10):
        self.redis = redis_client
        self.lock_timeout = lock_timeout
    
    async def get_or_set(self, key: str, factory, ttl: int = 300) -> Any:
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        lock_key = f"lock:{key}"
        lock_value = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        lock_acquired = await self.redis.set(lock_key, lock_value, nx=True, ex=self.lock_timeout)
        if not lock_acquired:
            await asyncio.sleep(0.1)
            return await self.get_or_set(key, factory, ttl)
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
            data = await factory()
            await self.redis.setex(key, ttl, json.dumps(data, default=str))
            return data
        finally:
            current_lock = await self.redis.get(lock_key)
            if current_lock == lock_value:
                await self.redis.delete(lock_key)

class ClusterDetector:
    def __init__(self, db_pool: asyncpg.Pool, cache: redis.Redis, bot: Bot):
        self.db = db_pool
        self.cache = cache
        self.bot = bot
        self.vip_channel = Config.CHANNEL_VIP
        self.cache_helper = CacheAside(cache)
    
    async def update_position(self, wallet: str, token: str, tx_type: str, 
                             token_amount: float, price_usd: float = 0, 
                             sol_amount: float = 0):
        try:
            if tx_type == "buy":
                await self.db.execute(
                    """INSERT INTO wallet_positions (
                        wallet_address, token_address, total_bought, net_position, 
                        avg_buy_price, total_cost_usd, total_sol_invested, last_buy_time
                    ) VALUES ($1, $2, $3::numeric, $3::numeric, $4::numeric, 
                        ($3::numeric * $4::numeric), $5::numeric, NOW())
                    ON CONFLICT (wallet_address, token_address) DO UPDATE SET 
                    total_bought = wallet_positions.total_bought + $3::numeric,
                    net_position = wallet_positions.net_position + $3::numeric,
                    avg_buy_price = CASE 
                        WHEN (wallet_positions.total_bought + $3::numeric) > 0 
                        THEN (wallet_positions.total_cost_usd + ($3::numeric * $4::numeric)) 
                             / (wallet_positions.total_bought + $3::numeric)
                        ELSE $4::numeric 
                    END,
                    total_cost_usd = wallet_positions.total_cost_usd + ($3::numeric * $4::numeric),
                    total_sol_invested = wallet_positions.total_sol_invested + $5::numeric,
                    last_buy_time = NOW(), 
                    is_active = TRUE""",
                    wallet, token, token_amount, price_usd, sol_amount
                )
            else:
                await self.db.execute(
                    """UPDATE wallet_positions 
                    SET total_sold = COALESCE(total_sold, 0) + $3::numeric,
                        net_position = GREATEST(0, net_position - $3::numeric),
                        is_active = (net_position - $3::numeric) > 0.0001
                    WHERE wallet_address = $1 AND token_address = $2""",
                    wallet, token, token_amount
                )
        except Exception as e:
            logger.error("Database error", extra={
                "error": str(e), 
                "wallet": wallet[:10], 
                "token": token[:10],
                "type": tx_type
            })
            raise
    
    async def check_cluster(self, token: str, new_wallet: str, wallet_labels: Dict[str, str] = None) -> bool:
        try:
            rows = await self.db.fetch(
                """SELECT wallet_address, first_buy_time, net_position, 
                    total_bought, total_sold, total_cost_usd, 
                    total_sol_invested, avg_buy_price,
                    CASE WHEN total_bought > 0 
                        THEN ROUND((net_position / total_bought * 100)::numeric, 1) 
                        ELSE 0 
                    END as hold_percentage
                FROM wallet_positions 
                WHERE token_address = $1 
                AND is_active = TRUE 
                AND net_position > 0.001
                ORDER BY first_buy_time ASC""", token
            )
            if len(rows) >= Config.CLUSTER_THRESHOLD:
                cluster_key = f"cluster:{token}"
                if not await self.cache.get(cluster_key):
                    await self.cache.setex(cluster_key, 3600, str(len(rows)))
                    await self.send_cluster_alert(token, rows, wallet_labels)
                    return True
            return False
        except Exception as e:
            logger.error("Cluster check error", extra={"error": str(e)})
            return False
    
    async def send_cluster_alert(self, token: str, wallets: List[asyncpg.Record], 
                                 wallet_labels: Dict[str, str] = None):
        if not self.vip_channel:
            return
        
        if wallet_labels is None:
            wallet_labels = {}
        
        try:
            info = await self.get_token_info(token)
            wallet_lines = []
            now = datetime.utcnow()
            
            for row in wallets:
                wallet = row['wallet_address']
                label = wallet_labels.get(wallet, wallet[:8] + "...")
                pnl = (float(row['net_position'] or 0) * info['price']) - (row['total_cost_usd'] or 0)
                
                net_position = float(row['net_position'] or 0)
                status = "💎 HOLDING" if net_position > 0.001 else "💨 SOLD OUT"
                
                sol_invested = float(row['total_sol_invested'] or 0)
                sol_str = f"{sol_invested:.2f} SOL" if sol_invested > 0 else "N/A"
                
                first_buy = row['first_buy_time']
                if first_buy and first_buy.tzinfo is not None:
                    first_buy = first_buy.replace(tzinfo=None)
                
                time_str = "unknown"
                if first_buy:
                    time_diff = now - first_buy
                    if time_diff.days > 0:
                        time_str = f"{time_diff.days}d"
                    elif time_diff.seconds > 3600:
                        time_str = f"{time_diff.seconds // 3600}h"
                    else:
                        time_str = f"{time_diff.seconds // 60}m"
                
                pnl_emoji = "🟢+" if pnl >= 0 else "🔴-"
                pnl_str = f"{pnl_emoji}${abs(pnl):.0f}"
                
                wallet_lines.append(f"*{label}* | {status} | 💰{sol_str} | {time_str} | {pnl_str}")
            
            if info['market_cap'] >= 1_000_000:
                mc_str = f"${info['market_cap']/1_000_000:.2f}M"
            elif info['market_cap'] > 0:
                mc_str = f"${info['market_cap']/1000:.1f}K"
            else:
                mc_str = "Unknown"
            
            holders = sum(1 for r in wallets if float(r['net_position'] or 0) > 0.001)
            sellers = len(wallets) - holders
            total_sol = sum(float(r['total_sol_invested'] or 0) for r in wallets)
            
            message = f"""🚨 *WALLET CLUSTER* 🚨

*{info['ticker']}* ({info['name']})
`{token}`

💰 *Market Cap:* `{mc_str}`
📈 *Price:* `${info['price']:.8f}`
💵 *Total SOL in Cluster:* `{total_sol:.2f} SOL`

👥 *{len(wallets)} Wallets | 💎 {holders} Holding | 💨 {sellers} Sold*

{chr(10).join(wallet_lines[:10])}

[📊 View on DexScreener]({info['dexscreener']})"""
            
            await self.bot.send_message(
                chat_id=self.vip_channel, 
                text=message, 
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info("VIP cluster alert sent", extra={
                "token": info['ticker'],
                "wallets": len(wallets),
                "channel": self.vip_channel
            })
            
        except Exception as e:
            logger.error("VIP cluster alert failed", extra={"error": str(e)})
    
    async def get_pumpfun_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        if not Config.BITQUERY_API_KEY:
            return None
        
        url = "https://streaming.bitquery.io/graphql"
        query = """
        query GetPumpFunToken($token: String!) {
          Solana {
            DEXTradeByTokens(
              limit: {count: 1}
              orderBy: {descending: Block_Time}
              where: {Trade: {Currency: {MintAddress: {is: $token}}}}
            ) {
              Trade {
                Currency {Name Symbol MintAddress}
                PriceInUSD
              }
            }
          }
        }
        """
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(
                    url,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {Config.BITQUERY_API_KEY}"},
                    json={"query": query, "variables": {"token": token}}
                ) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    if data.get("errors"):
                        return None
                    
                    trades = data.get("data", {}).get("Solana", {}).get("DEXTradeByTokens", [])
                    if not trades:
                        return None
                    
                    trade = trades[0]
                    currency = trade.get("Trade", {}).get("Currency", {})
                    price_usd = trade.get("Trade", {}).get("PriceInUSD", 0)
                    
                    estimated_supply = 1_000_000_000
                    market_cap = price_usd * estimated_supply if price_usd else 0
                    
                    return {
                        'ticker': currency.get('Symbol', 'PUMP'),
                        'name': currency.get('Name', 'Pump.fun Token'),
                        'market_cap': market_cap,
                        'price': price_usd,
                        'liquidity': 0,
                        'dexscreener': f"https://dexscreener.com/solana/{token}",
                        'dex': 'Pump.fun',
                        'source': 'bitquery'
                    }
        except Exception as e:
            logger.debug(f"Bitquery error: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=10),
           retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)))
    async def get_token_info(self, token: str) -> Dict[str, Any]:
        cache_key = f"token_info:{token}"
        
        async def fetch_token():
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        raise aiohttp.ClientError("Rate limited")
                    
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get('pairs') or []
                        
                        if pairs:
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
                                'dexscreener': f"https://dexscreener.com/solana/{token}",
                                'dex': best.get('dexId', 'Unknown'),
                                'source': 'dexscreener'
                            }
            
            bitquery_data = await self.get_pumpfun_token_info(token)
            if bitquery_data:
                return bitquery_data
            
            return {
                'ticker': 'NEW', 
                'name': 'New Token', 
                'market_cap': 0, 
                'price': 0,
                'liquidity': 0, 
                'dexscreener': f"https://dexscreener.com/solana/{token}", 
                'dex': 'Unknown',
                'source': 'none'
            }
        
        return await self.cache_helper.get_or_set(cache_key, fetch_token, ttl=Config.TOKEN_INFO_TTL)

class SpeedTracker:
    def __init__(self):
        self.db = None
        self.cache = None
        self.bot = None
        self.session = None
        self.cluster_detector = None
        self.wallets = []
        self.rpc_urls = Config.RPC_URLS
        self.rpc_index = 0
        self.birdeye_circuit = CircuitBreaker("birdeye", failure_threshold=3, recovery_timeout=300)
        self._shutdown_event = asyncio.Event()
    
    def _signal_handler(self, signum: int, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()
    
    async def connect(self):
        self.db = await asyncpg.create_pool(
            host=Config.DB_HOST, port=Config.DB_PORT, database=Config.DB_NAME,
            user=Config.DB_USER, password=Config.DB_PASSWORD,
            min_size=5, max_size=20, command_timeout=10, server_settings={'jit': 'off'}
        )
        self.cache = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True, max_connections=20)
        await self.cache.ping()
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        me = await self.bot.get_me()
        logger.info("Bot connected", extra={"username": me.username})
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=Config.RPC_TIMEOUT, connect=2),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=30)
        )
        self.cluster_detector = ClusterDetector(self.db, self.cache, self.bot)
        
        if Config.CHANNEL_PINGS:
            logger.info(f"Normal alerts will go to: {Config.CHANNEL_PINGS}")
        if Config.CHANNEL_VIP:
            logger.info(f"VIP cluster alerts will go to: {Config.CHANNEL_VIP}")
        if Config.CHANNEL_SCANNER:
            logger.info(f"Token scanner active in: {Config.CHANNEL_SCANNER}")
    
    async def close(self):
        if self.session:
            await self.session.close()
        if self.db:
            await self.db.close()
        if self.cache:
            await self.cache.aclose()
    
    def get_rpc(self) -> str:
        url = self.rpc_urls[self.rpc_index % len(self.rpc_urls)]
        self.rpc_index += 1
        return url
    
    def load_wallets(self) -> List[Dict[str, str]]:
        wallets = []
        try:
            with open('wallets.txt', 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '|' in line:
                        address, label = line.split('|', 1)
                        address = address.strip()
                        label = label.strip()
                    else:
                        address = line.strip()
                        label = None
                    
                    if len(address) < 32:
                        continue
                    
                    wallets.append({
                        'address': address,
                        'label': label or f"Wallet {len(wallets) + 1}"
                    })
        except FileNotFoundError:
            logger.error("wallets.txt not found")
        
        logger.info(f"Loaded {len(wallets)} wallets")
        return wallets
    
    async def get_token_supply_helius(self, token: str) -> Optional[float]:
        """Get token supply from Helius RPC."""
        try:
            rpc_url = self.get_rpc()
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",
                "params": [token]
            }
            
            logger.info(f"SUPPLY HELIUS: Fetching supply for {token[:10]}...")
            
            async with self.session.post(rpc_url, json=payload) as resp:
                if resp.status != 200:
                    logger.warning(f"SUPPLY HELIUS: HTTP {resp.status}")
                    return None
                
                data = await resp.json()
                result = data.get('result', {})
                value = result.get('value', {})
                
                amount = value.get('amount', '0')
                decimals = value.get('decimals', 9)
                
                if amount:
                    supply = float(amount) / (10 ** decimals)
                    logger.info(f"SUPPLY HELIUS: Supply = {supply:,.2f}")
                    return supply
                
                return None
                
        except Exception as e:
            logger.error(f"SUPPLY HELIUS: Error - {e}")
            return None
    
    async def get_token_ath_bitquery(self, token: str) -> Optional[Dict[str, float]]:
        """Get ATH price from Bitquery using aATH field."""
        if not Config.BITQUERY_API_KEY:
            logger.warning("ATH BITQUERY: No BITQUERY_API_KEY configured")
            return None
        
        url = "https://streaming.bitquery.io/graphql"
        
        query = """
        query GetTokenATH($token: String!) {
            Solana(dataset: combined) {
                DEXTradeByTokens(
                    where: {Trade: {Side: {Currency: {MintAddress: {in:
                        ["11111111111111111111111111111111",
                            "So11111111111111111111111111111111111111112"]}}, 
                        AmountInUSD: {gt: "10"}}, Currency: 
                        {MintAddress: {is: $token}}}}
                    limit: {count: 1}
                    orderBy: {descendingByField: "aATH"}
                ) {
                    aATH: quantile(of: Trade_PriceInUSD, level: 0.99)
                    Trade {
                        Price(maximum: Trade_Price)
                    }
                }
            }
        }
        """
        
        try:
            logger.info(f"ATH BITQUERY: Fetching aATH for {token[:10]}...")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.post(
                    url,
                    headers={
                        "Content-Type": "application/json", 
                        "Authorization": f"Bearer {Config.BITQUERY_API_KEY}"
                    },
                    json={"query": query, "variables": {"token": token}}
                ) as resp:
                    logger.info(f"ATH BITQUERY: HTTP {resp.status}")
                    
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(f"ATH BITQUERY: HTTP {resp.status} - {text[:200]}")
                        return None
                    
                    data = await resp.json()
                    
                    if data.get("errors"):
                        logger.warning(f"ATH BITQUERY: GraphQL errors: {data['errors']}")
                        return None
                    
                    solana_data = data.get("data", {}).get("Solana", {})
                    
                    trades = solana_data.get("DEXTradeByTokens", [])
                    if not trades:
                        logger.warning("ATH BITQUERY: No trades found")
                        return None
                    
                    ath_price = float(trades[0].get("aATH", 0) or 0)
                    
                    if ath_price <= 0:
                        logger.warning("ATH BITQUERY: No aATH found")
                        return None
                    
                    logger.info(f"ATH BITQUERY: aATH = ${ath_price:.10f}")
                    
                    total_supply = await self.get_token_supply_helius(token)
                    
                    if not total_supply or total_supply <= 0:
                        logger.warning("ATH: No supply data from Helius")
                        return None
                    
                    ath_market_cap = ath_price * total_supply
                    logger.info(f"ATH: Calculated ATH MC = ${ath_market_cap:,.2f}")
                    
                    return {
                        'ath_price': ath_price,
                        'total_supply': total_supply,
                        'ath_market_cap': ath_market_cap
                    }
                    
        except Exception as e:
            logger.error(f"ATH BITQUERY: Error - {type(e).__name__}: {e}")
            return None
    
    async def scan_token(self, contract_address: str, channel_id: str):
        """Scan a token and send info to the scanner channel."""
        try:
            if len(contract_address) < 32 or len(contract_address) > 44:
                await self.bot.send_message(
                    chat_id=channel_id,
                    text="❌ Invalid Solana contract address format."
                )
                return
            
            logger.info(f"Scanning token: {contract_address[:15]}...")
            
            token_info = await self.cluster_detector.get_token_info(contract_address)
            logger.info(f"SCAN: Got token: {token_info['ticker']} @ ${token_info['price']:.8f}")
            
            logger.info(f"SCAN: Fetching ATH data...")
            ath_data = await self.get_token_ath_bitquery(contract_address)
            
            ath_market_cap = None
            ath_price = None
            if ath_data:
                ath_market_cap = ath_data['ath_market_cap']
                ath_price = ath_data['ath_price']
                logger.info(f"SCAN: ATH found: ${ath_market_cap:,.2f}")
            else:
                logger.warning(f"SCAN: No ATH data available")
            
            if token_info['market_cap'] >= 1_000_000:
                mc_str = f"${token_info['market_cap']/1_000_000:.2f}M"
            elif token_info['market_cap'] > 0:
                mc_str = f"${token_info['market_cap']/1000:.1f}K"
            else:
                mc_str = "Unknown"
            
            if ath_market_cap and ath_market_cap >= 1_000_000:
                ath_str = f"${ath_market_cap/1_000_000:.2f}M"
            elif ath_market_cap and ath_market_cap > 0:
                ath_str = f"${ath_market_cap/1000:.1f}K"
            else:
                ath_str = "N/A"
            
            ath_price_str = ""
            if ath_price and ath_price > 0:
                ath_price_str = f"🏆 *ATH Price:* `${ath_price:.10f}`\n"
            
            drawdown = ""
            if token_info['market_cap'] > 0 and ath_market_cap and ath_market_cap > 0:
                pct = (1 - token_info['market_cap'] / ath_market_cap) * 100
                drawdown = f"📉 *From ATH:* `-{pct:.1f}%`\n"
            
            source_emoji = "💎" if token_info.get('source') in ['bitquery', 'pumpfun_api'] else "📊"
            
            message = f"""{source_emoji} *TOKEN SCAN RESULTS*

*{token_info['ticker']}* ({token_info['name']})
`{contract_address}`

💰 *Current Market Cap:* `{mc_str}`
🏆 *ATH Market Cap:* `{ath_str}`
{ath_price_str}{drawdown}💵 *Current Price:* `${token_info['price']:.10f}`

🔗 [DexScreener]({token_info['dexscreener']})
🔗 [Pump.fun](https://pump.fun/{contract_address}) | [Photon](https://photon-sol.tinyastro.io/en/lp/{contract_address}) | [BullX](https://bullx.io/terminal?chainId=1399811149&address={contract_address})

_Scan provided by ShadowHunter_ 🤖"""
            
            await self.bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info("Token scan complete", extra={
                "token": token_info['ticker'],
                "ath_mc": ath_market_cap,
                "current_mc": token_info['market_cap']
            })
            
        except Exception as e:
            logger.error("Token scan failed", extra={"error": str(e)})
            await self.bot.send_message(
                chat_id=channel_id,
                text=f"❌ Error scanning token. Please try again."
            )
    
    async def send_alert(self, wallet: str, token: str, tx_type: str, sol_amount: float, sig: str):
        """Send transaction alert - with fresh market cap data."""
        try:
            emoji = "🟢" if tx_type == "buy" else "🔴"
            
            wallet_label = None
            for w in self.wallets:
                if w['address'] == wallet:
                    wallet_label = w['label']
                    break
            
            # Fetch fresh token info for alerts (bypass cache)
            token_info = await self._fetch_fresh_token_info(token)
            
            # Handle case where token_info is None
            if token_info is None:
                logger.warning(f"Could not fetch token info for {token[:10]}, using fallback")
                token_info = {
                    'ticker': 'UNKNOWN',
                    'name': 'Unknown Token',
                    'market_cap': 0,
                    'price': 0,
                    'dexscreener': f"https://dexscreener.com/solana/{token}",
                    'source': 'none'
                }
            
            if token_info['market_cap'] >= 1_000_000:
                mc_str = f"${token_info['market_cap']/1_000_000:.2f}M"
            elif token_info['market_cap'] > 0:
                mc_str = f"${token_info['market_cap']/1000:.1f}K"
            else:
                mc_str = "Unknown"
            
            if wallet_label and not wallet_label.startswith("Wallet "):
                wallet_display = f"*{wallet_label}*\n`{wallet}`"
            else:
                wallet_display = f"`{wallet}`"
            
            sol_str = f"{sol_amount:.4f} SOL"
            
            source_line = ""
            if token_info.get('source') == 'bitquery':
                source_line = "💎 *Source:* Bitquery (Pre-migration)\n"
            elif token_info.get('source') == 'pumpfun_api':
                source_line = "💎 *Source:* Pump.fun (Bonding Curve)\n"
            
            message = f"""{emoji} *{tx_type.upper()} ALERT*

👤 *Wallet:* {wallet_display}

*{token_info['ticker']}* ({token_info['name']})
`{token}`

{source_line}*Market Cap:* `{mc_str}`
*Price:* `${token_info['price']:.8f}`

💰 *{tx_type.capitalize()} Amount:* `{sol_str}`
🕐 *Time:* `{datetime.now().strftime('%H:%M:%S')}`

[📊 DexScreener]({token_info['dexscreener']})
[🔗 Solscan](https://solscan.io/tx/{sig})"""
            
            target_channel = Config.CHANNEL_PINGS or Config.TELEGRAM_CHAT_ID
            
            await self.bot.send_message(
                chat_id=target_channel, 
                text=message, 
                parse_mode='Markdown', 
                disable_web_page_preview=True
            )
            
            logger.info("Alert sent", extra={
                "token": token_info['ticker'], 
                "type": tx_type, 
                "sol": sol_amount, 
                "wallet": wallet[:10]
            })
            
        except Exception as e:
            logger.error("Alert failed", extra={"error": str(e)})
    
    async def _fetch_fresh_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Fetch fresh token info directly from DexScreener - no caching."""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get('pairs') or []
                    
                    if pairs:
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
                            'dexscreener': f"https://dexscreener.com/solana/{token}",
                            'dex': best.get('dexId', 'Unknown'),
                            'source': 'dexscreener'
                        }
            
            # Fallback to Bitquery for Pump.fun tokens
            bitquery_data = await self.cluster_detector.get_pumpfun_token_info(token)
            if bitquery_data:
                return bitquery_data
            
            return None
        except Exception as e:
            logger.warning(f"Fresh token fetch failed: {e}")
            return None
    
    async def check_wallet_fast(self, wallet_dict: Dict[str, str]) -> int:
        wallet = wallet_dict['address']
        label = wallet_dict.get('label', 'Unknown')
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
                        "params": [sig, {
                            "encoding": "jsonParsed", 
                            "maxSupportedTransactionVersion": 0,
                            "commitment": "confirmed"
                        }]
                    }
                    
                    async with self.session.post(rpc_url, json=tx_payload) as tx_resp:
                        if tx_resp.status != 200:
                            continue
                        
                        tx_data = await tx_resp.json()
                        tx = tx_data.get('result')
                        if not tx:
                            continue
                        
                        meta = tx.get('meta', {})
                        pre_tokens = meta.get('preTokenBalances', []) or []
                        post_tokens = meta.get('postTokenBalances', []) or []
                        
                        pre_sol_balances = meta.get('preBalances', [])
                        post_sol_balances = meta.get('postBalances', [])
                        
                        message = tx.get('transaction', {}).get('message', {})
                        account_keys = message.get('accountKeys', [])
                        
                        wallet_index = None
                        for i, key in enumerate(account_keys):
                            addr = key if isinstance(key, str) else key.get('pubkey', '')
                            if addr == wallet:
                                wallet_index = i
                                break
                        
                        sol_change = 0.0
                        if wallet_index is not None and wallet_index < len(pre_sol_balances) and wallet_index < len(post_sol_balances):
                            pre_lamports = pre_sol_balances[wallet_index]
                            post_lamports = post_sol_balances[wallet_index]
                            sol_change = (post_lamports - pre_lamports) / 1e9
                        
                        wallet_token_indices = set()
                        for balance in pre_tokens + post_tokens:
                            owner = balance.get('owner', '')
                            if owner == wallet:
                                wallet_token_indices.add(balance.get('accountIndex'))
                        
                        if not wallet_token_indices:
                            continue
                        
                        pre_balances = {}
                        post_balances = {}
                        
                        for bal in pre_tokens:
                            idx = bal.get('accountIndex')
                            if idx in wallet_token_indices:
                                mint = bal.get('mint', '')
                                amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                                pre_balances[mint] = amount
                        
                        for bal in post_tokens:
                            idx = bal.get('accountIndex')
                            if idx in wallet_token_indices:
                                mint = bal.get('mint', '')
                                amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                                post_balances[mint] = amount
                        
                        all_mints = set(pre_balances.keys()) | set(post_balances.keys())
                        changes = []
                        
                        for mint in all_mints:
                            pre = pre_balances.get(mint, 0)
                            post = post_balances.get(mint, 0)
                            change = post - pre
                            
                            if abs(change) > 0:
                                changes.append({
                                    'token': mint,
                                    'type': "buy" if change > 0 else "sell",
                                    'token_amount': abs(change),
                                    'sol_amount': abs(sol_change)
                                })
                        
                        if not changes:
                            continue
                        
                        for change in changes:
                            if change['sol_amount'] < Config.MIN_SOL_THRESHOLD:
                                continue
                            
                            await self.cluster_detector.update_position(
                                wallet, 
                                change['token'], 
                                change['type'], 
                                change['token_amount'], 
                                price_usd=0,
                                sol_amount=change['sol_amount'] if change['type'] == 'buy' else 0
                            )
                            
                            if change['type'] == "buy":
                                wallet_labels = {w['address']: w['label'] for w in self.wallets}
                                await self.cluster_detector.check_cluster(change['token'], wallet, wallet_labels)
                            
                            await self.send_alert(wallet, change['token'], change['type'], change['sol_amount'], sig)
                            new_count += 1
                            
                            await asyncio.sleep(0.5)
                
                return new_count
                
        except asyncio.TimeoutError:
            return 0
        except Exception as e:
            logger.error(f"Check error: {e}")
            return 0
    
    async def run(self):
        await self.connect()
        self.wallets = self.load_wallets()
        if not self.wallets:
            logger.error("No wallets loaded")
            return
        
        logger.info("Starting tracker", extra={
            "wallets": len(self.wallets),
            "min_sol": Config.MIN_SOL_THRESHOLD
        })
        
        cycle_count = 0
        while not self._shutdown_event.is_set():
            cycle_start = time.time()
            cycle_count += 1
            try:
                tasks = [self.check_wallet_fast(w) for w in self.wallets]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                total_new = sum(r for r in results if isinstance(r, int))
                elapsed = time.time() - cycle_start
                logger.info("Cycle complete", extra={
                    "cycle": cycle_count, 
                    "elapsed": f"{elapsed:.2f}s", 
                    "new_transactions": total_new
                })
                
                sleep_time = max(0, Config.CHECK_INTERVAL - elapsed)
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=sleep_time)
                except asyncio.TimeoutError:
                    pass
            except Exception as e:
                logger.error("Cycle error", extra={"error": str(e)})
                await asyncio.sleep(1)

async def start_cmd(update: Update, context):
    await update.message.reply_text("⚡ ShadowHunter Online")

async def status_cmd(update: Update, context):
    await update.message.reply_text("✅ Running")

async def main():
    tracker = SpeedTracker()
    signal.signal(signal.SIGTERM, tracker._signal_handler)
    signal.signal(signal.SIGINT, tracker._signal_handler)
    
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    
    if Config.CHANNEL_SCANNER:
        solana_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
        
        async def scan_handler(update: Update, context):
            chat_id = update.effective_chat.id if update.effective_chat else "NONE"
            
            if str(chat_id) != str(Config.CHANNEL_SCANNER):
                return
            
            message = update.message or update.edited_message or update.channel_post
            if not message:
                return
            
            message_text = message.text or message.caption or ""
            if not message_text:
                return
            
            addresses = re.findall(solana_pattern, message_text)
            
            skip_list = {
                '11111111111111111111111111111111',
                'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
                'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'
            }
            
            for address in addresses:
                if address in skip_list:
                    continue
                await tracker.scan_token(address, Config.CHANNEL_SCANNER)
        
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan_handler), group=1)
        logger.info(f"Token scanner registered for channel: {Config.CHANNEL_SCANNER}")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        await tracker.run()
    finally:
        await app.stop()
        await tracker.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.critical("Fatal error", extra={"error": str(e)})
        raise
