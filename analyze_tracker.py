#!/usr/bin/env python3
"""
ShadowHunter Tracker Log Analyzer
Parses HTML log files and calculates PnL and winrate for each wallet
"""

import re
import json
from collections import defaultdict
from datetime import datetime

# Read all three log files
file_paths = [
    '/root/.openclaw/media/inbound/1d3958d4-a699-4263-b2eb-6b8fa6fb38e6',
    '/root/.openclaw/media/inbound/e32c473f-470d-4693-aa1b-d57cfd4e1657',
    '/root/.openclaw/media/inbound/b61b1ddb-20d8-4d9e-a300-e386199ce9ec'
]

all_content = []
for fp in file_paths:
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            all_content.append(f.read())
    except Exception as e:
        print(f"Error reading {fp}: {e}")

# Pattern to match trade alerts
# BUY ALERT pattern
buy_pattern = re.compile(
    r'🟢\s*<strong>BUY ALERT</strong><br>👤\s*<strong>Wallet:</strong>\s*<strong>([^<]+)</strong><br><code>([^<]+)</code><br><br><strong>([^<]+)</strong>\s*\([^)]*\)<br><code>([^<]+)</code><br><br><strong>Market Cap:</strong>\s*<code>([^<]+)</code><br><strong>Price:</strong>\s*<code>([^<]+)</code><br>💰\s*<strong>Buy Amount:</strong>\s*<code>([\d.]+)\s*SOL</code><br>🕐\s*<strong>Time:</strong>\s*<code>(\d{2}:\d{2}:\d{2})</code>',
    re.DOTALL
)

# SELL ALERT pattern  
sell_pattern = re.compile(
    r'🔴\s*<strong>SELL ALERT</strong><br>👤\s*<strong>Wallet:</strong>\s*<strong>([^<]+)</strong><br><code>([^<]+)</code><br><br><strong>([^<]+)</strong>\s*\([^)]*\)<br><code>([^<]+)</code><br><br><strong>Market Cap:</strong>\s*<code>([^<]+)</code><br><strong>Price:</strong>\s*<code>([^<]+)</code><br>💰\s*<strong>Sell Amount:</strong>\s*<code>([\d.]+)\s*SOL</code><br>🕐\s*<strong>Time:</strong>\s*<code>(\d{2}:\d{2}:\d{2})</code>',
    re.DOTALL
)

# Date extraction
date_pattern = re.compile(r'<div class="body details">\s*(\d{2})\s+([A-Za-z]+)\s+(\d{4})\s*</div>')

# Parse all trades
trades = []

for content in all_content:
    # Find all dates in the file
    current_date = None
    
    # Simple date tracking - look for date headers
    lines = content.split('\n')
    file_date = None
    
    for line in lines:
        # Try to extract date from service messages
        if 'message service' in line or 'body details' in line:
            date_match = re.search(r'(\d{2})\s+([A-Za-z]+)\s+(\d{4})', line)
            if date_match:
                day, month_str, year = date_match.groups()
                month_map = {
                    'March': 3, 'April': 4, 'May': 5, 'June': 6,
                    'July': 7, 'August': 8, 'September': 9, 'October': 10,
                    'November': 11, 'December': 12, 'January': 1, 'February': 2
                }
                month = month_map.get(month_str, 3)
                file_date = f"{year}-{month:02d}-{day}"
        
        # Look for BUY alerts
        if 'BUY ALERT' in line and 'Buy Amount' in line:
            # Extract using regex on the full message block
            pass
    
    # More robust: extract all message blocks first
    message_pattern = re.compile(
        r'<div class="message default[^"]*"[^>]*>.*?<div class="text">(.*?)</div>\s*</div>\s*</div>',
        re.DOTALL
    )
    
    messages = message_pattern.findall(content)
    
    for msg in messages:
        # Check for BUY
        if '🟢' in msg and 'BUY ALERT' in msg:
            # Extract wallet name
            wallet_match = re.search(r'<strong>Wallet:</strong>\s*<strong>([^<]+)</strong>', msg)
            wallet_addr_match = re.search(r'<code>([^<]+)</code>', msg)
            token_match = re.search(r'<br><br><strong>([^<]+)</strong>', msg)
            token_addr_match = re.search(r'<code>([A-Za-z0-9]{32,44})</code>', msg)
            amount_match = re.search(r'Buy Amount:</strong>\s*<code>([\d.]+)\s*SOL', msg)
            time_match = re.search(r'Time:</strong>\s*<code>([\d:]+)</code>', msg)
            
            if wallet_match and amount_match:
                trades.append({
                    'type': 'BUY',
                    'wallet_name': wallet_match.group(1).strip(),
                    'wallet_address': wallet_addr_match.group(1) if wallet_addr_match else 'Unknown',
                    'token': token_match.group(1) if token_match else 'Unknown',
                    'token_address': token_addr_match.group(1) if token_addr_match else 'Unknown',
                    'amount_sol': float(amount_match.group(1)),
                    'time': time_match.group(1) if time_match else 'Unknown',
                    'date': file_date or 'Unknown'
                })
        
        # Check for SELL
        if '🔴' in msg and 'SELL ALERT' in msg:
            wallet_match = re.search(r'<strong>Wallet:</strong>\s*<strong>([^<]+)</strong>', msg)
            wallet_addr_match = re.search(r'<code>([^<]+)</code>', msg)
            token_match = re.search(r'<br><br><strong>([^<]+)</strong>', msg)
            token_addr_match = re.search(r'<code>([A-Za-z0-9]{32,44})</code>', msg)
            amount_match = re.search(r'Sell Amount:</strong>\s*<code>([\d.]+)\s*SOL', msg)
            time_match = re.search(r'Time:</strong>\s*<code>([\d:]+)</code>', msg)
            
            if wallet_match and amount_match:
                trades.append({
                    'type': 'SELL',
                    'wallet_name': wallet_match.group(1).strip(),
                    'wallet_address': wallet_addr_match.group(1) if wallet_addr_match else 'Unknown',
                    'token': token_match.group(1) if token_match else 'Unknown',
                    'token_address': token_addr_match.group(1) if token_addr_match else 'Unknown',
                    'amount_sol': float(amount_match.group(1)),
                    'time': time_match.group(1) if time_match else 'Unknown',
                    'date': file_date or 'Unknown'
                })

