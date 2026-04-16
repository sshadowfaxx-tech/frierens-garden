#!/usr/bin/env python3
"""
Smart Money Wallet Hunter for Solana
Integrates DexCheck (top traders + early birds) + Helius (deep analysis)
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wallet_hunter")

# API Configuration
HELIUS_RPC_URL = "https://beta.helius-rpc.com/?api-key=1030a4da-93a6-4d2a-af5e-9ec3f4ce4a8c"
DEXCHECK_API_KEY = "BostDZLJBBPu44iXpiOneGprXhTpSFCg"
DEXCHECK_BASE = "https://api.dexcheck.ai"

@dataclass
class WalletProfile:
    address: str
    wallet_type: str  # 'consistent_winner', 'early_sniper', 'hybrid'
    pattern_type: str  # 'diamond_hand', 'active_trader', 'dumped', etc.
    buy_count: int
    sell_count: int
    dexcheck_score: float
    win_rate: float
    total_trades: int
    realized_pnl: float
    unrealized_pnl: float
    roi_percentage: float
    avg_trade_size: float
    early_entry_rank: Optional[int] = None
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    helius_verified: bool = False
    total_transactions: int = 0
    sol_balance: float = 0.0
    tokens_traded: List[str] = None
    last_active: str = ""
    
    def __post_init__(self):
        if self.tokens_traded is None:
            self.tokens_traded = []

class DexCheckClient:
    """DexCheck API client for top traders and early birds."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.dexcheck.ai"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"X-API-Key": self.api_key}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_top_traders(self, chain: str, pair_id: str, limit: int = 50) -> List[Dict]:
        """Get top profitable traders for a token pair.
        
        Note: pair_id is typically the pool/pair address, not token address
        """
        url = f"{self.base_url}/api/v1/blockchain/top-traders-for-pair"
        params = {
            "chain": chain,
            "pair_id": pair_id,
            "duration": "30d",  # Required parameter
            "limit": limit
        }
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Handle both list and dict responses
                    if isinstance(data, list):
                        return data
                    return data.get("traders", [])
                else:
                    text = await resp.text()
                    logger.error(f"DexCheck top traders error: {resp.status} - {text}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching top traders: {e}")
            return []
    
    async def get_early_birds(self, chain: str, pair_address: str, limit: int = 50) -> List[Dict]:
        """Get early buyers (snipers) for a token pair.
        
        Note: pair_address is the pool/pair address
        """
        url = f"{self.base_url}/api/v1/blockchain/early-birds"
        params = {
            "chain": chain,
            "pair": pair_address,
            "limit": limit
        }
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Handle both list and dict responses
                    if isinstance(data, list):
                        return data
                    # DexCheck early-birds returns {success: true, data: [...]}
                    if isinstance(data, dict):
                        return data.get("data", [])
                    return []
                else:
                    text = await resp.text()
                    logger.error(f"DexCheck early birds error: {resp.status} - {text}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching early birds: {e}")
            return []

