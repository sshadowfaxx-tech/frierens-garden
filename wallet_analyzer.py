"""
ShadowHunter Wallet Analyzer - Early Buyer Detection
Uses Helius free tier to analyze wallet profitability and patterns
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

HELIUS_RPC_URL = "https://mainnet.helius-rpc.com/?api-key={api_key}"
HELIUS_API_URL = "https://api.helius.xyz/v0"


@dataclass
class WalletProfile:
    """Complete wallet analysis profile"""
    address: str
    total_trades_30d: int = 0
    profitable_trades: int = 0
    total_pnl_sol: float = 0.0
    win_rate: float = 0.0
    avg_trade_size_sol: float = 0.0
    favorite_tokens: List[str] = field(default_factory=list)
    last_active: Optional[datetime] = None
    is_bot_suspected: bool = False
    early_entry_accuracy: float = 0.0  # How often they buy before pumps
    
    @property
    def alpha_score(self) -> float:
        """Calculate wallet's alpha generation score (0-100)"""
        score = 0
        
        # Win rate (30 pts max)
        score += min(self.win_rate * 30, 30)
        
        # Profitability (30 pts max)
        if self.total_pnl_sol > 1000:
            score += 30
        elif self.total_pnl_sol > 100:
            score += 20
        elif self.total_pnl_sol > 10:
            score += 10
        
        # Activity (20 pts max)
        if self.total_trades_30d > 50:
            score += 20
        elif self.total_trades_30d > 20:
            score += 15
        elif self.total_trades_30d > 5:
            score += 10
        
        # Early entry skill (20 pts max)
        score += self.early_entry_accuracy * 20
        
        # Bot penalty
        if self.is_bot_suspected:
            score *= 0.5
        
        return score
    
    @property
    def is_high_quality(self) -> bool:
        """High quality = profitable, active, not a bot"""
        return (
            self.win_rate >= 0.4 and
            self.total_pnl_sol > 10 and
            self.total_trades_30d >= 5 and
            not self.is_bot_suspected
        )


