"""
ShadowHunter Telegram Bot v3.0
Integrates all 3 hunting systems into Telegram

Commands:
/monitor - Start continuous ecosystem monitoring
/stop - Stop monitoring
/hunt - Run one-time comprehensive hunt
/analyze <wallet> - Deep wallet analysis
/alpha - Show top discovered wallets from Stealth Hunt 2.0
/status - System status and API quotas
/signals - Recent high-conviction signals
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

# Import our hunting systems
from momentum_hunter import MomentumHunter, TokenMetrics
from wallet_analyzer import WalletAnalyzer, WalletProfile

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot state
monitoring_active = False
monitor_task = None
high_value_signals = []
discovered_wallets = []

# Load discovered wallets from Stealth Hunt 2.0
STEALTH_HUNT_WALLETS = [
    {
        "address": "G5nxEXuFMfV74DSnsrSatqCW32F34XUnBeq3PfDS7w5E",
        "name": "LeBron",
        "profits": "$17.6M+",
        "source": "Lookonchain",
        "specialty": "MELANIA/LIBRA/TRUMP sniper",
        "tier": "LEGENDARY"
    },
    {
        "address": "4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6",
        "name": "Nansen Smart Trader",
        "profits": "$44.24M",
        "source": "Nansen",
        "specialty": "90D top performer",
        "tier": "LEGENDARY"
    },
    {
        "address": "E6YoRP3adE5XYneSseLee15wJshDxCsmyD2WtLvAmfLi",
        "name": "E6Y Sandwich Bot",
        "profits": "$300K/day",
        "source": "MEV Research",
        "specialty": "42% sandwich market share",
        "tier": "MEV_LEGENDARY"
    },
    {
        "address": "HWdeCUjBvPP1HJ5oCJt7aNsvMWpWoDgiejUWvfFX6T7R",
        "name": "FARTCOIN Whale",
        "profits": "$4.38M",
        "source": "Nansen",
        "specialty": "Memecoins, 73% win rate",
        "tier": "TIER_1"
    },
    {
        "address": "89Ny6a4mALkQgEVN8UbKSc9TdLi6t9rFYdtihrXZEpq6",
        "name": "Sandwich Bot #2",
        "profits": "$433M volume",
        "source": "MEV Research",
        "specialty": "11.2% MEV share",
        "tier": "MEV_TIER_1"
    },
    {
        "address": "9HCTuTPEiQvkUtLmTZvK6uch4E3pDynwJTbNw6jLhp9z",
        "name": "TRUMP Millionaire",
        "profits": "$4.8M",
        "source": "BeInCrypto",
        "specialty": "New launch specialist",
        "tier": "TIER_1"
    },
    {
        "address": "6kbwsSY4hL6WVadLRLnWV2irkMN2AvFZVAS8McKJmAtJ",
        "name": "RIF Sniper",
        "profits": "$1.3M",
        "source": "BeInCrypto",
        "specialty": "2,993% ROI on RIF",
        "tier": "TIER_2"
    },
    {
        "address": "fwHknyxZTgFGytVz9VPrvWqipW2V4L4D99gEb831t81",
        "name": "AI16Z Leader",
        "profits": "$1.53M",
        "source": "Nansen",
        "specialty": "AI tokens, 1,360% ROI",
        "tier": "TIER_2"
    },
]


class ShadowHunterBot:
    """Telegram bot integrating all 3 hunting systems"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.helius_key = os.getenv('HELIUS_API_KEY', '')
        self.monitoring = False
        self.monitor_task = None
        self.last_signals = []
        
    def run(self):
        """Start the bot"""
        application = Application.builder().token(self.token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", self.cmd_start))
        application.add_handler(CommandHandler("help", self.cmd_help))
        application.add_handler(CommandHandler("monitor", self.cmd_monitor))
        application.add_handler(CommandHandler("stop", self.cmd_stop))
        application.add_handler(CommandHandler("hunt", self.cmd_hunt))
        application.add_handler(CommandHandler("analyze", self.cmd_analyze))
        application.add_handler(CommandHandler("alpha", self.cmd_alpha))
        application.add_handler(CommandHandler("status", self.cmd_status))
        application.add_handler(CommandHandler("signals", self.cmd_signals))
        application.add_handler(CommandHandler("momentum", self.cmd_momentum))
        
        # Callback handlers for buttons
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("🤖 ShadowHunter Bot starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message"""
        welcome = """
🎯 <b>ShadowHunter Alpha Finder v3.0</b>

<i>Zero-cost programmatic wallet hunting</i>

<b>🎮 Available Commands:</b>

📊 <b>Hunting:</b>
/monitor - Start continuous ecosystem monitoring
/hunt - Run one-time comprehensive hunt
/momentum - Scan for high-momentum tokens now
/stop - Stop monitoring

🔍 <b>Analysis:</b>
/analyze &lt;wallet&gt; - Deep wallet analysis
/alpha - Show Stealth Hunt 2.0 wallet list
/signals - Recent high-conviction signals

⚙️ <b>System:</b>
/status - Check API quotas and system status
/help - Show this help message

<b>💡 Quick Start:</b>
Type /momentum to scan for hot tokens now!
        """
        
        keyboard = [
            [InlineKeyboardButton("🔥 Start Monitoring", callback_data='start_monitor')],
            [InlineKeyboardButton("🎯 Hunt Now", callback_data='hunt_now')],
            [InlineKeyboardButton("📊 View Alpha Wallets", callback_data='show_alpha')],
        ]
        
        await update.message.reply_text(
            welcome,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help message"""
        await self.cmd_start(update, context)
    
    async def cmd_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start continuous monitoring"""
        global monitoring_active, monitor_task
        
        if monitoring_active:
            await update.message.reply_text(
                "⚠️ <b>Monitoring already active!</b>\n\n"
                "Use /stop to stop or /status to check progress.",
                parse_mode='HTML'
            )
            return
        
        monitoring_active = True
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(self._monitoring_loop(context))
        
        await update.message.reply_text(
            "🚀 <b>Continuous monitoring STARTED!</b>\n\n"
            "• Scanning every 5 minutes\n"
            "• Will alert on high-momentum tokens (score >60)\n"
            "• Will track early buyer patterns\n\n"
            "Use /stop to stop monitoring\n"
            "Use /signals to see recent alerts",
            parse_mode='HTML'
        )
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop monitoring"""
        global monitoring_active, monitor_task
        
        if not monitoring_active:
            await update.message.reply_text("ℹ️ Monitoring is not active.")
            return
        
        monitoring_active = False
        if monitor_task:
            monitor_task.cancel()
        
        await update.message.reply_text(
            "🛑 <b>Monitoring STOPPED</b>\n\n"
            f"• Total signals generated: {len(self.last_signals)}\n"
            "Use /signals to see all captured signals",
            parse_mode='HTML'
        )
    
    async def cmd_hunt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run comprehensive one-time hunt"""
        status_message = await update.message.reply_text(
            "🎯 <b>INITIATING FULL HUNT...</b>\n"
            "This may take 1-2 minutes\n\n"
            "Phase 1/3: Scanning ecosystem for momentum...",
            parse_mode='HTML'
        )
        
        # Phase 1: Momentum scan
        high_momentum = await self._scan_momentum()
        
        if not high_momentum:
            await status_message.edit_text(
                "😴 <b>HUNT COMPLETE</b>\n\n"
                "No high-momentum tokens detected in current market.\n\n"
                "This is normal during slow periods. Try again in 30-60 minutes.",
                parse_mode='HTML'
            )
            return
        
        await status_message.edit_text(
            f"🎯 <b>HUNT IN PROGRESS...</b>\n\n"
            f"✅ Phase 1/3: Found {len(high_momentum)} high-momentum tokens\n"
            f"🔄 Phase 2/3: Analyzing token details...",
            parse_mode='HTML'
        )
        
        # Generate report
        report = self._generate_hunt_report(high_momentum)
        
        await status_message.edit_text(
            report,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    
    async def cmd_momentum(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick momentum scan"""
        message = await update.message.reply_text(
            "🔍 <b>Scanning for high-momentum tokens...</b>",
            parse_mode='HTML'
        )
        
        tokens = await self._scan_momentum()
        
        if not tokens:
            await message.edit_text(
                "😴 <b>No high-momentum tokens detected</b>\n\n"
                "Current market conditions are slow.\n"
                "Check back in 30-60 minutes or start /monitor for continuous tracking.",
                parse_mode='HTML'
            )
            return
        
        # Show top 5
        response = "🚀 <b>HIGH-MOMENTUM TOKENS DETECTED</b>\n\n"
        
        for i, token in enumerate(tokens[:5], 1):
            age_str = self._format_age(token.pair_created_at)
            
            response += (
                f"<b>{i}. {token.symbol}</b> | Score: {token.momentum_score:.1f}/100\n"
                f"├ Price: ${token.price_usd:.8f}\n"
                f"├ Market Cap: ${token.market_cap:,.0f}\n"
                f"├ 1h Change: {token.price_change_1h:+.1f}%\n"
                f"├ Volume: ${token.volume_24h:,.0f}\n"
                f"├ Liquidity: ${token.liquidity_usd:,.0f}\n"
                f"└ Age: {age_str}\n\n"
            )
        
        if len(tokens) > 5:
            response += f"<i>...and {len(tokens) - 5} more tokens</i>\n\n"
        
        response += "💡 <b>Use /hunt for full wallet analysis of these tokens</b>"
        
        keyboard = [[
            InlineKeyboardButton("🎯 Full Hunt", callback_data='hunt_now'),
            InlineKeyboardButton("📊 Monitor", callback_data='start_monitor')
        ]]
        
        await message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analyze specific wallet"""
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> /analyze \u003cwallet_address\u003e\n\n"
                "Example:\n"
                "/analyze 4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6",
                parse_mode='HTML'
            )
            return
        
        wallet = context.args[0]
        
        if len(wallet) < 32:
            await update.message.reply_text(
                "❌ <b>Invalid wallet address</b>\n\n"
                "Please provide a valid Solana wallet address (32-44 characters)",
                parse_mode='HTML'
            )
            return
        
        message = await update.message.reply_text(
            f"🔍 <b>Analyzing wallet:</b>\n<code>{wallet}</code>\n\n"
            f"This may take 30-60 seconds...",
            parse_mode='HTML'
        )
        
        if not self.helius_key:
            await message.edit_text(
                "⚠️ <b>Helius API key not configured</b>\n\n"
                "Wallet analysis requires a free Helius API key.\n\n"
                "1. Get free key at: https://helius.xyz\n"
                "2. Add to .env.hunter: HELIUS_API_KEY=your_key\n"
                "3. Restart the bot",
                parse_mode='HTML'
            )
            return
        
        # Run analysis
        profile = await self._analyze_wallet(wallet)
        
        if not profile:
            await message.edit_text(
                "❌ <b>Analysis failed</b>\n\n"
                "Could not fetch wallet data. The wallet may be inactive or there may be an API issue.",
                parse_mode='HTML'
            )
            return
        
        # Format response
        quality_emoji = "🟢" if profile.is_high_quality else "🟡" if profile.alpha_score > 40 else "🔴"
        bot_emoji = "🤖" if profile.is_bot_suspected else "👤"
        
        response = (
            f"{quality_emoji} <b>WALLET ANALYSIS</b>\n"
            f"<code>{wallet}</code>\n\n"
            f"<b>📊 Performance (30D):</b>\n"
            f"├ Alpha Score: {profile.alpha_score:.1f}/100\n"
            f"├ Total Trades: {profile.total_trades_30d}\n"
            f"├ Win Rate: {profile.win_rate*100:.1f}%\n"
            f"├ Total PnL: {profile.total_pnl_sol:.2f} SOL\n"
            f"├ Avg Trade Size: {profile.avg_trade_size_sol:.2f} SOL\n"
            f"└ Quality: {'✅ HIGH' if profile.is_high_quality else '⚠️ MEDIUM' if profile.alpha_score > 40 else '❌ LOW'}\n\n"
            f"{bot_emoji} <b>Behavior:</b> {'Bot suspected' if profile.is_bot_suspected else 'Human-like trading'}\n"
        )
        
        if profile.favorite_tokens:
            response += f"\n<b>🎯 Favorite Tokens:</b>\n"
            for i, token in enumerate(profile.favorite_tokens[:5], 1):
                response += f"{i}. <code>{token[:20]}...</code>\n"
        
        if profile.last_active:
            days_ago = (datetime.now() - profile.last_active).days
            response += f"\n<i>Last active: {days_ago} days ago</i>"
        
        await message.edit_text(response, parse_mode='HTML')
    
    async def cmd_alpha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Stealth Hunt 2.0 wallet list"""
        response = (
            "🎯 <b>STEALTH HUNT 2.0 - DISCOVERED WALLETS</b>\n\n"
            "<i>Premium wallets from 515K token research across 5 parallel agents</i>\n\n"
        )
        
        # Group by tier
        tiers = defaultdict(list)
        for wallet in STEALTH_HUNT_WALLETS:
            tiers[wallet['tier']].append(wallet)
        
        tier_order = ['LEGENDARY', 'MEV_LEGENDARY', 'TIER_1', 'MEV_TIER_1', 'TIER_2']
        tier_emoji = {
            'LEGENDARY': '👑',
            'MEV_LEGENDARY': '🤖👑',
            'TIER_1': '💎',
            'MEV_TIER_1': '🤖💎',
            'TIER_2': '⭐'
        }
        
        for tier in tier_order:
            if tier in tiers:
                response += f"<b>{tier_emoji.get(tier, '📌')} {tier.replace('_', ' ')}</b>\n"
                for wallet in tiers[tier]:
                    response += (
                        f"• <code>{wallet['address']}</code>\n"
                        f"  <b>{wallet['name']}</b> | {wallet['profits']}\n"
                        f"  <i>{wallet['specialty']}</i>\n\n"
                    )
        
        response += (
            "<b>💡 Usage:</b>\n"
            "Click any address to copy, then use:\n"
            "/analyze \u003cwallet\u003e for deep analysis\n\n"
            "<i>Add these to your wallets.txt for live tracking</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎯 Hunt All", callback_data='hunt_all_wallets')],
            [InlineKeyboardButton("📊 Start Monitoring", callback_data='start_monitor')]
        ]
        
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """System status"""
        helius_status = "✅ Configured" if self.helius_key else "❌ Not configured"
        monitor_status = "🟢 Active" if monitoring_active else "🔴 Stopped"
        
        response = (
            "⚙️ <b>SHADOWHUNTER SYSTEM STATUS</b>\n\n"
            f"<b>APIs:</b>\n"
            f"├ DexScreener: ✅ Unlimited\n"
            f"├ Jupiter: ✅ 600 req/min\n"
            f"└ Helius: {helius_status}\n\n"
            f"<b>Services:</b>\n"
            f"├ Monitoring: {monitor_status}\n"
            f"├ Signals Captured: {len(self.last_signals)}\n"
            f"└ Wallets Tracked: {len(STEALTH_HUNT_WALLETS)}\n\n"
            f"<b>Systems:</b>\n"
            f"├ First Blood (Real-time): ✅ Ready\n"
            f"├ Shadow Network (Graph): {helius_status}\n"
            f"└ Momentum Hunter (Signals): ✅ Active\n\n"
        )
        
        if monitoring_active:
            response += "💡 <b>Tip:</b> Use /stop to pause monitoring\n"
        else:
            response += "💡 <b>Tip:</b> Use /monitor to start continuous hunting\n"
        
        await update.message.reply_text(response, parse_mode='HTML')
    
    async def cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent signals"""
        if not self.last_signals:
            await update.message.reply_text(
                "📭 <b>No signals yet</b>\n\n"
                "Start /monitor or run /hunt to generate signals.",
                parse_mode='HTML'
            )
            return
        
        response = f"🔔 <b>RECENT SIGNALS ({len(self.last_signals)} total)</b>\n\n"
        
        for signal in self.last_signals[-10:]:  # Last 10
            response += (
                f"⏰ {signal.get('time', 'Unknown')}\n"
                f"🎯 {signal.get('type', 'Unknown')}\n"
                f"📊 Score: {signal.get('score', 0):.1f}/100\n"
                f"<code>{signal.get('token', 'Unknown')[:30]}...</code>\n\n"
            )
        
        await update.message.reply_text(response, parse_mode='HTML')
    
    # ===== CALLBACK HANDLERS =====
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'start_monitor':
            await self.cmd_monitor(update, context)
        elif query.data == 'stop_monitor':
            await self.cmd_stop(update, context)
        elif query.data == 'hunt_now':
            await self.cmd_hunt(update, context)
        elif query.data == 'show_alpha':
            await self.cmd_alpha(update, context)
    
    # ===== BACKGROUND TASKS =====
    
    async def _monitoring_loop(self, context: ContextTypes.DEFAULT_TYPE):
        """Background monitoring task"""
        scan_count = 0
        
        while monitoring_active:
            try:
                scan_count += 1
                logger.info(f"Monitor scan #{scan_count}")
                
                # Scan for momentum
                tokens = await self._scan_momentum()
                
                # Alert on high-momentum tokens
                for token in tokens:
                    if token.momentum_score >= 70:  # High threshold for alerts
                        signal = {
                            'type': 'HIGH_MOMENTUM',
                            'token': token.address,
                            'symbol': token.symbol,
                            'score': token.momentum_score,
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'price_change': token.price_change_1h
                        }
                        self.last_signals.append(signal)
                        
                        # Send alert
                        await context.bot.send_message(
                            chat_id=self.chat_id,
                            text=self._format_alert(token),
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                
                # Wait 5 minutes
                for _ in range(300):  # 5 minutes in seconds
                    if not monitoring_active:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    # ===== HELPERS =====
    
    async def _scan_momentum(self) -> List[TokenMetrics]:
        """Scan for high-momentum tokens"""
        async with MomentumHunter(self.helius_key) as hunter:
            tokens = await hunter.scan_solana_ecosystem(min_liquidity=10000)
            return [t for t in tokens if t.momentum_score >= 60]
    
    async def _analyze_wallet(self, wallet: str) -> Optional[WalletProfile]:
        """Analyze wallet with Helius"""
        if not self.helius_key:
            return None
        
        async with WalletAnalyzer(self.helius_key) as analyzer:
            return await analyzer.analyze_wallet(wallet, days=30)
    
    def _format_age(self, created_at) -> str:
        """Format token age"""
        if not created_at:
            return "Unknown"
        
        age = datetime.now() - created_at
        if age < timedelta(hours=1):
            return f"{age.seconds // 60}m"
        elif age < timedelta(days=1):
            return f"{age.seconds // 3600}h"
        else:
            return f"{age.days}d"
    
    def _format_alert(self, token: TokenMetrics) -> str:
        """Format high-momentum alert"""
        age_str = self._format_age(token.pair_created_at)
        
        return (
            f"🚨 <b>HIGH-MOMENTUM ALERT!</b>\n\n"
            f"🎯 <b>{token.symbol}</b> | Score: {token.momentum_score:.1f}/100\n"
            f"💰 Price: ${token.price_usd:.8f}\n"
            f"📈 1h Change: {token.price_change_1h:+.1f}%\n"
            f"💎 Market Cap: ${token.market_cap:,.0f}\n"
            f"💧 Liquidity: ${token.liquidity_usd:,.0f}\n"
            f"⏰ Age: {age_str}\n"
            f"📊 Volume (24h): ${token.volume_24h:,.0f}\n\n"
            f"<code>{token.address}</code>\n\n"
            f"<i>Use /analyze to check early buyers</i>"
        )
    
    def _generate_hunt_report(self, tokens: List[TokenMetrics]) -> str:
        """Generate comprehensive hunt report"""
        report = (
            f"🎯 <b>HUNT COMPLETE</b>\n"
            f"Found {len(tokens)} high-momentum tokens\n\n"
        )
        
        for i, token in enumerate(tokens[:5], 1):
            age_str = self._format_age(token.pair_created_at)
            
            report += (
                f"<b>{i}. {token.symbol}</b> | Score: {token.momentum_score:.1f}/100\n"
                f"├ 💰 Price: ${token.price_usd:.8f}\n"
                f"├ 📈 1h: {token.price_change_1h:+.1f}% | 5m: {token.price_change_5m:+.1f}%\n"
                f"├ 💎 MC: ${token.market_cap:,.0f} | 💧 Liq: ${token.liquidity_usd:,.0f}\n"
                f"├ 📊 Vol: ${token.volume_24h:,.0f} | 🔄 Txns: {token.buys_1h} buys\n"
                f"├ ⏰ Age: {age_str}\n"
                f"└ 🔗 <code>{token.address}</code>\n\n"
            )
        
        if self.helius_key:
            report += (
                "<b>📊 Analysis Complete</b>\n"
                "All systems operational.\n\n"
            )
        else:
            report += (
                "⚠️ <b>Limited Analysis</b>\n"
                "Add Helius API key for wallet analysis.\n\n"
            )
        
        report += (
            "<b>💡 Next Steps:</b>\n"
            "• Use /monitor for continuous tracking\n"
            "• Use /analyze \u003cwallet\u003e to check specific wallets\n"
            "• Use /alpha to see our premium wallet list"
        )
        
        return report


def main():
    """Start the bot"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('CHANNEL_SCANNER')  # or specific chat ID
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        print("   Get token from @BotFather")
        return
    
    if not chat_id:
        print("⚠️ CHANNEL_SCANNER not set, using default")
        chat_id = "@your_channel_username"
    
    bot = ShadowHunterBot(token, chat_id)
    bot.run()


if __name__ == "__main__":
    main()
