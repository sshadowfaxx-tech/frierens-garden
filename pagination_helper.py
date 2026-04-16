#!/usr/bin/env python3
"""
Pagination helper for getSignaturesForAddress
Use this if 50 transactions per check is still not enough
"""

async def fetch_all_signatures(session, rpc_url, wallet, limit_per_call=50, max_calls=3):
    """
    Fetch signatures with pagination using 'before' parameter.
    
    Args:
        session: aiohttp ClientSession
        rpc_url: RPC endpoint
        wallet: Wallet address
        limit_per_call: Signatures per call (max 1000)
        max_calls: Maximum pagination calls (safety limit)
    
    Returns:
        List of signature objects sorted by blockTime (oldest first)
    """
    all_signatures = []
    before_sig = None
    
    for call_num in range(max_calls):
        params = [wallet, {"limit": limit_per_call}]
        if before_sig:
            params[1]["before"] = before_sig
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": params
        }
        
        async with session.post(rpc_url, json=payload) as resp:
            if resp.status != 200:
                break
            data = await resp.json()
            signatures = data.get('result', [])
            
            if not signatures:
                break
            
            all_signatures.extend(signatures)
            
            # If we got fewer than limit, we're done
            if len(signatures) < limit_per_call:
                break
            
            # Use last signature as 'before' for next page
            # Note: RPC returns newest first, so last is oldest
            before_sig = signatures[-1]['signature']
    
    # Sort by blockTime (oldest first)
    return sorted(all_signatures, key=lambda x: x.get('blockTime', 0) or 0)


# Usage in check_wallet_fast:
# signatures = await fetch_all_signatures(
#     self.session, rpc_url, wallet, 
#     limit_per_call=50, 
#     max_calls=2  # Max 100 signatures total
# )