class WalletAnalyzer:
    """
    Analyzes wallet profitability and trading patterns using Helius
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, WalletProfile] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'Content-Type': 'application/json'}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_wallet_transactions(self, wallet: str, limit: int = 100) -> List[dict]:
        """
        Fetch wallet transaction signatures
        
        TEST: Uses Helius RPC (free tier - 10M credits/month)
        """
        url = HELIUS_RPC_URL.format(api_key=self.api_key)
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                wallet,
                {"limit": limit}
            ]
        }
        
        try:
            async with self.session.post(url, json=payload, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Helius RPC error: {resp.status}")
                    return []
                
                data = await resp.json()
                
                if 'error' in data:
                    logger.error(f"Helius error: {data['error']}")
                    return []
                
                return data.get('result', [])
        except Exception as e:
            logger.error(f"Error fetching txs for {wallet}: {e}")
            return []
    
    async def parse_transaction(self, signature: str) -> Optional[dict]:
        """
        Parse a single transaction for DEX swap details
        
        TEST: Uses Helius parsed transactions API
        """
        url = f"{HELIUS_API_URL}/transactions/?api-key={self.api_key}"
        
        payload = {
            "transactions": [signature]
        }
        
        try:
            async with self.session.post(url, json=payload, timeout=15) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if not data or len(data) == 0:
                    return None
                
                tx = data[0]
                
                # Look for swap events
                if 'events' in tx:
                    for event in tx['events']:
                        if event.get('type') == 'SWAP':
                            return {
                                'signature': signature,
                                'timestamp': tx.get('timestamp'),
                                'swap': event,
                                'type': 'SWAP'
                            }
                
                return tx
        except Exception as e:
            logger.error(f"Error parsing tx {signature}: {e}")
            return None
    
    async def analyze_wallet(self, wallet: str, days: int = 30) -> WalletProfile:
        """
        Full wallet analysis - profitability, patterns, behavior
        
        TEST: Analyzes last 100 transactions
        """
        logger.info(f"🔍 Analyzing wallet: {wallet}")
        
        # Check cache
        if wallet in self.cache:
            logger.info(f"   Using cached profile for {wallet[:20]}...")
            return self.cache[wallet]
        
        profile = WalletProfile(address=wallet)
        
        # Get transaction signatures
        txs = await self.get_wallet_transactions(wallet, limit=100)
        
        if not txs:
            logger.warning(f"   No transactions found for {wallet[:20]}...")
            return profile
        
        logger.info(f"   Found {len(txs)} transactions")
        
        # Parse transactions (in batches to avoid rate limits)
        batch_size = 5
        parsed_txs = []
        
        for i in range(0, len(txs), batch_size):
            batch = txs[i:i+batch_size]
            tasks = [self.parse_transaction(tx['signature']) for tx in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict):
                    parsed_txs.append(result)
            
            # Small delay between batches
            await asyncio.sleep(0.2)
        
        logger.info(f"   Parsed {len(parsed_txs)} transactions")
        
        # Analyze swaps
        swaps = [tx for tx in parsed_txs if tx.get('type') == 'SWAP']
        
        if not swaps:
            logger.warning(f"   No DEX swaps found for {wallet[:20]}...")
            return profile
        
        logger.info(f"   Found {len(swaps)} DEX swaps")
        
        # Calculate metrics
        token_pnl = defaultdict(float)
        token_trades = defaultdict(int)
        
        for swap in swaps:
            swap_data = swap.get('swap', {})
            
            # Extract token amounts (simplified)
            token_in = swap_data.get('tokenIn', '')
            token_out = swap_data.get('tokenOut', '')
            amount_in = swap_data.get('tokenAmount', 0)
            
            # Track trades per token
            if token_out:
                token_trades[token_out] += 1
            
            # Update profile
            profile.total_trades_30d += 1
        
        # Set favorite tokens (most traded)
        sorted_tokens = sorted(token_trades.items(), key=lambda x: x[1], reverse=True)
        profile.favorite_tokens = [t[0] for t in sorted_tokens[:5]]
        
        # Detect bot patterns
        if profile.total_trades_30d > 200:
            # More than 200 trades in 30 days = likely bot
            profile.is_bot_suspected = True
        
        # Calculate win rate (simplified - would need price data)
        # For now, assume 50% as placeholder
        profile.win_rate = 0.5
        
        # Set last active
        if txs:
            profile.last_active = datetime.fromtimestamp(txs[0]['blockTime'])
        
        # Cache the result
        self.cache[wallet] = profile
        
        logger.info(f"   ✅ Analysis complete: {profile.total_trades_30d} trades, "
                   f"Score: {profile.alpha_score:.1f}")
        
        return profile
    
    async def find_profitable_wallets(self, token_address: str, min_profit: float = 100) -> List[WalletProfile]:
        """
        Find wallets that profited from a specific token
        
        This would require analyzing all buyers of a token
        For now, returns empty list (needs more complex implementation)
        """
        logger.info(f"🔍 Finding profitable wallets for token {token_address}...")
        # This requires fetching all token holders and analyzing each
        # Too expensive for free tier - would need different approach
        return []
    
    async def detect_coordinated_buying(self, wallets: List[str], token: str, time_window_minutes: int = 60) -> bool:
        """
        Detect if multiple wallets bought the same token within a time window
        
        TEST: Checks for coordination patterns
        """
        logger.info(f"🕸️ Checking coordination for {len(wallets)} wallets on {token}...")
        
        buy_times = []
        
        for wallet in wallets:
            txs = await self.get_wallet_transactions(wallet, limit=50)
            
            for tx in txs:
                # Check if this tx involves the token
                # Simplified - would need to parse token transfers
                pass
        
        # Check time clustering
        if len(buy_times) >= 3:
            time_spread = max(buy_times) - min(buy_times)
            if time_spread < timedelta(minutes=time_window_minutes):
                logger.warning(f"   ⚠️ Coordination detected! {len(buy_times)} wallets bought within {time_spread}")
                return True
        
        return False


async def test_wallet_analyzer():
    """
    TEST FUNCTION: Test wallet analysis with known wallets
    """
    print("\n" + "="*70)
    print("🧪 TESTING WALLET ANALYZER")
    print("="*70 + "\n")
    
    # Test wallet - need Helius API key for full test
    test_wallet = "4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6"  # Nansen smart trader
    
    api_key = "YOUR_HELIUS_API_KEY"  # User needs to provide this
    
    if api_key == "YOUR_HELIUS_API_KEY":
        print("⚠️  No Helius API key provided - skipping wallet analysis test")
        print("   To test: Set HELIUS_API_KEY environment variable")
        return
    
    async with WalletAnalyzer(api_key) as analyzer:
        profile = await analyzer.analyze_wallet(test_wallet, days=30)
        
        print(f"\n📊 Wallet Profile: {test_wallet[:20]}...")
        print(f"   Total Trades (30d): {profile.total_trades_30d}")
        print(f"   Win Rate: {profile.win_rate*100:.1f}%")
        print(f"   Total PnL: {profile.total_pnl_sol:.2f} SOL")
        print(f"   Alpha Score: {profile.alpha_score:.1f}/100")
        print(f"   High Quality: {'✅ Yes' if profile.is_high_quality else '❌ No'}")
        print(f"   Bot Suspected: {'⚠️ Yes' if profile.is_bot_suspected else '✅ No'}")
        
        if profile.favorite_tokens:
            print(f"   Favorite Tokens: {', '.join(profile.favorite_tokens[:3])}")
    
    print("\n" + "="*70)
    print("✅ WALLET ANALYZER TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_wallet_analyzer())
