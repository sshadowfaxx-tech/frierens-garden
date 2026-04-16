#!/usr/bin/env python3
"""
ShadowHunter Alpha Finder - Main Entry Point
Zero-cost programmatic wallet hunting system

Usage:
    python3 hunter_main.py scan              # One-time ecosystem scan
    python3 hunter_main.py monitor           # Continuous monitoring
    python3 hunter_main.py analyze <wallet>  # Analyze specific wallet
    python3 hunter_main.py test              # Run all tests
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Import our modules
from momentum_hunter import MomentumHunter, test_momentum_hunter
from wallet_analyzer import WalletAnalyzer, test_wallet_analyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('ShadowHunter')

# Load environment variables from .env.hunter
def load_env_file(filepath):
    """Simple env file loader without dotenv dependency"""
    if not os.path.exists(filepath):
        return
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            # Remove inline comments
            if '#' in line:
                line = line[:line.index('#')].strip()
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

env_path = Path(__file__).parent / '.env.hunter'
load_env_file(env_path)


class ShadowHunter:
    """
    Main hunting coordinator - integrates all systems
    """
    
    def __init__(self):
        self.helius_key = os.getenv('HELIUS_API_KEY', '')
        self.min_liquidity = float(os.getenv('MIN_LIQUIDITY_USD', 10000))
        self.min_momentum = float(os.getenv('MIN_MOMENTUM_SCORE', 60))
        self.high_quality_wallets = set()
        
    async def scan_ecosystem(self):
        """
        One-time scan of Solana ecosystem for high-momentum tokens
        """
        logger.info("🚀 Starting ecosystem scan...")
        
        async with MomentumHunter(self.helius_key) as hunter:
            # Find high-momentum tokens
            tokens = await hunter.scan_solana_ecosystem(
                min_liquidity=self.min_liquidity
            )
            
            # Filter to only high momentum
            high_momentum = [t for t in tokens if t.momentum_score >= self.min_momentum]
            
            # Generate report
            report = hunter.generate_report(high_momentum)
            print(report)
            
            # Save to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"hunt_report_{timestamp}.txt"
            
            with open(report_file, 'w') as f:
                f.write(report)
            
            logger.info(f"📄 Report saved to: {report_file}")
            
            return high_momentum
    
    async def continuous_monitor(self, interval_minutes: int = 5):
        """
        Continuous monitoring loop - runs indefinitely
        """
        logger.info(f"🔄 Starting continuous monitoring (interval: {interval_minutes}m)")
        logger.info("Press Ctrl+C to stop\n")
        
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🔄 SCAN #{scan_count} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info('='*60)
                
                # Run scan
                tokens = await self.scan_ecosystem()
                
                if tokens:
                    logger.info(f"🎯 Found {len(tokens)} high-momentum tokens!")
                    
                    # If Helius key available, analyze top wallets
                    if self.helius_key:
                        logger.info("🔍 Analyzing early buyers...")
                        # TODO: Analyze early buyers for top tokens
                else:
                    logger.info("😴 No high-momentum tokens detected")
                
                # Wait for next scan
                logger.info(f"⏳ Waiting {interval_minutes} minutes until next scan...")
                await asyncio.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("\n👋 Monitoring stopped by user")
    
    async def analyze_wallet(self, wallet_address: str):
        """
        Deep analysis of a specific wallet
        """
        if not self.helius_key:
            logger.error("❌ Helius API key required for wallet analysis")
            logger.info("   Set HELIUS_API_KEY in .env.hunter")
            return
        
        logger.info(f"🔍 Analyzing wallet: {wallet_address}")
        
        async with WalletAnalyzer(self.helius_key) as analyzer:
            profile = await analyzer.analyze_wallet(wallet_address, days=30)
            
            print(f"\n{'='*60}")
            print(f"📊 WALLET ANALYSIS: {wallet_address}")
            print('='*60)
            print(f"Total Trades (30d): {profile.total_trades_30d}")
            print(f"Win Rate: {profile.win_rate*100:.1f}%")
            print(f"Total PnL: {profile.total_pnl_sol:.2f} SOL")
            print(f"Avg Trade Size: {profile.avg_trade_size_sol:.2f} SOL")
            print(f"Alpha Score: {profile.alpha_score:.1f}/100")
            print(f"Quality: {'✅ HIGH' if profile.is_high_quality else '❌ LOW'}")
            print(f"Bot Suspected: {'⚠️ YES' if profile.is_bot_suspected else '✅ NO'}")
            
            if profile.favorite_tokens:
                print(f"\nFavorite Tokens:")
                for i, token in enumerate(profile.favorite_tokens[:5], 1):
                    print(f"  {i}. {token}")
            
            if profile.last_active:
                print(f"\nLast Active: {profile.last_active.strftime('%Y-%m-%d %H:%M')}")
            
            print('='*60)
    
    async def find_early_buyers(self, token_address: str):
        """
        Find and score early buyers of a specific token
        """
        logger.info(f"🔍 Finding early buyers for {token_address}...")
        
        if not self.helius_key:
            logger.error("❌ Helius API key required")
            return
        
        # Get token metrics first
        async with MomentumHunter(self.helius_key) as hunter:
            metrics = await hunter.get_token_metrics(token_address)
            
            if not metrics:
                logger.error("❌ Could not fetch token metrics")
                return
            
            print(f"\n📊 Token: {metrics.symbol}")
            print(f"Age: {metrics.pair_created_at}")
            print(f"Current momentum: {metrics.momentum_score:.1f}")
        
        # TODO: Implement early buyer detection with Helius
        logger.info("⚠️ Early buyer detection requires webhook setup (System 1)")


async def run_tests():
    """
    Run all system tests
    """
    print("\n" + "="*70)
    print("🧪 RUNNING ALL SYSTEM TESTS")
    print("="*70 + "\n")
    
    # Test 1: Momentum Hunter
    await test_momentum_hunter()
    
    # Test 2: Wallet Analyzer (if API key available)
    await test_wallet_analyzer()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='ShadowHunter Alpha Finder - Zero-cost wallet hunting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 hunter_main.py scan                    # One-time ecosystem scan
  python3 hunter_main.py monitor                 # Continuous monitoring
  python3 hunter_main.py analyze <wallet>        # Analyze specific wallet
  python3 hunter_main.py test                    # Run all tests
        """
    )
    
    parser.add_argument(
        'command',
        choices=['scan', 'monitor', 'analyze', 'test', 'buyers'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'target',
        nargs='?',
        help='Target wallet or token address (for analyze/buyers commands)'
    )
    
    parser.add_argument(
        '--interval',
        '-i',
        type=int,
        default=5,
        help='Monitoring interval in minutes (default: 5)'
    )
    
    args = parser.parse_args()
    
    hunter = ShadowHunter()
    
    if args.command == 'scan':
        asyncio.run(hunter.scan_ecosystem())
    
    elif args.command == 'monitor':
        asyncio.run(hunter.continuous_monitor(args.interval))
    
    elif args.command == 'analyze':
        if not args.target:
            print("❌ Error: Wallet address required")
            print("   Usage: python3 hunter_main.py analyze <wallet_address>")
            sys.exit(1)
        asyncio.run(hunter.analyze_wallet(args.target))
    
    elif args.command == 'buyers':
        if not args.target:
            print("❌ Error: Token address required")
            print("   Usage: python3 hunter_main.py buyers <token_address>")
            sys.exit(1)
        asyncio.run(hunter.find_early_buyers(args.target))
    
    elif args.command == 'test':
        asyncio.run(run_tests())


if __name__ == "__main__":
    main()
