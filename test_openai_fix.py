#!/usr/bin/env python3
"""
Test OpenAI AsyncClient initialization to verify the fix
"""

import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

async def test_openai_client():
    """Test if OpenAI AsyncClient works without the 'proxies' error"""
    try:
        load_dotenv()
        
        print("🧪 Testing OpenAI AsyncClient initialization...")
        
        # Initialize client - this was causing the error
        client = AsyncOpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            http_client=None  # Use default httpx client to avoid conflicts
        )
        
        print("✅ AsyncClient initialized successfully")
        
        # Test a simple completion
        print("🤖 Testing completion...")
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'test successful' in one word"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI response: {result}")
        
        # Close client properly
        await client.close()
        print("✅ Client closed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🔧 OpenAI AsyncClient Fix Test")
    print("=" * 30)
    
    success = await test_openai_client()
    
    if success:
        print("\n🎉 OpenAI fix successful! The bot should work now.")
        return 0
    else:
        print("\n❌ OpenAI fix failed. Need to investigate further.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
