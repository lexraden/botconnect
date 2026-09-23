#!/usr/bin/env python3
"""
Smoke test for botconnect project.
Checks that the application can be imported and basic objects instantiated
without requiring real credentials.
"""
import os
import sys

# Set dummy environment variables before importing config
os.environ['TOKEN'] = '123456:ABCDEF'
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://user:pass@localhost/db'
os.environ['CRYPTO_BOT_TOKEN'] = 'dummy_token'
os.environ['WEBHOOK_TUNNEL_URL'] = 'https://example.com/webhook'
os.environ['ADMINS'] = '123456,654321'

def test_imports():
    try:
        from config import bot, dp, TOKEN, DATABASE_URL, WEBHOOK_TUNNEL_URL
        print("✓ Config imported successfully")
        print(f"  TOKEN: {TOKEN}")
        print(f"  DATABASE_URL: {DATABASE_URL}")
        print(f"  WEBHOOK_TUNNEL_URL: {WEBHOOK_TUNNEL_URL}")
        assert bot is not None
        assert dp is not None
        assert TOKEN == '123456:ABCDEF'
        return True
    except Exception as e:
        print(f"✗ Failed to import config: {e}")
        return False

def test_main_import():
    try:
        # Import main to ensure no syntax errors
        import main
        print("✓ Main imported successfully")
        # Check that the FastAPI app instance exists
        assert hasattr(main, 'app')
        print("✓ FastAPI app instance found")
        return True
    except Exception as e:
        print(f"✗ Failed to import main: {e}")
        return False

def test_handlers_import():
    try:
        from handlers import start, bot_settings
        print("✓ Handlers imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import handlers: {e}")
        return False

def test_regex_pattern():
    try:
        import re
        from main import BOT_TOKEN_PATTERN
        # Ensure it's a compiled regex pattern
        assert isinstance(BOT_TOKEN_PATTERN, re.Pattern)
        print("✓ Bot token pattern compiled successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to check regex pattern: {e}")
        return False

def main():
    print("Running smoke tests for botconnect...")
    all_pass = True
    all_pass &= test_imports()
    all_pass &= test_main_import()
    all_pass &= test_handlers_import()
    all_pass &= test_regex_pattern()
    
    if all_pass:
        print("\n✓ All smoke tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some smoke tests failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()