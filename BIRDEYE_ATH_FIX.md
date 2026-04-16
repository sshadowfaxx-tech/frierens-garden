# Fix for Birdeye ATH Not Working

## Problem
The `get_token_ath_birdeye` method is failing silently with no logs.

## Solution - Add Logging and Fix Endpoint

Replace your `get_token_ath_birdeye` method:

```python
    async def get_token_ath_birdeye(self, token: str) -> Optional[float]:
        """Get ATH market cap from Birdeye historical data."""
        logger.info(f"ATH FETCH: Starting for {token[:10]}...")
        
        if not Config.BIRDEYE_API_KEY:
            logger.warning("ATH FETCH: No BIRDEYE_API_KEY configured")
            return None
        
        try:
            # Try Birdeye's token overview endpoint first (has ATH data)
            url = f"https://public-api.birdeye.so/public/token_overview?address={token}"
            headers = {"X-API-KEY": Config.BIRDEYE_API_KEY, "accept": "application/json"}
            
            logger.info(f"ATH FETCH: Calling Birdeye overview API...")
            
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                logger.info(f"ATH FETCH: Response status {resp.status}")
                
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning(f"ATH FETCH: HTTP {resp.status} - {text[:200]}")
                    return None
                
                data = await resp.json()
                logger.info(f"ATH FETCH: Response keys: {list(data.keys())}")
                
                if not data.get('success'):
                    logger.warning(f"ATH FETCH: API returned success=false")
                    return None
                
                # Try to get ATH from data
                overview = data.get('data', {})
                
                # Check multiple possible field names for ATH
                ath_mc = (
                    overview.get('athMarketCap') or
                    overview.get('ath_market_cap') or
                    overview.get('maxMarketCap') or
                    overview.get('max_market_cap')
                )
                
                if ath_mc:
                    ath_value = float(ath_mc)
                    logger.info(f"ATH FETCH: Found ATH market cap: ${ath_value:,.2f}")
                    return ath_value
                
                # If no ATH field, try to calculate from price ATH
                ath_price = (
                    overview.get('ath') or
                    overview.get('athPrice') or
                    overview.get('ath_price') or
                    overview.get('maxPrice')
                )
                
                if ath_price:
                    # Estimate MC from price (need supply)
                    supply = overview.get('supply') or overview.get('circulatingSupply') or 0
                    if supply:
                        ath_mc = float(ath_price) * float(supply)
                        logger.info(f"ATH FETCH: Calculated ATH from price: ${ath_mc:,.2f}")
                        return ath_mc
                
                logger.info(f"ATH FETCH: No ATH data in overview, trying history endpoint...")
                
            # Fallback: Try history endpoint
            return await self._get_ath_from_history(token)
                
        except Exception as e:
            logger.error(f"ATH FETCH: Error - {type(e).__name__}: {e}")
            return None
    
    async def _get_ath_from_history(self, token: str) -> Optional[float]:
        """Fallback: Get ATH from 30-day history."""
        try:
            url = "https://public-api.birdeye.so/public/history_price"
            headers = {"X-API-KEY": Config.BIRDEYE_API_KEY, "accept": "application/json"}
            
            time_to = int(datetime.now().timestamp())
            time_from = time_to - (30 * 24 * 60 * 60)  # 30 days ago
            
            params = {
                "address": token,
                "address_type": "token",
                "type": "1D",  # Daily
                "time_from": time_from,
                "time_to": time_to
            }
            
            logger.info(f"ATH HISTORY: Fetching 30-day history...")
            
            async with self.session.get(url, headers=headers, params=params, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"ATH HISTORY: HTTP {resp.status}")
                    return None
                
                data = await resp.json()
                
                if not data.get('success'):
                    logger.warning(f"ATH HISTORY: API success=false")
                    return None
                
                items = data.get('data', {}).get('items', [])
                if not items:
                    logger.warning(f"ATH HISTORY: No history items")
                    return None
                
                # Find max market cap from history
                max_mc = 0
                for item in items:
                    mc = float(item.get('marketCap', 0) or item.get('mc', 0) or 0)
                    if mc > max_mc:
                        max_mc = mc
                
                if max_mc > 0:
                    logger.info(f"ATH HISTORY: Found max MC from history: ${max_mc:,.2f}")
                    return max_mc
                
                logger.warning(f"ATH HISTORY: No market cap data in history")
                return None
                
        except Exception as e:
            logger.error(f"ATH HISTORY: Error - {e}")
            return None
```

