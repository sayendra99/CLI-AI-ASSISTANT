"""Test the rocket configs works."""
from Rocket.Utils.Config import settings
from Rocket.Utils.Log import logger
import logging


def test_Configs():
    """Test if config loaded properly."""
    print("\n 🚀 Testing Configurations ...")
    print(f"🔑 OpenAI API Key: {settings.openai_api_key}")
    print(f"🤖 Model: {settings.model}")
    print(f"🔢 Max Tokens: {settings.max_tokens}")
    print(f"📁 Data Directory: {settings.data_dir}")
    print("✅ Configuration Loaded Successfully!")


def test_logger():
    """Test if logger works properly."""
    print("\n 🚀 Testing Logger ...")
    logger.info("This is an info message from the logger.")
    logger.warning("This is a warning message from the logger.")
    logger.debug("This is a debug message from the logger.")
    print("✅ Logger Tested Successfully!")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ROCKET - Setup Verification testing")
    print("=" * 60)

    try:
        test_Configs()
        test_logger()
        print("=" * 60)
        print("✅ All Tests Passed Successfully!")
        print("=" * 60)
        print()
    except Exception as e:
        print(f"❌ Tests Failed! : {e}")
        print("\n Please Check: ")
        print("1. Is your .env file created with OPENAI_API_KEY set?")
        print("2. Is your virtual environment activated?")
        print("3. Are all dependencies installed?")
        raise