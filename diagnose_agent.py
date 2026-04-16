import asyncio
import os
from telegram import Bot

async def diagnose():
    print("=== Agent Monitor Diagnostics ===\n")
    
    # Check environment variables
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    channel = os.getenv('CHANNEL_AGENT_LOGS')
    
    print(f"TELEGRAM_BOT_TOKEN: {'Set (' + token[:20] + '...)' if token else 'NOT SET'}")
    print(f"CHANNEL_AGENT_LOGS: {channel if channel else 'NOT SET'}")
    print()
    
    if not token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in environment")
        print("   Add to .env file: TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    if not channel:
        print("❌ ERROR: CHANNEL_AGENT_LOGS not found in environment")
        print("   Add to .env file: CHANNEL_AGENT_LOGS=-1003778576771")
        return
    
    # Test Telegram connection
    try:
        print("Testing Telegram connection...")
        bot = Bot(token=token)
        me = await bot.get_me()
        print(f"✅ Bot connected: @{me.username}")
        print(f"   Bot ID: {me.id}")
        print()
        
        # Try to send test message
        print(f"Sending test message to {channel}...")
        await bot.send_message(
            chat_id=channel,
            text="🧪 *Diagnostic Test*\n\nAgent monitor can reach Telegram!",
            parse_mode='Markdown'
        )
        print("✅ Test message sent successfully!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        if "Chat not found" in str(e):
            print("The bot is not in the channel or channel ID is wrong.")
            print("Steps to fix:")
            print("1. Add @shadowhuntermvpbot to the channel as admin")
            print("2. Forward a message from the channel to @userinfobot")
            print("3. Use the ID it gives you (starts with -100)")
        elif "Unauthorized" in str(e):
            print("Bot token is invalid or revoked.")
            print("Get a new token from @BotFather")

if __name__ == "__main__":
    asyncio.run(diagnose())