class HeliusClient:
    """Helius RPC client for deep wallet analysis."""
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_wallet_balance(self, wallet: str) -> float:
        """Get SOL balance for a wallet."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet]
        }
        
        try:
            async with self.session.post(self.rpc_url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("result", {})
                    lamports = result.get("value", 0)
                    return lamports / 1e9  # Convert to SOL
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
        
        return 0.0
    
    async def get_transaction_history(self, wallet: str, limit: int = 100) -> List[Dict]:
        """Get transaction signatures for a wallet."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": limit}]
        }
        
        try:
            async with self.session.post(self.rpc_url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("result", [])
        except Exception as e:
            logger.error(f"Error fetching signatures: {e}")
        
        return []
    
    async def get_transaction_details(self, signature: str) -> Optional[Dict]:
        """Get full transaction details."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        }
        
        try:
            async with self.session.post(self.rpc_url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("result")
        except Exception as e:
            logger.error(f"Error fetching transaction: {e}")
        
        return None

class SmartMoneyHunter:
    """Main wallet hunter that combines DexCheck + Helius."""
    
    def __init__(self):
        self.dexcheck: Optional[DexCheckClient] = None
        self.helius: Optional[HeliusClient] = None
    
    async def __aenter__(self):
        self.dexcheck = await DexCheckClient(DEXCHECK_API_KEY).__aenter__()
        self.helius = await HeliusClient(HELIUS_RPC_URL).__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.dexcheck:
            await self.dexcheck.__aexit__(exc_type, exc_val, exc_tb)
        if self.helius:
            await self.helius.__aexit__(exc_type, exc_val, exc_tb)
    
    async def hunt_wallets(self, 
                          token_address: str, 
                          chain: str = "solana",
                          min_win_rate: float = 0.5,
                          top_n: int = 20) -> Dict[str, Any]:
        """
        Main hunting function.
        
        Returns:
            Dictionary with top traders, early birds, and hybrid wallets
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "token_address": token_address,
            "chain": chain,
            "top_traders": [],
            "early_birds": [],
            "hybrid_wallets": [],  # Wallets in both lists
            "detailed_profiles": []
        }
        
        logger.info(f"🔍 Hunting wallets for token: {token_address[:15]}...")
        
        # Phase 1: Get top traders from DexCheck
        logger.info("📊 Fetching top traders...")
        top_traders = await self.dexcheck.get_top_traders(chain, token_address, limit=50)
        results["top_traders"] = top_traders
        logger.info(f"   Found {len(top_traders)} top traders")
        
        # Phase 2: Get early birds from DexCheck
        logger.info("🐣 Fetching early birds...")
        early_birds = await self.dexcheck.get_early_birds(chain, token_address, limit=50)
        results["early_birds"] = early_birds
        logger.info(f"   Found {len(early_birds)} early birds")
        
        # Phase 3: Find hybrid wallets (in both lists)
        trader_addresses = {t.get("address") for t in top_traders}
        early_bird_addresses = {e.get("address") for e in early_birds}
        hybrid_addresses = trader_addresses & early_bird_addresses
        
        results["hybrid_wallets"] = list(hybrid_addresses)
        logger.info(f"   Found {len(hybrid_addresses)} hybrid wallets (in both lists)")
        
        # Phase 4: Build detailed profiles for best wallets
        logger.info("🔬 Building detailed profiles...")
        
        # Priority: Hybrids first, then top traders, then early birds
        wallets_to_analyze = list(hybrid_addresses)[:10]
        
        # Add top traders not already included
        for trader in top_traders[:15]:
            addr = trader.get("address")
            if addr and addr not in wallets_to_analyze and len(wallets_to_analyze) < 20:
                wallets_to_analyze.append(addr)
        
        # Add early birds not already included
        for bird in early_birds[:10]:
            # DexCheck uses "maker" for wallet address in early-birds
            addr = bird.get("maker") or bird.get("address")
            if addr and addr not in wallets_to_analyze and len(wallets_to_analyze) < 25:
                wallets_to_analyze.append(addr)
        
        # Build profiles
        profiles = []
        for address in wallets_to_analyze:
            profile = await self._build_wallet_profile(
                address, 
                top_traders, 
                early_birds,
                hybrid_addresses
            )
            if profile:
                profiles.append(profile)
            await asyncio.sleep(0.5)  # Rate limiting
        
        # Sort by composite score
        profiles.sort(key=lambda x: x.dexcheck_score, reverse=True)
        results["detailed_profiles"] = [asdict(p) for p in profiles[:top_n]]
        
        return results
    
    def _analyze_buy_sell_pattern(self, trader_data: Dict, early_data: Dict) -> tuple:
        """
        Analyze buy/sell pattern to filter wallets.
        
        Returns: (should_include, pattern_type, reason)
        - should_include: True if wallet should be kept
        - pattern_type: 'diamond_hand', 'active_trader', 'dumped', etc.
        - reason: Explanation for filtering decision
        """
        # Get trade counts
        buy_count = trader_data.get('buyCount', 0) or early_data.get('buyCount', 0)
        sell_count = trader_data.get('sellCount', 0) or early_data.get('sellCount', 0)
        
        # Calculate from total trades if buy/sell counts not available
        total_trades = trader_data.get('totalTrades', 0)
        if total_trades > 0 and buy_count == 0 and sell_count == 0:
            # Estimate from win rate - rough heuristic
            win_rate = trader_data.get('winRate', 50) / 100
            buy_count = int(total_trades * 0.6)  # Assume 60% buys
            sell_count = total_trades - buy_count
        
        # Filter: Ignore wallets with sells but no buys (dumpers)
        if sell_count > 0 and buy_count == 0:
            return (False, 'seller_only', f'Only sells ({sell_count} sells, 0 buys) - likely dumper')
        
        # Highlight: Early birds with buys but no sells (diamond hands)
        if buy_count > 0 and sell_count == 0:
            return (True, 'diamond_hand', f'Only buys ({buy_count} buys, 0 sells) - diamond hands 🎯')
        
        # Active traders with both buys and sells
        if buy_count > 0 and sell_count > 0:
            return (True, 'active_trader', f'Active trading ({buy_count} buys, {sell_count} sells)')
        
        # Default case
        return (True, 'unknown', 'Pattern unclear')
    
    async def _build_wallet_profile(self, 
                                   address: str,
                                   top_traders: List[Dict],
                                   early_birds: List[Dict],
                                   hybrid_addresses: Set[str]) -> Optional[WalletProfile]:
        """Build a comprehensive profile for a wallet."""
        
        # Find data in DexCheck results
        # Top traders uses "address"
        trader_data = next((t for t in top_traders if t.get("address") == address), {})
        # Early birds uses "maker"
        early_data = next((e for e in early_birds if e.get("maker") == address or e.get("address") == address), {})
        
        if not trader_data and not early_data:
            return None
        
        # Analyze buy/sell pattern using DexCheck fields
        # Early birds: buy_trade_count, sell_trade_count, status
        buy_count = early_data.get('buy_trade_count', 0) or trader_data.get('buyCount', 0)
        sell_count = early_data.get('sell_trade_count', 0) or trader_data.get('sellCount', 0)
        
        # Filter: Ignore wallets with sells but no buys (dumpers)
        if sell_count > 0 and buy_count == 0:
            logger.debug(f"Filtering out {address[:15]}... - Only sells ({sell_count} sells, 0 buys)")
            return None
        
        # Determine pattern type
        is_diamond_hand = buy_count > 0 and sell_count == 0
        pattern_type = 'diamond_hand' if is_diamond_hand else 'active_trader'
        
        # Determine wallet type with highlighting for diamond hands
        if address in hybrid_addresses:
            if is_diamond_hand:
                wallet_type = "💎🔥 DIAMOND HYBRID (Early + Holder + Winner)"
            else:
                wallet_type = "🔥 HYBRID (Top Trader + Early Sniper)"
        elif is_diamond_hand and early_data:
            wallet_type = "💎 DIAMOND EARLY BIRD (HODLing)"
        elif is_diamond_hand:
            wallet_type = "💎 DIAMOND HAND (HODLing)"
        elif trader_data:
            wallet_type = "📈 Consistent Winner"
        else:
            wallet_type = "🚀 Early Sniper"
        
        # Get Helius data
        sol_balance = await self.helius.get_wallet_balance(address)
        tx_history = await self.helius.get_transaction_history(address, limit=50)
        
        # Extract values from DexCheck data
        # Early birds: pnl, unrealized_pnl, roi, unrealized_roi
        realized_pnl = early_data.get('pnl', 0) or trader_data.get('realizedPnl', 0)
        unrealized_pnl = early_data.get('unrealized_pnl', 0) or trader_data.get('unrealizedPnl', 0)
        roi_percentage = early_data.get('roi', 0) or early_data.get('unrealized_roi', 0) or trader_data.get('roiPercentage', 0)
        
        # Build profile
        profile = WalletProfile(
            address=address,
            wallet_type=wallet_type,
            pattern_type=pattern_type,
            buy_count=buy_count,
            sell_count=sell_count,
            dexcheck_score=trader_data.get("score", 50),
            win_rate=trader_data.get("winRate", 0),
            total_trades=buy_count + sell_count,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            roi_percentage=roi_percentage,
            avg_trade_size=trader_data.get("avgTradeSize", 0),
            early_entry_rank=None,
            entry_price=early_data.get("buy_avg_price"),
            current_price=None,
            helius_verified=len(tx_history) > 0,
            total_transactions=len(tx_history),
            sol_balance=sol_balance,
            last_active=tx_history[0].get("blockTime", "") if tx_history else ""
        )
        
        return profile

