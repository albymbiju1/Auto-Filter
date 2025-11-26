#!/usr/bin/env python3
"""
Configuration validation script for CineAI Bot
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        from app.config import config

        print("✅ Configuration loaded successfully!")
        print(f"🤖 Bot Token: {'*' * 10}{config.telegram.BOT_TOKEN[-10:] if config.telegram.BOT_TOKEN else 'MISSING'}")
        print(f"🔑 API ID: {config.telegram.API_ID}")
        print(f"🔗 API Hash: {'✓ Set' if config.telegram.API_HASH else '✗ MISSING'}")
        print(f"👤 Admin Users: {len(config.telegram.ADMIN_USER_IDS)} users")
        print(f"🌐 MongoDB URI: {'✓ Set' if config.database.MONGO_URI else '✗ MISSING'}")
        print(f"🎬 IMDB API Key: {'✓ Set' if config.external_apis.IMDB_API_KEY else '✗ MISSING'}")
        print(f"🔗 Shortener API Key: {'✓ Set' if config.external_apis.SHORTENER_API_KEY else '✗ MISSING'}")
        print(f"💳 PayPal Client ID: {'✓ Set' if config.payment.PAYPAL_CLIENT_ID else '✗ MISSING'}")

        # Test feature toggles
        print(f"\n🎛️  Feature Status:")
        print(f"  📱 PM Search: {config.features.PM_SEARCH}")
        print(f"  🎬 Auto Filter: {config.features.AUTO_FILTER}")
        print(f"  🔍 Inline Search: {config.features.INLINE_SEARCH}")
        print(f"  🎭 Force Subscribe: {config.features.FORCE_SUBSCRIBE}")
        print(f"  💎 Premium: {config.features.PREMIUM}")
        print(f"  📊 IMDB Integration: {config.features.IMDB_INTEGRATION}")

        # Critical checks
        critical_issues = []
        if not config.telegram.BOT_TOKEN:
            critical_issues.append("Bot token is missing")
        if not config.telegram.API_ID:
            critical_issues.append("API ID is missing")
        if not config.telegram.API_HASH:
            critical_issues.append("API hash is missing")
        if not config.database.MONGO_URI:
            critical_issues.append("MongoDB URI is missing")

        if critical_issues:
            print(f"\n❌ Critical Issues Found:")
            for issue in critical_issues:
                print(f"  - {issue}")
            return False
        else:
            print(f"\n✅ All critical configuration is valid!")
            return True

    except ImportError as e:
        print(f"❌ Failed to import configuration: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)