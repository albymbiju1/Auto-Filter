#!/usr/bin/env python3
import sys
import os

def test_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        print("ERROR: .env file not found")
        return False

    print("OK: .env file exists")
    return True

def test_imports():
    try:
        import motor
        import pyrogram
        import pymongo
        print("OK: All required libraries available")
        return True
    except ImportError as e:
        print(f"ERROR: Missing library - {e}")
        return False

def main():
    print("=== CineAI Bot Quick Test ===")

    if not test_env():
        return False
    if not test_imports():
        return False

    print("SUCCESS: Basic tests passed!")
    print("To start bot: python -m app.main")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)