#!/usr/bin/env python3
"""
Health Check Script for Stock News Bot
Monitors bot status and database connectivity
"""

import requests
import sqlite3
import sys
import os
from datetime import datetime

# Bot configuration
BOT_TOKEN = "8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE"
DB_PATH = "stock_bot.db"

def check_bot_api():
    """Check if bot API is responding"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"✅ Bot API: {bot_info.get('username', 'Unknown')} is responding")
                return True
            else:
                print(f"❌ Bot API: Invalid response - {data}")
                return False
        else:
            print(f"❌ Bot API: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Bot API: Network error - {e}")
        return False
    except Exception as e:
        print(f"❌ Bot API: Unexpected error - {e}")
        return False

def check_database():
    """Check database connectivity and integrity"""
    try:
        if not os.path.exists(DB_PATH):
            print(f"❌ Database: File {DB_PATH} not found")
            return False
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['users', 'admin_users']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Database: Missing tables - {missing_tables}")
            conn.close()
            return False
        
        # Check user count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # Check admin count
        cursor.execute("SELECT COUNT(*) FROM admin_users")
        admin_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Database: Connected ({user_count} users, {admin_count} admins)")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database: SQLite error - {e}")
        return False
    except Exception as e:
        print(f"❌ Database: Unexpected error - {e}")
        return False

def check_openai_api():
    """Check OpenAI API key validity"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OpenAI API: No API key found in environment")
            return False
        
        # Simple validation - check if key format is correct
        if api_key.startswith('sk-') and len(api_key) > 20:
            print(f"✅ OpenAI API: Key format valid ({api_key[:10]}...)")
            return True
        else:
            print("❌ OpenAI API: Invalid key format")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API: Error - {e}")
        return False

def check_disk_space():
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage('.')
        
        free_gb = free // (1024**3)
        total_gb = total // (1024**3)
        used_percent = (used / total) * 100
        
        if free_gb < 1:  # Less than 1GB free
            print(f"❌ Disk Space: Low ({free_gb}GB free, {used_percent:.1f}% used)")
            return False
        else:
            print(f"✅ Disk Space: {free_gb}GB free ({used_percent:.1f}% used)")
            return True
            
    except Exception as e:
        print(f"❌ Disk Space: Error checking - {e}")
        return False

def check_log_files():
    """Check if log files are being written"""
    try:
        log_files = ['logs/bot.log', 'stock_bot.log']
        log_found = False
        
        for log_file in log_files:
            if os.path.exists(log_file):
                size = os.path.getsize(log_file)
                modified = datetime.fromtimestamp(os.path.getmtime(log_file))
                print(f"✅ Logs: {log_file} ({size} bytes, modified: {modified})")
                log_found = True
                break
        
        if not log_found:
            print("⚠️  Logs: No log files found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Logs: Error checking - {e}")
        return False

def main():
    """Run all health checks"""
    print(f"🔍 Stock News Bot Health Check - {datetime.now()}")
    print("=" * 50)
    
    checks = [
        ("Bot API", check_bot_api),
        ("Database", check_database),
        ("OpenAI API", check_openai_api),
        ("Disk Space", check_disk_space),
        ("Log Files", check_log_files)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        result = check_func()
        results.append((name, result))
    
    print("\n" + "=" * 50)
    print("📊 Health Check Summary:")
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All health checks passed! Bot is healthy.")
        sys.exit(0)
    else:
        print("⚠️  Some health checks failed. Please investigate.")
        sys.exit(1)

if __name__ == "__main__":
    main()