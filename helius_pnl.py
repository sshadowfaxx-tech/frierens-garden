#!/usr/bin/env python3
"""
Helius 90D PnL Calculator - Simplified Version
Tracks SOL, USDC, USDT profits only
"""
import asyncio
import aiohttp
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# Token addresses on Solana
SOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

TRACKED_TOKENS = {SOL_MINT, USDC_MINT, USDT_MINT}
TOKEN_SYMBOLS = {
    SOL_MINT: "SOL",
    USDC_MINT: "USDC", 
    USDT_MINT: "USDT"
}
TOKEN_DECIMALS = {
    SOL_MINT: 9,
    USDC_MINT: 6,
    USDT_MINT: 6
}

HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')


@dataclass
class SwapTrade:
    """Represents a single swap trade involving SOL/USDC/USDT."""
    signature: str
    timestamp: int
    token_in: str  # Mint address
    token_out: str  # Mint address
    amount_in: float  # Human readable
    amount_out: float  # Human readable
    
    # Calculated fields
    usd_value_in: float = 0.0
    usd_value_out: float = 0.0
    pnl_usd: float = 0.0
    roi_pct: float = 0.0  # NEW: ROI percentage for this trade
    is_win: bool = False
    
    def __post_init__(self):
        self.token_in_symbol = TOKEN_SYMBOLS.get(self.token_in, "UNKNOWN")
        self.token_out_symbol = TOKEN_SYMBOLS.get(self.token_out, "UNKNOWN")


@dataclass 
class WalletPnL:
    """90D PnL summary for a wallet."""
    wallet_address: str
    trades: List[SwapTrade] = field(default_factory=list)
    valid_trades: int = 0
    invalid_trades: int = 0
    
    # Totals
    total_sol_profit: float = 0.0
    total_usdc_profit: float = 0.0
    total_usdt_profit: float = 0.0
    total_pnl_usd: float = 0.0
    
    # Winrate stats
    wins: int = 0
    losses: int = 0
    winrate: float = 0.0
    
    # Average metrics
    avg_profit_usd: float = 0.0
    avg_roi_per_trade: float = 0.0  # NEW: Average ROI percentage per trade


def log(msg: str):
    print(f"[PnL Calc] {msg}", flush=True)


async def fetch_dexscreener_sol_price() -> float:
    """Fetch current SOL price from DexScreener."""
    try:
        url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        sorted_pairs = sorted(
                            pairs, 
                            key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), 
                            reverse=True
                        )
                        price = float(sorted_pairs[0].get("priceUsd", 0))
                        log(f"Current SOL price: ${price:.2f}")
                        return price
    except Exception as e:
        log(f"Error fetching SOL price: {e}")
    return 150.0


async def fetch_helius_transactions(wallet: str) -> List[Dict]:
    """Fetch 90 days of SWAP transactions from Helius."""
    if not HELIUS_API_KEY:
        log("❌ HELIUS_API_KEY not set")
        return []
    
    all_transactions = []
    days_90_ago = int((datetime.now() - timedelta(days=90)).timestamp())
    base_url = f"https://api-mainnet.helius-rpc.com/v0/addresses/{wallet}/transactions"
    
    last_signature = None
    page = 0
    
    async with aiohttp.ClientSession() as session:
        while page < 20:
            url = f"{base_url}?api-key={HELIUS_API_KEY}&type=SWAP&limit=100"
            if last_signature:
                url += f"&before-signature={last_signature}"
            
            try:
                async with session.get(url, timeout=30) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    if not isinstance(data, list) or not data:
                        break
                    
                    filtered = [tx for tx in data if tx.get("timestamp", 0) >= days_90_ago]
                    all_transactions.extend(filtered)
                    
                    if not filtered or filtered[-1].get("timestamp", 0) < days_90_ago:
                        break
                    if len(data) < 100:
                        break
                    
                    last_signature = data[-1].get("signature")
                    page += 1
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                log(f"Error fetching transactions: {e}")
                break
    
    log(f"Total SWAPS found (90D): {len(all_transactions)}")
    return all_transactions


