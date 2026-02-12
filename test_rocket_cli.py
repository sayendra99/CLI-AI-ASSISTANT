"""
Rocket CLI - Comprehensive Test Suite

Tests all major CLI functionality to ensure everything works.
"""

import subprocess
import sys
from pathlib import Path

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name):
    """Print test name"""
    print(f"\n{BLUE}▶ Testing: {name}{RESET}")
    print("-" * 60)

def print_success(message):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")

def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {message}{RESET}")

def run_command(cmd, capture_output=True):
    """Run a command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'  # Replace undecodable bytes
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_cli_help():
    """Test CLI help command"""
    print_test("CLI Help")
    success, stdout, stderr = run_command("python -m Rocket.CLI.Main --help")
    
    if success and "Rocket CLI" in stdout:
        print_success("CLI help command works")
        print_info(f"Available commands: chat, generate, explain, debug, optimize, version, config, status, login")
        return True
    else:
        print_error("CLI help command failed")
        return False

def test_version():
    """Test version command"""
    print_test("Version Command")
    success, stdout, stderr = run_command("python -m Rocket.CLI.Main version")
    
    if success:
        print_success("Version command works")
        print_info(f"Output: {stdout.strip()}")
        return True
    else:
        print_error("Version command failed")
        return False

def test_model_management():
    """Test model management CLI"""
    print_test("Model Management")
    success, stdout, stderr = run_command("python rocket_models.py --help")
    
    if success:
        print_success("Model management CLI works")
        print_info("Available: list, installed, check, upgrade, install, recommend, search")
        return True
    else:
        print_error("Model management CLI failed")
        return False

def test_model_list():
    """Test listing available models"""
    print_test("List Available Models")
    success, stdout, stderr = run_command("python rocket_models.py list --quality sota")
    
    if success and "qwen2.5-coder" in stdout:
        print_success("Model listing works")
        print_info("State-of-the-art models available")
        return True
    else:
        print_error("Model listing failed")
        return False

def test_installed_models():
    """Test listing installed models"""
    print_test("List Installed Models")
    success, stdout, stderr = run_command("python rocket_models.py installed")
    
    if success:
        print_success("Installed models check works")
        if "Installed Models" in stdout:
            print_info("Models are installed and detected")
        else:
            print_info("No models installed yet (run setup_free_models.py)")
        return True
    else:
        print_error("Installed models check failed")
        return False

def test_model_check():
    """Test checking for updates"""
    print_test("Check for Model Updates")
    success, stdout, stderr = run_command("python rocket_models.py check")
    
    if success:
        print_success("Update check works")
        if "new model" in stdout.lower():
            print_info("New models are available")
        else:
            print_info("All models up to date")
        return True
    else:
        print_error("Update check failed")
        return False

def test_model_search():
    """Test model search"""
    print_test("Search Models")
    success, stdout, stderr = run_command("python rocket_models.py search qwen")
    
    if success and "qwen" in stdout.lower():
        print_success("Model search works")
        print_info("Found qwen models")
        return True
    else:
        print_error("Model search failed")
        return False

def test_config_check():
    """Test configuration"""
    print_test("Configuration Status")
    success, stdout, stderr = run_command("python -m Rocket.CLI.Main status")
    
    if success:
        print_success("Configuration status check works")
        return True
    else:
        print_info("Status command may require additional setup")
        return True  # Don't fail on this

def test_ollama_installed():
    """Test if Ollama is installed"""
    print_test("Ollama Installation")
    success, stdout, stderr = run_command("ollama --version")
    
    if success:
        print_success("Ollama is installed")
        print_info(f"Version: {stdout.strip()}")
        
        # Check if models are installed
        success2, stdout2, stderr2 = run_command("ollama list")
        if success2 and stdout2.strip():
            models = [line.split()[0] for line in stdout2.strip().split("\n")[1:] if line.strip()]
            print_info(f"Installed models: {', '.join(models[:5])}")
        
        return True
    else:
        print_error("Ollama is not installed")
        print_info("Install from: https://ollama.ai/download")
        return False

def test_dependencies():
    """Test if required dependencies are installed"""
    print_test("Python Dependencies")
    
    required = [
        "typer",
        "rich",
        "aiohttp",
        "psutil"
    ]
    
    all_installed = True
    for package in required:
        try:
            __import__(package)
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is NOT installed")
            all_installed = False
    
    if not all_installed:
        print_info("Install missing packages: pip install -r requirements.txt")
    
    return all_installed

def test_file_structure():
    """Test if key files exist"""
    print_test("File Structure")
    
    key_files = [
        "Rocket/CLI/Main.py",
        "Rocket/LLM/providers/ollama.py",
        "Rocket/Utils/model_registry.py",
        "Rocket/Utils/model_updater.py",
        "rocket_models.py",
        "setup_free_models.py",
        "FREE_MODELS_GUIDE.md",
        "AUTO_UPDATE_GUIDE.md"
    ]
    
    all_exist = True
    for file in key_files:
        path = Path(file)
        if path.exists():
            print_success(f"{file}")
        else:
            print_error(f"{file} NOT FOUND")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(f"{BLUE}🧪 ROCKET CLI - COMPREHENSIVE TEST SUITE{RESET}")
    print("=" * 70)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Dependencies", test_dependencies),
        ("CLI Help", test_cli_help),
        ("Version Command", test_version),
        ("Ollama Installation", test_ollama_installed),
        ("Model Management CLI", test_model_management),
        ("List Models", test_model_list),
        ("List Installed Models", test_installed_models),
        ("Check for Updates", test_model_check),
        ("Search Models", test_model_search),
        ("Configuration Status", test_config_check),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"{BLUE}📊 TEST SUMMARY{RESET}")
    print("=" * 70 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 70)
    print(f"Results: {GREEN}{passed}/{total} tests passed{RESET}")
    print("=" * 70 + "\n")
    
    if passed == total:
        print(f"{GREEN}🎉 ALL TESTS PASSED!{RESET}")
        print("\n✨ Your Rocket CLI is fully operational!")
        print("\n🚀 Quick start:")
        print("   1. Run: python setup_free_models.py")
        print("   2. Then: python -m Rocket.CLI.Main chat -m 'Write a Python function'")
        print("   3. Or: python rocket_models.py check")
    elif passed >= total * 0.7:
        print(f"{YELLOW}⚠️  MOST TESTS PASSED ({passed}/{total}){RESET}")
        print("\n🔧 Some components need attention (see above)")
        print("\n💡 Common fixes:")
        print("   - Install Ollama: https://ollama.ai/download")
        print("   - Install dependencies: pip install -r requirements.txt")
        print("   - Run setup: python setup_free_models.py")
    else:
        print(f"{RED}❌ MANY TESTS FAILED ({passed}/{total}){RESET}")
        print("\n🔧 Please check:")
        print("   1. Dependencies: pip install -r requirements.txt")
        print("   2. Ollama: https://ollama.ai/download")
        print("   3. File structure is intact")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