print(f"Total trades extracted: {len(trades)}")
print(f"BUY trades: {len([t for t in trades if t['type'] == 'BUY'])}")
print(f"SELL trades: {len([t for t in trades if t['type'] == 'SELL'])}")

# Group by wallet
wallets = defaultdict(lambda: {'buys': [], 'sells': []})

for trade in trades:
    wallet_key = f"{trade['wallet_name']} ({trade['wallet_address'][:8]}...)"
    if trade['type'] == 'BUY':
        wallets[wallet_key]['buys'].append(trade)
    else:
        wallets[wallet_key]['sells'].append(trade)

print(f"\n\n{'='*80}")
print("WALLET PERFORMANCE ANALYSIS")
print("="*80)

# Calculate metrics for each wallet
results = []

for wallet_name, data in sorted(wallets.items()):
    buys = data['buys']
    sells = data['sells']
    
    total_bought = sum(b['amount_sol'] for b in buys)
    total_sold = sum(s['amount_sol'] for s in sells)
    
    # PnL calculation: (Total Sold - Total Bought)
    pnl = total_sold - total_bought
    
    # Winrate calculation
    # For each token, check if there's a matching buy and sell
    # A "win" is when sell amount > buy amount for a position
    
    # Group by token
    token_positions = defaultdict(lambda: {'buys': [], 'sells': []})
    
    for b in buys:
        token_positions[b['token']]['buys'].append(b['amount_sol'])
    for s in sells:
        token_positions[s['token']]['sells'].append(s['amount_sol'])
    
    wins = 0
    losses = 0
    incomplete = 0
    
    position_details = []
    
    for token, pos_data in token_positions.items():
        buy_total = sum(pos_data['buys'])
        sell_total = sum(pos_data['sells'])
        
        if pos_data['buys'] and pos_data['sells']:
            # Complete position
            if sell_total > buy_total:
                wins += 1
                result = "WIN"
            else:
                losses += 1
                result = "LOSS"
            position_details.append({
                'token': token,
                'buy': buy_total,
                'sell': sell_total,
                'pnl': sell_total - buy_total,
                'result': result
            })
        elif pos_data['buys'] and not pos_data['sells']:
            # Open position (no sell recorded)
            incomplete += 1
            position_details.append({
                'token': token,
                'buy': buy_total,
                'sell': 0,
                'pnl': -buy_total,  # Assuming full loss if not sold
                'result': 'OPEN'
            })
        elif pos_data['sells'] and not pos_data['buys']:
            # Sell without recorded buy (incomplete data)
            incomplete += 1
            position_details.append({
                'token': token,
                'buy': 0,
                'sell': sell_total,
                'pnl': sell_total,
                'result': 'MISSING_BUY'
            })
    
    total_positions = wins + losses
    winrate = (wins / total_positions * 100) if total_positions > 0 else 0
    
    results.append({
        'wallet': wallet_name,
        'total_bought': total_bought,
        'total_sold': total_sold,
        'pnl': pnl,
        'wins': wins,
        'losses': losses,
        'incomplete': incomplete,
        'winrate': winrate,
        'positions': position_details
    })

