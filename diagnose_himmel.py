#!/usr/bin/env python3
"""Himmel Diagnostic Script - Test what's broken"""

import os
import sys
import asyncio
import aiohttp
import ssl

# Fix SSL certificates on Windows
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv loaded")
except ImportError:
    print("❌ dotenv not installed")
    sys.exit(1)

# Check environment variables
print("\n=== ENVIRONMENT VARIABLES ===")
token = os.getenv('TELEGRAM_BOT_TOKEN')
helius = os.getenv('HELIUS_API_KEY')
birdeye = os.getenv('BIRDEYE_API_KEY')

print(f"TELEGRAM_BOT_TOKEN: {'✅ Set' if token else '❌ Missing'}")
print(f"HELIUS_API_KEY: {'✅ Set' if helius else '❌ Missing'}")
print(f"BIRDEYE_API_KEY: {'✅ Set' if birdeye else '❌ Missing'}")

if helius:
    print(f"   Key starts with: {helius[:10]}...")

# Test internet connectivity
print("\n=== NETWORK TEST ===")
async def test_network():
    try:
        async with aiohttp.ClientSession() as session:
            # Test general internet
            async with session.get('https://httpbin.org/get', timeout=10) as resp:
                if resp.status == 200:
                    print("✅ Internet connection OK")
                else:
                    print(f"❌ Internet test failed: {resp.status}")
            
            # Test Helius RPC
            if helius:
                url = f"https://mainnet.helius-rpc.com/?api-key={helius}"
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }
                async with session.post(url, json=payload, timeout=10) as resp:
                    data = await resp.json()
                    if data.get('result') == 'ok':
                        print("✅ Helius RPC connection OK")
                    else:
                        print(f"❌ Helius RPC error: {data}")
            
            # Test DexScreener
            async with session.get('https://api.dexscreener.com/latest/dex/tokens/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', timeout=10) as resp:
                if resp.status == 200:
                    print("✅ DexScreener API OK")
                else:
                    print(f"❌ DexScreener failed: {resp.status}")
            
            # Test Birdeye (if key available)
            if birdeye:
                headers = {"X-API-KEY": birdeye}
                async with session.get('https://public-api.birdeye.so/public/wallet/net-worth?wallet=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 
                                      headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        print("✅ Birdeye API OK")
                    else:
                        print(f"❌ Birdeye failed: {resp.status}")
                        text = await resp.text()
                        print(f"   Response: {text[:200]}")
                        
    except Exception as e:
        print(f"❌ Network error: {type(e).__name__}: {e}")

asyncio.run(test_network())

# Check Python version
print("\n=== PYTHON INFO ===")
print(f"Python version: {sys.version}")
print(f"aiohttp: ", end="")
try:
    import aiohttp
    print(aiohttp.__version__)
except:
    print("❌ Not installed")

print("\nDone!")
