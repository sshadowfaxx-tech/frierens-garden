# Recommended RPC configuration for trackerv2_clean.py
# Optimized for upgraded Helius plan with staked connections

# TIER 1: Helius Staked - Use for latency-critical operations
HELIUS_STAKED_RPC_URL = os.getenv('HELIUS_STAKED_RPC_URL')  # If available in your plan
HELIUS_RPC_URL = os.getenv('HELIUS_RPC_URL')

# TIER 2: Public RPCs - Use for high-volume, non-critical operations
PUBLIC_RPC_URLS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
    "https://solana-api.instantnodes.io",
    "https://solana.public-rpc.com",
]

# TIER 3: Alchemy - Emergency fallback only
ALCHEMY_RPC_URL = os.getenv('ALCHEMY_RPC_URL')

# OPERATION ROUTING (which RPC to use for each operation)
OPERATION_RPC_PRIORITY = {
    # HIGH PRIORITY: Use Helius (staked if available)
    # These need speed for real-time detection
    'getSignaturesForAddress': [
        HELIUS_STAKED_RPC_URL,  # Staked = fastest
        HELIUS_RPC_URL,          # Standard Helius
        *PUBLIC_RPC_URLS,        # Fallback to public
    ],
    
    # MEDIUM PRIORITY: Public first to save credits, Helius on failure
    'getTransaction': [
        *PUBLIC_RPC_URLS[:2],    # Try public first
        HELIUS_STAKED_RPC_URL,   # Then Helius staked
        HELIUS_RPC_URL,          # Then standard Helius
        *PUBLIC_RPC_URLS[2:],    # Remaining public
    ],
    
    # LOW PRIORITY: Public only (save Helius credits)
    'getTokenSupply': [
        *PUBLIC_RPC_URLS,
        ALCHEMY_RPC_URL,
        HELIUS_RPC_URL,  # Last resort
    ],
    
    'getTokenBalance': [
        *PUBLIC_RPC_URLS,
        ALCHEMY_RPC_URL,
    ],
    
    'getAccountInfo': [
        *PUBLIC_RPC_URLS,
        ALCHEMY_RPC_URL,
    ],
}

# CREDIT BUDGETING (adjust based on your specific plan)
HELIUS_DAILY_CREDIT_LIMIT = 500000  # Example: 500K plan
HELIUS_WARNING_THRESHOLD = 0.8       # Warn at 80% usage
HELIUS_CRITICAL_THRESHOLD = 0.95     # Switch to fallback at 95%

# CREDIT COSTS (Helius approximate)
HELIUS_CREDIT_COSTS = {
    'getSignaturesForAddress': 100,
    'getTransaction': 100,
    'getTokenSupply': 50,
    'getTokenBalance': 50,
    'getAccountInfo': 50,
}

# STRATEGY NOTES:
#
# 1. Staked connections: If your upgraded plan includes staked URLs, use them
#    for getSignaturesForAddress. They're faster but cost the same credits.
#
# 2. Credit budgeting: With 43 wallets polling every 5 seconds, you'll use
#    approximately 2.2M credits/day if everything goes through Helius.
#    Most plans can't handle this, so use public RPCs for getTransaction.
#
# 3. Smart fallback: If Helius returns rate limit (429), automatically
#    switch to public RPCs for 60 seconds before retrying Helius.
#
# 4. Daily reset: Track credits_used_today and reset at midnight UTC.
#    Switch to public-only mode if approaching limit.