async def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Money Wallet Hunter')
    parser.add_argument('token', type=str, help='Token address to analyze')
    parser.add_argument('--chain', type=str, default='solana', help='Blockchain (default: solana)')
    parser.add_argument('--top', type=int, default=20, help='Top N wallets to return')
    parser.add_argument('--output', type=str, default='wallet_hunt_results.json', help='Output file')
    
    args = parser.parse_args()
    
    print("🚀 Smart Money Wallet Hunter")
    print("=" * 60)
    print(f"Token: {args.token}")
    print(f"Chain: {args.chain}")
    print()
    
    async with SmartMoneyHunter() as hunter:
        results = await hunter.hunt_wallets(
            token_address=args.token,
            chain=args.chain,
            top_n=args.top
        )
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 HUNTING RESULTS")
    print("=" * 60)
    print(f"Top Traders Found: {len(results['top_traders'])}")
    print(f"Early Birds Found: {len(results['early_birds'])}")
    print(f"Hybrid Wallets: {len(results['hybrid_wallets'])}")
    print()
    
    if results['detailed_profiles']:
        # Count diamond hands vs others
        diamond_hands = [w for w in results['detailed_profiles'] if 'diamond' in w['wallet_type'].lower()]
        filtered_out = len(results['top_traders']) + len(results['early_birds']) - len(set([w['address'] for w in results['detailed_profiles']]))
        
        print("🏆 TOP WALLETS TO FOLLOW:")
        print("-" * 60)
        print(f"💎 Diamond Hands Found: {len(diamond_hands)} | 🗑️ Dumpers Filtered: {filtered_out}")
        print()
        
        for i, wallet in enumerate(results['detailed_profiles'][:10], 1):
            # Highlight diamond hands with emoji
            is_diamond = 'diamond' in wallet['wallet_type'].lower()
            highlight = "✨ " if is_diamond else "   "
            
            print(f"{highlight}#{i} | {wallet['wallet_type']}")
            print(f"      Address: {wallet['address']}")
            print(f"      Trades: {wallet['buy_count']} buys / {wallet['sell_count']} sells", end="")
            if wallet['buy_count'] > 0 and wallet['sell_count'] == 0:
                print(" 💎 HODLing")
            else:
                print()
            print(f"      Score: {wallet['dexcheck_score']:.1f} | Win Rate: {wallet['win_rate']:.1f}% | ROI: {wallet['roi_percentage']:.1f}%")
            print(f"      Realized PnL: {wallet['realized_pnl']:.4f} SOL")
            if wallet['early_entry_rank']:
                print(f"      Early Entry Rank: #{wallet['early_entry_rank']}")
            print(f"      SOL Balance: {wallet['sol_balance']:.4f}")
            print()
    else:
        print("❌ No profitable wallets found")
    
    print(f"\n💾 Full results saved to: {args.output}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
