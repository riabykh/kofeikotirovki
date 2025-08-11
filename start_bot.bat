@echo off
chcp 65001 >nul
echo 🚀 Starting Stock Market News Telegram Bot...

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️  Warning: .env file not found!
    echo 📝 Please create a .env file with your TELEGRAM_BOT_TOKEN
    echo 💡 You can copy from env.example as a starting point
    pause
    exit /b 1
)

REM Check if bot token is set
findstr /C:"your_bot_token_here" .env >nul
if %errorlevel% equ 0 (
    echo ⚠️  Error: TELEGRAM_BOT_TOKEN not properly set in .env file!
    echo 🔑 Please set your actual bot token from @BotFather
    pause
    exit /b 1
)

echo ✅ Environment setup complete!
echo 🤖 Starting bot...

REM Start the bot
python stock_bot.py
pause