def parse_swap_transaction(tx: Dict) -> Optional[SwapTrade]:
    """Parse a Helius SWAP transaction. Returns SwapTrade if valid, None otherwise."""
    try:
        signature = tx.get("signature", "")
        timestamp = tx.get("timestamp", 0)
        token_transfers = tx.get("tokenTransfers", [])
        
        if len(token_transfers) < 2:
            return None
        
        # Get tracked token transfers
        tracked_transfers = [t for t in token_transfers if t.get("mint", "") in TRACKED_TOKENS][:2]
        if len(tracked_transfers) < 2:
            return None
        
        transfer_in = tracked_transfers[0]
        transfer_out = tracked_transfers[1]
        
        token_in = transfer_in.get("mint", "")
        token_out = transfer_out.get("mint", "")
        
        # Skip SOL/USDC/USDT swaps between themselves
        if token_in in TRACKED_TOKENS and token_out in TRACKED_TOKENS:
            return None
        
        amount_in = float(transfer_in.get("tokenAmount", 0))
        amount_out = float(transfer_out.get("tokenAmount", 0))
        
        decimals_in = TOKEN_DECIMALS.get(token_in, 9)
        decimals_out = TOKEN_DECIMALS.get(token_out, 9)
        
        human_amount_in = amount_in / (10 ** decimals_in)
        human_amount_out = amount_out / (10 ** decimals_out)
        
        return SwapTrade(
            signature=signature,
            timestamp=timestamp,
            token_in=token_in,
            token_out=token_out,
            amount_in=human_amount_in,
            amount_out=human_amount_out
        )
    except Exception:
        return None


def calculate_trade_pnl(trade: SwapTrade, sol_price: float) -> bool:
    """Calculate PnL and ROI for a single trade. Returns True if successful."""
    try:
        # Calculate USD values
        if trade.token_in == SOL_MINT:
            trade.usd_value_in = trade.amount_in * sol_price
        elif trade.token_in in (USDC_MINT, USDT_MINT):
            trade.usd_value_in = trade.amount_in
        else:
            return False
        
        if trade.token_out == SOL_MINT:
            trade.usd_value_out = trade.amount_out * sol_price
        elif trade.token_out in (USDC_MINT, USDT_MINT):
            trade.usd_value_out = trade.amount_out
        else:
            return False
        
        # Calculate PnL
        trade.pnl_usd = trade.usd_value_out - trade.usd_value_in
        
        # Calculate ROI percentage for this trade
        if trade.usd_value_in > 0:
            trade.roi_pct = (trade.pnl_usd / trade.usd_value_in) * 100
            trade.is_win = trade.roi_pct >= 50
        else:
            trade.roi_pct = 0.0
            trade.is_win = False
        
        return True
    except Exception:
        return False


async def calculate_wallet_pnl_simple(wallet_address: str) -> Dict:
    """Calculate 90D PnL for a wallet using Helius. Returns simplified dict."""
    result = {
        "wallet_address": wallet_address,
        "trades": [],
        "valid_trades": 0,
        "invalid_trades": 0,
        "total_sol_profit": 0.0,
        "total_usdc_profit": 0.0,
        "total_usdt_profit": 0.0,
        "total_pnl_usd": 0.0,
        "wins": 0,
        "losses": 0,
        "winrate": 0.0,
        "avg_profit_usd": 0.0,
        "avg_roi_per_trade": 0.0,  # NEW FIELD
    }
    
    sol_price = await fetch_dexscreener_sol_price()
    transactions = await fetch_helius_transactions(wallet_address)
    
    if not transactions:
        return result
    
    trades = []
    for tx in transactions:
        trade = parse_swap_transaction(tx)
        if not trade:
            result["invalid_trades"] += 1
            continue
        
        if not calculate_trade_pnl(trade, sol_price):
            result["invalid_trades"] += 1
            continue
        
        trades.append(trade)
        result["valid_trades"] += 1
        
        if trade.is_win:
            result["wins"] += 1
        else:
            result["losses"] += 1
    
    # Calculate totals
    for trade in trades:
        if trade.pnl_usd > 0:
            if trade.token_out == SOL_MINT:
                result["total_sol_profit"] += trade.amount_out - trade.amount_in
            elif trade.token_out == USDC_MINT:
                result["total_usdc_profit"] += trade.amount_out
            elif trade.token_out == USDT_MINT:
                result["total_usdt_profit"] += trade.amount_out
    
    result["total_pnl_usd"] = (
        result["total_sol_profit"] * sol_price +
        result["total_usdc_profit"] +
        result["total_usdt_profit"]
    )
    
    if result["valid_trades"] > 0:
        result["winrate"] = (result["wins"] / result["valid_trades"]) * 100
    
    # Average profit (of winning trades only)
    winning_trades = [t for t in trades if t.is_win]
    if winning_trades:
        result["avg_profit_usd"] = sum(t.pnl_usd for t in winning_trades) / len(winning_trades)
    
    # NEW: Calculate average ROI per trade (all valid trades)
    if trades:
        result["avg_roi_per_trade"] = sum(t.roi_pct for t in trades) / len(trades)
    
    result["trades"] = trades
    return result


