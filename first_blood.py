#!/usr/bin/env python3
"""
ShadowHunter First Blood - Real-time Early Buyer Detection
Webhook receiver for Helius to detect first-block buyers

This requires:
1. Publicly accessible server (or ngrok for testing)
2. Helius webhook configured to send to your URL
3. Async processing to handle high volume

Usage:
    # Start webhook server
    python3 first_blood.py --port 8000
    
    # With ngrok for testing
    ngrok http 8000
    # Then configure Helius webhook with ngrok URL
"""

import asyncio
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# FastAPI for webhook server
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Import our modules
from momentum_hunter import MomentumHunter
from wallet_analyzer import WalletAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | 🩸 FIRST-BLOOD | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger('FirstBlood')

# Global state
detected_launches: Dict[str, dict] = {}
early_buyers: Dict[str, List[dict]] = defaultdict(list)
scored_wallets: Dict[str, dict] = {}
high_value_signals: List[dict] = []

app = FastAPI(title="ShadowHunter First Blood", version="3.0")


@dataclass
class LaunchEvent:
    """Token launch detection"""
    token_address: str
    pair_address: str
    dex: str  # 'raydium', 'orca', 'pumpfun'
    block_time: datetime
    slot: int
    initial_liquidity_sol: float
    initial_price_usd: float
    
    @property
    def age_seconds(self) -> int:
        return (datetime.now() - self.block_time).seconds


@dataclass
class EarlyBuyer:
    """Early buyer detection"""
    wallet: str
    token: str
    buy_slot: int
    buy_time: datetime
    sol_spent: float
    tokens_received: float
    price_paid: float
    wallet_balance_before: float
    is_first_10: bool = False
    is_first_100: bool = False
    
    @property
    def blocks_from_launch(self) -> int:
        launch = detected_launches.get(self.token, {})
        if launch:
            return self.buy_slot - launch.get('slot', self.buy_slot)
        return 0
    
    @property
    def conviction_score(self) -> float:
        """Score 0-100 based on early entry and position size"""
        score = 0
        
        # Early entry (50 pts max)
        blocks = self.blocks_from_launch
        if blocks <= 1:
            score += 50
        elif blocks <= 3:
            score += 40
        elif blocks <= 5:
            score += 30
        elif blocks <= 10:
            score += 15
        
        # Position size relative to balance (30 pts max)
        if self.wallet_balance_before > 0:
            pct = self.sol_spent / self.wallet_balance_before
            if pct > 0.5:
                score += 30
            elif pct > 0.3:
                score += 20
            elif pct > 0.1:
                score += 10
        
        # Absolute size (20 pts max)
        if self.sol_spent > 10:
            score += 20
        elif self.sol_spent > 5:
            score += 15
        elif self.sol_spent > 1:
            score += 10
        elif self.sol_spent > 0.1:
            score += 5
        
        return score


