#!/usr/bin/env python3
"""
Minimal Stock News Bot - Clean version for Railway deployment
Focus on reliability and basic functionality
"""

import asyncio
import logging
import os
import sqlite3
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'ru',
                    topic_preferences TEXT DEFAULT 'all',
                    subscribed BOOLEAN DEFAULT 1,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Admin users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    user_id INTEGER PRIMARY KEY
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
    
    def add_user(self, user_id, username, first_name, last_name):
        """Add or update user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or ignore, then update to preserve existing preferences
            cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
            cursor.execute('''
                UPDATE users 
                SET username=?, first_name=?, last_name=?, last_active=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (username, first_name, last_name, user_id))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ User {user_id} added/updated")
            
        except Exception as e:
            logger.error(f"❌ Error adding user {user_id}: {e}")
    
    def get_user_language(self, user_id):
        """Get user's preferred language"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT language FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 'ru'
        except:
            return 'ru'
    
    def set_user_language(self, user_id, language):
        """Set user's preferred language"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET language = ? WHERE id = ?', (language, user_id))
            conn.commit()
            conn.close()
            logger.info(f"✅ Language set to {language} for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Error setting language for user {user_id}: {e}")
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM admin_users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except:
            return False
    
    def add_admin(self, user_id):
        """Add admin user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO admin_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
            conn.close()
            logger.info(f"✅ User {user_id} added as admin")
        except Exception as e:
            logger.error(f"❌ Error adding admin {user_id}: {e}")
    
    def get_user_count(self):
        """Get total user count"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

class MinimalStockBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.db = DatabaseManager()
        
        # Create application
        self.application = Application.builder().token(bot_token).build()
        
        # Translations
        self.translations = {
            'en': {
                'welcome': 'Welcome to Кофе и Котировки! 🤖\n\nI\'m your AI-powered stock market assistant.\n\nCommands:\n/start - This message\n/language - Change language\n/help - Show help\n/status - Bot status',
                'language_changed': '✅ Language changed to English',
                'choose_language': '🌍 Choose your language:',
                'status_message': '🤖 Bot Status: Online\n📊 Users: {users}\n🕐 Time: {time}',
                'help_message': '📖 Available Commands:\n\n/start - Welcome message\n/language - Change language\n/help - This help\n/status - Bot status\n\n🤖 Bot is working!'
            },
            'ru': {
                'welcome': 'Добро пожаловать в Кофе и Котировки! 🤖\n\nЯ ваш ИИ-помощник по фондовому рынку.\n\nКоманды:\n/start - Это сообщение\n/language - Изменить язык\n/help - Показать помощь\n/status - Статус бота',
                'language_changed': '✅ Язык изменен на русский',
                'choose_language': '🌍 Выберите язык:',
                'status_message': '🤖 Статус бота: Онлайн\n📊 Пользователей: {users}\n🕐 Время: {time}',
                'help_message': '📖 Доступные команды:\n\n/start - Приветственное сообщение\n/language - Изменить язык\n/help - Эта справка\n/status - Статус бота\n\n🤖 Бот работает!'
            }
        }
        
        # Setup handlers
        self.setup_handlers()
        
        logger.info("✅ Minimal bot initialized")
    
    def get_text(self, user_id, key):
        """Get translated text"""
        language = self.db.get_user_language(user_id)
        return self.translations.get(language, self.translations['ru']).get(key, key)
    
    def setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        logger.info("✅ Handlers registered")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            logger.info(f"📥 /start from user {user.id} ({user.username})")
            
            # Add user to database
            self.db.add_user(user.id, user.username, user.first_name, user.last_name)
            
            # Make first user admin
            if self.db.get_user_count() == 1:
                self.db.add_admin(user.id)
                logger.info(f"👑 First user {user.id} made admin")
            
            # Send welcome message
            welcome_text = self.get_text(user.id, 'welcome')
            await update.message.reply_text(welcome_text)
            
            logger.info(f"✅ Welcome sent to {user.id}")
            
        except Exception as e:
            logger.error(f"❌ Error in start_command: {e}")
            await update.message.reply_text("❌ Error occurred. Please try again.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            user = update.effective_user
            logger.info(f"📥 /help from user {user.id}")
            
            help_text = self.get_text(user.id, 'help_message')
            await update.message.reply_text(help_text)
            
            logger.info(f"✅ Help sent to {user.id}")
            
        except Exception as e:
            logger.error(f"❌ Error in help_command: {e}")
            await update.message.reply_text("❌ Error occurred.")
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /language command"""
        try:
            user = update.effective_user
            logger.info(f"📥 /language from user {user.id}")
            
            # Create language keyboard
            keyboard = [
                [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
                [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = self.get_text(user.id, 'choose_language')
            await update.message.reply_text(text, reply_markup=reply_markup)
            
            logger.info(f"✅ Language menu sent to {user.id}")
            
        except Exception as e:
            logger.error(f"❌ Error in language_command: {e}")
            await update.message.reply_text("❌ Error occurred.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            user = update.effective_user
            logger.info(f"📥 /status from user {user.id}")
            
            user_count = self.db.get_user_count()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            status_text = self.get_text(user.id, 'status_message').format(
                users=user_count,
                time=current_time
            )
            
            await update.message.reply_text(status_text)
            logger.info(f"✅ Status sent to {user.id}")
            
        except Exception as e:
            logger.error(f"❌ Error in status_command: {e}")
            await update.message.reply_text("❌ Error occurred.")
    
    async def handle_callback(self, query):
        """Handle callback queries"""
        try:
            user = query.from_user
            data = query.data
            
            logger.info(f"📥 Callback {data} from user {user.id}")
            
            if data.startswith("lang_"):
                language = data.split("_")[1]
                self.db.set_user_language(user.id, language)
                
                success_text = self.get_text(user.id, 'language_changed')
                await query.edit_message_text(success_text)
                
                logger.info(f"✅ Language {language} set for user {user.id}")
            
            await query.answer()
            
        except Exception as e:
            logger.error(f"❌ Error in callback handler: {e}")
            try:
                await query.answer("❌ Error occurred")
            except:
                pass
    
    async def setup_bot_menu(self):
        """Setup bot commands menu"""
        try:
            commands = [
                ("start", "Welcome message"),
                ("help", "Show help"),
                ("language", "Change language"), 
                ("status", "Bot status")
            ]
            
            await self.application.bot.set_my_commands(commands)
            logger.info("✅ Bot menu set successfully")
            
        except Exception as e:
            logger.error(f"❌ Error setting bot menu: {e}")
    
    def run(self):
        """Run the bot"""
        logger.info("🚀 Starting Minimal Stock Bot...")
        
        try:
            # Setup menu and run
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Setup bot menu
            loop.run_until_complete(self.setup_bot_menu())
            
            logger.info("🔄 Starting polling...")
            self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"❌ Error running bot: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main function"""
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Environment loaded")
    except:
        pass
    
    # Get bot token
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        sys.exit(1)
    
    logger.info(f"✅ Bot token loaded: {BOT_TOKEN[:10]}...")
    
    # Create and run bot
    bot = MinimalStockBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()