def format_pnl_summary(pnl_data: Dict) -> str:
    """Format PnL results for display."""
    lines = [
        f"📊 90D PnL Report",
        f"",
        f"📈 Total Trades: {pnl_data.get('valid_trades', 0)} valid | {pnl_data.get('invalid_trades', 0)} skipped",
        f"🏆 Winrate: {pnl_data.get('winrate', 0):.1f}% ({pnl_data.get('wins', 0)}W / {pnl_data.get('losses', 0)}L)",
        f"📊 Avg ROI/Trade: {pnl_data.get('avg_roi_per_trade', 0):+.1f}%",  # NEW
        f"",
        f"💰 Profit Breakdown:",
        f"   SOL: {pnl_data.get('total_sol_profit', 0):+.4f} SOL",
        f"   USDC: ${pnl_data.get('total_usdc_profit', 0):+.2f}",
        f"   USDT: ${pnl_data.get('total_usdt_profit', 0):+.2f}",
        f"",
        f"💵 Total 90D PnL: ${pnl_data.get('total_pnl_usd', 0):+.2f}",
        f"📊 Avg Profit/Win: ${pnl_data.get('avg_profit_usd', 0):.2f}",
    ]
    return "\n".join(lines)


# Keep old function name for backward compatibility
async def calculate_wallet_pnl(wallet_address: str) -> WalletPnL:
    """Calculate 90D PnL for a wallet (legacy class-based return)."""
    data = await calculate_wallet_pnl_simple(wallet_address)
    
    result = WalletPnL(wallet_address=wallet_address)
    result.valid_trades = data.get("valid_trades", 0)
    result.invalid_trades = data.get("invalid_trades", 0)
    result.total_sol_profit = data.get("total_sol_profit", 0.0)
    result.total_usdc_profit = data.get("total_usdc_profit", 0.0)
    result.total_usdt_profit = data.get("total_usdt_profit", 0.0)
    result.total_pnl_usd = data.get("total_pnl_usd", 0.0)
    result.wins = data.get("wins", 0)
    result.losses = data.get("losses", 0)
    result.winrate = data.get("winrate", 0.0)
    result.avg_profit_usd = data.get("avg_profit_usd", 0.0)
    result.avg_roi_per_trade = data.get("avg_roi_per_trade", 0.0)
    result.trades = data.get("trades", [])
    
    return result


def format_pnl_report(pnl: WalletPnL) -> str:
    """Format PnL results for display (legacy class-based)."""
    data = {
        "valid_trades": pnl.valid_trades,
        "invalid_trades": pnl.invalid_trades,
        "winrate": pnl.winrate,
        "wins": pnl.wins,
        "losses": pnl.losses,
        "avg_roi_per_trade": pnl.avg_roi_per_trade,
        "total_sol_profit": pnl.total_sol_profit,
        "total_usdc_profit": pnl.total_usdc_profit,
        "total_usdt_profit": pnl.total_usdt_profit,
        "total_pnl_usd": pnl.total_pnl_usd,
        "avg_profit_usd": pnl.avg_profit_usd,
    }
    return format_pnl_summary(data)


async def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 helius_pnl.py <wallet_address>")
        print("Example: python3 helius_pnl.py 5pxkp8Rpg7xHekFf7URJ25i4P5ZXVk8hRQUaDKytU5K7")
        sys.exit(1)
    
    wallet = sys.argv[1]
    
    if not HELIUS_API_KEY:
        print("❌ Error: HELIUS_API_KEY environment variable not set")
        sys.exit(1)
    
    log(f"Calculating 90D PnL for {wallet[:20]}...")
    pnl_data = await calculate_wallet_pnl_simple(wallet)
    print("\n" + format_pnl_summary(pnl_data))


if __name__ == "__main__":
    asyncio.run(main())
