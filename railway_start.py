#!/usr/bin/env python3
"""
Railway-specific startup script with enhanced conflict resolution
"""

import os
import sys
import time
import requests
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def clear_telegram_webhook(bot_token):
    """Clear webhook with retries"""
    for attempt in range(3):
        try:
            logger.info(f"🧹 Attempt {attempt + 1}: Clearing Telegram webhook...")
            webhook_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook?drop_pending_updates=true"
            response = requests.post(webhook_url, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Webhook cleared successfully")
                return True
            else:
                logger.warning(f"Webhook clear response: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
        if attempt < 2:  # Don't sleep after last attempt
            time.sleep(5)
    
    logger.error("❌ Failed to clear webhook after 3 attempts")
    return False

def main():
    logger.info("🚂 Railway Bot Startup - Enhanced Conflict Resolution")
    logger.info("=" * 50)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Environment variables loaded")
    except Exception as e:
        logger.warning(f"Could not load .env file: {e}")
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found")
        sys.exit(1)
    
    # Clear webhook with retries
    logger.info("🔧 Preparing Telegram connection...")
    if clear_telegram_webhook(bot_token):
        logger.info("✅ Telegram webhook cleared - ready for polling")
    else:
        logger.warning("⚠️ Webhook clear failed - proceeding anyway")
    
    # Wait for Telegram to process
    logger.info("⏳ Waiting for Telegram to process changes...")
    time.sleep(5)
    
    # Start the main bot
    logger.info("🚀 Starting main bot application...")
    try:
        # Import and run the main bot
        from stock_bot import main
        main()
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
