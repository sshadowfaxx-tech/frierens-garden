#!/usr/bin/env python3
"""
Critical fixes for ShadowHunter tracker to ensure information flow during high volume.
Apply these to trackerv2_clean.py
"""

# FIX 1: Replace pagination logic in check_wallet_fast()
"""
OLD (BROKEN):
    last_seen = self.last_seen_sigs.get(wallet)
    if last_seen:
        new_signatures = []
        for sig_info in signatures:
            if sig_info['signature'] == last_seen:
                break
            new_signatures.append(sig_info)
        signatures = new_signatures
    
    if signatures:
        self.last_seen_sigs[wallet] = signatures[0]['signature']

NEW (CORRECT):
    # Use before parameter for proper pagination
    if last_seen:
        payload["params"][1]["before"] = last_seen
    
    # After fetching, update last_seen to oldest (for next page)
    if signatures:
        self.last_seen_sigs[wallet] = signatures[-1]['signature']
"""

# FIX 2: Add error type detection
"""
In check_wallet_fast() error handling:

    except aiohttp.ClientResponseError as e:
        if e.status == 429:
            logger.warning(f"Rate limited on {rpc_url}, backing off...")
            # Mark this RPC as rate-limited for 30s
            self.rate_limited_until[rpc_url] = time.time() + 30
        elif e.status >= 500:
            logger.warning(f"Server error on {rpc_url}, trying next...")
        if attempt < max_retries - 1:
            continue
        return 0
"""

# FIX 3: Non-blocking alerts
"""
OLD:
    await self.send_alert(wallet, change['token'], change['type'],
                          change['sol_amount'], change['token_amount'], sig)

NEW:
    # Fire-and-forget - don't block processing for alerts
    asyncio.create_task(self.send_alert(wallet, change['token'], change['type'],
                                        change['sol_amount'], change['token_amount'], sig))
"""

# FIX 4: Database write batching
"""
Add to SpeedTracker.__init__:
    self.db_write_queue = asyncio.Queue()
    self.db_batch_size = 10
    self.db_flush_interval = 2  # seconds

Add method:
    async def _db_writer_loop(self):
        while not self._shutdown_event.is_set():
            batch = []
            try:
                # Wait for first item
                item = await asyncio.wait_for(self.db_write_queue.get(), timeout=self.db_flush_interval)
                batch.append(item)
                
                # Collect more items up to batch size
                while len(batch) < self.db_batch_size:
                    try:
                        item = self.db_write_queue.get_nowait()
                        batch.append(item)
                    except asyncio.QueueEmpty:
                        break
                
                # Batch insert
                async with self.db_semaphore:
                    async with self.db.transaction():
                        for item in batch:
                            await self._execute_db_write(item)
                            
            except asyncio.TimeoutError:
                # Flush partial batch on timeout
                if batch:
                    async with self.db_semaphore:
                        async with self.db.transaction():
                            for item in batch:
                                await self._execute_db_write(item)

Replace individual DB calls with:
    await self.db_write_queue.put({
        'type': 'update_position',
        'wallet': wallet,
        'token': token,
        'tx_type': tx_type,
        # ... etc
    })
"""

# FIX 5: Add RPC health tracking to SpeedTracker
"""
Add to __init__:
    self.rpc_health = {url: {'score': 100, 'failures': 0, 'rate_limited_until': 0} for url in self.rpc_urls}
    self._rpc_health_lock = asyncio.Lock()

Add methods:
    async def get_healthy_rpc(self) -> str:
        async with self._rpc_health_lock:
            now = time.time()
            # Filter healthy RPCs
            healthy = [
                url for url in self.rpc_urls
                if self.rpc_health[url]['score'] > 30
                and now > self.rpc_health[url]['rate_limited_until']
            ]
            if not healthy:
                # All unhealthy, pick least bad
                healthy = sorted(self.rpc_urls, key=lambda u: self.rpc_health[u]['score'], reverse=True)
            return healthy[0]
    
    def report_rpc_success(self, url: str):
        self.rpc_health[url]['score'] = min(100, self.rpc_health[url]['score'] + 5)
        self.rpc_health[url]['failures'] = max(0, self.rpc_health[url]['failures'] - 1)
    
    def report_rpc_failure(self, url: str, error_type: str):
        self.rpc_health[url]['failures'] += 1
        if error_type == 'rate_limit':
            self.rpc_health[url]['rate_limited_until'] = time.time() + 30
            self.rpc_health[url]['score'] = max(0, self.rpc_health[url]['score'] - 30)
        elif error_type == 'timeout':
            self.rpc_health[url]['score'] = max(0, self.rpc_health[url]['score'] - 15)
        else:
            self.rpc_health[url]['score'] = max(0, self.rpc_health[url]['score'] - 20)
"""
