#!/usr/bin/env python3
"""
ShadowHunter First Blood - Lightweight Webhook Receiver
Uses only Python standard library (no FastAPI/uvicorn needed)

Usage:
    python3 first_blood_simple.py --port 8000
    
    # With ngrok for external access
    ngrok http 8000
"""

import json
import argparse
import threading
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | 🩸 FIRST-BLOOD | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger('FirstBlood')

# Global state (thread-safe with locks)
launches: Dict[str, dict] = {}
buyers: Dict[str, List[dict]] = defaultdict(list)
signals: List[dict] = []
state_lock = threading.Lock()


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhooks"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle status checks"""
        if self.path == '/status':
            with state_lock:
                response = {
                    "status": "running",
                    "tracked_launches": len(launches),
                    "total_buyers": sum(len(b) for b in buyers.values()),
                    "high_value_signals": len(signals)
                }
            
            self._send_json(response)
        
        elif self.path == '/signals':
            with state_lock:
                response = {
                    "count": len(signals),
                    "recent": signals[-20:]  # Last 20
                }
            self._send_json(response)
        
        else:
            self._send_json({"message": "ShadowHunter First Blood is running"})
    
    def do_POST(self):
        """Handle incoming webhooks"""
        if self.path == '/webhook':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                processed = self._process_webhook(data)
                
                self._send_json({
                    "status": "ok",
                    "processed": processed,
                    "tracked_launches": len(launches),
                    "total_buyers": sum(len(b) for b in buyers.values())
                })
                
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                self._send_json({"status": "error", "message": str(e)}, 400)
        else:
            self._send_json({"status": "error", "message": "Unknown endpoint"}, 404)
    
    def _process_webhook(self, data) -> int:
        """Process incoming webhook data"""
        processed = 0
        
        # Handle array of events
        events = data if isinstance(data, list) else [data]
        
        for event in events:
            event_type = event.get('type', '')
            
            # Detect new launches
            if event_type in ['CREATE_POOL', 'initializeAccount']:
                token = event.get('tokenAddress') or event.get('account')
                if token and token not in launches:
                    with state_lock:
                        launches[token] = {
                            'address': token,
                            'time': datetime.now().isoformat(),
                            'slot': event.get('slot', 0),
                            'dex': event.get('dex', 'unknown')
                        }
                    
                    logger.info(f"🚀 NEW LAUNCH: {token[:20]}...")
                    logger.info(f"   DEX: {event.get('dex', 'unknown')}")
                    logger.info(f"   Slot: {event.get('slot', 0)}")
                    processed += 1
            
            # Detect early buys
            elif event_type == 'SWAP':
                token_out = event.get('tokenOut', '')
                token_in = event.get('tokenIn', '')
                
                # Only SOL -> Token buys
                if token_in in ['SOL', 'So11111111111111111111111111111111111111112']:
                    wallet = event.get('wallet', '')
                    slot = event.get('slot', 0)
                    
                    with state_lock:
                        if token_out in launches:
                            launch_slot = launches[token_out].get('slot', slot)
                            blocks_from_launch = slot - launch_slot
                            
                            # Track first 20 blocks only
                            if blocks_from_launch <= 20:
                                buy_data = {
                                    'wallet': wallet,
                                    'token': token_out,
                                    'blocks_from_launch': blocks_from_launch,
                                    'sol_spent': event.get('tokenAmount', 0),
                                    'time': datetime.now().isoformat()
                                }
                                buyers[token_out].append(buy_data)
                                
                                # Score the buyer
                                score = self._score_buyer(buy_data)
                                
                                if score > 60:
                                    logger.warning("🔥 HIGH-CONVICTION BUYER!")
                                    logger.warning(f"   Wallet: {wallet[:20]}...")
                                    logger.warning(f"   Token: {token_out[:20]}...")
                                    logger.warning(f"   Blocks: {blocks_from_launch}")
                                    logger.warning(f"   SOL: {buy_data['sol_spent']:.3f}")
                                    logger.warning(f"   Score: {score:.1f}/100")
                                    
                                    signals.append({
                                        'wallet': wallet,
                                        'token': token_out,
                                        'score': score,
                                        'time': datetime.now().isoformat()
                                    })
                                
                                processed += 1
        
        return processed
    
    def _score_buyer(self, buy_data: dict) -> float:
        """Calculate buyer conviction score"""
        score = 0
        
        # Early entry (50 pts max)
        blocks = buy_data.get('blocks_from_launch', 20)
        if blocks <= 1:
            score += 50
        elif blocks <= 3:
            score += 40
        elif blocks <= 5:
            score += 30
        elif blocks <= 10:
            score += 15
        
        # Position size (50 pts max)
        sol = buy_data.get('sol_spent', 0)
        if sol > 10:
            score += 50
        elif sol > 5:
            score += 35
        elif sol > 1:
            score += 20
        elif sol > 0.1:
            score += 10
        
        return score
    
    def _send_json(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def print_status():
    """Print current status"""
    with state_lock:
        print("\n" + "="*60)
        print("📊 CURRENT STATUS")
        print("="*60)
        print(f"Tracked Launches: {len(launches)}")
        print(f"Total Early Buyers: {sum(len(b) for b in buyers.values())}")
        print(f"High-Value Signals: {len(signals)}")
        
        if launches:
            print("\nRecent Launches:")
            for token, data in sorted(launches.items(), key=lambda x: x[1].get('time', ''), reverse=True)[:5]:
                buyer_count = len(buyers.get(token, []))
                print(f"  • {token[:20]}... ({buyer_count} buyers)")
        
        if signals:
            print("\nRecent High-Conviction Signals:")
            for sig in signals[-5:]:
                print(f"  • {sig['wallet'][:20]}... → {sig['token'][:15]}... (Score: {sig['score']:.1f})")
        
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='ShadowHunter First Blood (Lightweight)')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to run on')
    parser.add_argument('--host', '-H', default='0.0.0.0', help='Host to bind to')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🩸 SHADOWHUNTER FIRST BLOOD (LIGHTWEIGHT)")
    print("   Real-time Early Buyer Detection")
    print("   Zero dependencies - Python standard library only")
    print("="*70 + "\n")
    
    server = HTTPServer((args.host, args.port), WebhookHandler)
    
    print(f"📡 Starting webhook server on {args.host}:{args.port}")
    print(f"📊 Status endpoint: http://localhost:{args.port}/status")
    print(f"🎯 Webhook endpoint: http://localhost:{args.port}/webhook")
    print(f"📈 Signals endpoint: http://localhost:{args.port}/signals\n")
    
    print("⚠️  Configure Helius webhook with your public URL")
    print("   For local testing:")
    print("   1. Install ngrok: https://ngrok.com")
    print("   2. Run: ngrok http 8000")
    print("   3. Copy the https URL and configure Helius\n")
    
    print("💡 Press Ctrl+C to stop\n")
    
    # Status printer thread
    def status_loop():
        while True:
            try:
                import time
                time.sleep(30)  # Print status every 30 seconds
                print_status()
            except:
                break
    
    status_thread = threading.Thread(target=status_loop, daemon=True)
    status_thread.start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Stopping server...")
        server.shutdown()
        print_status()


if __name__ == "__main__":
    main()
