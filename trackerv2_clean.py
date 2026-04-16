"""
ShadowHunter - Wallet Tracker with Live Cluster Updates
Cleaned version - essential functionality only
"""
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
import os
import json
import time
import signal
import logging
import sys
import re
# Fix SSL certificates on Windows
import ssl
import certifi

# Create SSL context with proper certificates
ssl_context = ssl.create_default_context(cafile=certifi.where())
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

load_dotenv()


class Config:
    HELIUS_RPC_URL = os.getenv('HELIUS_RPC_URL')
    ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
    ALCHEMY_RPC_URL = f"https://solana-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}" if ALCHEMY_API_KEY else None
    RPC_URLS = [
        url for url in [
            "https://api.mainnet-beta.solana.com",
            "https://solana-rpc.publicnode.com",
            HELIUS_RPC_URL  # Fallback for when public RPCs fail
        ]
        if url
    ]
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    CHANNEL_PINGS = os.getenv('CHANNEL_PINGS')
    CHANNEL_VIP = os.getenv('CHANNEL_VIP')
    CHANNEL_TRANSFERS = os.getenv('CHANNEL_TRANSFERS')  # For wallet-to-wallet transfer alerts
    # Transfer thresholds
    TRANSFER_SOL_THRESHOLD = 0.5  # SOL
    TRANSFER_TOKEN_THRESHOLD = 100  # tokens
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'shadowhunter')
    DB_USER = os.getenv('DB_USER', 'sh')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'sh123')
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    CHECK_INTERVAL = 5
    RPC_TIMEOUT = 5  # Increased for Helius enhanced RPCs
    TOKEN_INFO_TTL = 300
    CLUSTER_THRESHOLD = 2
    MIN_SOL_THRESHOLD = 0.02
    IGNORED_TOKENS = [
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    ]
    # Retry settings
    DB_MAX_RETRIES = 5
    DB_BASE_RETRY_DELAY = 0.5  # seconds, doubles each retry
    # Performance tracking
    PERFORMANCE_SNAPSHOT_INTERVAL = 3600  # Save snapshot every hour
    # Admin users for wallet management commands (comma-separated Telegram user IDs)
    ADMIN_USERS = [int(uid.strip()) for uid in os.getenv('ADMIN_USERS', '').split(',') if uid.strip()]
    
    # Helius Optimized Settings (Upgraded Plan)
    # With paid Helius, we can fetch more transactions per call (100 vs 20)
    # and make more concurrent requests without rate limiting
    HELIUS_TX_LIMIT = 100  # Max transactions per getSignaturesForAddress call
    HELIUS_PRIORITY_FEE = 10000  # Micro-lamports for faster confirmation tracking


# Simple console logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("shadowhunter")
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


