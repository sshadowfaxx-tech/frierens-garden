# Add this to agent_monitor_server.py for independent operation

import os
import json
from datetime import datetime
from telegram import Bot

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LOG_CHANNEL = os.getenv('CHANNEL_AGENT_LOGS')  # Where I monitor
NOTIFY_CHANNEL = os.getenv('CHANNEL_PINGS')     # Where you get alerts

class IndependentNotifier:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
        self.decisions_file = 'agent_decisions.jsonl'
        
    async def notify_trade(self, decision, result, token_info):
        """Send trade notification to both channels"""
        
        # Format message
        emoji = "🟢" if decision.action == "BUY" else "👀" if decision.action == "WATCH" else "❌"
        
        message = f"""{emoji} *AGENT TRADE DECISION*

*{decision.symbol}*
`{decision.token}`

*Action:* {decision.action}
*Confidence:* {decision.confidence}%
*Weight:* {decision.total_weight:.1f}x

*Analysis:*
"""
        for reason in decision.reasoning[:5]:  # Top 5 reasons
            message += f"• {reason}\n"
        
        if token_info:
            message += f"\n*Token Info:*"
            message += f"\n• Narrative: {token_info.get('narrative', 'Unknown')}"
            message += f"\n• MC: ${token_info.get('market_cap', 0)/1000:.0f}K"
            message += f"\n• Age: {token_info.get('age_hours', 0):.1f}h"
            message += f"\n• Liq: ${token_info.get('liquidity', 0)/1000:.0f}K"
        
        if result:
            message += f"\n\n*Trade:* {result['amount']:.2f} SOL"
            message += f"\n*Balance:* {result['balance']:.2f} SOL"
        
        # Send to my monitoring channel
        if self.bot and LOG_CHANNEL:
            try:
                await self.bot.send_message(
                    chat_id=LOG_CHANNEL,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Failed to notify log channel: {e}")
        
        # Also send to your alerts channel (optional)
        if self.bot and NOTIFY_CHANNEL and decision.action == "BUY":
            try:
                await self.bot.send_message(
                    chat_id=NOTIFY_CHANNEL,
                    text=message,
                    parse_mode='Markdown'
                )
            except:
                pass
        
        # Save to JSONL for pattern analysis
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'token': decision.token,
            'symbol': decision.symbol,
            'action': decision.action,
            'confidence': decision.confidence,
            'weight': decision.total_weight,
            'reasoning': decision.reasoning,
            'executed_amount': result['amount'] if result else 0,
            'balance_after': result['balance'] if result else 0,
            'token_info': token_info
        }
        
        with open(self.decisions_file, 'a') as f:
            f.write(json.dumps(record) + '\n')

# Usage in agent_monitor_server.py:
# notifier = IndependentNotifier()
# await notifier.notify_trade(decision, result, research.__dict__ if research else {})
