#!/usr/bin/env python3
"""Debug script to test DexCheck early-birds API"""
import aiohttp
import asyncio

DEXCHECK_API_KEY = "BostDZLJBBPu44iXpiOneGprXhTpSFCg"

async def test_early_birds():
    url = "https://api.dexcheck.ai/api/v1/blockchain/early-birds"
    params = {
        "chain": "solana",
        "pair": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
        "limit": 5
    }
    headers = {"X-API-Key": DEXCHECK_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Response type: {type(data)}")
            print(f"Response: {data}")
            
            if isinstance(data, list):
                print(f"\nList length: {len(data)}")

asyncio.run(test_early_birds())
