#!/usr/bin/env python3
"""
Birdeye API Test Script
Tests the wallet/v2/pnl/summary endpoint

Usage:
  python3 birdeye_test.py                    # Uses BIRDEYE_API_KEY from environment
  python3 birdeye_test.py YOUR_API_KEY       # Pass key as argument
  BIRDEYE_API_KEY=xxx python3 birdeye_test.py # Set inline
"""
import asyncio
import aiohttp
import os
import sys

# Get API key from environment or command line
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY') or (sys.argv[1] if len(sys.argv) > 1 else None)

# Test wallet (a known profitable Solana wallet)
TEST_WALLET = "5pxkp8Rpg7xHekFf7URJ25i4P5ZXVk8hRQUaDKytU5K7"


def log(msg: str):
    print(f"[TEST] {msg}")


async def test_birdeye_pnl():
    """Test Birdeye PnL endpoint."""
    
    log("=" * 60)
    log("BIRDEYE API TEST")
    log("=" * 60)
    
    # Check API key
    if not BIRDEYE_API_KEY:
        log("❌ ERROR: BIRDEYE_API_KEY not found in environment!")
        log("   Add BIRDEYE_API_KEY=your_key to .env file")
        return
    
    log(f"✓ API Key found: {BIRDEYE_API_KEY[:10]}...{BIRDEYE_API_KEY[-4:]}")
    log(f"✓ Test Wallet: {TEST_WALLET}")
    log("")
    
    # Build request
    url = "https://public-api.birdeye.so/wallet/v2/pnl/summary"
    params = {
        "wallet": TEST_WALLET,
        "timeframe": "90D"
    }
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY,
        "accept": "application/json"
    }
    
    log(f"Request URL: {url}")
    log(f"Params: {params}")
    log(f"Headers: {{'X-API-KEY': '***', 'accept': 'application/json'}}")
    log("")
    
    # Make request
    async with aiohttp.ClientSession() as session:
        try:
            log("Sending request...")
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                log(f"Response Status: {resp.status}")
                log(f"Response Headers: {dict(resp.headers)}")
                log("")
                
                # Check status
                if resp.status == 200:
                    log("✅ HTTP 200 - Success!")
                elif resp.status == 401:
                    log("❌ HTTP 401 - Unauthorized (Invalid API Key)")
                elif resp.status == 403:
                    log("❌ HTTP 403 - Forbidden (Key may not have access to this endpoint)")
                elif resp.status == 429:
                    log("❌ HTTP 429 - Rate Limited")
                elif resp.status == 404:
                    log("❌ HTTP 404 - Endpoint not found")
                else:
                    log(f"⚠️  HTTP {resp.status} - Unexpected status")
                
                # Get response body
                try:
                    text = await resp.text()
                    log("")
                    log("Response Body:")
                    log("-" * 40)
                    
                    # Try to parse as JSON
                    try:
                        import json
                        data = json.loads(text)
                        log(json.dumps(data, indent=2))
                        
                        # Check success field
                        if data.get("success"):
                            log("")
                            log("✅ API returned success=True")
                            
                            result = data.get("data", {})
                            log("")
                            log("Extracted Data:")
                            log(f"  - Realized Profit: ${result.get('realized_profit', 0)}")
                            log(f"  - Winrate: {result.get('winrate', 0)}%")
                            log(f"  - Trade Count: {result.get('trade_count', 0)}")
                            log(f"  - Unrealized Profit: ${result.get('unrealized_profit', 0)}")
                        else:
                            log("")
                            log("❌ API returned success=False")
                            log(f"   Message: {data.get('message', 'No message')}")
                    
                    except json.JSONDecodeError:
                        log("Raw response (not JSON):")
                        log(text[:500])
                        
                except Exception as e:
                    log(f"❌ Error reading response: {e}")
                    
        except asyncio.TimeoutError:
            log("❌ Request timed out (15s)")
        except Exception as e:
            log(f"❌ Request failed: {e}")
    
    log("")
    log("=" * 60)
    log("TEST COMPLETE")
    log("=" * 60)


async def test_simple_price():
    """Test a simpler Birdeye endpoint to verify API key works."""
    log("")
    log("=" * 60)
    log("SIMPLE PRICE TEST (Defi Price API)")
    log("=" * 60)
    
    if not BIRDEYE_API_KEY:
        log("❌ No API key available")
        return
    
    # Test with SOL token
    sol_mint = "So11111111111111111111111111111111111111112"
    url = f"https://public-api.birdeye.so/defi/price"
    params = {"address": sol_mint}
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    log(f"Testing: {url}")
    log(f"Token: SOL ({sol_mint[:10]}...)")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                log(f"Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        price = data.get("data", {}).get("value", 0)
                        log(f"✅ Success! SOL Price: ${price}")
                    else:
                        log(f"❌ API Error: {data.get('message')}")
                else:
                    text = await resp.text()
                    log(f"❌ HTTP {resp.status}: {text[:200]}")
        except Exception as e:
            log(f"❌ Error: {e}")


async def main():
    """Run all tests."""
    await test_simple_price()
    await test_birdeye_pnl()


if __name__ == "__main__":
    asyncio.run(main())
