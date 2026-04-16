# Fixing Birdeye & Alert Timeout Issues

## Problem 1: Birdeye API Failing

The Birdeye API is returning errors, causing the circuit breaker to OPEN.

### Quick Fix: Add Timeout & Better Error Handling

Replace your `_fetch_wallet_stats` method:

```python
    async def _fetch_wallet_stats(self, wallet: str) -> Dict[str, Any]:
        """Fetch wallet stats with shorter timeout to avoid blocking alerts."""
        if not Config.BIRDEYE_API_KEY:
            return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0}
        
        headers = {"X-API-KEY": Config.BIRDEYE_API_KEY, "accept": "application/json"}
        
        # Try the simpler token list endpoint first (more reliable)
        url = "https://public-api.birdeye.so/v1/wallet/token_list"
        params = {"wallet": wallet}
        
        try:
            async with self.session.get(url, headers=headers, params=params, timeout=5) as resp:
                if resp.status == 429:
                    logger.warning("Birdeye rate limited")
                    raise aiohttp.ClientError("Rate limited")
                
                if resp.status == 401:
                    logger.error("Birdeye API key invalid")
                    return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0}
                
                if resp.status != 200:
                    text = await resp.text()
                    logger.debug(f"Birdeye error {resp.status}: {text[:200]}")
                    return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0}
                
                data = await resp.json()
                
                if not data.get('success'):
                    return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0}
                
                items = data.get('data', {}).get('items', [])
                
                total_value = 0.0
                notable_tokens = []
                
                for item in items:
                    try:
                        value = float(item.get('valueUsd', 0) or 0)
                        total_value += value
                        
                        if value >= Config.NOTABLE_THRESHOLD:
                            notable_tokens.append({
                                'symbol': item.get('symbol', 'UNKNOWN'),
                                'name': item.get('name', 'Unknown'),
                                'value_usd': value,
                                'balance': float(item.get('balance', 0) or 0),
                                'price_usd': float(item.get('priceUsd', 0) or 0)
                            })
                    except (ValueError, TypeError):
                        continue
                
                notable_tokens.sort(key=lambda x: x['value_usd'], reverse=True)
                
                logger.info(f"Birdeye success for {wallet[:10]}...: ${total_value:,.2f}")
                return {
                    'total_value_usd': total_value,
                    'notable_tokens': notable_tokens[:10],
                    'notable_count': len(notable_tokens)
                }
                
        except asyncio.TimeoutError:
            logger.warning(f"Birdeye timeout for {wallet[:10]}...")
            raise  # Let circuit breaker handle it
        except Exception as e:
            logger.debug(f"Birdeye error: {e}")
            raise
```

## Problem 2: Alerts Timing Out

Birdeye is blocking `send_alert`. Make wallet stats **non-blocking**:

### Option A: Skip Birdeye if Circuit Open (Fastest)

Replace `get_wallet_stats`:

```python
    async def get_wallet_stats(self, wallet: str) -> Dict[str, Any]:
        """Get wallet stats - returns immediately if circuit open or no API key."""
        if not Config.BIRDEYE_API_KEY:
            return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0, 'cached': False}
        
        # Check if circuit is open - don't even try if it is
        if self.birdeye_circuit.state.name == "OPEN":
            logger.debug(f"Birdeye circuit OPEN, skipping wallet stats for {wallet[:10]}...")
            return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0, 'cached': False}
        
        cache_key = f"wallet_stats:{wallet}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            stats = json.loads(cached)
            if stats.get('total_value_usd', 0) > 0 or stats.get('notable_tokens'):
                stats['cached'] = True
                return stats
        
        # Try Birdeye with timeout wrapper
        try:
            # Use asyncio.wait_for to enforce max 6 second total time
            stats = await asyncio.wait_for(
                self.birdeye_circuit.call(self._fetch_wallet_stats, wallet),
                timeout=6.0
            )
            
            # Cache successful results
            if stats.get('total_value_usd', 0) > 0 or stats.get('notable_tokens'):
                await self.cache.setex(cache_key, Config.WALLET_STATS_TTL, json.dumps(stats))
            else:
                await self.cache.setex(cache_key, 3600, json.dumps(stats))
            
            stats['cached'] = False
            return stats
            
        except asyncio.TimeoutError:
            logger.warning(f"Wallet stats timeout for {wallet[:10]}...")
            return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0, 'cached': False}
        except Exception as e:
            logger.debug(f"Wallet stats failed: {e}")
            return {'total_value_usd': 0.0, 'notable_tokens': [], 'notable_count': 0, 'cached': False}
```

### Option B: Fire-and-Forget (Best for Speed)

Make wallet stats completely async from alerts:

