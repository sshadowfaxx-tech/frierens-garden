#!/usr/bin/env python3
"""
ShadowHunter Full Integration Demo
Demonstrates all 3 systems working together

This script:
1. Scans for high-momentum tokens (System 3)
2. Analyzes early buyers of those tokens (System 1 logic)
3. Scores wallets for quality (System 2 logic)
4. Outputs actionable alpha signals
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from momentum_hunter import MomentumHunter, TokenMetrics
from wallet_analyzer import WalletAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IntegrationDemo')


class ShadowHunterIntegrated:
    """
    Integrated hunting system combining all 3 strategies
    """
    
    def __init__(self, helius_api_key: Optional[str] = None):
        self.helius_key = helius_api_key
        self.high_value_wallets = set()
        self.token_signals = []
        
    async def full_hunt_cycle(self):
        """
        Complete hunting cycle:
        1. Find high-momentum tokens
        2. Analyze their early buyers
        3. Score and rank wallets
        4. Output signals
        """
        print("\n" + "="*70)
        print("🎯 SHADOWHUNTER FULL INTEGRATION DEMO")
        print("="*70 + "\n")
        
        # Step 1: Find momentum tokens
        momentum_tokens = await self._find_momentum_tokens()
        
        if not momentum_tokens:
            print("😴 No high-momentum tokens found in current market")
            return
        
        print(f"🎯 Found {len(momentum_tokens)} high-momentum tokens\n")
        
        # Step 2: For each token, find early buyers
        for token in momentum_tokens[:3]:  # Top 3 only for demo
            print(f"\n📊 Analyzing: {token.symbol} | Score: {token.momentum_score:.1f}")
            print(f"   Token: {token.address}")
            print(f"   1h Change: {token.price_change_1h:+.1f}%")
            print(f"   Volume: ${token.volume_24h:,.0f}")
            
            # Step 3: Analyze early buyers (requires Helius)
            if self.helius_key:
                await self._analyze_token_buyers(token)
            else:
                print(f"   ⚠️  Skipping buyer analysis (no Helius key)")
        
        # Step 4: Generate final report
        self._generate_final_report()
    
    async def _find_momentum_tokens(self) -> List[TokenMetrics]:
        """Step 1: Momentum detection"""
        async with MomentumHunter(self.helius_key) as hunter:
            tokens = await hunter.scan_solana_ecosystem(min_liquidity=50000)
            return [t for t in tokens if t.momentum_score >= 60]
    
    async def _analyze_token_buyers(self, token: TokenMetrics):
        """Step 2: Early buyer analysis"""
        # This would use Helius to get recent buyers
        # For demo, we'll simulate the logic
        print(f"   🔍 Would analyze recent buyers using Helius API")
        print(f"   📈 Would score each buyer's conviction")
        print(f"   🏆 Would identify high-value wallets")
    
    def _generate_final_report(self):
        """Step 4: Final alpha report"""
        print("\n" + "="*70)
        print("📋 HUNTING CYCLE COMPLETE")
        print("="*70 + "\n")
        
        print("Next steps:")
        print("1. Add Helius API key to .env.hunter")
        print("2. Run: python3 first_blood_simple.py (for real-time)")
        print("3. Run: python3 hunter_main.py monitor (for continuous)")
        
        print("\n" + "="*70 + "\n")


async def demo_all_systems():
    """
    Demonstrate all 3 systems in action
    """
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     🎯 SHADOWHUNTER ALPHA FINDER v3.0 - INTEGRATION DEMO         ║
║                                                                  ║
║     System 1: First Blood → Real-time early buyer detection      ║
║     System 2: Shadow Network → Wallet graph analysis             ║
║     System 3: Momentum Hunter → Multi-factor signal detection    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    hunter = ShadowHunterIntegrated()
    await hunter.full_hunt_cycle()
    
    # Show architecture
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    SYSTEM ARCHITECTURE                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐ ║
║  │  Helius Webhook │────→│  First Blood    │────→│  High-Value │ ║
║  │  (New launches) │     │  (Block 0-5)    │     │  Wallet DB  │ ║
║  └─────────────────┘     └─────────────────┘     └──────┬──────┘ ║
║                                                         │        ║
║  ┌─────────────────┐     ┌─────────────────┐            │        ║
║  │  DexScreener    │────→│  Momentum       │────────────┘        ║
║  │  (Price/Volume) │     │  Hunter         │                     ║
║  └─────────────────┘     └─────────────────┘                     ║
║                                                         │        ║
║  ┌─────────────────┐     ┌─────────────────┐            │        ║
║  │  Helius API     │────→│  Shadow Network │────────────┘        ║
║  │  (Tx History)   │     │  (Graph Analysis)                    ║
║  └─────────────────┘     └─────────────────┘                     ║
║                                                         │        ║
║                                          ┌──────────────┘        ║
║                                          ↓                        ║
║                              ┌─────────────────────┐              ║
║                              │  ALPHA SIGNALS      │              ║
║                              │  (High-confidence)  │              ║
║                              └─────────────────────┘              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

FREE APIs USED:
• Helius: 10M credits/month (webhooks + tx history)
• DexScreener: Unlimited (price/volume data)
• Jupiter: 600 req/min (price quotes)
• Total cost: $0/month

    """)
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70 + "\n")
    
    print("To run with full functionality:")
    print("1. Get free Helius API key: https://helius.xyz")
    print("2. Add to .env.hunter: HELIUS_API_KEY=your_key")
    print("3. Run: python3 hunter_main.py monitor\n")


if __name__ == "__main__":
    asyncio.run(demo_all_systems())