Also update `scan_token` to add more logging:

```python
    async def scan_token(self, contract_address: str, channel_id: str):
        """Scan a token and send info to the scanner channel."""
        try:
            if len(contract_address) < 32 or len(contract_address) > 44:
                await self.bot.send_message(
                    chat_id=channel_id,
                    text="❌ Invalid Solana contract address format."
                )
                return
            
            logger.info(f"Scanning token: {contract_address[:15]}...")
            
            # Get token info
            token_info = await self.cluster_detector.get_token_info(contract_address)
            logger.info(f"SCAN: Got token info: {token_info['ticker']} @ ${token_info['price']:.8f}")
            
            # Get ATH from Birdeye
            logger.info(f"SCAN: Fetching ATH...")
            ath_market_cap = await self.get_token_ath_birdeye(contract_address)
            
            if ath_market_cap:
                logger.info(f"SCAN: ATH found: ${ath_market_cap:,.2f}")
            else:
                logger.warning(f"SCAN: No ATH data available")
            
            # Format current market cap
            if token_info['market_cap'] >= 1_000_000:
                mc_str = f"${token_info['market_cap']/1_000_000:.2f}M"
            elif token_info['market_cap'] > 0:
                mc_str = f"${token_info['market_cap']/1000:.1f}K"
            else:
                mc_str = "Unknown"
            
            # Format ATH
            if ath_market_cap and ath_market_cap >= 1_000_000:
                ath_str = f"${ath_market_cap/1_000_000:.2f}M"
            elif ath_market_cap and ath_market_cap > 0:
                ath_str = f"${ath_market_cap/1000:.1f}K"
            else:
                ath_str = "N/A"
            
            # Calculate drawdown
            drawdown = ""
            if token_info['market_cap'] > 0 and ath_market_cap and ath_market_cap > 0:
                pct = (1 - token_info['market_cap'] / ath_market_cap) * 100
                drawdown = f"📉 *From ATH:* `-{pct:.1f}%`\n"
            
            source_emoji = "💎" if token_info.get('source') in ['bitquery', 'pumpfun_api'] else "📊"
            
            message = f"""{source_emoji} *TOKEN SCAN RESULTS*

*{token_info['ticker']}* ({token_info['name']})
`{contract_address}`

💰 *Current Market Cap:* `{mc_str}`
🏆 *ATH Market Cap:* `{ath_str}`
{drawdown}💵 *Price:* `${token_info['price']:.10f}`

🔗 [DexScreener]({token_info['dexscreener']})
🔗 [Pump.fun](https://pump.fun/{contract_address}) | [Photon](https://photon-sol.tinyastro.io/en/lp/{contract_address}) | [BullX](https://bullx.io/terminal?chainId=1399811149&address={contract_address})

_Scan provided by ShadowHunter_ 🤖"""
            
            await self.bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info("Token scan complete", extra={
                "token": token_info['ticker'],
                "address": contract_address[:15],
                "channel": channel_id
            })
            
        except Exception as e:
            logger.error("Token scan failed", extra={"error": str(e)})
            await self.bot.send_message(
                chat_id=channel_id,
                text=f"❌ Error scanning token. Please try again."
            )
```

## Check Your API Key

Make sure your `.env` has:
```bash
BIRDEYE_API_KEY=your_actual_api_key_here
```

**NOT** empty or commented out.

## Birdeye API Tier

Note: The `token_overview` and `history_price` endpoints may require a paid Birdeye tier. 

Free tier typically only supports:
- `/v1/wallet/token_list` (wallet holdings)
- Basic price queries

Check your Birdeye dashboard for available endpoints.

## Alternative: Calculate ATH Yourself

If Birdeye doesn't provide ATH, you can track it yourself in the database:

```sql
-- Add to your schema
ALTER TABLE tokens ADD COLUMN max_market_cap_seen NUMERIC DEFAULT 0;
ALTER TABLE tokens ADD COLUMN ath_timestamp TIMESTAMP;
```

Then update it whenever you see a higher MC:

```python
if token_info['market_cap'] > stored_ath:
    update_ath_in_db(token, token_info['market_cap'])
```