```python
    async def send_alert(self, wallet: str, token: str, tx_type: str, sol_amount: float, sig: str):
        """Send alert - wallet stats fetched in background, doesn't block."""
        try:
            emoji = "🟢" if tx_type == "buy" else "🔴"
            
            wallet_label = None
            for w in self.wallets:
                if w['address'] == wallet:
                    wallet_label = w['label']
                    break
            
            # Get token info (DexScreener - usually fast)
            token_info = await self.cluster_detector.get_token_info(token)
            
            # Start wallet stats fetch in background (don't await yet)
            stats_task = asyncio.create_task(self.get_wallet_stats(wallet))
            
            # Format what we have immediately
            if token_info['market_cap'] >= 1_000_000:
                mc_str = f"${token_info['market_cap']/1_000_000:.2f}M"
            elif token_info['market_cap'] > 0:
                mc_str = f"${token_info['market_cap']/1000:.1f}K"
            else:
                mc_str = "Unknown"
            
            sol_str = f"{sol_amount:.4f} SOL"
            
            # Wait for wallet stats with short timeout
            try:
                wallet_stats = await asyncio.wait_for(stats_task, timeout=2.0)
                w_val = wallet_stats.get('total_value_usd', 0)
                if w_val >= 1_000_000:
                    w_str = f"${w_val/1_000_000:.2f}M"
                elif w_val >= 1000:
                    w_str = f"${w_val/1000:.1f}K"
                else:
                    w_str = f"${w_val:.0f}"
                
                notable_lines = []
                for t in wallet_stats.get('notable_tokens', [])[:5]:
                    v_str = f"${t['value_usd']/1000:.1f}K" if t['value_usd'] >= 1000 else f"${t['value_usd']:.0f}"
                    notable_lines.append(f"• ${t['symbol']}: {v_str}")
                notable = "\n".join(notable_lines) if notable_lines else "Loading..."
                cache_indicator = "🔄" if wallet_stats.get('cached') else "📊"
                
            except asyncio.TimeoutError:
                # Stats didn't load in time - show loading state
                w_str = "Loading..."
                notable = "Loading..."
                cache_indicator = "⏳"
            
            if wallet_label and not wallet_label.startswith("Wallet "):
                wallet_display = f"*{wallet_label}*\n`{wallet}`"
            else:
                wallet_display = f"`{wallet}`"
            
            source_line = ""
            if token_info.get('source') == 'bitquery':
                source_line = "💎 *Source:* Bitquery (Pre-migration)\n"
            elif token_info.get('source') == 'pumpfun_api':
                source_line = "💎 *Source:* Pump.fun (Bonding Curve)\n"
            
            message = f"""{emoji} *{tx_type.upper()} ALERT*

👤 *Wallet:* {wallet_display}

*{token_info['ticker']}* ({token_info['name']})
`{token}`

{source_line}*Market Cap:* `{mc_str}`
*Price:* `${token_info['price']:.8f}`

{cache_indicator} *Wallet Stats:*
• Total Value: `{w_str}`
• Notable Holdings (>${Config.NOTABLE_THRESHOLD}):
{notable}

💰 *{tx_type.capitalize()} Amount:* `{sol_str}`
🕐 *Time:* `{datetime.now().strftime('%H:%M:%S')}`

[📊 DexScreener]({token_info['dexscreener']})
[🔗 Solscan](https://solscan.io/tx/{sig})"""
            
            target_channel = Config.CHANNEL_PINGS or Config.TELEGRAM_CHAT_ID
            
            await self.bot.send_message(
                chat_id=target_channel, 
                text=message, 
                parse_mode='Markdown', 
                disable_web_page_preview=True
            )
            
            logger.info("Alert sent", extra={
                "token": token_info['ticker'], 
                "type": tx_type, 
                "sol": sol_amount, 
                "wallet": wallet[:10], 
                "label": wallet_label,
                "source": token_info.get('source', 'unknown'),
                "channel": target_channel
            })
            
        except Exception as e:
            logger.error("Alert failed", extra={"error": str(e)})
```

## Problem 3: Telegram Flood Control

Add rate limiting between alerts:

```python
    async def send_alert(self, wallet: str, token: str, tx_type: str, sol_amount: float, sig: str):
        # ... existing code ...
        
        # Add small delay between alerts to avoid flood control
        await asyncio.sleep(0.5)
        
        await self.bot.send_message(...)
```

Or use a queue system in `check_wallet_fast`:

```python
# At the end of check_wallet_fast, instead of immediate alerts:
for change in changes:
    # ... process change ...
    await self.send_alert(...)
    await asyncio.sleep(0.3)  # 300ms between alerts
```

## Immediate Workaround

If you want alerts NOW without Birdeye:

1. Comment out the `get_wallet_stats` call in `send_alert`:
```python
# wallet_stats = await self.get_wallet_stats(wallet)
wallet_stats = {'total_value_usd': 0, 'notable_tokens': [], 'cached': False}
```

2. Or set `BIRDEYE_API_KEY=` (empty) in `.env` to skip it entirely.

## Recommended Fix

Use **Option A** (circuit check + timeout) - it's the cleanest and keeps functionality while preventing blocking.