class FirstBloodDetector:
    """
    Detects and scores early buyers in real-time
    """
    
    def __init__(self, helius_api_key: Optional[str] = None):
        self.helius_key = helius_api_key
        self.launches: Dict[str, LaunchEvent] = {}
        self.buyers: Dict[str, List[EarlyBuyer]] = defaultdict(list)
        self.wallet_scores: Dict[str, float] = {}
        
    def process_launch(self, webhook_data: dict) -> Optional[LaunchEvent]:
        """
        Process new token launch from Helius webhook
        
        Expected webhook format from Helius:
        {
            "type": "CREATE_POOL",
            "tokenAddress": "...",
            "poolAddress": "...",
            "dex": "raydium",
            "slot": 123456789,
            "timestamp": 1234567890,
            "liquidity": {...}
        }
        """
        try:
            event_type = webhook_data.get('type', '')
            
            # Filter to only pool creation events
            if event_type not in ['CREATE_POOL', 'initializeAccount', 'InitializeAccount2']:
                return None
            
            token = webhook_data.get('tokenAddress') or webhook_data.get('account')
            if not token:
                return None
            
            # Check if we already tracked this launch
            if token in self.launches:
                return None
            
            launch = LaunchEvent(
                token_address=token,
                pair_address=webhook_data.get('poolAddress', ''),
                dex=webhook_data.get('dex', 'unknown'),
                block_time=datetime.now(),
                slot=webhook_data.get('slot', 0),
                initial_liquidity_sol=webhook_data.get('liquidity', {}).get('sol', 0),
                initial_price_usd=webhook_data.get('price', 0)
            )
            
            self.launches[token] = launch
            
            logger.info(f"🚀 NEW LAUNCH DETECTED: {token[:20]}...")
            logger.info(f"   DEX: {launch.dex} | Slot: {launch.slot}")
            logger.info(f"   Liquidity: {launch.initial_liquidity_sol:.2f} SOL")
            logger.info(f"   Price: ${launch.initial_price_usd:.8f}")
            
            return launch
            
        except Exception as e:
            logger.error(f"Error processing launch: {e}")
            return None
    
    def process_buy(self, webhook_data: dict) -> Optional[EarlyBuyer]:
        """
        Process buy transaction from Helius webhook
        
        Expected format:
        {
            "type": "SWAP",
            "tokenIn": "SOL",
            "tokenOut": "TOKEN_ADDRESS",
            "tokenAmount": 1.5,
            "wallet": "BUYER_WALLET",
            "slot": 123456790,
            "timestamp": 1234567891
        }
        """
        try:
            event_type = webhook_data.get('type', '')
            
            if event_type != 'SWAP':
                return None
            
            token_out = webhook_data.get('tokenOut', '')
            token_in = webhook_data.get('tokenIn', '')
            
            # Only process SOL -> Token buys
            if token_in not in ['SOL', 'So11111111111111111111111111111111111111112']:
                return None
            
            # Check if this is a token we tracked
            if token_out not in self.launches:
                # Could be a token we missed - still track it
                pass
            
            wallet = webhook_data.get('wallet', '')
            slot = webhook_data.get('slot', 0)
            
            # Calculate blocks from launch
            launch_slot = 0
            if token_out in self.launches:
                launch_slot = self.launches[token_out].slot
            
            blocks_from_launch = slot - launch_slot
            
            # Only track early buyers (first 20 blocks)
            if blocks_from_launch > 20:
                return None
            
            buyer = EarlyBuyer(
                wallet=wallet,
                token=token_out,
                buy_slot=slot,
                buy_time=datetime.now(),
                sol_spent=webhook_data.get('tokenAmount', 0),
                tokens_received=webhook_data.get('outAmount', 0),
                price_paid=webhook_data.get('price', 0),
                wallet_balance_before=webhook_data.get('walletBalance', 0),
                is_first_10=len(self.buyers[token_out]) < 10,
                is_first_100=len(self.buyers[token_out]) < 100
            )
            
            self.buyers[token_out].append(buyer)
            
            # Log high-conviction buyers
            if buyer.conviction_score > 60:
                self._log_high_conviction_buyer(buyer)
            
            return buyer
            
        except Exception as e:
            logger.error(f"Error processing buy: {e}")
            return None
    
    def _log_high_conviction_buyer(self, buyer: EarlyBuyer):
        """Log high-quality early buyer"""
        logger.warning("🔥 HIGH-CONVICTION EARLY BUYER DETECTED!")
        logger.warning(f"   Wallet: {buyer.wallet}")
        logger.warning(f"   Token: {buyer.token[:20]}...")
        logger.warning(f"   Blocks from launch: {buyer.blocks_from_launch}")
        logger.warning(f"   SOL spent: {buyer.sol_spent:.3f}")
        logger.warning(f"   Conviction score: {buyer.conviction_score:.1f}/100")
        logger.warning(f"   First 10 buyer: {'✅ YES' if buyer.is_first_10 else '❌ No'}")
        
        # Store for batch analysis
        high_value_signals.append({
            'wallet': buyer.wallet,
            'token': buyer.token,
            'score': buyer.conviction_score,
            'time': datetime.now().isoformat()
        })
    
    def get_launch_summary(self, token: str) -> dict:
        """Get summary of launch and early buyers"""
        if token not in self.launches:
            return {}
        
        launch = self.launches[token]
        buyers = self.buyers.get(token, [])
        
        # Calculate stats
        avg_conviction = sum(b.conviction_score for b in buyers) / len(buyers) if buyers else 0
        high_conviction = len([b for b in buyers if b.conviction_score > 60])
        total_sol = sum(b.sol_spent for b in buyers)
        
        return {
            'token': token,
            'age_seconds': launch.age_seconds,
            'total_buyers': len(buyers),
            'high_conviction_buyers': high_conviction,
            'avg_conviction_score': avg_conviction,
            'total_sol_entered': total_sol,
            'top_buyers': sorted(buyers, key=lambda x: x.conviction_score, reverse=True)[:5]
        }


# Initialize detector
detector = FirstBloodDetector()


@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Main webhook endpoint for Helius
    """
    try:
        data = await request.json()
        
        # Handle both single events and arrays
        events = data if isinstance(data, list) else [data]
        
        processed = 0
        for event in events:
            # Try to process as launch
            launch = detector.process_launch(event)
            if launch:
                processed += 1
                continue
            
            # Try to process as buy
            buy = detector.process_buy(event)
            if buy:
                processed += 1
        
        return JSONResponse({
            "status": "ok",
            "processed": processed,
            "tracked_launches": len(detector.launches),
            "total_buyers": sum(len(b) for b in detector.buyers.values())
        })
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/status")
async def get_status():
    """Get current detector status"""
    return {
        "tracked_launches": len(detector.launches),
        "total_buyers": sum(len(b) for b in detector.buyers.values()),
        "high_value_signals": len(high_value_signals),
        "recent_launches": [
            {
                "token": t,
                "age_seconds": l.age_seconds,
                "buyers": len(detector.buyers.get(t, []))
            }
            for t, l in sorted(detector.launches.items(), key=lambda x: x[1].block_time, reverse=True)[:10]
        ]
    }


@app.get("/launch/{token}")
async def get_launch_details(token: str):
    """Get details for specific launch"""
    summary = detector.get_launch_summary(token)
    if not summary:
        raise HTTPException(status_code=404, detail="Token not found")
    return summary


@app.get("/signals")
async def get_high_value_signals():
    """Get all high-conviction buyer signals"""
    return {
        "count": len(high_value_signals),
        "signals": high_value_signals[-100:]  # Last 100
    }


def main():
    parser = argparse.ArgumentParser(description='ShadowHunter First Blood - Webhook Server')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to run server on')
    parser.add_argument('--host', '-H', default='0.0.0.0', help='Host to bind to')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🩸 SHADOWHUNTER FIRST BLOOD")
    print("   Real-time Early Buyer Detection")
    print("="*70 + "\n")
    
    print(f"📡 Starting webhook server on {args.host}:{args.port}")
    print(f"📊 Status endpoint: http://{args.host}:{args.port}/status")
    print(f"🎯 Webhook endpoint: http://{args.host}:{args.port}/webhook")
    print("\n⚠️  Configure Helius webhook with your public URL")
    print("   For local testing: ngrok http 8000\n")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