async def with_db_retry(func: Callable, *args, **kwargs):
    """
    Execute a DB function with exponential backoff retry.
    Retries on connection/pool errors, not on data errors.
    """
    last_exception = None
    
    for attempt in range(1, Config.DB_MAX_RETRIES + 1):
        try:
            return await func(*args, **kwargs)
        except (asyncpg.exceptions.TooManyConnectionsError,
                asyncpg.exceptions.ConnectionDoesNotExistError,
                asyncpg.exceptions.ConnectionFailureError,
                OSError) as e:
            # These are retryable connection errors
            last_exception = e
            if attempt < Config.DB_MAX_RETRIES:
                delay = Config.DB_BASE_RETRY_DELAY * (2 ** (attempt - 1))
                logger.warning(f"DB connection error (attempt {attempt}/{Config.DB_MAX_RETRIES}): {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"DB connection failed after {Config.DB_MAX_RETRIES} attempts: {e}")
                raise
        except Exception as e:
            # Non-retryable error (syntax error, constraint violation, etc.)
            logger.error(f"DB error (not retryable): {e}")
            raise
    
    raise last_exception


class ClusterDetector:
    def __init__(self, db_pool: asyncpg.Pool, cache: redis.Redis, bot: Bot, performance_tracker=None):
        self.db = db_pool
        self.cache = cache
        self.bot = bot
        self.vip_channel = Config.CHANNEL_VIP
        self.performance_tracker = performance_tracker

    async def _execute_update_position(self, wallet: str, token: str, tx_type: str,
                                        token_amount: float, sol_amount: float,
                                        market_cap: float = 0):
        """Internal method for actual DB execution"""
        if tx_type == "buy":
            # Calculate weighted average entry MC
            # Formula: ((existing_bought * existing_avg_mc) + (new_amount * current_mc)) / total_bought
            await self.db.execute(
                """INSERT INTO wallet_positions (
                    wallet_address, token_address, total_bought, net_position,
                    total_sol_invested, last_buy_time, avg_entry_mc
                ) VALUES ($1, $2, $3::numeric, $3::numeric, $4::numeric, NOW(), $5::numeric)
                ON CONFLICT (wallet_address, token_address) DO UPDATE SET
                total_bought = wallet_positions.total_bought + $3::numeric,
                net_position = wallet_positions.net_position + $3::numeric,
                total_sol_invested = wallet_positions.total_sol_invested + $4::numeric,
                last_buy_time = NOW(),
                is_active = TRUE,
                avg_entry_mc = CASE 
                    WHEN wallet_positions.avg_entry_mc IS NULL OR wallet_positions.avg_entry_mc = 0 
                        OR wallet_positions.total_bought = 0 THEN $5::numeric
                    ELSE ((wallet_positions.avg_entry_mc * wallet_positions.total_bought) + ($5::numeric * $3::numeric)) 
                        / (wallet_positions.total_bought + $3::numeric)
                END""",
                wallet, token, token_amount, sol_amount, market_cap
            )
        else:
            await self.db.execute(
                """UPDATE wallet_positions
                SET total_sold = COALESCE(total_sold, 0) + $3::numeric,
                    net_position = GREATEST(0, net_position - $3::numeric),
                    is_active = (net_position - $3::numeric) > 0.0001,
                    total_sol_returned = COALESCE(total_sol_returned, 0) + $4::numeric
                WHERE wallet_address = $1 AND token_address = $2""",
                wallet, token, token_amount, sol_amount
            )

    async def update_position(self, wallet: str, token: str, tx_type: str,
                             token_amount: float, sol_amount: float = 0,
                             market_cap: float = 0):
        """Update position with retry logic"""
        try:
            await with_db_retry(
                self._execute_update_position,
                wallet, token, tx_type, token_amount, sol_amount, market_cap
            )
        except Exception as e:
            logger.error(f"Failed to update position after retries: {e}")
            raise

    async def _execute_check_cluster(self, token: str) -> List[asyncpg.Record]:
        """Internal method for fetching cluster data"""
        return await self.db.fetch(
            """SELECT wallet_address, first_buy_time, net_position,
                total_bought, total_sold, total_sol_invested, is_active,
                avg_entry_mc,
                CASE WHEN total_bought > 0
                    THEN ROUND((net_position / total_bought * 100)::numeric, 1)
                    ELSE 0
                END as hold_percentage
            FROM wallet_positions
            WHERE token_address = $1
            AND (COALESCE(total_bought, 0) > 0 OR COALESCE(total_sold, 0) > 0)
            ORDER BY first_buy_time ASC""", token
        )

    async def check_cluster(self, token: str, new_wallet: str, tx_type: str,
                           wallet_labels: Dict[str, str] = None) -> bool:
        """Check cluster with retry logic"""
        try:
            rows = await with_db_retry(self._execute_check_cluster, token)

            if len(rows) < Config.CLUSTER_THRESHOLD:
                return False

            await self.send_cluster_alert(token, rows, wallet_labels, tx_type, new_wallet)
            return True

        except Exception as e:
            logger.error(f"Cluster check failed: {e}")
            return False

    async def send_cluster_alert(self, token: str, wallets: List[asyncpg.Record],
                                 wallet_labels: Dict[str, str] = None,
                                 trigger_tx_type: str = "buy",
                                 trigger_wallet: str = ""):
        if not self.vip_channel:
            return

        # FIX: Throttle cluster alerts - only alert same token once every 5 seconds
        # Use SET NX for atomic check-and-set (prevents race condition)
        throttle_key = f"cluster_throttle:{token}"
        try:
            throttle_set = await self.cache.set(throttle_key, "1", nx=True, ex=5)
            if not throttle_set:
                # Key already exists = within throttle window
                logger.debug(f"Cluster alert throttled for {token[:16]}... (within 5s window)")
                return
        except Exception as e:
            # FIX: Fail open - if Redis fails, allow the alert rather than miss it
            logger.warning(f"Redis throttle failed for {token[:16]}..., allowing alert: {e}")

        wallet_labels = wallet_labels or {}

        try:
            # Fetch fresh token info for cluster alert
            info = await self.get_token_info(token, use_cache=False)
            wallet_lines = []

            holding_count = 0
            sold_count = 0
            total_sol_invested = 0

            for row in wallets:
                wallet = row['wallet_address']
                label = wallet_labels.get(wallet, wallet[:8] + "...")

                net_position = float(row['net_position'] or 0)
                sol_invested = float(row['total_sol_invested'] or 0)
                is_active = row.get('is_active', False)
                hold_percentage = row.get('hold_percentage', 0)
                avg_entry_mc = float(row.get('avg_entry_mc') or 0)

                total_sol_invested += sol_invested

                if net_position > 0.001 and is_active:
                    status = "💎 HOLDING"
                    holding_count += 1
                else:
                    status = "💨 SOLD OUT"
                    sold_count += 1

                first_buy = row['first_buy_time']
                
                # Handle timezone-aware vs timezone-naive datetime comparison
                time_str = "unknown"
                if first_buy:
                    # Get current time with same timezone awareness as first_buy
                    if hasattr(first_buy, 'tzinfo') and first_buy.tzinfo is not None:
                        now = datetime.now(timezone.utc)
                    else:
                        now = datetime.utcnow()
                    
                    # Convert first_buy to naive if it's aware (for comparison)
                    if hasattr(first_buy, 'tzinfo') and first_buy.tzinfo is not None:
                        first_buy = first_buy.replace(tzinfo=None)
                    
                    # Now both now and first_buy are timezone-naive
                    if isinstance(first_buy, datetime):
                        time_diff = now - first_buy
                        if time_diff.days > 0:
                            time_str = f"{time_diff.days}d"
                        elif time_diff.seconds > 3600:
                            time_str = f"{time_diff.seconds // 3600}h"
                        else:
                            time_str = f"{time_diff.seconds // 60}m"

                sol_str = f"{sol_invested:.2f} SOL" if sol_invested > 0 else "N/A"

                hold_str = f"({hold_percentage}% held)" if net_position > 0.001 else ""
                
                # Format avg entry MC
                if avg_entry_mc >= 1_000_000:
                    entry_mc_str = f"📍${avg_entry_mc/1_000_000:.1f}M"
                elif avg_entry_mc > 0:
                    entry_mc_str = f"📍${avg_entry_mc/1000:.0f}K"
                else:
                    entry_mc_str = ""
                
                # Get performance data for this wallet
                perf_emoji = "🔍"
                if self.performance_tracker:
                    try:
                        perf = await self.performance_tracker.get_wallet_performance_fast(wallet)
                        if perf:
                            perf_emoji = perf['confidence_emoji']
                    except Exception:
                        pass

                wallet_lines.append(
                    f"{perf_emoji} *{label}* | {status} {hold_str}\n"
                    f"  💰 {sol_str} | ⏱ {time_str} {entry_mc_str}"
                )

            if info['market_cap'] >= 1_000_000:
                mc_str = f"${info['market_cap']/1_000_000:.2f}M"
            elif info['market_cap'] > 0:
                mc_str = f"${info['market_cap']/1000:.1f}K"
            else:
                mc_str = "Unknown"

            trigger_emoji = "🟢" if trigger_tx_type == "buy" else "🔴"
            trigger_label = wallet_labels.get(trigger_wallet, trigger_wallet[:8] + "...")

            message = f"""🚨 *WALLET CLUSTER UPDATE* 🚨

*{info['ticker']}* ({info['name']})
`{token}`
💰 *Market Cap:* `{mc_str}`
📈 *Price:* `${info['price']:.8f}`
💵 *Total SOL in Cluster:* `{total_sol_invested:.2f} SOL`

{trigger_emoji} *Triggered by:* {trigger_label} ({trigger_tx_type.upper()})

👥 *{len(wallets)} Total Wallets | 💎 {holding_count} Holding | 💨 {sold_count} Sold*

{chr(10).join(wallet_lines)}

🏆 Elite (80-100) | ✅ Strong (60-79) | ⚠️ Moderate (40-59) | 🔴 Weak (20-39) | 💀 Poor (0-19) | 🔍 New (<3 trades)

[📊 DexScreener]({info['dexscreener']}) | [⚡ Photon]({info.get('photon', f'https://photon-sol.tinyastro.io/en/lp/{token}')})"""

            await self.bot.send_message(
                chat_id=self.vip_channel,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )

            logger.info(f"VIP alert sent: {info['ticker']} | {len(wallets)} wallets")

        except Exception as e:
            logger.error(f"VIP alert failed: {e}")

    async def get_token_info(self, token: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get token info. If use_cache=False, fetches fresh data from DexScreener."""
        cache_key = f"token_info:{token}"

        # Check cache first (if allowed)
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return json.loads(cached)

        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get('pairs') or []

                        if pairs:
                            solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                            if solana_pairs:
                                pairs = solana_pairs

                            best = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))

                            result = {
                                'ticker': best.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                                'name': best.get('baseToken', {}).get('name', 'Unknown'),
                                'market_cap': float(best.get('marketCap', 0) or 0),
                                'price': float(best.get('priceUsd', 0) or 0),
                                'dexscreener': f"https://dexscreener.com/solana/{token}",
                                'photon': f"https://photon-sol.tinyastro.io/en/lp/{token}",
                                'source': 'dexscreener'
                            }

                            # Cache result
                            await self.cache.setex(cache_key, Config.TOKEN_INFO_TTL, json.dumps(result))
                            return result

            # Fallback
            result = {
                'ticker': 'NEW',
                'name': 'New Token',
                'market_cap': 0,
                'price': 0,
                'dexscreener': f"https://dexscreener.com/solana/{token}",
                'photon': f"https://photon-sol.tinyastro.io/en/lp/{token}",
                'source': 'none'
            }
            await self.cache.setex(cache_key, Config.TOKEN_INFO_TTL, json.dumps(result))
            return result

        except Exception as e:
            logger.warning(f"Token info fetch failed: {e}")
            # Try to return cached data as fallback even if use_cache=False
            if not use_cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    return json.loads(cached)
            return {
                'ticker': 'ERROR',
                'name': 'Fetch Error',
                'market_cap': 0,
                'price': 0,
                'dexscreener': f"https://dexscreener.com/solana/{token}",
                'photon': f"https://photon-sol.tinyastro.io/en/lp/{token}",
                'source': 'error'
            }


class WalletPerformance:
    """Tracks wallet performance metrics (PnL, winrate, ROI) from position data"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def record_trade(self, wallet: str, token: str, tx_type: str, 
                          sol_amount: float, token_amount: float):
        """Record a trade and update performance metrics"""
        try:
            if tx_type == "buy":
                # Record buy - just increment trade count and investment
                await with_db_retry(
                    self._execute_buy_record,
                    wallet, sol_amount, token_amount
                )
            else:
                # Record sell - calculate PnL for this trade
                await with_db_retry(
                    self._execute_sell_record,
                    wallet, token, sol_amount, token_amount
                )
        except Exception as e:
            logger.error(f"Failed to record trade for {wallet}: {e}")
    
    async def _execute_buy_record(self, wallet: str, sol_amount: float, token_amount: float):
        """Record buy trade"""
        await self.db.execute(
            """INSERT INTO wallet_performance (
                wallet_address, total_trades, total_sol_invested, 
                created_at, updated_at
            ) VALUES ($1, 1, $2, NOW(), NOW())
            ON CONFLICT (wallet_address) DO UPDATE SET
            total_trades = wallet_performance.total_trades + 1,
            total_sol_invested = wallet_performance.total_sol_invested + $2,
            updated_at = NOW()""",
            wallet, sol_amount
        )
    
    async def _execute_sell_record(self, wallet: str, token: str, 
                                   sol_received: float, token_amount: float):
        """Record sell trade and calculate PnL and hold time"""
        # Get the position data to calculate cost basis and hold time
        row = await self.db.fetchrow(
            """SELECT total_bought, total_sold, total_sol_invested, net_position, first_buy_time
            FROM wallet_positions 
            WHERE wallet_address = $1 AND token_address = $2""",
            wallet, token
        )
        
        if not row:
            return
        
        total_bought = float(row['total_bought'] or 0)
        total_sol_invested = float(row['total_sol_invested'] or 0)
        first_buy_time = row.get('first_buy_time')
        
        # Calculate average cost per token
        if total_bought > 0:
            avg_cost_per_token = total_sol_invested / total_bought
            cost_basis = token_amount * avg_cost_per_token
            trade_pnl = sol_received - cost_basis
            is_win = trade_pnl > 0
        else:
            trade_pnl = 0
            is_win = False
            cost_basis = 0
        
        # Calculate hold time in seconds
        hold_time_seconds = 0
        if first_buy_time:
            # Handle timezone-aware vs timezone-naive comparison
            if first_buy_time.tzinfo:
                now = datetime.now(timezone.utc)
            else:
                now = datetime.utcnow()
            hold_time_seconds = (now - first_buy_time).total_seconds()
        
        # Update performance stats with hold time
        await self.db.execute(
            """INSERT INTO wallet_performance (
                wallet_address, total_trades, total_sol_returned,
                realized_pnl, winning_trades, losing_trades,
                total_hold_time_seconds, created_at, updated_at
            ) VALUES ($1, 1, $2, $3, $4, $5, $6, NOW(), NOW())
            ON CONFLICT (wallet_address) DO UPDATE SET
            total_trades = wallet_performance.total_trades + 1,
            total_sol_returned = wallet_performance.total_sol_returned + $2,
            realized_pnl = wallet_performance.realized_pnl + $3,
            winning_trades = wallet_performance.winning_trades + $4,
            losing_trades = wallet_performance.losing_trades + $5,
            total_hold_time_seconds = COALESCE(wallet_performance.total_hold_time_seconds, 0) + $6,
            updated_at = NOW()""",
            wallet, sol_received, trade_pnl, 1 if is_win else 0, 0 if is_win else 1, 
            hold_time_seconds
        )
    
    async def get_performance(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a wallet"""
        try:
            row = await with_db_retry(self._fetch_performance, wallet)
            if not row:
                return None
            
            total_trades = row['total_trades'] or 0
            winning_trades = row['winning_trades'] or 0
            losing_trades = row['losing_trades'] or 0
            realized_pnl = float(row['realized_pnl'] or 0)
            total_invested = float(row['total_sol_invested'] or 0)
            total_returned = float(row['total_sol_returned'] or 0)
            
            # Calculate derived metrics
            winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_roi = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
            
            return {
                'wallet': wallet,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'winrate': winrate,
                'realized_pnl': realized_pnl,
                'total_invested': total_invested,
                'total_returned': total_returned,
                'avg_roi': avg_roi,
                'updated_at': row['updated_at']
            }
        except Exception as e:
            logger.error(f"Failed to get performance for {wallet}: {e}")
            return None
    
    async def _fetch_performance(self, wallet: str):
        return await self.db.fetchrow(
            """SELECT * FROM wallet_performance 
            WHERE wallet_address = $1""",
            wallet
        )
    
    async def get_all_performance(self) -> List[Dict[str, Any]]:
        """Get performance for all wallets sorted by PnL"""
        try:
            rows = await with_db_retry(self._fetch_all_performance)
            results = []
            for row in rows:
                total_trades = row['total_trades'] or 0
                winning_trades = row['winning_trades'] or 0
                realized_pnl = float(row['realized_pnl'] or 0)
                total_invested = float(row['total_sol_invested'] or 0)
                
                winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                avg_roi = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
                
                results.append({
                    'wallet': row['wallet_address'],
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': row['losing_trades'] or 0,
                    'winrate': winrate,
                    'realized_pnl': realized_pnl,
                    'avg_roi': avg_roi,
                    'updated_at': row['updated_at']
                })
            return results
        except Exception as e:
            logger.error(f"Failed to get all performance: {e}")
            return []
    
    async def _fetch_all_performance(self):
        return await self.db.fetch(
            """SELECT * FROM wallet_performance 
            ORDER BY realized_pnl DESC"""
        )

    async def get_wallet_performance_fast(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get performance data for a single wallet (cached in memory for alerts)"""
        try:
            row = await with_db_retry(self._fetch_performance, wallet)
            if not row:
                return None
            
            total_trades = row['total_trades'] or 0
            winning_trades = row['winning_trades'] or 0
            realized_pnl = float(row['realized_pnl'] or 0)
            total_invested = float(row['total_sol_invested'] or 0)
            
            winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_roi = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
            
            # Calculate confidence score (0-100)
            # 50% winrate, 50% ROI (capped at 100% for normalization)
            roi_component = min(abs(avg_roi), 100)  # Cap ROI at 100% for scoring
            winrate_component = winrate
            
            # Weight: winrate 60%, ROI 40%
            confidence_score = (winrate_component * 0.6) + (roi_component * 0.4)
            
            # Get confidence emoji
            emoji = self._get_confidence_emoji(confidence_score, total_trades)
            
            return {
                'wallet': wallet,
                'total_trades': total_trades,
                'winrate': winrate,
                'avg_roi': avg_roi,
                'realized_pnl': realized_pnl,
                'confidence_score': confidence_score,
                'confidence_emoji': emoji
            }
        except Exception as e:
            logger.error(f"Failed to get performance for {wallet}: {e}")
            return None
    
    def _get_confidence_emoji(self, score: float, trades: int) -> str:
        """Get confidence emoji based on score and trade count"""
        if trades < 3:
            return "🔍"  # Too few trades to judge
        elif score >= 80:
            return "🏆"  # Elite
        elif score >= 60:
            return "✅"  # Strong
        elif score >= 40:
            return "⚠️"  # Moderate
        elif score >= 20:
            return "🔴"  # Weak
        else:
            return "💀"  # Poor

    def _format_hold_time(self, seconds: float) -> str:
        """Format hold time in human-readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}h"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            return f"{days}d {hours}h"

    async def get_performance_timeframe(self, days: int) -> List[Dict[str, Any]]:
        """Get performance data for wallets active within the last N days"""
        try:
            # Use proper asyncpg parameter format and cast to interval
            rows = await self.db.fetch(
                """SELECT DISTINCT ON (wp.wallet_address)
                    wp.wallet_address,
                    wp.total_trades,
                    wp.winning_trades,
                    wp.losing_trades,
                    wp.realized_pnl,
                    wp.total_sol_invested,
                    wp.updated_at,
                    wp.total_hold_time_seconds
                FROM wallet_performance wp
                JOIN wallet_positions wpos ON wp.wallet_address = wpos.wallet_address
                WHERE wpos.last_buy_time >= NOW() - ($1 || ' days')::interval
                   OR wp.updated_at >= NOW() - ($1 || ' days')::interval
                ORDER BY wp.wallet_address, wp.updated_at DESC""",
                str(days)
            )
            
            results = []
            for row in rows:
                total_trades = row['total_trades'] or 0
                winning_trades = row['winning_trades'] or 0
                realized_pnl = float(row['realized_pnl'] or 0)
                total_invested = float(row['total_sol_invested'] or 0)
                total_hold_time = float(row.get('total_hold_time_seconds') or 0)
                sell_count = winning_trades + (row['losing_trades'] or 0)
                
                winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                avg_roi = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
                avg_hold_time = (total_hold_time / sell_count) if sell_count > 0 else 0
                
                results.append({
                    'wallet': row['wallet_address'],
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': row['losing_trades'] or 0,
                    'winrate': winrate,
                    'realized_pnl': realized_pnl,
                    'avg_roi': avg_roi,
                    'avg_hold_time_seconds': avg_hold_time,
                    'updated_at': row['updated_at']
                })
            
            return results
        except Exception as e:
            logger.error(f"Failed to get performance for last {days} days: {e}")
            return []

    async def get_token_analysis(self, token: str, tracker_wallets: List[str]) -> Dict[str, Any]:
        """Analyze a token across tracked wallets with PnL data"""
        try:
            rows = await self.db.fetch(
                """SELECT 
                    wallet_address,
                    first_buy_time,
                    last_buy_time,
                    total_bought,
                    total_sold,
                    net_position,
                    total_sol_invested,
                    avg_entry_mc,
                    is_active,
                    total_sol_returned
                FROM wallet_positions
                WHERE token_address = $1 
                  AND wallet_address = ANY($2)
                ORDER BY first_buy_time ASC""",
                token, tracker_wallets
            )
            
            wallet_data = []
            total_invested = 0
            total_bought = 0
            total_sold = 0
            total_returned = 0
            active_positions = 0
            total_realized_pnl = 0
            
            now = datetime.now(timezone.utc)
            
            for row in rows:
                wallet = row['wallet_address']
                first_buy = row['first_buy_time']
                net_position = float(row['net_position'] or 0)
                sol_invested = float(row['total_sol_invested'] or 0)
                avg_entry_mc = float(row['avg_entry_mc'] or 0)
                is_active = row['is_active']
                total_sold_amount = float(row['total_sold'] or 0)
                sol_returned = float(row['total_sol_returned'] or 0)
                total_bought_amount = float(row['total_bought'] or 0)
                
                total_invested += sol_invested
                total_bought += total_bought_amount
                total_sold += total_sold_amount
                total_returned += sol_returned
                
                if is_active and net_position > 0:
                    active_positions += 1
                
                # Calculate PnL
                realized_pnl = 0
                unrealized_pnl = 0
                roi_percent = 0
                
                if total_sold_amount > 0:
                    # Calculate realized PnL from sells
                    # Cost basis of sold tokens
                    if total_bought_amount > 0:
                        avg_cost_per_token = sol_invested / total_bought_amount
                        cost_basis_sold = total_sold_amount * avg_cost_per_token
                        realized_pnl = sol_returned - cost_basis_sold
                        total_realized_pnl += realized_pnl
                        
                        # Debug logging for PnL calculation issues
                        if abs(realized_pnl) > 100:  # Suspiciously large PnL
                            logger.warning(
                                f"PnL Debug for {wallet[:8]} on token {token[:8]}: "
                                f"sol_invested={sol_invested:.4f}, total_bought={total_bought_amount:.4f}, "
                                f"total_sold={total_sold_amount:.4f}, sol_returned={sol_returned:.4f}, "
                                f"avg_cost={avg_cost_per_token:.6f}, cost_basis_sold={cost_basis_sold:.4f}, "
                                f"realized_pnl={realized_pnl:.4f}"
                            )
                
                # Calculate time since first buy
                time_held_str = "Unknown"
                if first_buy:
                    # Handle timezone-aware vs timezone-naive comparison
                    if first_buy.tzinfo:
                        # first_buy is timezone-aware, use timezone-aware now
                        now = datetime.now(timezone.utc)
                    else:
                        # first_buy is timezone-naive, use timezone-naive now
                        now = datetime.utcnow()
                    
                    time_diff = now - first_buy
                    if time_diff.days > 0:
                        time_held_str = f"{time_diff.days}d {time_diff.seconds // 3600}h"
                    elif time_diff.seconds > 3600:
                        time_held_str = f"{time_diff.seconds // 3600}h"
                    else:
                        time_held_str = f"{time_diff.seconds // 60}m"
                
                # Calculate ROI
                if total_sold_amount > 0 and total_bought_amount > 0:
                    # Calculate cost basis of sold tokens
                    avg_cost_per_token = sol_invested / total_bought_amount
                    cost_basis_sold = total_sold_amount * avg_cost_per_token
                    
                    # ROI is based on the cost basis of what was sold
                    if cost_basis_sold > 0:
                        roi_percent = (realized_pnl / cost_basis_sold) * 100
                
                wallet_data.append({
                    'wallet': wallet,
                    'first_buy': first_buy,
                    'time_held_str': time_held_str,
                    'net_position': net_position,
                    'sol_invested': sol_invested,
                    'sol_returned': sol_returned,
                    'avg_entry_mc': avg_entry_mc,
                    'is_active': is_active,
                    'realized_pnl': realized_pnl,
                    'roi_percent': roi_percent,
                    'total_sold': total_sold_amount,
                    'total_bought': total_bought_amount
                })
            
            return {
                'token': token,
                'wallet_count': len(wallet_data),
                'active_positions': active_positions,
                'total_sol_invested': total_invested,
                'total_sol_returned': total_returned,
                'total_realized_pnl': total_realized_pnl,
                'total_bought': total_bought,
                'total_sold': total_sold,
                'wallets': wallet_data
            }
        except Exception as e:
            logger.error(f"Failed to analyze token {token}: {e}")
            return {'token': token, 'wallet_count': 0, 'wallets': []}

    async def cleanup_removed_wallets(self, active_wallets: List[str]):
        """Delete performance data for wallets not in active_wallets list"""
        try:
            # Get all wallets with performance data
            rows = await self.db.fetch(
                "SELECT wallet_address FROM wallet_performance"
            )
            
            active_set = set(active_wallets)
            removed = []
            
            for row in rows:
                wallet = row['wallet_address']
                if wallet not in active_set:
                    removed.append(wallet)
            
            if removed:
                # Delete performance data for removed wallets
                await self.db.execute(
                    "DELETE FROM wallet_performance WHERE wallet_address = ANY($1)",
                    removed
                )
                logger.info(f"Cleaned up performance data for {len(removed)} removed wallet(s): {', '.join(w[:8] + '...' for w in removed)}")
            
            return len(removed)
        except Exception as e:
            logger.error(f"Failed to cleanup removed wallets: {e}")
            return 0

    async def get_wallet_performance_detailed(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get detailed performance data for a single wallet"""
        try:
            row = await with_db_retry(self._fetch_performance, wallet)
            if not row:
                return None
            
            total_trades = row['total_trades'] or 0
            winning_trades = row['winning_trades'] or 0
            losing_trades = row['losing_trades'] or 0
            realized_pnl = float(row['realized_pnl'] or 0)
            total_invested = float(row['total_sol_invested'] or 0)
            total_returned = float(row['total_sol_returned'] or 0)
            total_hold_time = float(row.get('total_hold_time_seconds') or 0)
            
            winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_roi = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
            
            # Calculate average hold time (only for sells which have hold time recorded)
            sell_count = row.get('sell_count') or losing_trades + winning_trades
            avg_hold_time_seconds = (total_hold_time / sell_count) if sell_count > 0 else 0
            
            # Calculate confidence score
            roi_component = min(abs(avg_roi), 100)
            winrate_component = winrate
            confidence_score = (winrate_component * 0.6) + (roi_component * 0.4)
            
            emoji = self._get_confidence_emoji(confidence_score, total_trades)
            
            return {
                'wallet': wallet,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'winrate': winrate,
                'realized_pnl': realized_pnl,
                'total_invested': total_invested,
                'total_returned': total_returned,
                'avg_roi': avg_roi,
                'total_hold_time_seconds': total_hold_time,
                'avg_hold_time_seconds': avg_hold_time_seconds,
                'confidence_score': confidence_score,
                'confidence_emoji': emoji,
                'updated_at': row['updated_at']
            }
        except Exception as e:
            logger.error(f"Failed to get detailed performance for {wallet}: {e}")
            return None

    async def get_recent_trades(self, wallet: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent trades for a wallet with PnL data per token"""
        try:
            # Get positions with recent activity (has buy or sell data)
            rows = await self.db.fetch(
                """SELECT 
                    token_address,
                    first_buy_time,
                    last_buy_time,
                    total_bought,
                    total_sold,
                    net_position,
                    total_sol_invested,
                    avg_entry_mc,
                    is_active,
                    total_sol_returned
                FROM wallet_positions
                WHERE wallet_address = $1
                  AND (total_bought > 0 OR total_sold > 0)
                ORDER BY last_buy_time DESC NULLS LAST
                LIMIT $2""",
                wallet, limit
            )
            
            results = []
            for row in rows:
                token = row['token_address']
                first_buy = row['first_buy_time']
                last_buy = row['last_buy_time']
                total_bought = float(row['total_bought'] or 0)
                total_sold = float(row['total_sold'] or 0)
                net_position = float(row['net_position'] or 0)
                sol_invested = float(row['total_sol_invested'] or 0)
                avg_entry_mc = float(row['avg_entry_mc'] or 0)
                is_active = row['is_active']
                sol_returned = float(row['total_sol_returned'] or 0)
                
                # Determine status
                if total_sold == 0:
                    status = "🟢 HOLDING"
                    status_detail = "No sells yet"
                elif net_position <= 0.000001:
                    status = "🔴 SOLD"
                    status_detail = "Fully exited"
                else:
                    pct_sold = (total_sold / total_bought * 100) if total_bought > 0 else 0
                    status = "🟡 PARTIAL"
                    status_detail = f"{pct_sold:.1f}% sold"
                
                # Calculate PnL
                realized_pnl = 0
                roi = 0
                if total_sold > 0 and sol_invested > 0:
                    # Average cost per token
                    avg_cost = sol_invested / total_bought if total_bought > 0 else 0
                    # Cost of sold tokens
                    cost_of_sold = total_sold * avg_cost
                    # Realized PnL = SOL returned - cost of sold tokens
                    realized_pnl = sol_returned - cost_of_sold
                    # ROI based on cost of sold tokens
                    roi = (realized_pnl / cost_of_sold * 100) if cost_of_sold > 0 else 0
                
                # Calculate hold time
                hold_time_str = "Unknown"
                if first_buy and last_buy:
                    try:
                        # Ensure both are datetime objects (not strings)
                        if isinstance(first_buy, str):
                            from datetime import datetime
                            first_buy_dt = datetime.fromisoformat(first_buy.replace('Z', '+00:00'))
                        else:
                            first_buy_dt = first_buy
                            
                        if isinstance(last_buy, str):
                            from datetime import datetime
                            last_buy_dt = datetime.fromisoformat(last_buy.replace('Z', '+00:00'))
                        else:
                            last_buy_dt = last_buy
                        
                        # Make both timezone-naive for comparison
                        if hasattr(first_buy_dt, 'tzinfo') and first_buy_dt.tzinfo is not None:
                            first_buy_dt = first_buy_dt.replace(tzinfo=None)
                        if hasattr(last_buy_dt, 'tzinfo') and last_buy_dt.tzinfo is not None:
                            last_buy_dt = last_buy_dt.replace(tzinfo=None)
                        
                        if last_buy_dt >= first_buy_dt:
                            diff = last_buy_dt - first_buy_dt
                            days = diff.days
                            hours = diff.seconds // 3600
                            if days > 0:
                                hold_time_str = f"{days}d {hours}h"
                            else:
                                hold_time_str = f"{hours}h"
                    except Exception as e:
                        logger.debug(f"Hold time calculation error: {e}")
                
                results.append({
                    'token': token,
                    'total_bought': total_bought,
                    'total_sold': total_sold,
                    'net_position': net_position,
                    'sol_invested': sol_invested,
                    'sol_returned': sol_returned,
                    'realized_pnl': realized_pnl,
                    'roi': roi,
                    'avg_entry_mc': avg_entry_mc,
                    'status': status,
                    'status_detail': status_detail,
                    'hold_time': hold_time_str,
                    'first_buy': first_buy,
                    'last_buy': last_buy,
                    'is_active': is_active
                })
            
            return results
        except Exception as e:
            logger.error(f"Failed to get recent trades for {wallet}: {e}")
            return []


class SpeedTracker:
    def __init__(self):
        self.db = None
        self.cache = None
        self.bot = None
        self.session = None
        self.cluster_detector = None
        self.performance_tracker = None
        self.wallets = []
        self._wallet_labels = {}  # Pre-built mapping for performance
        self.rpc_urls = Config.RPC_URLS
        self.rpc_index = 0
        self._shutdown_event = asyncio.Event()
        self.db_semaphore = asyncio.Semaphore(10)  # Increased for better throughput
        self.wallet_check_semaphore = asyncio.Semaphore(20)  # Match RPC semaphore for parallel checks
        # FIX: RPC rate limiting to prevent hitting rate limits
        self.rpc_semaphore = asyncio.Semaphore(20)  # Max 20 concurrent RPC calls
        # FIX: Allow 5 min of recent history on startup (was int(time.time()))
        self.script_start_time = int(time.time()) - 300
        # FIX: Simple RPC routing (Helius for speed, no credit limits)
        self._setup_rpc_routing()
        self.exchange_wallets = self._load_exchange_wallets()
        self.lp_programs = self._load_lp_programs()

    def _setup_rpc_routing(self):
        """Setup RPC URLs - Public RPCs primary, Helius fallback"""
        # Standard Solana RPC endpoints (PRIMARY - free)
        # Added more public RPCs to reduce rate limiting with 51 wallets
        self.public_rpcs = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-rpc.publicnode.com", 
            "https://solana-api.instantnodes.io",
            "https://rpc.ankr.com/solana",
            "https://solana-mainnet.rpc.extrnode.com",
            "https://solana.public-rpc.com",
        ]
        
        # Helius enhanced endpoints (FALLBACK - preserve credits)
        self.helius_rpc = os.getenv('HELIUS_RPC_URL', '')
        
        # Health tracking
        self.rate_limited_until = {}
        self.current_rpc = None  # Track which RPC is being used
        self.helius_usage_count = 0  # Track Helius fallback usage
        self.public_usage_count = 0   # Track public RPC usage
        
        # OPTIMIZATION: Adaptive check intervals per wallet
        self.wallet_check_interval = {}  # wallet -> current interval in seconds
        self.wallet_last_activity = {}   # wallet -> timestamp of last transaction
        
        logger.info(f"RPC: Public primary ({len(self.public_rpcs)}), Helius fallback={'✓' if self.helius_rpc else '✗'}")

    def get_rpc(self, force_public: bool = False) -> str:
        """
        Get RPC URL - Public RPCs primary, Helius fallback.
        Uses public RPCs to preserve Helius credits.
        """
        now = time.time()
        
        # Try public RPCs first (FREE)
        for i in range(len(self.public_rpcs)):
            idx = (self.rpc_index + i) % len(self.public_rpcs)
            rpc = self.public_rpcs[idx]
            if rpc not in self.rate_limited_until or now > self.rate_limited_until[rpc]:
                self.rpc_index = (idx + 1) % len(self.public_rpcs)
                self.current_rpc = rpc
                self.public_usage_count += 1
                return rpc
        
        # All public RPCs rate limited - fallback to Helius
        if self.helius_rpc:
            helius_limited = self.helius_rpc in self.rate_limited_until and now < self.rate_limited_until[self.helius_rpc]
            if not helius_limited:
                # Log Helius usage periodically (every 100 calls)
                self.helius_usage_count += 1
                if self.helius_usage_count % 100 == 0:
                    public_pct = (self.public_usage_count / (self.public_usage_count + self.helius_usage_count)) * 100
                    logger.warning(f"Helius fallback #{self.helius_usage_count} | Public: {public_pct:.1f}% | Helius: {100-public_pct:.1f}%")
                else:
                    logger.debug(f"All public RPCs rate limited, using Helius fallback #{self.helius_usage_count}")
                self.current_rpc = self.helius_rpc
                return self.helius_rpc
        
        # Everything rate limited - return first public anyway and hope for best
        self.current_rpc = self.public_rpcs[0]
        self.public_usage_count += 1
        return self.public_rpcs[0]
    
    def _get_rpc_excluding(self, excluded_rpcs: set) -> str:
        """Get RPC URL, excluding ones that have already been tried for this wallet check"""
        now = time.time()
        
        # Try public RPCs first, excluding already tried ones
        for i in range(len(self.public_rpcs)):
            idx = (self.rpc_index + i) % len(self.public_rpcs)
            rpc = self.public_rpcs[idx]
            if rpc in excluded_rpcs:
                continue
            if rpc not in self.rate_limited_until or now > self.rate_limited_until[rpc]:
                self.rpc_index = (idx + 1) % len(self.public_rpcs)
                self.current_rpc = rpc
                self.public_usage_count += 1
                return rpc
        
        # All public RPCs excluded or rate limited - fallback to Helius
        if self.helius_rpc and self.helius_rpc not in excluded_rpcs:
            helius_limited = self.helius_rpc in self.rate_limited_until and now < self.rate_limited_until[self.helius_rpc]
            if not helius_limited:
                self.helius_usage_count += 1
                if self.helius_usage_count % 100 == 0:
                    public_pct = (self.public_usage_count / (self.public_usage_count + self.helius_usage_count)) * 100
                    logger.warning(f"Helius fallback #{self.helius_usage_count} | Public: {public_pct:.1f}% | Helius: {100-public_pct:.1f}%")
                else:
                    logger.debug(f"All public RPCs exhausted for this check, using Helius fallback #{self.helius_usage_count}")
                self.current_rpc = self.helius_rpc
                return self.helius_rpc
        
        # Everything excluded or rate limited - return least recently used
        for rpc in self.public_rpcs:
            if rpc not in excluded_rpcs:
                self.current_rpc = rpc
                self.public_usage_count += 1
                return rpc
        
        # All excluded - just return first public anyway
        self.current_rpc = self.public_rpcs[0]
        self.public_usage_count += 1
        return self.public_rpcs[0]
    
    def get_adaptive_interval(self, wallet: str) -> int:
        """Get check interval based on wallet activity - VERY conservative for public RPCs"""
        now = time.time()
        last_activity = self.wallet_last_activity.get(wallet, 0)
        hours_inactive = (now - last_activity) / 3600
        
        # VERY conservative intervals to prevent RPC rate limiting with 52 wallets
        if hours_inactive >= 24:
            return 120  # 120s (2 min) for 24h+ inactive
        elif hours_inactive >= 12:
            return 90   # 90s for 12h+ inactive
        elif hours_inactive >= 6:
            return 60   # 60s for 6h+ inactive
        elif hours_inactive >= 1:
            return 30   # 30s for 1h+ inactive
        else:
            return 15   # 15s only for recently active (<1h)
    
    def report_rpc_failure(self, rpc: str, error_type: str):
        """Report RPC failure for health tracking - marks ALL failures for cooldown"""
        now = time.time()
        if error_type == 'rate_limit':
            # Rate limit: 10 minute cooldown
            self.rate_limited_until[rpc] = now + 600
            logger.warning(f"Rate limited on {rpc[:40]}... cooling down for 10 min")
        elif error_type == 'timeout':
            # Timeout: 2 minute cooldown
            self.rate_limited_until[rpc] = now + 120
            logger.debug(f"Timeout on {rpc[:40]}... cooling down for 2 min")
        elif error_type == 'server_error':
            # 5xx errors: 1 minute cooldown
            self.rate_limited_until[rpc] = now + 60
            logger.debug(f"Server error on {rpc[:40]}... cooling down for 1 min")
        elif error_type == 'connection_error':
            # Connection errors: 30 second cooldown
            self.rate_limited_until[rpc] = now + 30
            logger.debug(f"Connection error on {rpc[:40]}... cooling down for 30s")

    def _load_exchange_wallets(self) -> set:
        """Load exchange wallet addresses from exchanges.txt"""
        exchanges = set()
        try:
            with open('exchanges.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        exchanges.add(line)
            logger.info(f"Loaded {len(exchanges)} exchange wallets")
        except FileNotFoundError:
            logger.warning("exchanges.txt not found, exchange filtering disabled")
        except Exception as e:
            logger.error(f"Error loading exchanges.txt: {e}")
        return exchanges

    def _load_lp_programs(self) -> set:
        """Load LP program addresses from lpools.txt"""
        lps = set()
        try:
            with open('lpools.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        lps.add(line)
            logger.info(f"Loaded {len(lps)} LP programs")
        except FileNotFoundError:
            logger.warning("lpools.txt not found, LP filtering disabled")
        except Exception as e:
            logger.error(f"Error loading lpools.txt: {e}")
        return lps

    def _is_lp_or_exchange(self, address: str) -> bool:
        """Check if an address is an LP program, exchange, or bonding curve"""
        if not address:
            return False
        
        # Known exchange/LP addresses
        if address in self.exchange_wallets or address in self.lp_programs:
            return True
        
        # Pump.fun bonding curve pattern
        # Bonding curves on Pump.fun start with specific patterns
        if address.startswith('7OjP') or address.startswith('39az'):
            return True
        
        return False

    def _signal_handler(self, signum: int, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()

    async def connect(self):
        logger.info("Connecting to database...")
        self.db = await asyncpg.create_pool(
            host=Config.DB_HOST, port=Config.DB_PORT, database=Config.DB_NAME,
            user=Config.DB_USER, password=Config.DB_PASSWORD,
            min_size=2, max_size=8, command_timeout=10  # Reduced max_size from 10
        )
        logger.info("Database connected")

        logger.info("Connecting to Redis...")
        self.cache = redis.Redis(
            host=Config.REDIS_HOST, port=Config.REDIS_PORT,
            decode_responses=True, max_connections=10
        )
        await self.cache.ping()
        logger.info("Redis connected")

        logger.info("Connecting to Telegram...")
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        me = await self.bot.get_me()
        logger.info(f"Bot connected: @{me.username}")

        self.session = self._create_session()

        # Initialize performance_tracker BEFORE cluster_detector (dependency order)
        self.performance_tracker = WalletPerformance(self.db)
        self.cluster_detector = ClusterDetector(self.db, self.cache, self.bot, self.performance_tracker)

        if Config.CHANNEL_PINGS:
            logger.info(f"Alerts channel: {Config.CHANNEL_PINGS}")
        if Config.CHANNEL_VIP:
            logger.info(f"VIP channel: {Config.CHANNEL_VIP}")

    async def close(self):
        if self.session:
            await self.session.close()
        if self.db:
            await self.db.close()
        if self.cache:
            await self.cache.aclose()
        logger.info("Connections closed")

    def _create_session(self) -> aiohttp.ClientSession:
        """Create aiohttp session with proper SSL context for Windows"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=20,
            ssl=ssl_context if ssl_context else None,
            enable_cleanup_closed=True,
            force_close=True
        )
        return aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=Config.RPC_TIMEOUT, connect=2),
            connector=connector
        )

    def get_rpc(self) -> str:
        url = self.rpc_urls[self.rpc_index % len(self.rpc_urls)]
        self.rpc_index += 1
        return url

    async def get_token_supply(self, token: str) -> Optional[int]:
        """Get total supply of a token via RPC"""
    async def get_token_supply_alchemy(self, token: str) -> Optional[float]:
        """Get total supply of a token via Alchemy API with proper decimals"""
        if not Config.ALCHEMY_RPC_URL:
            # Fallback to regular RPC
            return await self._get_token_supply_public(token)
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",
                "params": [token]
            }
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.post(Config.ALCHEMY_RPC_URL, json=payload) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if 'error' in data:
                        logger.warning(f"Alchemy supply error: {data['error']}")
                        return None
                    
                    value = data.get('result', {}).get('value', {})
                    amount = float(value.get('amount', 0))
                    decimals = int(value.get('decimals', 0))
                    
                    # Convert to actual token amount
                    return amount / (10 ** decimals) if decimals > 0 else amount
                    
        except Exception as e:
            logger.warning(f"Alchemy supply failed: {e}")
            return await self._get_token_supply_public(token)
    
    async def _get_token_supply_public(self, token: str) -> Optional[float]:
        """Fallback: Get supply via public RPC"""
        try:
            url = self.get_rpc()
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",
                "params": [token]
            }
            
            async with self.session.post(url, json=payload, timeout=5) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                value = data.get('result', {}).get('value', {})
                amount = float(value.get('amount', 0))
                decimals = int(value.get('decimals', 0))
                return amount / (10 ** decimals) if decimals > 0 else amount
        except Exception as e:
            logger.warning(f"Failed to get token supply: {e}")
            return None

    async def get_token_balance(self, wallet: str, token: str) -> Optional[float]:
        """Get token balance for a specific wallet via RPC with retries"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = self.get_rpc()
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet,
                        {"mint": token},
                        {"encoding": "jsonParsed"}
                    ]
                }
                
                async with self.session.post(url, json=payload, timeout=5) as resp:
                    if resp.status != 200:
                        logger.warning(f"RPC {url[:30]}... returned status {resp.status} for {wallet[:8]}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        return None
                    
                    data = await resp.json()
                    
                    if 'error' in data:
                        logger.warning(f"RPC error for {wallet[:8]}: {data['error']}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        return None
                    
                    accounts = data.get('result', {}).get('value', [])
                    total_balance = 0.0
                    
                    for acc in accounts:
                        try:
                            parsed = acc.get('account', {}).get('data', {}).get('parsed', {})
                            if isinstance(parsed, dict) and 'info' in parsed:
                                info = parsed['info']
                                token_amount = info.get('tokenAmount', {})
                                ui_amount = token_amount.get('uiAmount')
                                if ui_amount is not None:
                                    total_balance += float(ui_amount)
                        except (KeyError, TypeError, ValueError) as e:
                            logger.debug(f"Failed to parse account data for {wallet[:8]}: {e}")
                            continue
                    
                    return total_balance
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout checking balance for {wallet[:8]} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                return None
            except Exception as e:
                logger.warning(f"Failed to get token balance for {wallet[:8]}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                return None
        
        return None

    async def get_token_balance_alchemy(self, wallet: str, token: str) -> Optional[float]:
        """Get token balance using Alchemy API (for trackhold command only)"""
        if not Config.ALCHEMY_RPC_URL:
            logger.warning("Alchemy API key not configured, falling back to regular RPC")
            return await self.get_token_balance(wallet, token)
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet,
                    {"mint": token},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            # Use SSL context for Windows certificate support
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.post(Config.ALCHEMY_RPC_URL, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"Alchemy returned status {resp.status} for {wallet[:8]}")
                        return None
                    
                    data = await resp.json()
                    
                    if 'error' in data:
                        logger.warning(f"Alchemy error for {wallet[:8]}: {data['error']}")
                        return None
                    
                    accounts = data.get('result', {}).get('value', [])
                    total_balance = 0.0
                    
                    for acc in accounts:
                        try:
                            parsed = acc.get('account', {}).get('data', {}).get('parsed', {})
                            if isinstance(parsed, dict) and 'info' in parsed:
                                info = parsed['info']
                                token_amount = info.get('tokenAmount', {})
                                ui_amount = token_amount.get('uiAmount')
                                if ui_amount is not None:
                                    total_balance += float(ui_amount)
                        except (KeyError, TypeError, ValueError) as e:
                            logger.debug(f"Failed to parse account data for {wallet[:8]}: {e}")
                            continue
                    
                    return total_balance
                
        except asyncio.TimeoutError:
            logger.warning(f"Alchemy timeout for {wallet[:8]}")
            return None
        except Exception as e:
            logger.warning(f"Alchemy request failed for {wallet[:8]}: {e}")
            return None

    def load_wallets(self) -> List[Dict[str, str]]:
        wallets = []
        try:
            with open('wallets.txt', 'r') as f:
                for line in f:
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
            logger.error("wallets.txt not found!")

        logger.info(f"Loaded {len(wallets)} wallets")
        return wallets

    def reload_wallets(self) -> List[Dict[str, str]]:
        """Reload wallets from file and update internal state"""
        self.wallets = self.load_wallets()
        # Rebuild wallet labels mapping
        self._wallet_labels = {w['address']: w['label'] for w in self.wallets}
        return self.wallets

    def add_wallet(self, address: str, label: str = None) -> tuple[bool, str]:
        """Add a wallet to wallets.txt. Returns (success, message)"""
        # Validate Solana address
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
            return False, "Invalid Solana address format"
        
        # Check if wallet already exists
        for w in self.wallets:
            if w['address'] == address:
                return False, f"Wallet already exists: {w['label']}"
            if label and w['label'].lower() == label.lower():
                return False, f"Label '{label}' already used by another wallet"
        
        # Generate label if not provided
        if not label:
            label = f"Wallet {len(self.wallets) + 1}"
        
        # Append to file
        try:
            with open('wallets.txt', 'a') as f:
                f.write(f"\n{address}|{label}")
        except Exception as e:
            return False, f"Failed to write to wallets.txt: {e}"
        
        # Reload wallets
        self.reload_wallets()
        return True, f"Added wallet: {label} ({address[:8]}...)"

    def remove_wallet(self, query: str) -> tuple[bool, str]:
        """Remove a wallet by address or label. Returns (success, message)"""
        address_to_remove = None
        label_to_remove = None
        
        # Try to find by address (full or partial)
        for w in self.wallets:
            if w['address'].lower() == query.lower() or w['address'].lower().startswith(query.lower()):
                address_to_remove = w['address']
                label_to_remove = w['label']
                break
        
        # Try to find by label (case-insensitive)
        if not address_to_remove:
            for w in self.wallets:
                if w['label'].lower() == query.lower():
                    address_to_remove = w['address']
                    label_to_remove = w['label']
                    break
        
        if not address_to_remove:
            return False, f"Wallet not found: {query}"
        
        # Read current file
        try:
            with open('wallets.txt', 'r') as f:
                lines = f.readlines()
        except Exception as e:
            return False, f"Failed to read wallets.txt: {e}"
        
        # Filter out the wallet
        new_lines = []
        removed = False
        for line in lines:
            original_line = line.strip()
            if not original_line or original_line.startswith('#'):
                new_lines.append(line)
                continue
            
            # Check if this line contains the wallet to remove
            if '|' in original_line:
                line_address = original_line.split('|', 1)[0].strip()
            else:
                line_address = original_line.strip()
            
            if line_address == address_to_remove:
                removed = True
                continue  # Skip this line
            
            new_lines.append(line)
        
        if not removed:
            return False, f"Wallet found in memory but not in file: {query}"
        
        # Write back to file
        try:
            with open('wallets.txt', 'w') as f:
                f.writelines(new_lines)
        except Exception as e:
            return False, f"Failed to write to wallets.txt: {e}"
        
        # Reload wallets and cleanup performance data
        self.reload_wallets()
        
        # Also remove from database
        try:
            asyncio.create_task(self.performance_tracker.cleanup_removed_wallets([w['address'] for w in self.wallets]))
        except Exception:
            pass  # Don't fail if cleanup fails
        
        return True, f"Removed wallet: {label_to_remove} ({address_to_remove[:8]}...)"

    async def _fetch_hold_percentage(self, wallet: str, token: str) -> float:
        """Fetch hold percentage with retry logic"""
        try:
            async def _fetch():
                return await self.db.fetchrow(
                    """SELECT 
                        CASE WHEN total_bought > 0 
                            THEN ROUND((net_position / total_bought * 100)::numeric, 1)
                            ELSE 0 
                        END as hold_percentage
                    FROM wallet_positions 
                    WHERE wallet_address = $1 AND token_address = $2""",
                    wallet, token
                )
            
            row = await with_db_retry(_fetch)
            return row['hold_percentage'] if row else 0
        except Exception as e:
            logger.debug(f"Could not fetch hold_percentage: {e}")
            return 0

    async def _fetch_avg_entry_mc(self, wallet: str, token: str) -> float:
        """Fetch average entry market cap for a wallet's position"""
        try:
            async def _fetch():
                return await self.db.fetchrow(
                    """SELECT avg_entry_mc FROM wallet_positions 
                    WHERE wallet_address = $1 AND token_address = $2""",
                    wallet, token
                )
            
            row = await with_db_retry(_fetch)
            return float(row['avg_entry_mc']) if row and row['avg_entry_mc'] else 0
        except Exception as e:
            logger.debug(f"Could not fetch avg_entry_mc: {e}")
            return 0

    async def send_alert(self, wallet: str, token: str, tx_type: str, sol_amount: float, token_amount: float, sig: str):
        try:
            emoji = "🟢" if tx_type == "buy" else "🔴"

            wallet_label = None
            for w in self.wallets:
                if w['address'] == wallet:
                    wallet_label = w['label']
                    break

            # Fetch fresh token info (no cache)
            token_info = await self.cluster_detector.get_token_info(token, use_cache=False)

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
            token_str = f"{token_amount:,.2f}"

            # Get hold percentage and avg entry MC from database (with retry)
            hold_percentage = 0
            avg_entry_mc = 0
            async with self.db_semaphore:
                hold_percentage = await self._fetch_hold_percentage(wallet, token)
                avg_entry_mc = await self._fetch_avg_entry_mc(wallet, token)

            hold_str = f"📊 *Hold:* `{hold_percentage}%`\n" if hold_percentage > 0 else ""
            
            # Format avg entry MC
            if avg_entry_mc >= 1_000_000:
                entry_mc_str = f"${avg_entry_mc/1_000_000:.2f}M"
            elif avg_entry_mc > 0:
                entry_mc_str = f"${avg_entry_mc/1000:.1f}K"
            else:
                entry_mc_str = "Unknown"
            
            entry_mc_str_full = f"📍 *Avg Entry:* `{entry_mc_str}`\n" if avg_entry_mc > 0 else ""

            # Get wallet performance data and determine emoji
            perf_emoji = "🔍"
            perf_stats = ""
            perf = await self.performance_tracker.get_wallet_performance_fast(wallet)
            if perf:
                perf_emoji = perf['confidence_emoji']
                perf_stats = (
                    f"📈 *Winrate:* `{perf['winrate']:.1f}%` | *Avg ROI:* `{perf['avg_roi']:+.1f}%`\n"
                    f"💰 *Total PnL:* `{perf['realized_pnl']:+.2f}` SOL ({perf['total_trades']} trades)\n"
                )

            message = f"""{emoji} *{tx_type.upper()} ALERT*
{perf_emoji} *Wallet:* {wallet_display}

{perf_stats}
*{token_info['ticker']}* ({token_info['name']})
`{token}`

*Current MC:* `{mc_str}`
{entry_mc_str_full}💰 *{tx_type.capitalize()}:* `{sol_str}`
🪙 *Tokens:* `{token_str}`
{hold_str}
[📊 DexScreener]({token_info['dexscreener']}) | [⚡ Photon]({token_info.get('photon', f'https://photon-sol.tinyastro.io/en/lp/{token}')})
[🔗 Solscan](https://solscan.io/tx/{sig})"""

            target_channel = Config.CHANNEL_PINGS or Config.TELEGRAM_CHAT_ID

            await self.bot.send_message(
                chat_id=target_channel,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )

            logger.info(f"Alert: {token_info['ticker']} | {tx_type} | {sol_amount:.3f} SOL | {token_amount:.2f} tokens")

        except Exception as e:
            logger.error(f"Alert failed: {e}")

    async def send_transfer_alert(self, wallet: str, token: Optional[str], amount: float, 
                                  is_sol: bool, sig: str, counterparty: Optional[str] = None,
                                  direction: str = "in"):
        """Send wallet-to-wallet transfer alert to CHANNEL_TRANSFERS"""
        try:
            if not Config.CHANNEL_TRANSFERS:
                return

            # Determine wallet label
            wallet_label = self._wallet_labels.get(wallet, "Unknown")
            wallet_display = f"*{wallet_label}*\n`{wallet}`" if wallet_label and wallet_label != "Unknown" else f"`{wallet}`"

            # Determine counterparty label if tracked
            counterparty_label = None
            if counterparty:
                counterparty_label = self._wallet_labels.get(counterparty)

            if is_sol:
                # SOL transfer
                amount_str = f"{amount:.4f} SOL"
                emoji = "🟡" if direction == "in" else "🔵"
                transfer_type = "SOL IN" if direction == "in" else "SOL OUT"
                
                counterparty_display = ""
                if counterparty:
                    if counterparty_label:
                        counterparty_display = f"\n📤 *From:* `{counterparty}` ({counterparty_label})" if direction == "in" else f"\n📥 *To:* `{counterparty}` ({counterparty_label})"
                    else:
                        counterparty_display = f"\n📤 *From:* `{counterparty}`" if direction == "in" else f"\n📥 *To:* `{counterparty}`"
                else:
                    counterparty_display = "\n❓ *Counterparty:* Unknown (may be multi-transfer or fee adjustment)"
                
                message = f"""{emoji} *{transfer_type}*
👤 *Wallet:* {wallet_display}{counterparty_display}

💰 *Amount:* `{amount_str}`

[🔗 Solscan](https://solscan.io/tx/{sig})"""
            else:
                # Token transfer
                if amount < Config.TRANSFER_TOKEN_THRESHOLD:
                    return
                
                amount_str = f"{amount:,.2f}"
                emoji = "🟢" if direction == "in" else "🔴"
                transfer_type = "TOKEN IN" if direction == "in" else "TOKEN OUT"
                
                # Get token info
                token_info = await self.cluster_detector.get_token_info(token, use_cache=True)
                ticker = token_info.get('ticker', 'Unknown')
                name = token_info.get('name', 'Unknown')
                
                counterparty_display = ""
                if counterparty:
                    if counterparty_label:
                        counterparty_display = f"\n📤 *From:* `{counterparty}` ({counterparty_label})" if direction == "in" else f"\n📥 *To:* `{counterparty}` ({counterparty_label})"
                    else:
                        counterparty_display = f"\n📤 *From:* `{counterparty}`" if direction == "in" else f"\n📥 *To:* `{counterparty}`"
                
                message = f"""{emoji} *{transfer_type}*
👤 *Wallet:* {wallet_display}{counterparty_display}

🪙 *Token:* *{ticker}* ({name})
📊 *Amount:* `{amount_str}` tokens
`{token}`

[📊 DexScreener]({token_info.get('dexscreener', f'https://dexscreener.com/solana/{token}')}) | [⚡ Photon](https://photon-sol.tinyastro.io/en/lp/{token})
[🔗 Solscan](https://solscan.io/tx/{sig})"""

            await self.bot.send_message(
                chat_id=Config.CHANNEL_TRANSFERS,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"Transfer alert: {wallet[:8]} | {transfer_type} | {amount_str}")

        except Exception as e:
            logger.error(f"Transfer alert failed: {e}")

    def _is_dex_program(self, program_id: str) -> bool:
        """Check if program ID is a known DEX/swap program"""
        dex_programs = {
            # Jupiter
            "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
            # Raydium
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
            "5quB7PxxgfP86MCT74D29itB5RFzZPn6Y4zvGJY6Vj6S",
            # Orca
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
            "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",
            # Meteora
            "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
            # Pump.fun
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
            # Pump.fun bonding curve / migration related
            "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJmw",
            "7OjPdbU7RjUoJzUpK1wZsWkdtWPS5bDrPmfxnzMT3JFR",
            # Raydium CLMM
            "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
            # Moonshot
            "MoonCVVNZFSYkqNXP6bxHLPL6QQJiMagDL3qcE14FZp",
            # Tensor (NFT trading but sometimes involved)
            "TSWAPaqyCSx2KABk68Shruf4rp7CxcNi8hAsbdwmHbN",
        }
        return program_id in dex_programs

    async def _mark_processed(self, sig: str):
        """Fire-and-forget cache write - handles failures gracefully"""
        try:
            await self.cache.setex(f"tx:{sig}", 2592000, "1")  # 30 days
        except Exception as e:
            logger.warning(f"Failed to mark tx {sig[:16]}... as processed: {e}")

    def _detect_transfers(self, tx: dict, wallet: str, account_keys: list) -> list:
        """
        Detect wallet-to-wallet transfers (not DEX swaps).
        Returns list of transfer events: [{type: 'sol'|'token', amount, direction, counterparty}]
        """
        transfers = []
        
        meta = tx.get('meta', {})
        pre_sol = meta.get('preBalances', [])
        post_sol = meta.get('postBalances', [])
        pre_tokens = meta.get('preTokenBalances', []) or []
        post_tokens = meta.get('postTokenBalances', []) or []
        
        # Find wallet index
        wallet_index = None
        for i, key in enumerate(account_keys):
            addr = key if isinstance(key, str) else key.get('pubkey', '')
            if addr == wallet:
                wallet_index = i
                break
        
        if wallet_index is None:
            return transfers
        
        # Calculate SOL change
        sol_change = 0.0
        if wallet_index < len(pre_sol) and wallet_index < len(post_sol):
            sol_change = (post_sol[wallet_index] - pre_sol[wallet_index]) / 1e9
        
        # Get token changes for this wallet
        wallet_token_accounts = {}
        for bal in pre_tokens + post_tokens:
            if bal.get('owner') == wallet:
                idx = bal.get('accountIndex')
                mint = bal.get('mint', '')
                wallet_token_accounts[idx] = mint
        
        # Calculate token balance changes
        pre_balances = {}
        post_balances = {}
        for bal in pre_tokens:
            idx = bal.get('accountIndex')
            if idx in wallet_token_accounts:
                mint = wallet_token_accounts[idx]
                amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                pre_balances[mint] = amount
        
        for bal in post_tokens:
            idx = bal.get('accountIndex')
            if idx in wallet_token_accounts:
                mint = wallet_token_accounts[idx]
                amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                post_balances[mint] = amount
        
        # Get transaction instructions to check for DEX programs
        message = tx.get('transaction', {}).get('message', {})
        instructions = message.get('instructions', [])
        inner_instructions = meta.get('innerInstructions', [])
        
        # Check if any DEX program is involved - if so, it's a swap not a transfer
        for ix in instructions:
            prog_id = ix.get('programId', '')
            if self._is_dex_program(prog_id):
                return transfers  # DEX program found = swap, not transfer
        
        for inner in inner_instructions:
            for ix in inner.get('instructions', []):
                # Inner instructions may use programIdIndex instead of programId
                program_id = ix.get('programId', '')
                if not program_id and 'programIdIndex' in ix:
                    # Look up program ID from account keys
                    idx = ix.get('programIdIndex')
                    if idx is not None and idx < len(account_keys):
                        program_id = account_keys[idx] if isinstance(account_keys[idx], str) else account_keys[idx].get('pubkey', '')
                
                if self._is_dex_program(program_id):
                    return transfers  # DEX program found = swap, not transfer
        
        # Debug: Log all program IDs found in instructions for troubleshooting
        logger.debug(f"Transfer detection - Checking tx for wallet {wallet[:8]}")
        for ix in instructions:
            logger.debug(f"  Top-level program: {ix.get('programId', 'N/A')[:20]}...")
        
        # Calculate total token change across all mints
        all_mints = set(pre_balances.keys()) | set(post_balances.keys())
        has_token_in = False
        has_token_out = False
        
        for mint in all_mints:
            if mint in Config.IGNORED_TOKENS:
                continue
            pre = pre_balances.get(mint, 0)
            post = post_balances.get(mint, 0)
            change = post - pre
            if abs(change) >= Config.TRANSFER_TOKEN_THRESHOLD:
                if change > 0:
                    has_token_in = True
                else:
                    has_token_out = True
        
        # Additional check: if tokens move AND there's any SOL movement, it's likely a swap
        # This catches cases where SOL change is just fees or where detection missed DEX programs
        sol_any_change = abs(sol_change) > 0.0001  # Any SOL movement (catches fees)
        
        if sol_any_change and (has_token_in or has_token_out):
            # SOL moved and tokens moved = swap, not pure transfer
            return transfers
        
        # Get transaction instructions for counterparty detection
        message = tx.get('transaction', {}).get('message', {})
        instructions = message.get('instructions', [])
        
        # Check for simple SOL transfer (System Program transfer)
        has_simple_transfer = False
        transfer_info = {'source': None, 'destination': None, 'amount': 0}
        
        for ix in instructions:
            if ix.get('programId') == '11111111111111111111111111111111':
                parsed = ix.get('parsed', {})
                if isinstance(parsed, dict) and parsed.get('type') == 'transfer':
                    info = parsed.get('info', {})
                    source = info.get('source')
                    destination = info.get('destination')
                    
                    # Skip if this is a transfer to/from an LP or exchange (DEX-related)
                    if self._is_lp_or_exchange(source) or self._is_lp_or_exchange(destination):
                        continue
                    
                    has_simple_transfer = True
                    transfer_info['source'] = source
                    transfer_info['destination'] = destination
                    transfer_info['amount'] = int(info.get('lamports', 0)) / 1e9
                    break
        
        # Detect SOL transfers (not swaps - we already filtered those)
        if abs(sol_change) >= Config.TRANSFER_SOL_THRESHOLD:
            counterparty = None
            
            # Try to get counterparty from System Program instruction
            if has_simple_transfer and transfer_info['source'] and transfer_info['destination']:
                if wallet == transfer_info['source']:
                    counterparty = transfer_info['destination']
                elif wallet == transfer_info['destination']:
                    counterparty = transfer_info['source']
            
            # Fallback: look for opposite change in account balances
            if not counterparty:
                for i, (pre, post) in enumerate(zip(pre_sol, post_sol)):
                    if i != wallet_index and i < len(account_keys):
                        other_change = (post - pre) / 1e9
                        # Check if other account has significant opposite change
                        if sol_change < 0 and other_change > 0.01:
                            key = account_keys[i]
                            counterparty = key if isinstance(key, str) else key.get('pubkey', '')
                            break
                        elif sol_change > 0 and other_change < -0.01:
                            key = account_keys[i]
                            counterparty = key if isinstance(key, str) else key.get('pubkey', '')
                            break
            
            # Skip if counterparty is an LP or exchange
            if not self._is_lp_or_exchange(counterparty):
                transfers.append({
                    'type': 'sol',
                    'amount': abs(sol_change),
                    'direction': 'in' if sol_change > 0 else 'out',
                    'counterparty': counterparty
                })
        
        # Detect token transfers (not swaps - we already filtered those)
        for mint in all_mints:
            if mint in Config.IGNORED_TOKENS:
                continue
            
            pre = pre_balances.get(mint, 0)
            post = post_balances.get(mint, 0)
            change = post - pre
            
            if abs(change) >= Config.TRANSFER_TOKEN_THRESHOLD:
                # Find counterparty by looking at token balance changes
                counterparty = None
                other_pre = {b.get('accountIndex'): b for b in pre_tokens if b.get('mint') == mint}
                other_post = {b.get('accountIndex'): b for b in post_tokens if b.get('mint') == mint}
                
                for idx in set(other_pre.keys()) | set(other_post.keys()):
                    if idx not in wallet_token_accounts:
                        pre_amt = float(other_pre.get(idx, {}).get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                        post_amt = float(other_post.get(idx, {}).get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                        other_change = post_amt - pre_amt
                        
                        if change < 0 and other_change > 0:
                            if idx < len(account_keys):
                                key = account_keys[idx]
                                counterparty = key if isinstance(key, str) else key.get('pubkey', '')
                            break
                        elif change > 0 and other_change < 0:
                            if idx < len(account_keys):
                                key = account_keys[idx]
                                counterparty = key if isinstance(key, str) else key.get('pubkey', '')
                            break
                
                # Skip if counterparty is an LP or exchange
                if not self._is_lp_or_exchange(counterparty):
                    transfers.append({
                        'type': 'token',
                        'token': mint,
                        'amount': abs(change),
                        'direction': 'in' if change > 0 else 'out',
                        'counterparty': counterparty
                    })
        
        return transfers

    async def check_wallet_fast(self, wallet_dict: Dict[str, str]) -> int:
        wallet = wallet_dict['address']
        
        # Track which RPCs we've tried for this wallet check to avoid repeats
        attempted_rpcs = set()
        
        # Try multiple RPCs on connection errors - up to all available public RPCs
        max_retries = min(6, len(self.public_rpcs) + 1)
        for attempt in range(max_retries):
            # Get RPC, excluding ones we've already tried
            rpc_url = self._get_rpc_excluding(attempted_rpcs)
            attempted_rpcs.add(rpc_url)
            
            # Always fetch most recent 20 - cache handles deduplication
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [wallet, {"limit": 20}]
            }

            try:
                async with self.session.post(rpc_url, json=payload) as resp:
                    if resp.status != 200:
                        if resp.status == 429:
                            self.report_rpc_failure(rpc_url, 'rate_limit')
                        elif resp.status >= 500:
                            self.report_rpc_failure(rpc_url, 'server_error')
                        continue

                    data = await resp.json()
                signatures = data.get('result', [])
                if not signatures:
                    return 0

                # FIX: Always sort by blockTime (oldest first) for consistent processing
                signatures = sorted(signatures, key=lambda x: x.get('blockTime', 0) or 0)

                new_count = 0
                processed_sigs = []
                cache_hits = 0
                cache_misses = 0

                # FIX: Process all signatures
                for sig_info in signatures:
                    sig = sig_info['signature']
                    block_time = sig_info.get('blockTime')  # Unix timestamp

                    # Skip transactions that occurred before script started
                    if block_time and block_time < self.script_start_time:
                        continue

                    # FIX: Check cache BEFORE fetching transaction (saves RPC calls)
                    if await self.cache.get(f"tx:{sig}"):
                        cache_hits += 1
                        continue
                    
                    cache_misses += 1

                    # Mark that we'll process this one
                    processed_sigs.append(sig)

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

                    # FIX: Use same RPC for transaction fetch (maintain session affinity)
                    tx_rpc_url = rpc_url
                    
                    # FIX: Use RPC semaphore to limit concurrent calls
                    async with self.rpc_semaphore:
                        async with self.session.post(tx_rpc_url, json=tx_payload) as tx_resp:
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
                    if wallet_index is not None:
                        if wallet_index < len(pre_sol_balances) and wallet_index < len(post_sol_balances):
                            pre_lamports = pre_sol_balances[wallet_index]
                            post_lamports = post_sol_balances[wallet_index]
                            sol_change = (post_lamports - pre_lamports) / 1e9

                    wallet_token_indices = set()
                    for balance in pre_tokens + post_tokens:
                        if balance.get('owner') == wallet:
                            wallet_token_indices.add(balance.get('accountIndex'))

                    if not wallet_token_indices:
                        continue

                    pre_balances = {}
                    post_balances = {}

                    for bal in pre_tokens:
                        if bal.get('accountIndex') in wallet_token_indices:
                            mint = bal.get('mint', '')
                            amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                            pre_balances[mint] = amount

                    for bal in post_tokens:
                        if bal.get('accountIndex') in wallet_token_indices:
                            mint = bal.get('mint', '')
                            amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0) or 0)
                            post_balances[mint] = amount

                    all_mints = set(pre_balances.keys()) | set(post_balances.keys())
                    changes = []

                    for mint in all_mints:
                        if mint in Config.IGNORED_TOKENS:
                            continue

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

                        # Check for wallet-to-wallet transfers (separate from buy/sell)
                        transfers = self._detect_transfers(tx, wallet, account_keys)
                        for transfer in transfers:
                            # FIX: Fire-and-forget transfer alerts
                            asyncio.create_task(self.send_transfer_alert(
                                wallet=wallet,
                                token=transfer.get('token'),
                                amount=transfer['amount'],
                                is_sol=(transfer['type'] == 'sol'),
                                sig=sig,
                                counterparty=transfer.get('counterparty'),
                                direction=transfer['direction']
                            ))
                            # Reduced sleep since non-blocking
                            await asyncio.sleep(0.05)

                        if not changes:
                            continue

                        for change in changes:
                            if change['sol_amount'] < Config.MIN_SOL_THRESHOLD:
                                continue

                            # Fetch market cap for buys to track entry price
                            market_cap = 0
                            if change['type'] == 'buy':
                                token_info = await self.cluster_detector.get_token_info(change['token'], use_cache=False)
                                market_cap = token_info.get('market_cap', 0)

                            async with self.db_semaphore:
                                # These now have internal retry logic
                                # For sells, pass the SOL amount to update total_sol_returned
                                await self.cluster_detector.update_position(
                                    wallet, change['token'], change['type'],
                                    change['token_amount'],
                                    sol_amount=change['sol_amount'],
                                    market_cap=market_cap
                                )

                                # Use pre-built wallet_labels instead of recreating every time
                                await self.cluster_detector.check_cluster(
                                    change['token'], wallet, change['type'], self._wallet_labels
                                )
                                
                                # Record trade for performance tracking
                                await self.performance_tracker.record_trade(
                                    wallet, change['token'], change['type'],
                                    change['sol_amount'], change['token_amount']
                                )

                            # FIX: Fire-and-forget alerts - don't block processing
                            asyncio.create_task(self.send_alert(wallet, change['token'], change['type'],
                                                change['sol_amount'], change['token_amount'], sig))
                            new_count += 1
                            # Reduced sleep since we're not blocking
                            await asyncio.sleep(0.1)

                        # FIX: Mark transaction as processed AFTER successful handling
                        # CRITICAL: Must await cache set to ensure transaction is tracked
                        # Fire-and-forget caused cache misses, wasting Helius credits
                        try:
                            await self._mark_processed(sig)
                        except Exception as e:
                            logger.error(f"Failed to mark tx {sig[:16]}... as processed: {e}")
                            # Continue anyway - don't block processing, but log the error

                # Log cache stats for debugging credit usage
                if cache_hits + cache_misses > 0:
                    hit_rate = cache_hits / (cache_hits + cache_misses) * 100
                    if cache_misses > 5:  # Only log if significant activity
                        logger.debug(f"Wallet {wallet[:8]}... cache: {cache_hits} hits, {cache_misses} misses ({hit_rate:.0f}% hit rate)")

                # OPTIMIZATION: Update activity timestamp if new transactions found
                if new_count > 0:
                    self.wallet_last_activity[wallet] = time.time()

                return new_count

            except asyncio.TimeoutError:
                self.report_rpc_failure(rpc_url, 'timeout')
                if attempt < max_retries - 1:
                    logger.debug(f"Timeout for {wallet[:8]}, trying next RPC...")
                    continue
                return 0
            except aiohttp.ClientSSLError as e:
                self.report_rpc_failure(rpc_url, 'connection_error')
                if attempt < max_retries - 1:
                    logger.debug(f"SSL error for {wallet[:8]}, trying next RPC...")
                    continue
                logger.warning(f"SSL errors exhausted for {wallet[:8]}: {e}")
                return 0
            except aiohttp.ClientConnectorError as e:
                self.report_rpc_failure(rpc_url, 'connection_error')
                if attempt < max_retries - 1:
                    logger.debug(f"Connection error for {wallet[:8]}, trying next RPC...")
                    continue
                logger.warning(f"Connection errors exhausted for {wallet[:8]}: {e}")
                return 0
            except Exception as e:
                logger.error(f"Check error for {wallet[:8]}: {e}")
                return 0
        
        return 0

    async def run(self):
        await self.connect()
        self.wallets = self.load_wallets()
        if not self.wallets:
            logger.error("No wallets loaded - exiting")
            return

        # Clean up performance data for removed wallets
        wallet_addresses = [w['address'] for w in self.wallets]
        removed_count = await self.performance_tracker.cleanup_removed_wallets(wallet_addresses)
        if removed_count > 0:
            logger.info(f"Removed performance data for {removed_count} wallet(s) no longer in wallets.txt")

        # Pre-build wallet_labels to avoid recreating every transaction
        self._wallet_labels = {w['address']: w['label'] for w in self.wallets}
        
        # OPTIMIZATION: Initialize check intervals and stagger initial check times
        # This prevents all wallets from being checked simultaneously on startup
        now = time.time()
        self._wallet_last_check = {}  # Initialize here, not in the loop
        
        for i, w in enumerate(self.wallets):
            wallet = w['address']
            # Start with 60s interval (very conservative for public RPCs)
            self.wallet_check_interval[wallet] = 60
            # Assume 24h inactive on startup
            self.wallet_last_activity[wallet] = now - 86400
            # STAGGER: Spread initial checks over 60 seconds to prevent RPC burst
            # Wallet 0 checks immediately, wallet 1 checks at +1s, wallet 2 at +2s, etc.
            self._wallet_last_check[wallet] = now - (60 - i)
        
        logger.info(f"Starting tracker | {len(self.wallets)} wallets | min: {Config.MIN_SOL_THRESHOLD} SOL | Staggered startup over 60s, 60s intervals")

        cycle_count = 0
        last_memory_log = 0
        
        while not self._shutdown_event.is_set():
            cycle_start = time.time()
            cycle_count += 1

            # Log memory every 1000 cycles
            if cycle_count - last_memory_log >= 1000:
                import gc
                import sys
                gc.collect()
                obj_count = len(gc.get_objects())
                logger.info(f"Memory check - Cycle {cycle_count} | GC objects: {obj_count}")
                last_memory_log = cycle_count
            
            # Refresh session every 5000 cycles to prevent connection pool exhaustion
            if cycle_count % 5000 == 0 and cycle_count > 0:
                logger.info(f"Refreshing HTTP session at cycle {cycle_count}")
                if self.session:
                    await self.session.close()
                self.session = self._create_session()

            try:
                # OPTIMIZATION: Only check wallets that are due based on adaptive interval
                now = time.time()
                due_wallets = []
                interval_counts = {15: 0, 30: 0, 60: 0, 90: 0, 120: 0}  # For logging
                
                for w in self.wallets:
                    wallet = w['address']
                    # Get adaptive interval based on activity
                    interval = self.get_adaptive_interval(wallet)
                    self.wallet_check_interval[wallet] = interval
                    interval_counts[interval] = interval_counts.get(interval, 0) + 1
                    
                    # Check if this wallet is due
                    last_check = self._wallet_last_check.get(wallet, 0)
                    if now - last_check >= interval:
                        due_wallets.append(w)
                
                # Log interval distribution periodically
                if cycle_count % 10 == 0:
                    logger.info(f"Intervals: 15s={interval_counts.get(15, 0)}, 30s={interval_counts.get(30, 0)}, 60s={interval_counts.get(60, 0)}, 90s={interval_counts.get(90, 0)}, 120s={interval_counts.get(120, 0)}")
                
                # Update last check time for due wallets
                for w in due_wallets:
                    self._wallet_last_check[w['address']] = now
                
                if due_wallets:
                    # OPTIMIZATION: Add small stagger delay to prevent RPC burst
                    # Process wallets sequentially with small delays to spread load
                    total_new = 0
                    for i, w in enumerate(due_wallets):
                        # Stagger checks by 100ms each to prevent RPC burst
                        if i > 0:
                            await asyncio.sleep(0.1)
                        
                        async with self.wallet_check_semaphore:
                            result = await self.check_wallet_fast(w)
                            if isinstance(result, int):
                                total_new += result
                else:
                    total_new = 0
                
                elapsed = time.time() - cycle_start

                logger.info(f"Cycle {cycle_count} | {elapsed:.1f}s | {len(due_wallets)}/{len(self.wallets)} wallets | {total_new} new txs")

                # Adaptive sleep - check again in min interval time
                min_interval = min(self.wallet_check_interval.get(w['address'], 5) for w in self.wallets) if self.wallets else 5
                sleep_time = max(0, min_interval - elapsed)
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=sleep_time)
                except asyncio.TimeoutError:
                    pass

            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(1)

        logger.info("Tracker stopped")


