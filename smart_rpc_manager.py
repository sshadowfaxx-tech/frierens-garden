"""
Drop-in replacement for get_rpc() with tiered selection
Add this to trackerv2_clean.py
"""

class SmartRPCManager:
    """
    Intelligent RPC selection based on operation type and credit budgeting.
    Optimized for upgraded Helius plan with staked connections.
    """
    
    def __init__(self):
        # Tier 1: Helius Staked (fastest, use sparingly)
        self.helius_staked = os.getenv('HELIUS_STAKED_RPC_URL', '')
        self.helius_standard = os.getenv('HELIUS_RPC_URL', '')
        
        # Tier 2: Public (unlimited, slower)
        self.public_rpcs = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-rpc.publicnode.com",
            "https://solana-api.instantnodes.io",
        ]
        
        # Tier 3: Alchemy (emergency only)
        self.alchemy = os.getenv('ALCHEMY_RPC_URL', '')
        
        # Health tracking
        self.health_scores = {}
        self.rate_limited_until = {}
        self.credits_used_today = 0
        self.daily_credit_limit = 500000  # Adjust to your plan
        
        # Operation routing
        self.operation_tiers = {
            # High priority: Use Helius first
            'getSignaturesForAddress': ['helius', 'public'],
            'getTransaction': ['public', 'helius'],  # Public first to save credits
            
            # Low priority: Public only
            'getTokenSupply': ['public', 'alchemy'],
            'getTokenBalance': ['public', 'alchemy'],
            'getAccountInfo': ['public', 'alchemy'],
        }
    
    def get_rpc(self, operation: str = 'default') -> str:
        """
        Get optimal RPC for operation type.
        
        Args:
            operation: The RPC method being called
            
        Returns:
            Best available RPC URL
        """
        tiers = self.operation_tiers.get(operation, ['public', 'helius'])
        
        # Check credit budget
        helius_budget_exceeded = self.credits_used_today > self.daily_credit_limit * 0.9
        
        for tier in tiers:
            if tier == 'helius' and helius_budget_exceeded:
                continue  # Skip Helius if near budget limit
                
            rpc = self._get_from_tier(tier)
            if rpc and self._is_healthy(rpc):
                return rpc
        
        # Fallback: any available
        return self._get_any_healthy()
    
    def _get_from_tier(self, tier: str) -> str:
        """Get RPC from specific tier."""
        if tier == 'helius':
            # Prefer staked if available
            if self.helius_staked:
                return self.helius_staked
            return self.helius_standard
        elif tier == 'public':
            # Round-robin through public
            idx = int(time.time()) % len(self.public_rpcs)
            return self.public_rpcs[idx]
        elif tier == 'alchemy':
            return self.alchemy
        return ''
    
    def _is_healthy(self, rpc: str) -> bool:
        """Check if RPC is healthy and not rate limited."""
        if not rpc:
            return False
        if rpc in self.rate_limited_until:
            if time.time() < self.rate_limited_until[rpc]:
                return False
        health = self.health_scores.get(rpc, 100)
        return health > 30
    
    def report_result(self, rpc: str, success: bool, is_rate_limit: bool = False):
        """Report RPC call result for health tracking."""
        if is_rate_limit:
            self.rate_limited_until[rpc] = time.time() + 60
            self.health_scores[rpc] = max(0, self.health_scores.get(rpc, 100) - 20)
        elif success:
            self.health_scores[rpc] = min(100, self.health_scores.get(rpc, 100) + 5)
            # Track Helius credits
            if 'helius' in rpc.lower():
                self.credits_used_today += 100  # Approximate per call
        else:
            self.health_scores[rpc] = max(0, self.health_scores.get(rpc, 100) - 10)
    
    def get_budget_status(self) -> dict:
        """Get current credit usage status."""
        return {
            'used': self.credits_used_today,
            'limit': self.daily_credit_limit,
            'remaining': self.daily_credit_limit - self.credits_used_today,
            'percent': (self.credits_used_today / self.daily_credit_limit) * 100,
        }


# Integration with SpeedTracker:
"""
In SpeedTracker.__init__:
    self.rpc_manager = SmartRPCManager()

In check_wallet_fast:
    # For signature polling (latency sensitive)
    rpc_url = self.rpc_manager.get_rpc('getSignaturesForAddress')
    
    # After call
    self.rpc_manager.report_result(rpc_url, success=True)
    
    # For transaction fetching
    rpc_url = self.rpc_manager.get_rpc('getTransaction')
"""
