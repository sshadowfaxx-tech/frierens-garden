#!/usr/bin/env python3
"""
ShadowHunter Missing Buy Backfill Script

This script identifies orphaned sell transactions (sells without corresponding buys)
and reconstructs the missing buy data by querying the Helius API for historical
transaction data.

Usage:
    python backfill_missing_buys.py [--dry-run] [--batch-size N] [--max-wallets N]

Features:
    - Async database operations with asyncpg
    - Rate-limited Helius API calls via aiohttp
    - Dry-run mode for safe testing
    - Batch processing with progress reporting
    - Idempotent (safe to re-run)
    - Resumable (tracks processed wallets)
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Set, Tuple
from pathlib import Path

import aiohttp
import asyncpg
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
HELIUS_RPC_URL = os.getenv('HELIUS_RPC_URL', 'https://mainnet.helius-rpc.com/')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'shadowhunter')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# Rate limiting
HELIUS_RATE_LIMIT = int(os.getenv('HELIUS_RATE_LIMIT', 10))  # requests per second
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 50))

# State file for resumability
STATE_FILE = Path('.backfill_state.json')

# Solana token program
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
NATIVE_SOL_MINT = "So11111111111111111111111111111111111111112"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class OrphanedSell:
    """Represents an orphaned sell transaction"""
    wallet_address: str
    token_address: str
    sell_signature: str
    sell_timestamp: datetime
    token_amount_sold: Decimal
    sol_received: Decimal


@dataclass
class ReconstructedBuy:
    """Represents a reconstructed buy transaction"""
    wallet_address: str
    token_address: str
    signature: str
    timestamp: datetime
    token_amount: Decimal
    sol_amount: Decimal
    slot: int
    source: str = "helius_backfill"


@dataclass
class BackfillStats:
    """Tracks backfill statistics"""
    total_wallets: int = 0
    wallets_processed: int = 0
    orphaned_sells_found: int = 0
    buys_reconstructed: int = 0
    buys_inserted: int = 0
    positions_updated: int = 0
    errors: int = 0
    skipped_already_processed: int = 0
    failed_wallets: List[str] = field(default_factory=list)
    
    def log_summary(self):
        """Log final statistics"""
        logger.info("=" * 60)
        logger.info("BACKFILL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total wallets scanned:      {self.total_wallets}")
        logger.info(f"Wallets successfully processed: {self.wallets_processed}")
        logger.info(f"Orphaned sells found:       {self.orphaned_sells_found}")
        logger.info(f"Buys reconstructed:         {self.buys_reconstructed}")
        logger.info(f"Buys inserted to DB:        {self.buys_inserted}")
        logger.info(f"Positions updated:          {self.positions_updated}")
        logger.info(f"Already processed (skipped): {self.skipped_already_processed}")
        logger.info(f"Errors encountered:         {self.errors}")
        if self.failed_wallets:
            logger.info(f"Failed wallets:             {len(self.failed_wallets)}")
            for wallet in self.failed_wallets[:10]:  # Show first 10
                logger.info(f"  - {wallet}")
        logger.info("=" * 60)


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

class Database:
    """Database operations for the backfill process"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create database connection pool"""
        self.pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Database connection established")
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")
    
    async def get_wallets_with_orphaned_sells(self) -> List[str]:
        """
        Find all unique wallet addresses that have orphaned sells.
        An orphaned sell is a sell where no buy exists for the same wallet+token.
        """
        query = """
        SELECT DISTINCT wt.wallet_address
        FROM wallet_trades wt
        WHERE wt.tx_type = 'sell'
          AND NOT EXISTS (
              SELECT 1 FROM wallet_trades wt2
              WHERE wt2.wallet_address = wt.wallet_address
                AND wt2.token_address = wt.token_address
                AND wt2.tx_type = 'buy'
          )
        ORDER BY wt.wallet_address
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [row['wallet_address'] for row in rows]
    
    async def get_orphaned_sells_for_wallet(
        self, 
        wallet_address: str
    ) -> List[OrphanedSell]:
        """
        Get all orphaned sells for a specific wallet.
        Groups by wallet+token to handle efficiently.
        """
        query = """
        SELECT 
            wt.wallet_address,
            wt.token_address,
            wt.signature,
            wt.timestamp,
            wt.token_amount,
            wt.sol_amount
        FROM wallet_trades wt
        WHERE wt.wallet_address = $1
          AND wt.tx_type = 'sell'
          AND NOT EXISTS (
              SELECT 1 FROM wallet_trades wt2
              WHERE wt2.wallet_address = wt.wallet_address
                AND wt2.token_address = wt.token_address
                AND wt2.tx_type = 'buy'
          )
        ORDER BY wt.token_address, wt.timestamp
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, wallet_address)
            return [
                OrphanedSell(
                    wallet_address=row['wallet_address'],
                    token_address=row['token_address'],
                    sell_signature=row['signature'],
                    sell_timestamp=row['timestamp'],
                    token_amount_sold=Decimal(str(row['token_amount'])),
                    sol_received=Decimal(str(row['sol_amount']))
                )
                for row in rows
            ]
    
    async def check_buy_exists(
        self,
        wallet_address: str,
        token_address: str,
        signature: str
    ) -> bool:
        """Check if a specific buy transaction already exists (idempotency)"""
        query = """
        SELECT 1 FROM wallet_trades
        WHERE wallet_address = $1
          AND token_address = $2
          AND signature = $3
          AND tx_type = 'buy'
        LIMIT 1
        """
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, wallet_address, token_address, signature)
            return result is not None
    
    async def insert_missing_buy(
        self,
        buy: ReconstructedBuy
    ) -> bool:
        """Insert a reconstructed buy into wallet_trades"""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would insert buy: {buy.signature[:20]}... "
                       f"for {buy.wallet_address[:8]}... token {buy.token_address[:8]}...")
            return True
        
        query = """
        INSERT INTO wallet_trades (
            wallet_address,
            token_address,
            tx_type,
            sol_amount,
            token_amount,
            timestamp,
            signature,
            source
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (signature) DO NOTHING
        RETURNING 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    query,
                    buy.wallet_address,
                    buy.token_address,
                    'buy',
                    float(buy.sol_amount),
                    float(buy.token_amount),
                    buy.timestamp,
                    buy.signature,
                    buy.source
                )
                return result is not None
        except Exception as e:
            logger.error(f"Failed to insert buy {buy.signature}: {e}")
            return False
    
    async def upsert_wallet_position(
        self,
        wallet_address: str,
        token_address: str,
        token_amount: Decimal,
        sol_spent: Decimal,
        timestamp: datetime
    ) -> bool:
        """
        Update or create wallet position based on reconstructed buy.
        Uses proper cost basis calculation.
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would upsert position for {wallet_address[:8]}... "
                       f"token {token_address[:8]}...")
            return True
        
        query = """
        INSERT INTO wallet_positions (
            wallet_address,
            token_address,
            net_position,
            total_bought,
            total_sol_invested,
            avg_entry_mc,
            first_buy_time
        ) VALUES (
            $1, $2, $3, $3, $4, $5, $6
        )
        ON CONFLICT (wallet_address, token_address) DO UPDATE SET
            net_position = wallet_positions.net_position + EXCLUDED.net_position,
            total_bought = wallet_positions.total_bought + EXCLUDED.total_bought,
            total_sol_invested = wallet_positions.total_sol_invested + EXCLUDED.total_sol_invested,
            avg_entry_mc = CASE 
                WHEN wallet_positions.total_bought + EXCLUDED.total_bought > 0 
                THEN (wallet_positions.total_sol_invested + EXCLUDED.total_sol_invested) 
                     / (wallet_positions.total_bought + EXCLUDED.total_bought)
                ELSE 0 
            END,
            first_buy_time = LEAST(wallet_positions.first_buy_time, EXCLUDED.first_buy_time)
        RETURNING 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                # Calculate rough market cap estimate (will be approximate)
                avg_entry_mc = sol_spent / token_amount if token_amount > 0 else Decimal('0')
                
                result = await conn.fetchval(
                    query,
                    wallet_address,
                    token_address,
                    float(token_amount),
                    float(sol_spent),
                    float(avg_entry_mc),
                    timestamp
                )
                return result is not None
        except Exception as e:
            logger.error(f"Failed to upsert position for {wallet_address}: {e}")
            return False


# ============================================================================
# HELIUS API OPERATIONS
# ============================================================================

class HeliusClient:
    """Helius API client with rate limiting"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or HELIUS_API_KEY
        if not self.api_key:
            raise ValueError("Helius API key is required. Set HELIUS_API_KEY in .env")
        
        self.rpc_url = f"{HELIUS_RPC_URL}?api-key={self.api_key}"
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(HELIUS_RATE_LIMIT)
        self._last_request_time = 0
        self._rate_limit_delay = 1.0 / HELIUS_RATE_LIMIT
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'Content-Type': 'application/json'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a rate-limited request to Helius RPC"""
        async with self._semaphore:
            # Rate limiting
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < self._rate_limit_delay:
                await asyncio.sleep(self._rate_limit_delay - time_since_last)
            
            try:
                async with self.session.post(self.rpc_url, json=payload) as response:
                    self._last_request_time = asyncio.get_event_loop().time()
                    
                    if response.status == 429:
                        logger.warning("Rate limited by Helius, backing off...")
                        await asyncio.sleep(2)
                        return None
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    if 'error' in data:
                        logger.error(f"Helius RPC error: {data['error']}")
                        return None
                    
                    return data
                    
            except aiohttp.ClientError as e:
                logger.error(f"Helius request failed: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error in Helius request: {e}")
                return None
    
    async def get_transaction_history(
        self,
        wallet_address: str,
        until: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get transaction history for a wallet"""
        # Helius uses getSignaturesForAddress for history
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                wallet_address,
                {
                    "limit": limit,
                    "before": until
                }
            ]
        }
        
        data = await self._make_request(payload)
        if not data or 'result' not in data:
            return []
        
        return data['result']
    
    async def get_transaction_details(
        self,
        signature: str,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Get detailed transaction data with retry logic"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                    "commitment": "confirmed"
                }
            ]
        }
        
        for attempt in range(max_retries):
            data = await self._make_request(payload)
            if data and 'result' in data:
                return data['result']
            
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
        
        return None
    
    async def get_token_accounts(
        self,
        wallet_address: str,
        token_address: str
    ) -> List[Dict[str, Any]]:
        """Get token accounts for a specific token owned by wallet"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {
                    "mint": token_address
                },
                {
                    "encoding": "jsonParsed"
                }
            ]
        }
        
        data = await self._make_request(payload)
        if not data or 'result' not in data or 'value' not in data['result']:
            return []
        
        return data['result']['value']
    
    async def get_token_supply(
        self,
        token_address: str
    ) -> Optional[int]:
        """Get token decimals to properly parse amounts"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenSupply",
            "params": [
                token_address,
                {"encoding": "jsonParsed"}
            ]
        }
        
        data = await self._make_request(payload)
        if data and 'result' in data and 'value' in data['result']:
            return data['result']['value'].get('decimals', 9)
        return None


