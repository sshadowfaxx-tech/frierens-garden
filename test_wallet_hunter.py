#!/usr/bin/env python3
"""
Quick test script to verify DexCheck and Helius APIs are working
"""

import asyncio
import aiohttp

HELIUS_RPC_URL = "https://beta.helius-rpc.com/?api-key=1030a4da-93a6-4d2a-af5e-9ec3f4ce4a8c"
DEXCHECK_API_KEY = "BostDZLJBBPu44iXpiOneGprXhTpSFCg"

# Sample Raydium SOL/USDC pair for testing
SAMPLE_PAIR = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"  # Raydium SOL-USDC

async def test_helius():
    """Test Helius RPC connection."""
    print("🧪 Testing Helius RPC...")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": ["So11111111111111111111111111111111111111112"]  # Wrapped SOL
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(HELIUS_RPC_URL, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                balance = data.get("result", {}).get("value", 0)
                print(f"   ✅ Helius connected!")
                print(f"   Wrapped SOL account balance: {balance / 1e9:.4f} SOL")
                return True
            else:
                print(f"   ❌ Helius error: {resp.status}")
                return False

async def test_dexcheck():
    """Test DexCheck API connection."""
    print("\n🧪 Testing DexCheck API...")
    
    # Note: DexCheck requires pair_id, not token address
    # Using a sample Raydium pair
    url = "https://api.dexcheck.ai/api/v1/blockchain/top-traders-for-pair"
    params = {
        "chain": "solana",
        "pair_id": SAMPLE_PAIR,  # Raydium SOL-USDC pair
        "duration": "30d",
        "limit": 5
    }
    headers = {"X-API-Key": DEXCHECK_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                traders = data.get("traders", [])
                print(f"   ✅ DexCheck connected!")
                print(f"   Found {len(traders)} top traders")
                if traders:
                    print(f"   Top trader: {traders[0].get('address', 'N/A')[:20]}...")
                return True
            else:
                text = await resp.text()
                print(f"   ❌ DexCheck error: {resp.status}")
                print(f"   Response: {text[:200]}")
                print(f"   Note: Make sure you're using a valid pair_id (pool address)")
                return False

async def test_dexcheck_early_birds():
    """Test DexCheck early birds endpoint."""
    print("\n🧪 Testing DexCheck Early Birds...")
    
    url = "https://api.dexcheck.ai/api/v1/blockchain/early-birds"
    params = {
        "chain": "solana",
        "pair": SAMPLE_PAIR,  # Raydium SOL-USDC pair
        "limit": 5
    }
    headers = {"X-API-Key": DEXCHECK_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                early_birds = data.get("earlyBirds", [])
                print(f"   ✅ Early Birds endpoint working!")
                print(f"   Found {len(early_birds)} early birds")
                if early_birds:
                    print(f"   First entry rank: #{early_birds[0].get('rank', 'N/A')}")
                return True
            else:
                text = await resp.text()
                print(f"   ❌ Early Birds error: {resp.status}")
                print(f"   Response: {text[:200]}")
                return False

async def main():
    print("=" * 60)
    print("🔧 Wallet Hunter API Test")
    print("=" * 60)
    print()
    
    helius_ok = await test_helius()
    dexcheck_ok = await test_dexcheck()
    early_birds_ok = await test_dexcheck_early_birds()
    
    print("\n" + "=" * 60)
    print("📊 Test Results")
    print("=" * 60)
    print(f"Helius RPC:     {'✅ PASS' if helius_ok else '❌ FAIL'}")
    print(f"DexCheck:       {'✅ PASS' if dexcheck_ok else '❌ FAIL'}")
    print(f"Early Birds:    {'✅ PASS' if early_birds_ok else '❌ FAIL'}")
    print("=" * 60)
    
    if helius_ok and dexcheck_ok and early_birds_ok:
        print("\n🎉 All APIs working! Ready to hunt wallets.")
        print("\n⚠️  Important: DexCheck requires POOL/PAIR addresses, not token addresses.")
        print("   You can get pair addresses from DexScreener or Raydium.")
        return 0
    elif helius_ok:
        print("\n⚠️  Helius working. DexCheck may need pair addresses instead of token addresses.")
        print("   The wallet hunter will still work with Helius-only mode.")
        return 0
    else:
        print("\n⚠️  Some APIs failed. Check configuration.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