async def start_cmd(update: Update, context):
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    
    message = (
        "⚡ *ShadowHunter Online*\n\n"
        "📊 *Commands:*\n"
        "`/status` - Tracker status\n"
        "`/performance` - Wallet leaderboard\n"
        "`/performance 7d|30d` - Time-based performance\n"
        "`/performance \u003cwallet\u003e` - Specific wallet stats\n"
        "`/trackhold \u003ctoken\u003e` - Check holdings\n"
        "`/analyze \u003ctoken\u003e` - Analyze token across wallets\n"
        "`/suggest` - Find similar wallets"
    )
    
    if is_user_admin:
        message += (
            "\n\n🔐 *Admin Commands:*\n"
            "`/add \u003caddress\u003e [label]` - Add wallet\n"
            "`/remove \u003caddress|label\u003e` - Remove wallet"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def status_cmd(update: Update, context, tracker: SpeedTracker):
    """Show tracker status"""
    try:
        if tracker.performance_tracker is None:
            await update.message.reply_text("⏳ Initializing...")
            return
        
        wallet_count = len(tracker.wallets) if tracker.wallets else 0
        
        await update.message.reply_text(
            f"✅ ShadowHunter Running\n"
            f"• Wallets: `{wallet_count}`\n"
            f"• Min SOL: `{Config.MIN_SOL_THRESHOLD}`\n"
            f"• Cluster threshold: `{Config.CLUSTER_THRESHOLD}`"
        )
    except Exception as e:
        logger.error(f"Status command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def performance_cmd(update: Update, context, tracker: SpeedTracker):
    """Show wallet performance leaderboard, specific wallet stats, or time-based performance"""
    try:
        # Guard: Check if tracker is fully initialized
        if tracker.performance_tracker is None:
            await update.message.reply_text("⏳ Tracker is still initializing, please wait a moment...")
            return
        
        # Check if time-based argument
        if context.args:
            query = context.args[0].strip().lower()
            
            # Handle time-based performance
            if query in ['7d', '7day', '7days', 'week']:
                await performance_timeframe_cmd(update, context, tracker, days=7)
                return
            elif query in ['30d', '30day', '30days', 'month']:
                await performance_timeframe_cmd(update, context, tracker, days=30)
                return
            else:
                # Show specific wallet stats
                await _show_wallet_performance(update, context, tracker, query)
                return
        
        # Show paginated leaderboard
        await _show_performance_leaderboard(update, context, tracker, page=0)
        
    except Exception as e:
        logger.error(f"Performance command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def _show_wallet_performance(update: Update, context, tracker: SpeedTracker, query: str):
    """Show detailed performance for a specific wallet"""
    # Find wallet by label or address
    wallet_address = None
    wallet_label = None
    
    # Check if query matches a label (case-insensitive)
    for w in tracker.wallets:
        if w['label'].lower() == query.lower():
            wallet_address = w['address']
            wallet_label = w['label']
            break
    
    # Check if query matches an address (partial or full)
    if not wallet_address:
        for w in tracker.wallets:
            if w['address'].lower() == query.lower() or w['address'].lower().startswith(query.lower()):
                wallet_address = w['address']
                wallet_label = w['label']
                break
    
    if not wallet_address:
        await update.message.reply_text(
            f"❌ Wallet not found: `{query}`\n\n"
            f"Use `/performance` to see all tracked wallets.",
            parse_mode='Markdown'
        )
        return
    
    # Escape special Markdown characters in label
    wallet_label_escaped = wallet_label.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
    
    # Get performance data
    perf = await tracker.performance_tracker.get_wallet_performance_detailed(wallet_address)
    
    if not perf or perf['total_trades'] == 0:
        await update.message.reply_text(
            f"📊 *{wallet_label_escaped}*\n\n"
            f"No trades recorded yet.",
            parse_mode='Markdown'
        )
        return
    
    # Build detailed message
    pnl_emoji = "🟢" if perf['realized_pnl'] >= 0 else "🔴"
    winrate_emoji = "✅" if perf['winrate'] >= 50 else "⚠️"
    
    # Format average hold time
    avg_hold = tracker.performance_tracker._format_hold_time(perf.get('avg_hold_time_seconds', 0))
    
    lines = [
        f"📊 *WALLET PERFORMANCE: {wallet_label_escaped}* 📊\n",
        f"`{wallet_address}`\n",
        f"{perf['confidence_emoji']} *Confidence Score:* `{perf['confidence_score']:.1f}/100`\n",
        f"📈 *Trading Stats:*",
        f"   Total Trades: `{perf['total_trades']}`",
        f"   {winrate_emoji} Winrate: `{perf['winrate']:.1f}%`",
        f"   🏆 Wins: `{perf['winning_trades']}` | 💀 Losses: `{perf['losing_trades']}`",
        f"   ⏱ Avg Hold Time: `{avg_hold}`\n",
        f"💰 *Financial Performance:*",
        f"   {pnl_emoji} Realized PnL: `{perf['realized_pnl']:+.2f}` SOL",
        f"   📊 Avg ROI: `{perf['avg_roi']:+.1f}%`",
        f"   💵 Total Invested: `{perf['total_invested']:.2f}` SOL",
        f"   💸 Total Returned: `{perf['total_returned']:.2f}` SOL\n",
        f"🕐 Last Updated: `{perf['updated_at'].strftime('%Y-%m-%d %H:%M UTC') if perf['updated_at'] else 'Unknown'}`"
    ]
    
    message = "\n".join(lines)
    
    # Add back button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Leaderboard", callback_data="perf:page:0")]
    ])
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def _show_performance_leaderboard(update: Update, context, tracker: SpeedTracker, page: int, edit_message=None):
    """Show paginated performance leaderboard sorted by winrate"""
    performances = await tracker.performance_tracker.get_all_performance()
    
    if not performances:
        message = "📊 No performance data yet. Trades will be recorded as they occur."
        if edit_message:
            await edit_message.edit_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    # Sort by winrate descending
    performances.sort(key=lambda x: x['winrate'], reverse=True)
    
    # Pagination
    per_page = 10
    total_wallets = len(performances)
    total_pages = (total_wallets + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_wallets)
    page_performances = performances[start_idx:end_idx]
    
    # Build message
    lines = [f"📊 *WALLET PERFORMANCE LEADERBOARD* 📊\n"]
    lines.append(f"Sorted by Winrate | Page {page + 1}/{total_pages}\n")
    
    for i, p in enumerate(page_performances, start_idx + 1):
        # Find wallet label
        label = None
        for w in tracker.wallets:
            if w['address'] == p['wallet']:
                label = w['label']
                break
        
        name = label if label and not label.startswith("Wallet ") else p['wallet'][:8] + "..."
        
        # Escape special Markdown characters in name to prevent parsing errors
        name_escaped = name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
        
        # Color code
        pnl_emoji = "🟢" if p['realized_pnl'] >= 0 else "🔴"
        winrate_emoji = "✅" if p['winrate'] >= 50 else "⚠️"
        
        lines.append(
            f"{i}. *{name_escaped}*\n"
            f"   {winrate_emoji} Winrate: `{p['winrate']:.1f}%` ({p['winning_trades']}/{p['total_trades']})\n"
            f"   {pnl_emoji} PnL: `{p['realized_pnl']:+.2f}` SOL | ROI: `{p['avg_roi']:+.1f}%`\n"
        )
    
    # Add summary
    total_pnl = sum(p['realized_pnl'] for p in performances)
    total_trades = sum(p['total_trades'] for p in performances)
    total_winning_trades = sum(p['winning_trades'] for p in performances)
    overall_winrate = (total_winning_trades / total_trades * 100) if total_trades > 0 else 0
    overall_emoji = "🟢" if overall_winrate >= 50 else "🔴"
    
    lines.append(
        f"\n📊 *SUMMARY*\n"
        f"Total PnL: `{total_pnl:+.2f}` SOL | "
        f"{overall_emoji} Overall Winrate: `{overall_winrate:.1f}%`"
    )
    
    message = "\n".join(lines)
    
    # Build pagination buttons
    buttons = []
    
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"perf:page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"perf:page:{page+1}"))
        buttons.append(nav_buttons)
    
    # Add quick select buttons for top performers
    if page == 0 and len(page_performances) >= 3:
        quick_buttons = []
        for p in page_performances[:3]:
            for w in tracker.wallets:
                if w['address'] == p['wallet']:
                    label = w['label'] if w['label'] and not w['label'].startswith("Wallet ") else p['wallet'][:6]
                    quick_buttons.append(InlineKeyboardButton(f"👤 {label}", callback_data=f"perf:wallet:{p['wallet']}"))
                    break
        if quick_buttons:
            buttons.append(quick_buttons)
    
    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    
    if edit_message:
        await edit_message.edit_text(message, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def performance_callback(update: Update, context, tracker: SpeedTracker):
    """Handle performance pagination and wallet selection callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "noop":
        return
    
    if data.startswith("perf:page:"):
        try:
            page = int(data.split(":")[2])
            await _show_performance_leaderboard(update, context, tracker, page, edit_message=query.message)
        except (IndexError, ValueError):
            await query.answer("Invalid page", show_alert=True)
    
    elif data.startswith("perf:wallet:"):
        try:
            wallet_address = data.split(":", 2)[2]
            await _show_wallet_performance_callback(update, context, tracker, wallet_address)
        except IndexError:
            await query.answer("Invalid wallet", show_alert=True)


async def _show_wallet_performance_callback(update: Update, context, tracker: SpeedTracker, wallet_address: str):
    """Show wallet performance from callback (edits message instead of replying)"""
    query = update.callback_query
    
    # Find wallet label
    wallet_label = None
    for w in tracker.wallets:
        if w['address'] == wallet_address:
            wallet_label = w['label']
            break
    
    if not wallet_label:
        wallet_label = wallet_address[:8] + "..."
    
    # Get performance data
    perf = await tracker.performance_tracker.get_wallet_performance_detailed(wallet_address)
    
    if not perf or perf['total_trades'] == 0:
        await query.message.edit_text(
            f"📊 *{wallet_label}*\n\n"
            f"No trades recorded yet.",
            parse_mode='Markdown'
        )
        return
    
    # Build detailed message
    pnl_emoji = "🟢" if perf['realized_pnl'] >= 0 else "🔴"
    winrate_emoji = "✅" if perf['winrate'] >= 50 else "⚠️"
    
    # Format average hold time
    avg_hold = tracker.performance_tracker._format_hold_time(perf.get('avg_hold_time_seconds', 0))
    
    lines = [
        f"📊 *WALLET PERFORMANCE: {wallet_label}* 📊\n",
        f"`{wallet_address}`\n",
        f"{perf['confidence_emoji']} *Confidence Score:* `{perf['confidence_score']:.1f}/100`\n",
        f"📈 *Trading Stats:*",
        f"   Total Trades: `{perf['total_trades']}`",
        f"   {winrate_emoji} Winrate: `{perf['winrate']:.1f}%`",
        f"   🏆 Wins: `{perf['winning_trades']}` | 💀 Losses: `{perf['losing_trades']}`",
        f"   ⏱ Avg Hold Time: `{avg_hold}`\n",
        f"💰 *Financial Performance:*",
        f"   {pnl_emoji} Realized PnL: `{perf['realized_pnl']:+.2f}` SOL",
        f"   📊 Avg ROI: `{perf['avg_roi']:+.1f}%`",
        f"   💵 Total Invested: `{perf['total_invested']:.2f}` SOL",
        f"   💸 Total Returned: `{perf['total_returned']:.2f}` SOL\n",
        f"🕐 Last Updated: `{perf['updated_at'].strftime('%Y-%m-%d %H:%M UTC') if perf['updated_at'] else 'Unknown'}`"
    ]
    
    message = "\n".join(lines)
    
    # Add back button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Leaderboard", callback_data="perf:page:0")]
    ])
    
    await query.message.edit_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def trackhold_cmd(update: Update, context, tracker: SpeedTracker):
    """Show which tracked wallets are holding a specific token via live RPC balance check"""
    try:
        # Guard: Check if tracker is fully initialized
        if tracker.cluster_detector is None:
            await update.message.reply_text("⏳ Tracker is still initializing, please wait a moment...")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/trackhold <token_address>`\n"
                "Example: `/trackhold EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`",
                parse_mode='Markdown'
            )
            return
        
        token_address = context.args[0]
        
        # Validate Solana address format
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', token_address):
            await update.message.reply_text("❌ Invalid Solana address format")
            return
        
        loading_msg = await update.message.reply_text(f"🔍 Checking {len(tracker.wallets)} wallets...")
        
        # Get token info
        token_info = await tracker.cluster_detector.get_token_info(token_address)
        token_symbol = token_info.get('ticker', '???') if token_info else '???'
        token_price = token_info.get('price', 0) if token_info else 0
        
        # Get SOL price for PnL calculation in SOL terms
        sol_info = await tracker.cluster_detector.get_token_info("So11111111111111111111111111111111111111112")
        sol_price = sol_info.get('price', 0) if sol_info else 0
        
        # Get token supply via Alchemy
        token_supply = await tracker.get_token_supply_alchemy(token_address)
        
        # Check cache first
        cache_key = f"trackhold:{token_address}"
        cached = await tracker.cache.get(cache_key)
        if cached:
            holders_data = json.loads(cached)
            cache_age = time.time() - holders_data.get('timestamp', 0)
            if cache_age < 300:  # 5 minute cache
                await loading_msg.edit_text(
                    holders_data['message'] + f"\n\n_(cached {int(cache_age)}s ago)_",
                    parse_mode='Markdown'
                )
                return
        
        # Query live balances for all tracked wallets
        holders = []
        
        # FIX: Batch query all wallet positions in ONE database call (N+1 fix)
        wallet_addresses = [w['address'] for w in tracker.wallets]
        async with tracker.db_semaphore:
            all_position_rows = await tracker.db.fetch(
                """SELECT 
                    wallet_address, 
                    total_bought, 
                    total_sold, 
                    total_sol_invested, 
                    first_buy_time, 
                    avg_entry_mc
                FROM wallet_positions 
                WHERE wallet_address = ANY($1) AND token_address = $2""",
                wallet_addresses, 
                token_address
            )
        
        # Build lookup dict for O(1) access
        position_data = {row['wallet_address']: row for row in all_position_rows}
        
        for i, wallet in enumerate(tracker.wallets):
            wallet_address = wallet['address']
            wallet_label = wallet['label']
            
            # Check live balance via Alchemy (dedicated RPC for trackhold)
            balance = await tracker.get_token_balance_alchemy(wallet_address, token_address)
            
            if balance is None:
                continue
            
            if balance <= 0.000001:  # Skip dust
                continue
            
            # Get historical data from dict (O(1) lookup, no DB call)
            row = position_data.get(wallet_address)
            
            if row:
                total_bought = float(row['total_bought'] or 0)
                total_sol_invested = float(row['total_sol_invested'] or 0)
                avg_entry_mc = float(row['avg_entry_mc'] or 0)
                first_buy = row['first_buy_time']
                
                # Calculate cost basis in SOL (what was spent to acquire current holdings)
                cost_basis_sol = (balance / total_bought * total_sol_invested) if total_bought > 0 else 0
                
                # Calculate current value in SOL (convert USD value to SOL)
                # current USD value = balance * token_price
                # convert to SOL = (balance * token_price) / sol_price
                if sol_price > 0:
                    current_value_sol = (balance * token_price) / sol_price
                else:
                    current_value_sol = 0
                
                # Unrealized PnL in SOL
                unrealized_pnl = current_value_sol - cost_basis_sol
                unrealized_roi = (unrealized_pnl / cost_basis_sol * 100) if cost_basis_sol > 0 else 0
            else:
                # No tracked history, just show balance
                avg_buy_price = 0
                avg_entry_mc = 0
                unrealized_pnl = 0
                unrealized_roi = 0
                first_buy = None
            
            # Calculate % of supply
            supply_pct = (balance / token_supply * 100) if token_supply else 0
            
            holders.append({
                'wallet': wallet_address,
                'label': wallet_label,
                'balance': balance,
                'supply_pct': supply_pct,
                'avg_entry_mc': avg_entry_mc,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_roi': unrealized_roi,
                'first_buy': first_buy,
                'has_history': row is not None
            })
            
            # Small delay to avoid RPC rate limits
            if i % 5 == 0 and i > 0:
                await asyncio.sleep(0.1)
        
        if not holders:
            await loading_msg.edit_text(
                f"📭 *{token_symbol}*\n"
                f"`{token_address}`\n\n"
                f"No tracked wallets found holding this token.",
                parse_mode='Markdown'
            )
            return
        
        # Sort by balance descending
        holders.sort(key=lambda x: x['balance'], reverse=True)
        
        # Build response
        lines = [
            f"📊 *{token_symbol}* LIVE HOLDINGS\n"
            f"`{token_address}`\n",
            f"*{len(holders)}* of {len(tracker.wallets)} wallets holding\n"
        ]
        
        total_balance = sum(h['balance'] for h in holders)
        total_unrealized_pnl = sum(h['unrealized_pnl'] for h in holders if h['has_history'])
        
        for h in holders:
            wallet_display = h['label'] if h['label'] else h['wallet'][:8] + "..."
            
            # Format balance
            if h['balance'] >= 1_000_000:
                balance_str = f"{h['balance']/1_000_000:.2f}M"
            elif h['balance'] >= 1_000:
                balance_str = f"{h['balance']/1_000:.1f}K"
            else:
                balance_str = f"{h['balance']:.2f}"
            
            # Format entry MC
            if h['avg_entry_mc'] >= 1_000_000:
                entry_mc_str = f"${h['avg_entry_mc']/1_000_000:.2f}M"
            elif h['avg_entry_mc'] > 0:
                entry_mc_str = f"${h['avg_entry_mc']/1000:.1f}K"
            else:
                entry_mc_str = "Unknown"
            
            # Format time held
            if h['first_buy']:
                try:
                    if isinstance(h['first_buy'], str):
                        from datetime import datetime, timezone
                        first_buy = datetime.fromisoformat(h['first_buy'].replace('Z', '+00:00'))
                    else:
                        first_buy = h['first_buy']
                    
                    # Handle timezone-aware vs timezone-naive comparison
                    if hasattr(first_buy, 'tzinfo') and first_buy.tzinfo is not None:
                        from datetime import datetime, timezone
                        now = datetime.now(timezone.utc)
                        if first_buy.tzinfo != now.tzinfo:
                            first_buy = first_buy.astimezone(timezone.utc)
                    else:
                        from datetime import datetime
                        now = datetime.utcnow()
                    
                    time_diff = now - first_buy
                    days = time_diff.days
                    hours = time_diff.seconds // 3600
                    if days > 0:
                        time_held_str = f"{days}d {hours}h"
                    else:
                        time_held_str = f"{hours}h"
                except Exception as e:
                    logger.debug(f"Time held calculation error: {e}")
                    time_held_str = "Unknown"
            else:
                time_held_str = "Unknown"
            
            # PnL emoji
            if h['has_history']:
                pnl_emoji = "🟢" if h['unrealized_pnl'] >= 0 else "🔴"
                pnl_line = f"\n   {pnl_emoji} Unrealized: `{h['unrealized_pnl']:+.2f}` SOL ({h['unrealized_roi']:+.1f}%)"
            else:
                pnl_line = "\n   ⚪ No trade history"
            
            lines.append(
                f"\n*{wallet_display}*\n"
                f"   🪙 Balance: `{balance_str}` ({h['supply_pct']:.3f}%)\n"
                f"   📍 Entry MC: `{entry_mc_str}`\n"
                f"   ⏱ Time Held: `{time_held_str}`"
                f"{pnl_line}"
            )
        
        # Summary with supply info
        total_supply_pct = (total_balance / token_supply * 100) if token_supply else 0
        
        # Format total supply
        if token_supply:
            if token_supply >= 1_000_000_000:
                supply_str = f"{token_supply/1_000_000_000:.2f}B"
            elif token_supply >= 1_000_000:
                supply_str = f"{token_supply/1_000_000:.2f}M"
            else:
                supply_str = f"{token_supply:,.0f}"
        else:
            supply_str = "Unknown"
        
        lines.append(
            f"\n\n📊 *AGGREGATE*\n"
            f"Total Supply: `{supply_str}`\n"
            f"Combined Holdings: `{total_supply_pct:.4f}%`\n"
            f"Total Unrealized PnL: `{total_unrealized_pnl:+.2f}` SOL"
        )
        
        message = "\n".join(lines)
        
        # Handle message length
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (truncated)"
        
        # Cache the result
        await tracker.cache.setex(
            cache_key,
            300,  # 5 minutes
            json.dumps({'message': message, 'timestamp': time.time()})
        )
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Trackhold command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def performance_timeframe_cmd(update: Update, context, tracker: SpeedTracker, days: int):
    """Show wallet performance for a specific time period (7d or 30d)"""
    try:
        if tracker.performance_tracker is None:
            await update.message.reply_text("⏳ Tracker is still initializing...")
            return
        
        loading_msg = await update.message.reply_text(f"📊 Analyzing last {days} days...")
        
        # Get timeframe data
        performances = await tracker.performance_tracker.get_performance_timeframe(days)
        
        if not performances:
            await loading_msg.edit_text(
                f"📊 No active wallets found in the last {days} days.\n\n"
                f"Wallets are included if they have recent trades or position updates."
            )
            return
        
        # Sort by winrate
        performances.sort(key=lambda x: x['winrate'], reverse=True)
        
        lines = [f"📊 *TOP PERFORMERS ({days}D)* 📊\n"]
        
        # Find wallet labels
        wallet_labels = {w['address']: w['label'] for w in tracker.wallets}
        
        for i, perf in enumerate(performances[:15], 1):
            wallet = perf['wallet']
            label = wallet_labels.get(wallet, wallet[:8] + "...")
            
            winrate = perf['winrate']
            pnl = perf['realized_pnl']
            trades = perf['total_trades']
            avg_hold = tracker.performance_tracker._format_hold_time(perf.get('avg_hold_time_seconds', 0))
            
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            lines.append(
                f"{i}. *{label}*\n"
                f"   {pnl_emoji} PnL: `{pnl:+.2f}` SOL | Winrate: `{winrate:.1f}%`\n"
                f"   Trades: `{trades}` | Avg Hold: `{avg_hold}`"
            )
        
        message = "\n\n".join(lines)
        
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (truncated)"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Performance timeframe command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def analyze_token_cmd(update: Update, context, tracker: SpeedTracker):
    """Analyze a token across all tracked wallets"""
    try:
        if tracker.cluster_detector is None:
            await update.message.reply_text("⏳ Tracker is still initializing...")
            return
        
        if not context.args:
            await update.message.reply_text(
                "🔍 *Analyze Token*\n\n"
                "Usage: `/analyze <token_address>`\n\n"
                "Shows which tracked wallets have traded this token.",
                parse_mode='Markdown'
            )
            return
        
        token = context.args[0].strip()
        loading_msg = await update.message.reply_text("🔍 Analyzing token across tracked wallets...")
        
        # Get token info from tracker
        token_info = await tracker.cluster_detector.get_token_info(token, use_cache=False)
        token_symbol = token_info.get('ticker', 'UNKNOWN') if token_info else 'UNKNOWN'
        
        # Get tracker wallet addresses
        tracker_wallets = [w['address'] for w in tracker.wallets]
        
        # Analyze token
        analysis = await tracker.performance_tracker.get_token_analysis(token, tracker_wallets)
        
        if analysis['wallet_count'] == 0:
            await loading_msg.edit_text(
                f"📭 *{token_symbol}*\n"
                f"`{token}`\n\n"
                f"No tracked wallets have traded this token.",
                parse_mode='Markdown'
            )
            return
        
        # Build response with PnL data
        total_pnl_emoji = "🟢" if analysis['total_realized_pnl'] >= 0 else "🔴"
        
        lines = [
            f"🔍 *{token_symbol}* ANALYSIS\n"
            f"`{token}`\n",
            f"📊 *Summary:*",
            f"   Wallets Traded: `{analysis['wallet_count']}`",
            f"   Active Holdings: `{analysis['active_positions']}`",
            f"   Total SOL Invested: `{analysis['total_sol_invested']:.2f}`",
            f"   Total SOL Returned: `{analysis['total_sol_returned']:.2f}`",
            f"   {total_pnl_emoji} Total PnL: `{analysis['total_realized_pnl']:+.2f}` SOL\n",
            f"👥 *Wallet Details:*"
        ]
        
        # Sort by realized PnL (best performers first)
        wallets = sorted(analysis['wallets'], key=lambda x: x['realized_pnl'], reverse=True)
        
        wallet_labels = {w['address']: w['label'] for w in tracker.wallets}
        
        for w in wallets:
            label = wallet_labels.get(w['wallet'], w['wallet'][:8] + "...")
            
            # Determine status and emoji
            if w['total_sold'] > 0 and not w['is_active']:
                status = "🔴 Fully Sold"
            elif w['total_sold'] > 0 and w['is_active']:
                status = "🟡 Partial Sold"
            else:
                status = "🟢 Holding"
            
            # Format entry MC
            if w['avg_entry_mc'] >= 1_000_000:
                entry_str = f"${w['avg_entry_mc']/1_000_000:.2f}M"
            elif w['avg_entry_mc'] > 0:
                entry_str = f"${w['avg_entry_mc']/1000:.1f}K"
            else:
                entry_str = "Unknown"
            
            # Build wallet section
            wallet_lines = [
                f"\n*{label}* {status}",
                f"   Invested: `{w['sol_invested']:.2f}` SOL"
            ]
            
            # Add PnL info if they sold anything
            if w['total_sold'] > 0:
                pnl_emoji = "🟢" if w['realized_pnl'] >= 0 else "🔴"
                wallet_lines.append(f"   {pnl_emoji} Realized PnL: `{w['realized_pnl']:+.2f}` SOL ({w['roi_percent']:+.1f}%)")
                wallet_lines.append(f"   Returned: `{w['sol_returned']:.2f}` SOL")
            
            # Add position info if still holding
            if w['is_active']:
                wallet_lines.append(f"   Holding: `{w['net_position']:.2f}` tokens")
            
            wallet_lines.append(f"   Entry MC: `{entry_str}`")
            wallet_lines.append(f"   First Buy: `{w['time_held_str']}` ago")
            
            lines.extend(wallet_lines)
        
        message = "\n".join(lines)
        
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (truncated)"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Analyze command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def suggest_wallets_cmd(update: Update, context, tracker: SpeedTracker):
    """Suggest wallets similar to top performers based on token overlap"""
    try:
        if tracker.cluster_detector is None:
            await update.message.reply_text("⏳ Tracker is still initializing...")
            return
        
        loading_msg = await update.message.reply_text("🎯 Finding similar wallets...")
        
        # Get top performing wallets by winrate
        performances = await tracker.performance_tracker.get_all_performance()
        if not performances:
            await loading_msg.edit_text("📊 No performance data available yet.")
            return
        
        # Sort by winrate, take top 5
        performances.sort(key=lambda x: x['winrate'], reverse=True)
        top_wallets = [p['wallet'] for p in performances[:5] if p['total_trades'] >= 3]
        
        if len(top_wallets) < 2:
            await loading_msg.edit_text(
                "📊 Not enough data to generate suggestions.\n"
                "Need at least 2 wallets with 3+ trades."
            )
            return
        
        # Find tokens commonly held by top wallets
        logger.info(f"Suggest: Looking for overlaps among {len(top_wallets)} top wallets: {[w[:8] + '...' for w in top_wallets]}")
        
        rows = await tracker.db.fetch(
            """SELECT token_address, COUNT(DISTINCT wallet_address) as wallet_count
            FROM wallet_positions
            WHERE wallet_address = ANY($1) AND is_active = TRUE
            GROUP BY token_address
            HAVING COUNT(DISTINCT wallet_address) >= 2
            ORDER BY wallet_count DESC
            LIMIT 20""",
            top_wallets
        )
        
        logger.info(f"Suggest: Found {len(rows)} common tokens among top wallets")
        
        if not rows:
            await loading_msg.edit_text(
                "📊 No common token overlaps found among top performers.\n"
                "Try again after more trading activity."
            )
            return
        
        # For each common token, find other wallets holding it
        suggestions = {}
        
        for row in rows:
            token = row['token_address']
            overlap_count = row['wallet_count']
            
            # Find other wallets holding this token (NOT IN syntax for compatibility)
            other_wallets = await tracker.db.fetch(
                """SELECT wallet_address, net_position, total_sol_invested
                FROM wallet_positions
                WHERE token_address = $1 
                  AND is_active = TRUE
                  AND wallet_address NOT IN (SELECT unnest($2::text[]))""",
                token, top_wallets
            )
            
            logger.info(f"Suggest: Token {token[:8]}... held by {overlap_count} top wallets, found {len(other_wallets)} other holders")
            
            for w in other_wallets:
                addr = w['wallet_address']
                if addr not in suggestions:
                    suggestions[addr] = {
                        'overlap_count': 0,
                        'total_invested': 0,
                        'positions': []
                    }
                suggestions[addr]['overlap_count'] += 1
                suggestions[addr]['total_invested'] += float(w['total_sol_invested'] or 0)
                suggestions[addr]['positions'].append({
                    'token': token[:8] + "...",
                    'balance': float(w['net_position'] or 0)
                })
        
        logger.info(f"Suggest: Total suggestions found: {len(suggestions)}")
        
        if not suggestions:
            await loading_msg.edit_text(
                "📊 No wallet suggestions found.\n"
                "No other wallets are holding the same tokens as your top performers.\n\n"
                "Debug info:\n"
                f"• Top wallets: {len(top_wallets)}\n"
                f"• Common tokens: {len(rows)}\n"
                "• Other holders: 0"
            )
            return
        
        # Sort by overlap count, then by investment
        sorted_suggestions = sorted(
            suggestions.items(),
            key=lambda x: (x[1]['overlap_count'], x[1]['total_invested']),
            reverse=True
        )[:10]
        
        lines = [
            "🎯 *WALLET SUGGESTIONS*\n",
            f"Based on tokens held by your top {len(top_wallets)} wallets:\n",
            "*Top Matches:*"
        ]
        
        for i, (addr, data) in enumerate(sorted_suggestions, 1):
            lines.append(
                f"\n{i}. `{addr}`\n"
                f"   🔄 Token Overlaps: `{data['overlap_count']}`\n"
                f"   💰 Total Invested: `{data['total_invested']:.2f}` SOL\n"
                f"   📊 Active Positions: `{len(data['positions'])}`"
            )
        
        lines.append(
            "\n\n💡 *How to use:*\n"
            "These wallets trade similar tokens as your top performers.\n"
            "Research them on DexScreener before adding to tracker."
        )
        
        message = "\n".join(lines)
        
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (truncated)"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Suggest command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def recent_cmd(update: Update, context, tracker: SpeedTracker):
    """Show 5 most recent tokens traded by a wallet with performance data"""
    try:
        if not context.args:
            await update.message.reply_text(
                "Usage: `/recent <wallet_address or label>`\n"
                "Example: `/recent LeBron`\n"
                "Example: `/recent G5nxEXuFS8...`",
                parse_mode='Markdown'
            )
            return
        
        query = ' '.join(context.args).strip()
        
        # Resolve wallet address from query
        wallet_address = None
        wallet_label = None
        
        # Check if it's a direct address match
        for w in tracker.wallets:
            if w['address'].lower() == query.lower():
                wallet_address = w['address']
                wallet_label = w['label']
                break
            # Check if it matches a label (exact or partial)
            if w['label'] and query.lower() in w['label'].lower():
                wallet_address = w['address']
                wallet_label = w['label']
                break
        
        if not wallet_address:
            await update.message.reply_text(
                f"❌ Wallet not found: `{query}`\n"
                f"Use wallet address or label from your tracking list.",
                parse_mode='Markdown'
            )
            return
        
        loading_msg = await update.message.reply_text(f"🔍 Loading recent trades for {wallet_label or wallet_address[:8]}...")
        
        # Get recent trades
        trades = await tracker.performance_tracker.get_recent_trades(wallet_address, limit=5)
        
        if not trades:
            await loading_msg.edit_text(
                f"📊 *{wallet_label or wallet_address[:8]}*\n"
                f"`{wallet_address}`\n\n"
                f"No recent trades found.",
                parse_mode='Markdown'
            )
            return
        
        # Build response
        display_name = wallet_label if wallet_label else wallet_address[:8] + "..."
        lines = [
            f"📊 *RECENT TRADES: {display_name}*",
            f"`{wallet_address}`\n",
            f"*Last {len(trades)} Tokens Traded:*\n"
        ]
        
        for i, trade in enumerate(trades, 1):
            token = trade['token']
            
            # Get token info
            token_info = await tracker.cluster_detector.get_token_info(token, use_cache=True)
            ticker = token_info.get('ticker', 'Unknown') if token_info else 'Unknown'
            
            # Format amounts
            if trade['total_bought'] >= 1_000_000:
                bought_str = f"{trade['total_bought']/1_000_000:.2f}M"
            elif trade['total_bought'] >= 1_000:
                bought_str = f"{trade['total_bought']/1_000:.1f}K"
            else:
                bought_str = f"{trade['total_bought']:.2f}"
            
            # PnL formatting
            pnl_emoji = "🟢" if trade['realized_pnl'] >= 0 else "🔴"
            pnl_str = f"{trade['realized_pnl']:+.2f}" if trade['total_sold'] > 0 else "--"
            roi_str = f"({trade['roi']:+.1f}%)" if trade['total_sold'] > 0 else ""
            
            # Entry MC
            if trade['avg_entry_mc'] >= 1_000_000:
                mc_str = f"${trade['avg_entry_mc']/1_000_000:.2f}M"
            elif trade['avg_entry_mc'] > 0:
                mc_str = f"${trade['avg_entry_mc']/1000:.1f}K"
            else:
                mc_str = "Unknown"
            
            lines.append(
                f"\n{i}. *{ticker}*\n"
                f"   `{token}`\n"
                f"   {trade['status']} ({trade['status_detail']})\n"
                f"   🪙 Bought: `{bought_str}` tokens | 💰 Invested: `{trade['sol_invested']:.2f}` SOL\n"
                f"   📍 Entry MC: `{mc_str}` | ⏱ Hold: `{trade['hold_time']}`\n"
                f"   {pnl_emoji} Realized PnL: `{pnl_str}` SOL {roi_str}"
            )
            
            # Add sold amount if applicable
            if trade['total_sold'] > 0:
                if trade['total_sold'] >= 1_000_000:
                    sold_str = f"{trade['total_sold']/1_000_000:.2f}M"
                elif trade['total_sold'] >= 1_000:
                    sold_str = f"{trade['total_sold']/1_000:.1f}K"
                else:
                    sold_str = f"{trade['total_sold']:.2f}"
                lines.append(f"   💸 Sold: `{sold_str}` tokens | Returned: `{trade['sol_returned']:.2f}` SOL")
            
            # Add remaining position if holding
            if trade['is_active'] and trade['net_position'] > 0.000001:
                if trade['net_position'] >= 1_000_000:
                    holding_str = f"{trade['net_position']/1_000_000:.2f}M"
                elif trade['net_position'] >= 1_000:
                    holding_str = f"{trade['net_position']/1_000:.1f}K"
                else:
                    holding_str = f"{trade['net_position']:.2f}"
                lines.append(f"   📦 Still Holding: `{holding_str}` tokens")
        
        message = "\n".join(lines)
        
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (truncated)"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Recent command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    if not Config.ADMIN_USERS:
        return False
    return user_id in Config.ADMIN_USERS


async def add_wallet_cmd(update: Update, context, tracker: SpeedTracker):
    """Add a new wallet to tracking (admin only)"""
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("⛔ This command is restricted to admin users.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/add \u003caddress\u003e [label]`\n"
                "Example: `/add G5nxEXuFS8PYvNQrhC1EFq3hmCpqkF86J7rWkEZDS7w5E LeBron`\n\n"
                "If no label is provided, a default one will be assigned.",
                parse_mode='Markdown'
            )
            return
        
        address = context.args[0].strip()
        label = ' '.join(context.args[1:]).strip() if len(context.args) > 1 else None
        
        success, message = tracker.add_wallet(address, label)
        
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"Add wallet command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def remove_wallet_cmd(update: Update, context, tracker: SpeedTracker):
    """Remove a wallet from tracking (admin only)"""
    try:
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("⛔ This command is restricted to admin users.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/remove \u003caddress or label\u003e`\n"
                "Example: `/remove LeBron`\n"
                "Example: `/remove G5nxEXuFS8...`\n\n"
                "You can use partial address or full label.",
                parse_mode='Markdown'
            )
            return
        
        query = ' '.join(context.args).strip()
        
        # Show confirmation for safety
        success, message = tracker.remove_wallet(query)
        
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"Remove wallet command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def main():
    tracker = SpeedTracker()
    signal.signal(signal.SIGTERM, tracker._signal_handler)
    signal.signal(signal.SIGINT, tracker._signal_handler)

    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", lambda u, c: status_cmd(u, c, tracker)))
    app.add_handler(CommandHandler("performance", lambda u, c: performance_cmd(u, c, tracker)))
    app.add_handler(CommandHandler("trackhold", lambda u, c: trackhold_cmd(u, c, tracker)))
    app.add_handler(CommandHandler("analyze", lambda u, c: analyze_token_cmd(u, c, tracker)))
    app.add_handler(CommandHandler("suggest", lambda u, c: suggest_wallets_cmd(u, c, tracker)))
    app.add_handler(CommandHandler("recent", lambda u, c: recent_cmd(u, c, tracker)))
    app.add_handler(CommandHandler("suggest", lambda u, c: suggest_wallets_cmd(u, c, tracker)))
    
    # Admin commands for wallet management
    app.add_handler(CommandHandler("add", lambda u, c: add_wallet_cmd(u, c, tracker)))
    app.add_handler(CommandHandler("remove", lambda u, c: remove_wallet_cmd(u, c, tracker)))
    
    # Callback handler for performance pagination
    app.add_handler(CallbackQueryHandler(lambda u, c: performance_callback(u, c, tracker), pattern="^perf:"))

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
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise
