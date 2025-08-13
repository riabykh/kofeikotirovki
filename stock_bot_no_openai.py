#!/usr/bin/env python3
"""
Temporary fallback version without OpenAI to test basic bot functionality
"""

import asyncio
import logging
import re
import signal
import sys
from datetime import datetime, timedelta
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import schedule
import time
from typing import List, Dict
import os
from dataclasses import dataclass
import sqlite3

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    published: str
    url: str = ""

@dataclass
class AssetItem:
    symbol: str
    name: str
    price: float
    change: float
    change_direction: str
    source: str = "Market Data"

class DatabaseManager:
    def __init__(self, db_path: str = "stock_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table to store subscriber information
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                subscribed BOOLEAN DEFAULT TRUE,
                language TEXT DEFAULT 'ru',
                topic_preferences TEXT DEFAULT 'all',
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                user_id INTEGER PRIMARY KEY,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update a user in the database without resetting preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use UPSERT to preserve existing preferences
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                last_active=CURRENT_TIMESTAMP
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def get_subscribed_users(self) -> List[int]:
        """Get all subscribed user IDs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE subscribed = TRUE')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_user_count(self) -> int:
        """Get total number of users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM admin_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def add_admin(self, user_id: int):
        """Add user as admin"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admin_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()

class StockNewsBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.application = Application.builder().token(bot_token).build()
        self.db = DatabaseManager()
        
        # Set up command handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("news", self.news_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Make first user admin automatically
        if self.db.get_user_count() == 1:
            self.db.add_admin(user.id)
        
        message = f"""
🎉 **Добро пожаловать в Кофе и Котировки!** 🎉

Привет, {user.first_name or user.username or "Друг"}!

📈 **Что я умею:**
• 📰 Рыночные новости и анализ
• 📊 Котировки активов  
• 🔮 Прогнозы и тенденции
• ⏰ Автоматические уведомления

**📱 Команды:**
/news - Получить новости (временно отключено - исправляем OpenAI)
/status - Проверить статус
/help - Помощь

⚠️ **Статус**: Временно работаем без OpenAI из-за технических проблем.
🔧 Исправляем совместимость библиотек...

Готов к работе! 🚀
        """
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await self.start_command(update, context)
    
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command - temporarily disabled"""
        await update.message.reply_text(
            "📰 **Новости временно недоступны**\n\n"
            "🔧 Исправляем проблему совместимости с OpenAI библиотекой.\n"
            "💡 Проблема: `AsyncClient.__init__() got an unexpected keyword argument 'proxies'`\n\n"
            "⏰ Скоро всё заработает!"
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        total_users = self.db.get_user_count()
        is_admin = self.db.is_admin(user.id)
        
        message = f"""
📊 **Статус бота**

👤 **Ваш статус**: {'👑 Администратор' if is_admin else '👤 Пользователь'}
📈 **Всего пользователей**: {total_users}
🤖 **Статус бота**: ✅ Запущен (без OpenAI)
⚠️ **OpenAI**: 🔧 Исправляем совместимость

**🔧 Техническая информация:**
• Telegram Bot API: ✅ Работает
• База данных: ✅ Работает  
• Планировщик: ✅ Работает
• OpenAI API: ❌ Проблема совместимости
        """
        
        await update.message.reply_text(message, parse_mode='Markdown')

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    sys.exit(0)

# Main execution
def main():
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Environment variables loaded from .env file")
    except Exception as e:
        logger.warning(f"Could not load .env file: {e}")
    
    # Load configuration from environment variables
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not BOT_TOKEN:
        logger.error("Please set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    logger.info(f"✅ Bot token loaded")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and start bot
    bot = StockNewsBot(BOT_TOKEN)
    
    try:
        logger.info("Bot started successfully! (Fallback mode without OpenAI)")
        logger.info(f"Current user count: {bot.db.get_user_count()}")
        
        # Start the bot
        try:
            logger.info("🚀 Starting Telegram bot polling...")
            bot.application.run_polling(
                drop_pending_updates=True,
                close_loop=False  # Prevent event loop conflicts
            )
        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")
        except Exception as e:
            # Handle specific Telegram conflicts
            if "getUpdates request" in str(e) or "Conflict" in str(e):
                logger.error("❌ Multiple bot instances detected! Please ensure only one bot is running.")
                logger.info("💡 To fix: pkill -f stock_bot.py && python3 stock_bot_no_openai.py")
            else:
                logger.error(f"Bot polling error: {e}")
            raise
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
