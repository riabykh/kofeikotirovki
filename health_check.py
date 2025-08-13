#!/usr/bin/env python3
"""
Кофе и Котировки - Health Check Script
Monitor bot status and perform basic diagnostics
"""

import subprocess
import sys
import os
from datetime import datetime

def check_process():
    """Check if bot process is running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'stock_bot.py'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return len(pids), pids
        return 0, []
    except Exception as e:
        print(f"❌ Error checking process: {e}")
        return 0, []

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'telegram', 'openai', 'schedule', 'dotenv'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return missing

def check_environment():
    """Check environment variables"""
    required_vars = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    return missing

def check_database():
    """Check if database file exists and is accessible"""
    db_file = "stock_bot.db"
    if os.path.exists(db_file):
        try:
            import sqlite3
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            conn.close()
            return True, user_count
        except Exception as e:
            return False, f"Database error: {e}"
    return False, "Database file not found"

def main():
    print("🔍 Кофе и Котировки - Health Check")
    print("=" * 40)
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check process
    process_count, pids = check_process()
    if process_count > 0:
        print(f"✅ Bot process running (PID: {', '.join(pids)})")
    else:
        print("❌ Bot process not running")
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("💡 Run: pip install -r requirements.txt")
    else:
        print("✅ All dependencies installed")
    
    # Check environment
    missing_env = check_environment()
    if missing_env:
        print(f"❌ Missing environment variables: {', '.join(missing_env)}")
        print("💡 Create .env file with required variables")
    else:
        print("✅ Environment variables configured")
    
    # Check database
    db_ok, db_info = check_database()
    if db_ok:
        print(f"✅ Database accessible ({db_info} users)")
    else:
        print(f"❌ Database issue: {db_info}")
    
    print()
    
    # Overall status
    issues = len(missing_deps) + len(missing_env) + (0 if db_ok else 1) + (0 if process_count > 0 else 1)
    
    if issues == 0:
        print("🎉 All systems operational!")
        return 0
    else:
        print(f"⚠️  Found {issues} issue(s) that need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())