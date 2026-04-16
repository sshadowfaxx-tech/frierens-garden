"""
Tiered RPC Strategy for ShadowHunter with Helius Upgraded Plan
Utilizes staked connections for high-frequency operations
"""

import os
from typing import List, Optional

class RPCTierConfig:
    """
    Tiered RPC configuration optimized for upgraded Helius plan.
    
    Strategy:
    - TIER_1 (Helius Staked): High-frequency, latency-critical operations
    - TIER_2 (Helius Standard): Medium priority, when staked unavailable
    - TIER_3 (Public): Fallback, non-critical operations
    - TIER_4 (Alchemy): Emergency fallback only
    """
    
    # High-priority: Frequent polling operations
    TIER_1_PRIORITY = [
        os.getenv('HELIUS_STAKED_RPC_URL', ''),  # Staked connection for speed
        os.getenv('HELIUS_RPC_URL', ''),          # Regular Helius fallback
    ]
    
    # Medium-priority: Standard Helius
    TIER_2_STANDARD = [
        os.getenv('HELIUS_RPC_URL', ''),
    ]
    
    # Low-priority: Public RPCs (unlimited, slower)
    TIER_3_PUBLIC = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-rpc.publicnode.com",
        "https://solana-api.instantnodes.io",
    ]
    
    # Emergency: Alchemy (preserve these credits)
    TIER_4_EMERGENCY = [
        os.getenv('ALCHEMY_RPC_URL', ''),
    ]
    
    @classmethod
    def get_rpc_for_operation(cls, operation: str) -> List[str]:
        """
        Get appropriate RPC list based on operation type.
        
        Operations:
        - 'poll_signatures': getSignaturesForAddress (frequent, needs speed)
        - 'fetch_transaction': getTransaction (critical path)
        - 'token_metadata': getTokenSupply, getAccountInfo (less frequent)
        - 'balance_check': getTokenBalance (can be slower)
        """
        tiers = {
            'poll_signatures': cls.TIER_1_PRIORITY + cls.TIER_3_PUBLIC,
            'fetch_transaction': cls.TIER_1_PRIORITY + cls.TIER_3_PUBLIC,
            'token_metadata': cls.TIER_3_PUBLIC + cls.TIER_2_STANDARD,
            'balance_check': cls.TIER_3_PUBLIC + cls.TIER_2_STANDARD,
            'default': cls.TIER_1_PRIORITY + cls.TIER_3_PUBLIC,
        }
        
        # Filter out empty strings
        rpcs = tiers.get(operation, tiers['default'])
        return [url for url in rpcs if url]


class HeliusCreditMonitor:
    """
    Monitor and budget Helius API credit usage.
    """
    
    def __init__(self, daily_credit_limit: int = 500000):  # 500K for upgraded plan
        self.daily_limit = daily_credit_limit
        self.credits_used_today = 0
        self.hourly_usage = []
        
    def estimate_credits_per_wallet(self) -> int:
        """
        Estimate credits used per wallet per check cycle.
        
        Per wallet per 5-second cycle:
        - getSignaturesForAddress: ~100 credits
        - getTransaction (avg 2 txs): ~200 credits (100 each)
        - Total: ~300 credits per wallet per cycle
        """
        return 300
    
    def estimate_daily_usage(self, num_wallets: int = 43) -> int:
        """
        Calculate estimated daily credit usage.
        
        43 wallets × 300 credits × 12 checks/min × 60 min/hr × 24 hr/day
        = 43 × 300 × 12 × 60 × 24
        = 222,912,000 credits/day (WAY TOO HIGH)
        
        Reality with caching:
        - Most wallets have 0-1 new tx per minute
        - Average: 1 getSignatures + 1 getTransaction = 200 credits
        - 43 × 200 × 12 × 60 × 24 = 148,608,000 (still too high)
        
        With smarter caching (cache-first):
        - Only fetch new signatures when cache miss
        - Realistic: ~10% cache miss rate
        - 43 × 200 × 0.1 × 12 × 60 × 24 = 14,860,800 credits/day
        
        This is still high for most plans. We need to:
        1. Use public RPCs for baseline polling
        2. Use Helius only when public fails OR for critical operations
        3. Aggressive caching
        """
        # Conservative estimate with caching
        credits_per_wallet = self.estimate_credits_per_wallet()
        checks_per_day = 12 * 60 * 24  # Every 5 seconds
        cache_efficiency = 0.1  # 90% hit rate
        
        return int(num_wallets * credits_per_wallet * checks_per_day * cache_efficiency)
    
    def get_recommendation(self, num_wallets: int = 43) -> dict:
        """Get usage recommendation based on plan."""
        estimated_daily = self.estimate_daily_usage(num_wallets)
        
        if estimated_daily > self.daily_limit * 0.8:
            return {
                'strategy': 'conservative',
                'helius_usage': 'fallback_only',
                'warning': f'Estimated {estimated_daily:,} credits/day exceeds 80% of limit',
                'recommendation': 'Use Helius only for cluster detection and VIP alerts'
            }
        elif estimated_daily > self.daily_limit * 0.5:
            return {
                'strategy': 'balanced',
                'helius_usage': 'mixed',
                'warning': f'Estimated {estimated_daily:,} credits/day at 50% of limit',
                'recommendation': 'Use Helius for signature polling, public for transactions'
            }
        else:
            return {
                'strategy': 'aggressive',
                'helius_usage': 'primary',
                'warning': None,
                'recommendation': 'Full Helius utilization with staked connections'
            }


# Credit costs for Helius operations (approximate)
HELIUS_CREDIT_COSTS = {
    'getSignaturesForAddress': 100,
    'getTransaction': 100,
    'getTokenSupply': 50,
    'getTokenBalance': 50,
    'getAccountInfo': 50,
    'getMultipleAccounts': 100,
    'simulateTransaction': 200,
    'sendTransaction': 500,
}


# Recommended configuration for upgraded plan
RECOMMENDED_CONFIG = {
    # Tier 1: Helius Staked - Use for high-frequency polling
    'helius_staked_url': os.getenv('HELIUS_STAKED_RPC_URL'),
    
    # Use Helius for these operations
    'helius_operations': [
        'getSignaturesForAddress',  # Polling - needs speed
        'getTransaction',            # Transaction details - critical path
    ],
    
    # Use public RPCs for these
    'public_operations': [
        'getTokenSupply',     # Rare, not time-sensitive
        'getTokenBalance',    # Can be slower
        'getAccountInfo',     # Metadata lookups
    ],
    
    # Credit budgeting
    'daily_credit_limit': 500000,  # Adjust based on your plan
    'credit_warning_threshold': 0.8,  # Warn at 80% usage
    'credit_critical_threshold': 0.95,  # Switch to fallback at 95%
}
