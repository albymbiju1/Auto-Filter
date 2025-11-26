#!/usr/bin/env python3
"""
Debug script to test config loading
"""

import os
import sys

print("=" * 60)
print("DEBUG: Testing Config Loading")
print("=" * 60)

# First, check raw environment variables
print("\n1. Raw Environment Variables:")
print(f"   BOT_TOKEN: {os.getenv('BOT_TOKEN', 'NOT SET')[:20]}...")
print(f"   API_ID: {os.getenv('API_ID', 'NOT SET')}")
print(f"   API_HASH: {os.getenv('API_HASH', 'NOT SET')[:20]}...")
print(f"   MONGO_URI: {os.getenv('MONGO_URI', 'NOT SET')[:30]}...")

# Try importing pydantic_settings
print("\n2. Testing pydantic_settings import:")
try:
    from pydantic_settings import BaseSettings
    print("   ✓ pydantic_settings imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import pydantic_settings: {e}")
    sys.exit(1)

# Try creating a simple config
print("\n3. Testing simple pydantic config:")
try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class SimpleConfig(BaseSettings):
        BOT_TOKEN: str
        API_ID: int
        API_HASH: str
        MONGO_URI: str

        model_config = SettingsConfigDict(
            case_sensitive=False,
            extra='ignore'
        )

    config = SimpleConfig()
    print(f"   ✓ SimpleConfig loaded successfully")
    print(f"   ✓ BOT_TOKEN: {config.BOT_TOKEN[:20]}...")
    print(f"   ✓ API_ID: {config.API_ID}")
    print(f"   ✓ MONGO_URI: {config.MONGO_URI[:30]}...")

except Exception as e:
    print(f"   ✗ Failed to load SimpleConfig: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Now try loading the actual config
print("\n4. Testing actual Config class:")
try:
    from app.config import Config
    config = Config()
    print(f"   ✓ Config loaded successfully!")
    print(f"   ✓ BOT_TOKEN: {config.BOT_TOKEN[:20]}...")
    print(f"   ✓ API_ID: {config.API_ID}")

except Exception as e:
    print(f"   ✗ Failed to load Config: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("SUCCESS: All config tests passed!")
print("=" * 60)
