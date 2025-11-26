#!/usr/bin/env python3
"""
Simple test for CineAI Bot basic functionality
"""

import sys
import os

def test_basic_imports():
    """Test if we can import required modules"""
    try:
        import motor
        print("OK: MongoDB driver (motor) available")
    except ImportError:
        print("ERROR: MongoDB driver (motor) missing - install with: pip install motor")
        return False

    try:
        import pyrogram
        print("OK: Telegram library (pyrogram) available")
    except ImportError:
        print("ERROR: Telegram library (pyrogram) missing - install with: pip install pyrogram")
        return False

    try:
        import pymongo
        print("OK: MongoDB library (pymongo) available")
    except ImportError:
        print("ERROR: MongoDB library (pymongo) missing - install with: pip install pymongo")
        return False

    return True

def test_env_file():
    """Test if .env file exists and has required variables"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')

    if not os.path.exists(env_path):
        print("ERROR: .env file not found")
        return False

    print("OK: .env file found")

    # Read and check key variables
    with open(env_path, 'r') as f:
        content = f.read()

    required_vars = ['BOT_TOKEN', 'API_ID', 'API_HASH', 'MONGO_URI']
    missing_vars = []

    for var in required_vars:
        if var not in content:
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required variables: {', '.join(missing_vars)}")
        return False

    print("✅ Required environment variables present")
    return True

def test_mongodb_connection():
    """Test MongoDB connection"""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        # Try to read MONGO_URI from .env
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('MONGO_URI='):
                    mongo_uri = line.split('=', 1)[1].strip()
                    break
            else:
                print("❌ MONGO_URI not found in .env")
                return False

        # Test connection
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)

        # Simple test
        import asyncio
        async def test_connection():
            try:
                await client.admin.command('ping')
                print("✅ MongoDB connection successful")
                return True
            except Exception as e:
                print(f"❌ MongoDB connection failed: {e}")
                return False
            finally:
                client.close()

        return asyncio.run(test_connection())

    except Exception as e:
        print(f"❌ MongoDB test error: {e}")
        return False

def main():
    print("Testing CineAI Bot Configuration...\n")

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Environment File", test_env_file),
        ("MongoDB Connection", test_mongodb_connection)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test:")
        result = test_func()
        results.append(result)

    print(f"\n{'='*50}")
    if all(results):
        print("✅ All tests passed! Bot should work correctly.")
        print("\n🚀 To start the bot, run:")
        print("   python -m app.main")
    else:
        print("❌ Some tests failed. Please fix the issues above.")

    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)