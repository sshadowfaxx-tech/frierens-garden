#!/usr/bin/env python3
"""
Smart Money Wallet Hunter for Solana
Searches for highly profitable wallets based on trading performance
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wallet_hunter")

# API Keys from environment
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY', '')

@dataclass
class WalletPerformance:
    address: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl_sol: float
    avg_trade_size: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    tokens_traded: List[str]
    last_active: datetime
    score: float  # Composite profitability score

class SmartMoneyHunter:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.helius_base = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
        self.birdeye_base = "https://public-api.birdeye.so"
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get token metadata and price info."""
        try:
            # Try Pump.fun API first (free, no key)
            url = f"https://frontend-api-v3.pump.fun/coins/{token_address}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        'name': data.get('name', 'Unknown'),
                        'symbol': data.get('symbol', '???'),
                        'market_cap': float(data.get('usd_market_cap', 0)),
                        'is_pump_fun': True,
                        'source': 'pump_fun'
                    }
        except Exception as e:
            logger.debug(f"Pump.fun fetch failed: {e}")
        
        # Fallback to Birdeye
        if BIRDEYE_API_KEY:
            try:
                url = f"{self.birdeye_base}/defi/token_info"
                headers = {
                    'X-API-KEY': BIRDEYE_API_KEY,
                    'x-chain': 'solana'
                }
                params = {'address': token_address}
                async with self.session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('success'):
                            token_data = data.get('data', {})
                            return {
                                'name': token_data.get('name', 'Unknown'),
                                'symbol': token_data.get('symbol', '???'),
                                'market_cap': float(token_data.get('mc', 0)),
                                'is_pump_fun': False,
                                'source': 'birdeye'
                            }
            except Exception as e:
                logger.debug(f"Birdeye fetch failed: {e}")
        
        return {
            'name': 'Unknown',
            'symbol': '???',
            'market_cap': 0,
            'is_pump_fun': False,
            'source': 'none'
        }
    
    async def get_wallet_transactions(self, wallet: str, days: int = 30) -> List[Dict]:
        """Fetch all token transactions for a wallet."""
        transactions = []
        
        try:
            # Use Helius to get transaction history
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    wallet,
                    {"limit": 100}  # Get last 100 transactions
                ]
            }
            
            async with self.session.post(self.helius_base, json=payload) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                signatures = data.get('result', [])
                
                # Fetch details for each transaction
                for sig_info in signatures:
                    sig = sig_info.get('signature')
                    if not sig:
                        continue
                    
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
                    }
                    
                    async with self.session.post(self.helius_base, json=tx_payload) as tx_resp:
                        if tx_resp.status == 200:
                            tx_data = await tx_resp.json()
                            tx = tx_data.get('result')
                            if tx:
                                transactions.append(self._parse_transaction(tx, wallet))
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
        
        return transactions
    
    def _parse_transaction(self, tx: Dict, wallet: str) -> Dict:
        """Parse transaction to extract token trade info."""
        meta = tx.get('meta', {})
        pre_balances = meta.get('preTokenBalances', [])
        post_balances = meta.get('postTokenBalances', [])
        
        # Find token changes for this wallet
        trades = []
        
        for pre in pre_balances:
            if pre.get('owner') == wallet:
                mint = pre.get('mint')
                pre_amount = float(pre.get('uiTokenAmount', {}).get('uiAmount', 0))
                
                # Find matching post balance
                post_amount = 0
                for post in post_balances:
                    if post.get('mint') == mint and post.get('owner') == wallet:
                        post_amount = float(post.get('uiTokenAmount', {}).get('uiAmount', 0))
                        break
                
                change = post_amount - pre_amount
                if abs(change) > 0:
                    trades.append({
                        'mint': mint,
                        'change': change,
                        'timestamp': tx.get('blockTime'),
                        'signature': tx.get('transaction', {}).get('signatures', [''])[0]
                    })
        
        return {
            'signature': tx.get('transaction', {}).get('signatures', [''])[0],
            'timestamp': tx.get('blockTime'),
            'trades': trades,
            'success': not meta.get('err')
        }
    
    def calculate_wallet_performance(self, wallet: str, transactions: List[Dict]) -> Optional[WalletPerformance]:
        """Calculate profitability metrics from transaction history."""
        if not transactions:
            return None
        
        # Track positions
        positions = defaultdict(lambda: {'buy_price': 0, 'buy_amount': 0, 'pnl': 0})
        total_pnl = 0
        winning_trades = 0
        losing_trades = 0
        largest_win = 0
        largest_loss = 0
        tokens_traded = set()
        
        # This is simplified - real PnL calculation would need historical prices
        # For now, we'll use a heuristic based on trade patterns
        
        for tx in transactions:
            for trade in tx.get('trades', []):
                mint = trade['mint']
                change = trade['change']
                tokens_traded.add(mint)
                
                # Simplified: assume buy if positive change, sell if negative
                # Real implementation would need price data at time of trade
                if change > 0:
                    # Buy - track position
                    positions[mint]['buy_amount'] += change
                else:
                    # Sell - calculate PnL (simplified)
                    sell_amount = abs(change)
                    position = positions[mint]
                    
                    if position['buy_amount'] > 0:
                        # Estimate PnL based on typical memecoin behavior
                        # This is a heuristic - would need real price data for accuracy
                        pnl_estimate = sell_amount * 0.1  # Placeholder
                        
                        total_pnl += pnl_estimate
                        
                        if pnl_estimate > 0:
                            winning_trades += 1
                            largest_win = max(largest_win, pnl_estimate)
                        else:
                            losing_trades += 1
                            largest_loss = min(largest_loss, pnl_estimate)
        
        total_trades = winning_trades + losing_trades
        if total_trades == 0:
            return None
        
        win_rate = winning_trades / total_trades
        
        # Calculate composite score
        # Factors: win rate, total PnL, consistency
        score = (win_rate * 40) + (min(total_pnl / 10, 30)) + (min(total_trades, 30))
        
        return WalletPerformance(
            address=wallet,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl_sol=total_pnl,
            avg_trade_size=0,  # Would need historical price data
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=winning_trades / max(losing_trades, 1),
            tokens_traded=list(tokens_traded),
            last_active=datetime.fromtimestamp(transactions[0].get('timestamp', 0)) if transactions[0].get('timestamp') else datetime.now(),
            score=score
        )
    
    async def discover_wallets_from_token(self, token_address: str) -> List[str]:
        """Discover wallets that traded a specific token."""
        wallets = set()
        
        try:
            # Use Helius to get recent transactions for the token
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [token_address, {"limit": 100}]
            }
            
            async with self.session.post(self.helius_base, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    signatures = data.get('result', [])
                    
                    for sig_info in signatures:
                        sig = sig_info.get('signature')
                        if not sig:
                            continue
                        
                        # Get transaction details
                        tx_payload = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getTransaction",
                            "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
                        }
                        
                        async with self.session.post(self.helius_base, json=tx_payload) as tx_resp:
                            if tx_resp.status == 200:
                                tx_data = await tx_resp.json()
                                tx = tx_data.get('result')
                                if tx:
                                    # Extract wallet addresses from transaction
                                    accounts = tx.get('transaction', {}).get('message', {}).get('accountKeys', [])
                                    for acc in accounts:
                                        if isinstance(acc, str) and len(acc) == 44:
                                            wallets.add(acc)
                                        elif isinstance(acc, dict):
                                            wallets.add(acc.get('pubkey', ''))
                        
                        await asyncio.sleep(0.05)
                        
        except Exception as e:
            logger.error(f"Error discovering wallets: {e}")
        
        return list(wallets)
    
    async def analyze_wallets(self, wallets: List[str]) -> List[WalletPerformance]:
        """Analyze multiple wallets and return sorted by profitability."""
        performances = []
        
        for wallet in wallets[:20]:  # Limit to 20 wallets per run (rate limits)
            try:
                logger.info(f"Analyzing wallet: {wallet[:10]}...")
                transactions = await self.get_wallet_transactions(wallet)
                
                if len(transactions) >= 3:  # Minimum activity threshold
                    performance = self.calculate_wallet_performance(wallet, transactions)
                    if performance and performance.total_trades >= 3:
                        performances.append(performance)
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error analyzing wallet {wallet}: {e}")
        
        # Sort by score (descending)
        performances.sort(key=lambda x: x.score, reverse=True)
        return performances
    
    async def hunt_profitable_wallets(self, 
                                       seed_token: Optional[str] = None,
                                       min_win_rate: float = 0.5,
                                       min_trades: int = 5,
                                       top_n: int = 10) -> Dict[str, Any]:
        """
        Main hunting function - find profitable wallets.
        
        Args:
            seed_token: Optional token address to start discovery from
            min_win_rate: Minimum win rate filter (0.0-1.0)
            min_trades: Minimum number of trades
            top_n: Return top N wallets
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'seed_token': seed_token,
            'wallets_found': 0,
            'wallets_analyzed': 0,
            'profitable_wallets': []
        }
        
        # Discover wallets
        if seed_token:
            logger.info(f"Discovering wallets from token: {seed_token[:15]}...")
            wallets = await self.discover_wallets_from_token(seed_token)
        else:
            # Use a list of known profitable tokens as seeds
            seed_tokens = [
                "So11111111111111111111111111111111111111112",  # SOL
                # Add more profitable memecoins here
            ]
            wallets = []
            for token in seed_tokens:
                token_wallets = await self.discover_wallets_from_token(token)
                wallets.extend(token_wallets)
                await asyncio.sleep(1)
        
        wallets = list(set(wallets))  # Deduplicate
        results['wallets_found'] = len(wallets)
        logger.info(f"Found {len(wallets)} unique wallets")
        
        # Analyze wallets
        performances = await self.analyze_wallets(wallets)
        results['wallets_analyzed'] = len(performances)
        
        # Filter and rank
        profitable = [
            p for p in performances 
            if p.win_rate >= min_win_rate and p.total_trades >= min_trades
        ]
        
        # Convert to dict for JSON serialization
        results['profitable_wallets'] = [
            {
                'address': p.address,
                'score': round(p.score, 2),
                'win_rate': round(p.win_rate * 100, 1),
                'total_trades': p.total_trades,
                'winning_trades': p.winning_trades,
                'losing_trades': p.losing_trades,
                'estimated_pnl_sol': round(p.total_pnl_sol, 4),
                'profit_factor': round(p.profit_factor, 2),
                'tokens_traded_count': len(p.tokens_traded),
                'last_active': p.last_active.isoformat()
            }
            for p in profitable[:top_n]
        ]
        
        return results


async def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Money Wallet Hunter for Solana')
    parser.add_argument('--seed', type=str, help='Seed token address to start discovery')
    parser.add_argument('--min-win-rate', type=float, default=0.5, help='Minimum win rate (0.0-1.0)')
    parser.add_argument('--min-trades', type=int, default=5, help='Minimum trades')
    parser.add_argument('--top', type=int, default=10, help='Top N wallets to return')
    parser.add_argument('--output', type=str, default='wallet_hunter_results.json', help='Output file')
    
    args = parser.parse_args()
    
    # Check for API keys
    if not HELIUS_API_KEY:
        print("⚠️  Warning: HELIUS_API_KEY not set. Set it in your environment for full functionality.")
    
    print("🚀 Starting Smart Money Wallet Hunter...")
    print(f"   Seed token: {args.seed or 'Default seeds'}")
    print(f"   Min win rate: {args.min_win_rate * 100}%")
    print(f"   Min trades: {args.min_trades}")
    print()
    
    async with SmartMoneyHunter() as hunter:
        results = await hunter.hunt_profitable_wallets(
            seed_token=args.seed,
            min_win_rate=args.min_win_rate,
            min_trades=args.min_trades,
            top_n=args.top
        )
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 HUNTING RESULTS")
    print("="*60)
    print(f"Total wallets found: {results['wallets_found']}")
    print(f"Wallets analyzed: {results['wallets_analyzed']}")
    print(f"Profitable wallets meeting criteria: {len(results['profitable_wallets'])}")
    print()
    
    if results['profitable_wallets']:
        print("🏆 TOP PROFITABLE WALLETS:")
        print("-" * 60)
        for i, wallet in enumerate(results['profitable_wallets'], 1):
            print(f"\n#{i} | Score: {wallet['score']}")
            print(f"   Address: {wallet['address']}")
            print(f"   Win Rate: {wallet['win_rate']}% ({wallet['winning_trades']}/{wallet['total_trades']})")
            print(f"   Est. PnL: {wallet['estimated_pnl_sol']} SOL")
            print(f"   Profit Factor: {wallet['profit_factor']}")
            print(f"   Tokens Traded: {wallet['tokens_traded_count']}")
    else:
        print("❌ No wallets met the profitability criteria")
    
    print(f"\n💾 Full results saved to: {args.output}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
