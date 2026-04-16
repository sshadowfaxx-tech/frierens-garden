"""
Claude-Powered Trading Integration

Sends alerts to Claude API for trading decisions,
then executes via Sol CLI on FX 6300.
"""

import os
import json
import httpx
from typing import Dict

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
CLAUDE_MODEL = "claude-4-6-20251001"  # Or latest

TRADING_PROMPT = """You are an expert Solana memecoin trader. Analyze this alert and decide:

TOKEN: {symbol}
ADDRESS: {token}
NARRATIVE: {narrative}
MARKET CAP: {market_cap}
LIQUIDITY: {liquidity}
AGE: {age_hours}h

WALLET ACTIVITY:
{wallet_summary}

Total Weight: {total_weight}x

DECISION OPTIONS:
1. BUY - Enter position (specify SOL amount 0.1-0.5)
2. HOLD - Already have position, do nothing
3. SKIP - Don't trade this

RESPOND IN JSON:
{{
    "decision": "BUY|HOLD|SKIP",
    "confidence": 0-100,
    "reasoning": "Why you chose this",
    "sol_amount": 0.0,  // Only if BUY
    "stop_loss": 0.0,   // % below entry
    "take_profit": [50, 100, 200]  // % targets to ladder out
}}
"""

async def get_claude_decision(alert_data: Dict) -> Dict:
    """Send alert to Claude API and get trading decision"""
    
    # Format wallet summary
    wallet_summary = ""
    for w in alert_data.get('wallets', []):
        wallet_summary += f"- {w['label']} ({w['weight']}x): {w['winrate']:.0f}% WR, {w['pnl']:+.1f} SOL\n"
    
    # Build prompt
    prompt = TRADING_PROMPT.format(
        symbol=alert_data.get('symbol', 'Unknown'),
        token=alert_data['token'],
        narrative=alert_data.get('narrative', 'Unknown'),
        market_cap=alert_data.get('market_cap', 0),
        liquidity=alert_data.get('liquidity', 0),
        age_hours=alert_data.get('age_hours', 0),
        wallet_summary=wallet_summary,
        total_weight=alert_data.get('total_weight', 0)
    )
    
    # Call Claude API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API error: {response.text}")
        
        result = response.json()
        content = result['content'][0]['text']
        
        # Parse JSON from Claude's response
        # Claude might wrap it in markdown, so extract JSON
        if '```json' in content:
            json_str = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            json_str = content.split('```')[1].split('```')[0].strip()
        else:
            json_str = content.strip()
        
        return json.loads(json_str)

async def execute_trade(decision: Dict, token: str, symbol: str):
    """Execute trade via Sol CLI"""
    
    if decision['decision'] != 'BUY':
        return None
    
    amount = decision.get('sol_amount', 0.2)
    
    # Execute via Sol CLI
    import subprocess
    
    result = subprocess.run(
        ["sol", "token", "swap", str(amount), "sol", token, "--yes"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Trade failed: {result.stderr}")
    
    return {
        "amount": amount,
        "token": token,
        "symbol": symbol,
        "output": result.stdout
    }

# Integration into agent_full_visibility.py:
# Replace the decision logic with:
# decision = await get_claude_decision(alert_data)
# if decision['decision'] == 'BUY':
#     result = await execute_trade(decision, token, symbol)