# Sort by PnL (highest to lowest)
results.sort(key=lambda x: x['pnl'], reverse=True)

# Print summary
print("\n\n📊 WALLET PERFORMANCE SUMMARY")
print("-" * 100)
print(f"{'Wallet':<40} {'Total SOL In':>12} {'Total SOL Out':>14} {'PnL (SOL)':>12} {'Winrate':>10} {'Trades':>8}")
print("-" * 100)

for r in results:
    wallet_short = r['wallet'][:38] + '..' if len(r['wallet']) > 40 else r['wallet']
    pnl_str = f"{r['pnl']:+.4f}"
    pnl_color = "🟢" if r['pnl'] > 0 else "🔴" if r['pnl'] < 0 else "⚪"
    winrate_str = f"{r['winrate']:.1f}%" if r['wins'] + r['losses'] > 0 else "N/A"
    trades_str = f"{r['wins']}W/{r['losses']}L"
    
    print(f"{wallet_short:<40} {r['total_bought']:>12.4f} {r['total_sold']:>14.4f} {pnl_color} {pnl_str:>10} {winrate_str:>10} {trades_str:>8}")

print("-" * 100)

# Detailed breakdown for each wallet
print("\n\n📋 DETAILED WALLET BREAKDOWN")
print("=" * 100)

for r in results:
    print(f"\n{'='*80}")
    print(f"👤 {r['wallet']}")
    print(f"{'='*80}")
    print(f"   Total Invested: {r['total_bought']:.4f} SOL")
    print(f"   Total Returned: {r['total_sold']:.4f} SOL")
    print(f"   Net PnL: {r['pnl']:+.4f} SOL ({((r['pnl']/r['total_bought'])*100 if r['total_bought'] > 0 else 0):+.2f}%)")
    print(f"   Winrate: {r['winrate']:.1f}% ({r['wins']} wins, {r['losses']} losses, {r['incomplete']} incomplete)")
    
    if r['positions']:
        print(f"\n   Position Details:")
        print(f"   {'Token':<25} {'Buy (SOL)':>12} {'Sell (SOL)':>12} {'PnL':>12} {'Result':>10}")
        print(f"   {'-'*75}")
        for pos in sorted(r['positions'], key=lambda x: x['pnl'], reverse=True):
            result_emoji = "🟢" if pos['result'] == 'WIN' else "🔴" if pos['result'] == 'LOSS' else "⚠️"
            print(f"   {pos['token'][:23]:<25} {pos['buy']:>12.4f} {pos['sell']:>12.4f} {pos['pnl']:>+12.4f} {result_emoji} {pos['result']:>8}")

# Summary statistics
print(f"\n\n{'='*100}")
print("📈 OVERALL SUMMARY")
print("="*100)

total_wallets = len(results)
profitable_wallets = len([r for r in results if r['pnl'] > 0])
losing_wallets = len([r for r in results if r['pnl'] < 0])
total_pnl = sum(r['pnl'] for r in results)
total_volume = sum(r['total_bought'] for r in results)

print(f"Total Wallets Analyzed: {total_wallets}")
print(f"Profitable Wallets: {profitable_wallets} ({profitable_wallets/total_wallets*100:.1f}%)")
print(f"Losing Wallets: {losing_wallets} ({losing_wallets/total_wallets*100:.1f}%)")
print(f"Neutral Wallets: {total_wallets - profitable_wallets - losing_wallets}")
print(f"\nCombined PnL: {total_pnl:+.4f} SOL")
print(f"Total Volume: {total_volume:.4f} SOL")
print(f"Average Return: {(total_pnl/total_volume*100 if total_volume > 0 else 0):+.2f}%")

# Top performers
print(f"\n🏆 TOP 3 PERFORMERS:")
for i, r in enumerate(results[:3], 1):
    print(f"   {i}. {r['wallet']} - PnL: {r['pnl']:+.4f} SOL")

print(f"\n🔻 BOTTOM 3 PERFORMERS:")
for i, r in enumerate(results[-3:], 1):
    print(f"   {i}. {r['wallet']} - PnL: {r['pnl']:+.4f} SOL")

# Export to JSON for further analysis
output_file = '/root/.openclaw/workspace/tracker_analysis.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\n💾 Detailed data exported to: {output_file}")