# ============================================================================
# TRANSACTION PARSING
# ============================================================================

class TransactionParser:
    """Parse Helius transaction data to extract buy information"""
    
    @staticmethod
    def find_token_transfers(
        tx_data: Dict[str, Any],
        wallet_address: str,
        token_address: str
    ) -> Tuple[Decimal, Decimal]:
        """
        Find token transfers in a transaction.
        Returns (tokens_in, tokens_out) from perspective of wallet.
        """
        tokens_in = Decimal('0')
        tokens_out = Decimal('0')
        
        meta = tx_data.get('meta', {})
        pre_balances = {b['accountIndex']: b for b in meta.get('preTokenBalances', [])}
        post_balances = {b['accountIndex']: b for b in meta.get('postTokenBalances', [])}
        
        message = tx_data.get('transaction', {}).get('message', {})
        account_keys = message.get('accountKeys', [])
        
        # Find wallet's account index
        wallet_index = None
        for idx, acc in enumerate(account_keys):
            if isinstance(acc, dict):
                if acc.get('pubkey') == wallet_address:
                    wallet_index = idx
                    break
            elif acc == wallet_address:
                wallet_index = idx
                break
        
        if wallet_index is None:
            return tokens_in, tokens_out
        
        # Check token balance changes
        pre = pre_balances.get(wallet_index, {})
        post = post_balances.get(wallet_index, {})
        
        pre_amount = Decimal('0')
        post_amount = Decimal('0')
        
        if pre and pre.get('mint') == token_address:
            pre_amount = Decimal(pre['uiTokenAmount'].get('uiAmountString', '0'))
        if post and post.get('mint') == token_address:
            post_amount = Decimal(post['uiTokenAmount'].get('uiAmountString', '0'))
        
        change = post_amount - pre_amount
        
        if change > 0:
            tokens_in = change
        elif change < 0:
            tokens_out = abs(change)
        
        return tokens_in, tokens_out
    
    @staticmethod
    def find_sol_change(
        tx_data: Dict[str, Any],
        wallet_address: str
    ) -> Decimal:
        """
        Calculate SOL balance change for the wallet in this transaction.
        Positive = received SOL, Negative = spent SOL.
        """
        meta = tx_data.get('meta', {})
        pre_balances = meta.get('preBalances', [])
        post_balances = meta.get('postBalances', [])
        
        message = tx_data.get('transaction', {}).get('message', {})
        account_keys = message.get('accountKeys', [])
        
        # Find wallet index
        wallet_index = None
        for idx, acc in enumerate(account_keys):
            pubkey = acc.get('pubkey') if isinstance(acc, dict) else acc
            if pubkey == wallet_address:
                wallet_index = idx
                break
        
        if wallet_index is None or wallet_index >= len(pre_balances):
            return Decimal('0')
        
        # Calculate change in lamports
        pre_lamports = pre_balances[wallet_index]
        post_lamports = post_balances[wallet_index]
        
        # Convert to SOL
        change_sol = Decimal(post_lamports - pre_lamports) / Decimal(1e9)
        
        return -change_sol  # Invert: negative means spent SOL
    
    @staticmethod
    def is_buy_transaction(
        tx_data: Dict[str, Any],
        wallet_address: str,
        token_address: str
    ) -> Optional[ReconstructedBuy]:
        """
        Determine if a transaction is a buy for the specified token.
        Returns ReconstructedBuy if it is a buy, None otherwise.
        """
        tokens_in, tokens_out = TransactionParser.find_token_transfers(
            tx_data, wallet_address, token_address
        )
        
        # Buy = tokens received (in) and SOL spent
        if tokens_in <= 0:
            return None
        
        sol_change = TransactionParser.find_sol_change(tx_data, wallet_address)
        
        # For a buy, SOL should be spent (positive value after our inversion)
        if sol_change <= 0:
            # Might be a transfer receive, not a buy
            return None
        
        # Extract timestamp and signature
        block_time = tx_data.get('blockTime')
        if block_time:
            timestamp = datetime.fromtimestamp(block_time)
        else:
            timestamp = datetime.utcnow()
        
        signature = tx_data.get('transaction', {}).get('signatures', ['unknown'])[0]
        slot = tx_data.get('slot', 0)
        
        return ReconstructedBuy(
            wallet_address=wallet_address,
            token_address=token_address,
            signature=signature,
            timestamp=timestamp,
            token_amount=tokens_in,
            sol_amount=sol_change,
            slot=slot
        )


