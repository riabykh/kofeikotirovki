#!/usr/bin/env python3
"""
Clear Telegram webhook and pending updates to resolve conflicts
"""

import asyncio
import os
import sys
from telegram import Bot

async def clear_webhook_and_updates():
    """Clear webhook and pending updates"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not found in environment")
            return False
            
        bot = Bot(token=bot_token)
        
        print("🧹 Clearing Telegram webhook...")
        # Delete webhook to stop any external polling
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook cleared")
        
        print("🧹 Clearing pending updates...")
        # Get and clear all pending updates
        updates = await bot.get_updates()
        if updates:
            # Get updates with offset to clear them
            last_update_id = updates[-1].update_id
            await bot.get_updates(offset=last_update_id + 1, limit=1)
            print(f"✅ Cleared {len(updates)} pending updates")
        else:
            print("✅ No pending updates found")
            
        return True
        
    except Exception as e:
        print(f"❌ Error clearing webhook/updates: {e}")
        return False

async def main():
    print("🤖 Telegram Bot Conflict Resolver")
    print("=" * 35)
    
    success = await clear_webhook_and_updates()
    
    if success:
        print("\n🎉 Successfully cleared webhook and updates!")
        print("💡 You can now start your bot safely")
        return 0
    else:
        print("\n❌ Failed to clear webhook/updates")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
