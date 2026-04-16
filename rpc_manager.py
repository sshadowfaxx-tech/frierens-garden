"""
Smart RPC Manager with Health Tracking
Drop-in replacement for current get_rpc() implementation
"""

import asyncio
import time
from typing import List, Dict, Optional
import aiohttp

class RPCManager:
    """
    Manages multiple RPC endpoints with health tracking and intelligent fallback.
    
    Features:
    - Health scoring per endpoint
    - Automatic failover on errors
    - Rate limit detection
    - Recovery probing
    """
    
    def __init__(self, rpc_urls: List[str]):
        self.rpc_urls = rpc_urls
        self.health_scores = {url: 100 for url in rpc_urls}  # 0-100 health score
        self.failure_counts = {url: 0 for url in rpc_urls}
        self.last_failure = {url: 0 for url in rpc_urls}
        self.rate_limited_until = {url: 0 for url in rpc_urls}
        self._lock = asyncio.Lock()
        
    async def get_healthy_rpc(self) -> str:
        """Get the healthiest available RPC endpoint"""
        async with self._lock:
            now = time.time()
            
            # Filter out rate-limited endpoints
            available = [
                url for url in self.rpc_urls 
                if now > self.rate_limited_until.get(url, 0)
            ]
            
            if not available:
                # All rate limited, wait for the soonest to recover
                soonest = min(self.rate_limited_until.values())
                wait_time = max(0, soonest - now)
                await asyncio.sleep(wait_time)
                available = self.rpc_urls
            
            # Sort by health score (descending)
            available.sort(key=lambda u: self.health_scores.get(u, 0), reverse=True)
            
            # Return healthiest
            return available[0]
    
    def report_success(self, url: str):
        """Report successful RPC call - improves health score"""
        self.health_scores[url] = min(100, self.health_scores[url] + 5)
        self.failure_counts[url] = max(0, self.failure_counts[url] - 1)
    
    def report_failure(self, url: str, error_type: str):
        """Report failed RPC call - reduces health score"""
        self.failure_counts[url] += 1
        self.last_failure[url] = time.time()
        
        if error_type == "rate_limit":
            # Rate limited - back off for 30 seconds
            self.rate_limited_until[url] = time.time() + 30
            self.health_scores[url] = max(0, self.health_scores[url] - 20)
        elif error_type == "timeout":
            self.health_scores[url] = max(0, self.health_scores[url] - 10)
        else:
            self.health_scores[url] = max(0, self.health_scores[url] - 15)
    
    def is_healthy(self, url: str) -> bool:
        """Check if RPC is currently healthy"""
        return (
            self.health_scores.get(url, 0) > 30 and
            time.time() > self.rate_limited_until.get(url, 0)
        )
    
    def get_status(self) -> Dict:
        """Get current status of all RPCs"""
        return {
            url: {
                "health": self.health_scores[url],
                "failures": self.failure_counts[url],
                "rate_limited": time.time() < self.rate_limited_until.get(url, 0)
            }
            for url in self.rpc_urls
        }


# Integration with existing tracker:
"""
In SpeedTracker.__init__:
    self.rpc_manager = RPCManager(Config.RPC_URLS)

In check_wallet_fast:
    rpc_url = await self.rpc_manager.get_healthy_rpc()
    
    try:
        # ... make RPC call ...
        self.rpc_manager.report_success(rpc_url)
    except asyncio.TimeoutError:
        self.rpc_manager.report_failure(rpc_url, "timeout")
        continue  # Retry with different RPC
    except aiohttp.ClientResponseError as e:
        if e.status == 429:  # Rate limited
            self.rpc_manager.report_failure(rpc_url, "rate_limit")
            continue
        self.rpc_manager.report_failure(rpc_url, "error")
        continue
"""