# ============================================================================
# BACKFILL ENGINE
# ============================================================================

class BackfillEngine:
    """Main engine for backfilling missing buy data"""
    
    def __init__(
        self,
        db: Database,
        helius: HeliusClient,
        dry_run: bool = False,
        batch_size: int = BATCH_SIZE
    ):
        self.db = db
        self.helius = helius
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.parser = TransactionParser()
        self.stats = BackfillStats()
        self.processed_wallets: Set[str] = self._load_state()
    
    def _load_state(self) -> Set[str]:
        """Load processed wallets from state file"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    return set(state.get('processed_wallets', []))
            except Exception as e:
                logger.warning(f"Could not load state file: {e}")
        return set()
    
    def _save_state(self):
        """Save processed wallets to state file"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    'processed_wallets': list(self.processed_wallets),
                    'last_run': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state file: {e}")
    
    async def process_wallet(self, wallet_address: str) -> bool:
        """
        Process all orphaned sells for a single wallet.
        Returns True on success, False on failure.
        """
        if wallet_address in self.processed_wallets:
            logger.debug(f"Skipping already processed wallet: {wallet_address[:8]}...")
            self.stats.skipped_already_processed += 1
            return True
        
        logger.info(f"Processing wallet: {wallet_address[:16]}...")
        
        try:
            # Get all orphaned sells for this wallet
            orphaned_sells = await self.db.get_orphaned_sells_for_wallet(wallet_address)
            
            if not orphaned_sells:
                logger.debug(f"No orphaned sells for wallet {wallet_address[:8]}...")
                self.processed_wallets.add(wallet_address)
                return True
            
            self.stats.orphaned_sells_found += len(orphaned_sells)
            
            # Group by token address
            sells_by_token: Dict[str, List[OrphanedSell]] = {}
            for sell in orphaned_sells:
                sells_by_token.setdefault(sell.token_address, []).append(sell)
            
            logger.info(f"Found {len(orphaned_sells)} orphaned sells across "
                       f"{len(sells_by_token)} tokens for wallet {wallet_address[:8]}...")
            
            # Process each token
            for token_address, sells in sells_by_token.items():
                success = await self._process_token_buys(
                    wallet_address, token_address, sells
                )
                if not success:
                    logger.warning(f"Failed to process buys for token {token_address[:8]}...")
            
            self.processed_wallets.add(wallet_address)
            self.stats.wallets_processed += 1
            return True
            
        except Exception as e:
            logger.error(f"Error processing wallet {wallet_address}: {e}")
            self.stats.errors += 1
            self.stats.failed_wallets.append(wallet_address)
            return False
    
    async def _process_token_buys(
        self,
        wallet_address: str,
        token_address: str,
        sells: List[OrphanedSell]
    ) -> bool:
        """
        Process and reconstruct buys for a specific wallet+token combination.
        Handles multiple buys and aggregates them.
        """
        logger.info(f"Processing {len(sells)} orphaned sells for token {token_address[:8]}...")
        
        # Find the earliest sell timestamp to limit our search
        earliest_sell = min(sells, key=lambda s: s.sell_timestamp)
        
        # Get transaction history for wallet
        tx_history = await self.helius.get_transaction_history(
            wallet_address,
            limit=1000  # Get substantial history
        )
        
        if not tx_history:
            logger.warning(f"No transaction history found for wallet {wallet_address[:8]}...")
            return False
        
        logger.info(f"Retrieved {len(tx_history)} transactions from history")
        
        # Track reconstructed buys
        reconstructed_buys: List[ReconstructedBuy] = []
        total_tokens_bought = Decimal('0')
        total_sol_spent = Decimal('0')
        
        # Process each transaction
        for tx_info in tx_history:
            signature = tx_info.get('signature')
            
            # Skip if this is one of the sell transactions
            if any(s.sell_signature == signature for s in sells):
                continue
            
            # Get full transaction details
            tx_details = await self.helius.get_transaction_details(signature)
            
            if not tx_details:
                continue
            
            # Check if this is a buy transaction
            buy = self.parser.is_buy_transaction(
                tx_details, wallet_address, token_address
            )
            
            if buy:
                logger.info(f"Found buy: {signature[:20]}... | "
                           f"{buy.token_amount} tokens for {buy.sol_amount:.6f} SOL")
                reconstructed_buys.append(buy)
                total_tokens_bought += buy.token_amount
                total_sol_spent += buy.sol_amount
                
                # Stop if we've found enough tokens to cover sells
                total_sold = sum(s.token_amount_sold for s in sells)
                if total_tokens_bought >= total_sold:
                    logger.info(f"Found sufficient buy volume ({total_tokens_bought} >= {total_sold})")
                    break
        
        if not reconstructed_buys:
            logger.warning(f"No buy transactions found for token {token_address[:8]}...")
            return False
        
        self.stats.buys_reconstructed += len(reconstructed_buys)
        
        # Insert reconstructed buys into database
        for buy in reconstructed_buys:
            # Check for idempotency
            exists = await self.db.check_buy_exists(
                buy.wallet_address, buy.token_address, buy.signature
            )
            
            if exists:
                logger.debug(f"Buy already exists: {buy.signature[:20]}...")
                continue
            
            # Insert the buy
            inserted = await self.db.insert_missing_buy(buy)
            if inserted:
                self.stats.buys_inserted += 1
        
        # Update wallet position
        position_updated = await self.db.upsert_wallet_position(
            wallet_address,
            token_address,
            total_tokens_bought,
            total_sol_spent,
            reconstructed_buys[0].timestamp
        )
        
        if position_updated:
            self.stats.positions_updated += 1
        
        logger.info(f"Successfully processed token {token_address[:8]}...: "
                   f"{len(reconstructed_buys)} buys, {total_tokens_bought} tokens, "
                   f"{total_sol_spent:.6f} SOL")
        
        return True
    
    async def run(self, max_wallets: Optional[int] = None):
        """Run the backfill process"""
        logger.info("=" * 60)
        logger.info("STARTING MISSING BUY BACKFILL")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info("=" * 60)
        
        # Get all wallets with orphaned sells
        wallets = await self.db.get_wallets_with_orphaned_sells()
        self.stats.total_wallets = len(wallets)
        
        if max_wallets:
            wallets = wallets[:max_wallets]
            logger.info(f"Limited to first {max_wallets} wallets")
        
        logger.info(f"Found {len(wallets)} wallets with orphaned sells")
        
        # Process wallets in batches
        for i in range(0, len(wallets), self.batch_size):
            batch = wallets[i:i + self.batch_size]
            logger.info(f"Processing batch {i//self.batch_size + 1}/"
                       f"{(len(wallets) + self.batch_size - 1)//self.batch_size}")
            
            for wallet in batch:
                await self.process_wallet(wallet)
                
                # Small delay between wallets to be nice to RPC
                await asyncio.sleep(0.1)
            
            # Save state after each batch
            self._save_state()
            logger.info(f"Progress: {self.stats.wallets_processed}/{self.stats.total_wallets} wallets")
        
        # Final save
        self._save_state()
        
        # Log summary
        self.stats.log_summary()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Backfill missing buy data for orphaned sells in ShadowHunter tracker'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making any changes'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help=f'Number of wallets to process in each batch (default: {BATCH_SIZE})'
    )
    parser.add_argument(
        '--max-wallets',
        type=int,
        default=None,
        help='Maximum number of wallets to process (default: all)'
    )
    parser.add_argument(
        '--reset-state',
        action='store_true',
        help='Clear the processed wallets state file and start fresh'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    
    return parser.parse_args()


async def main():
    """Main async entry point"""
    args = parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Reset state if requested
    if args.reset_state and STATE_FILE.exists():
        STATE_FILE.unlink()
        logger.info("State file cleared")
    
    # Validate environment
    if not HELIUS_API_KEY:
        logger.error("HELIUS_API_KEY not set in environment")
        sys.exit(1)
    
    # Initialize components
    db = Database(dry_run=args.dry_run)
    
    try:
        await db.connect()
        
        async with HeliusClient() as helius:
            engine = BackfillEngine(
                db=db,
                helius=helius,
                dry_run=args.dry_run,
                batch_size=args.batch_size
            )
            
            await engine.run(max_wallets=args.max_wallets)
            
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Progress saved to state file.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await db.close()


if __name__ == '__main__':
    asyncio.run(main())
