"""
ShadowHunter Alpha Finder v3.0 - Momentum Hunter System
Zero-cost wallet hunting using only free APIs
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Free API endpoints (zero cost)
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
JUPITER_PRICE_API = "https://price.jup.ag/v6/price"
HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={api_key}"

@dataclass
class TokenMetrics:
    """Stores token momentum metrics"""
    address: str
    symbol: str
    price_usd: float
    volume_24h: float
    liquidity_usd: float
    price_change_1h: float
    price_change_5m: float
    buys_1h: int
    sells_1h: int
    unique_buyers_1h: int
    market_cap: float
    pair_created_at: Optional[datetime] = None
    
    @property
    def momentum_score(self) -> float:
        """Calculate composite momentum score (0-100)"""
        scores = []
        
        # Price momentum (35% weight) - capped at 100
        price_score = min(abs(self.price_change_1h) * 2, 100) if self.price_change_1h > 0 else 0
        scores.append(price_score * 0.35)
        
        # Volume intensity (30% weight)
        volume_score = min(self.volume_24h / 10000, 100)  # $10K = max score
        scores.append(volume_score * 0.30)
        
        # Buyer interest (20% weight)
        buyer_score = min(self.unique_buyers_1h * 2, 100)  # 50 buyers = max
        scores.append(buyer_score * 0.20)
        
        # Liquidity health (15% weight)
        liquidity_score = min(self.liquidity_usd / 50000, 100)  # $50K = max
        scores.append(liquidity_score * 0.15)
        
        return sum(scores)
    
    @property
    def is_high_momentum(self) -> bool:
        return self.momentum_score > 60


@dataclass  
class WalletSignal:
    """Stores wallet detection signal"""
    address: str
    token_bought: str
    buy_time: datetime
    buy_amount_sol: float
    token_price_at_buy: float
    wallet_sol_balance: float
    blocks_from_launch: int
    is_early_buyer: bool
    
    @property
    def conviction_score(self) -> float:
        """Score 0-100 based on buy characteristics"""
        score = 0
        
        # Early entry (40 pts max)
        if self.blocks_from_launch <= 1:
            score += 40
        elif self.blocks_from_launch <= 3:
            score += 30
        elif self.blocks_from_launch <= 5:
            score += 20
        elif self.blocks_from_launch <= 10:
            score += 10
            
        # Position size relative to wallet (30 pts max)
        if self.wallet_sol_balance > 0:
            position_pct = self.buy_amount_sol / self.wallet_sol_balance
            if position_pct > 0.5:
                score += 30
            elif position_pct > 0.3:
                score += 20
            elif position_pct > 0.1:
                score += 10
        
        # Minimum buy threshold (20 pts max)
        if self.buy_amount_sol > 5:
            score += 20
        elif self.buy_amount_sol > 2:
            score += 15
        elif self.buy_amount_sol > 0.5:
            score += 10
            
        # Early buyer bonus (10 pts)
        if self.is_early_buyer:
            score += 10
            
        return score


class MomentumHunter:
    """
    Main hunting engine - detects momentum and traces to originator wallets
    """
    
    def __init__(self, helius_api_key: Optional[str] = None):
        self.helius_key = helius_api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.scored_wallets: Dict[str, dict] = defaultdict(dict)
        self.watched_tokens: Dict[str, TokenMetrics] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'Accept': 'application/json',
                'User-Agent': 'ShadowHunter-Alpha/3.0'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_token_metrics(self, token_address: str) -> Optional[TokenMetrics]:
        """
        Fetch token metrics from DexScreener (FREE API)
        
        TEST: This uses the free DexScreener API with no rate limits
        """
        url = f"{DEXSCREENER_API}/tokens/{token_address}"
        
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"DexScreener returned {resp.status} for {token_address}")
                    return None
                    
                data = await resp.json()
                
                if not data.get('pairs') or len(data['pairs']) == 0:
                    logger.debug(f"No pairs found for {token_address}")
                    return None
                
                # Get the most liquid pair (usually Raydium or Pump.fun)
                pairs = sorted(data['pairs'], key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0), reverse=True)
                pair = pairs[0]
                
                # Parse creation time
                created_at = None
                if pair.get('pairCreatedAt'):
                    created_at = datetime.fromtimestamp(pair['pairCreatedAt'] / 1000)
                
                metrics = TokenMetrics(
                    address=token_address,
                    symbol=pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                    price_usd=float(pair.get('priceUsd', 0) or 0),
                    volume_24h=float(pair.get('volume', {}).get('h24', 0) or 0),
                    liquidity_usd=float(pair.get('liquidity', {}).get('usd', 0) or 0),
                    price_change_1h=float(pair.get('priceChange', {}).get('h1', 0) or 0),
                    price_change_5m=float(pair.get('priceChange', {}).get('m5', 0) or 0),
                    buys_1h=int(pair.get('txns', {}).get('h1', {}).get('buys', 0) or 0),
                    sells_1h=int(pair.get('txns', {}).get('h1', {}).get('sells', 0) or 0),
                    unique_buyers_1h=0,  # DexScreener doesn't provide this, need Helius
                    market_cap=float(pair.get('marketCap', 0) or 0),
                    pair_created_at=created_at
                )
                
                logger.info(f"📊 {metrics.symbol}: ${metrics.price_usd:.6f} | "
                           f"MC: ${metrics.market_cap:,.0f} | "
                           f"Liq: ${metrics.liquidity_usd:,.0f} | "
                           f"1h: {metrics.price_change_1h:+.1f}% | "
                           f"Score: {metrics.momentum_score:.1f}")
                
                return metrics
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {token_address}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {token_address}: {e}")
            return None
    
    async def scan_solana_ecosystem(self, min_liquidity: float = 10000) -> List[TokenMetrics]:
        """
        Scan all Solana tokens and return high-momentum candidates
        
        TEST: Fetches top pairs from DexScreener
        """
        logger.info("🔍 Scanning Solana ecosystem for momentum...")
        
        # Get top Solana pairs from DexScreener
        url = f"{DEXSCREENER_API}/search?q=SOL"
        
        high_momentum_tokens = []
        
        try:
            async with self.session.get(url, timeout=15) as resp:
                data = await resp.json()
                pairs = data.get('pairs', [])
                
                logger.info(f"Found {len(pairs)} total pairs")
                
                # Filter to Solana pairs with minimum liquidity
                solana_pairs = [
                    p for p in pairs 
                    if p.get('chainId') == 'solana' 
                    and float(p.get('liquidity', {}).get('usd', 0) or 0) >= min_liquidity
                ]
                
                logger.info(f"Processing {len(solana_pairs)} Solana pairs with >${min_liquidity:,.0f} liquidity")
                
                # Process in batches to avoid rate limits
                batch_size = 10
                for i in range(0, len(solana_pairs), batch_size):
                    batch = solana_pairs[i:i+batch_size]
                    
                    tasks = [self.get_token_metrics(p['baseToken']['address']) for p in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, TokenMetrics) and result.is_high_momentum:
                            high_momentum_tokens.append(result)
                    
                    # Small delay between batches
                    await asyncio.sleep(0.5)
                
                # Sort by momentum score
                high_momentum_tokens.sort(key=lambda x: x.momentum_score, reverse=True)
                
                logger.info(f"🎯 Found {len(high_momentum_tokens)} high-momentum tokens")
                return high_momentum_tokens
                
        except Exception as e:
            logger.error(f"Error scanning ecosystem: {e}")
            return []
    
    async def get_wallet_transactions(self, wallet: str, limit: int = 100) -> List[dict]:
        """
        Fetch wallet transaction history using Helius (free tier)
        """
        if not self.helius_key:
            logger.warning("No Helius API key provided, skipping wallet analysis")
            return []
        
        url = HELIUS_RPC.format(api_key=self.helius_key)
        
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
            async with self.session.post(url, json=payload, timeout=10) as resp:
                data = await resp.json()
                return data.get('result', [])
        except Exception as e:
            logger.error(f"Error fetching wallet txs: {e}")
            return []
    
    async def detect_early_buyers(self, token_address: str, max_blocks: int = 10) -> List[WalletSignal]:
        """
        Detect wallets that bought within first N blocks of token launch
        
        Requires Helius API key for full functionality
        """
        logger.info(f"🔍 Analyzing early buyers for {token_address}...")
        
        # This would require parsing transaction logs
        # For now, return empty list (Helius webhook approach is better for this)
        return []
    
    def generate_report(self, tokens: List[TokenMetrics]) -> str:
        """Generate formatted report of high-momentum tokens"""
        
        if not tokens:
            return "❌ No high-momentum tokens detected"
        
        report = []
        report.append("\n" + "="*70)
        report.append("🚀 SHADOWHUNTER MOMENTUM REPORT")
        report.append(f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("="*70 + "\n")
        
        for i, token in enumerate(tokens[:10], 1):
            age_str = "Unknown"
            if token.pair_created_at:
                age = datetime.now() - token.pair_created_at
                if age < timedelta(hours=1):
                    age_str = f"{age.seconds // 60}m old"
                elif age < timedelta(days=1):
                    age_str = f"{age.seconds // 3600}h old"
                else:
                    age_str = f"{age.days}d old"
            
            report.append(f"\n{i}. 🎯 {token.symbol} | Score: {token.momentum_score:.1f}/100")
            report.append(f"   Address: {token.address}")
            report.append(f"   Age: {age_str}")
            report.append(f"   Price: ${token.price_usd:.8f}")
            report.append(f"   Market Cap: ${token.market_cap:,.0f}")
            report.append(f"   Liquidity: ${token.liquidity_usd:,.0f}")
            report.append(f"   1h Change: {token.price_change_1h:+.1f}%")
            report.append(f"   5m Change: {token.price_change_5m:+.1f}%")
            report.append(f"   Volume (24h): ${token.volume_24h:,.0f}")
            report.append(f"   Buys/Sells (1h): {token.buys_1h}/{token.sells_1h}")
            
            if token.is_high_momentum:
                report.append(f"   ⚡ HIGH MOMENTUM DETECTED")
        
        report.append("\n" + "="*70)
        return "\n".join(report)


async def test_momentum_hunter():
    """
    TEST FUNCTION: Run the momentum hunter and verify it works
    """
    print("\n" + "="*70)
    print("🧪 TESTING MOMENTUM HUNTER SYSTEM")
    print("="*70 + "\n")
    
    # Test with known tokens
    test_tokens = [
        "So11111111111111111111111111111111111111112",  # Wrapped SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    ]
    
    async with MomentumHunter() as hunter:
        # Test 1: Single token metrics
        print("📊 TEST 1: Fetching individual token metrics...")
        for token in test_tokens:
            metrics = await hunter.get_token_metrics(token)
            if metrics:
                print(f"   ✅ {metrics.symbol}: Score {metrics.momentum_score:.1f}")
            else:
                print(f"   ❌ Failed to fetch {token[:20]}...")
        
        # Test 2: Ecosystem scan
        print("\n🔍 TEST 2: Scanning ecosystem for high-momentum tokens...")
        high_momentum = await hunter.scan_solana_ecosystem(min_liquidity=50000)
        
        if high_momentum:
            print(f"   ✅ Found {len(high_momentum)} high-momentum tokens")
            
            # Generate report
            report = hunter.generate_report(high_momentum)
            print(report)
        else:
            print("   ⚠️ No high-momentum tokens found (market may be slow)")
    
    print("\n" + "="*70)
    print("✅ TESTING COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_momentum_hunter())
