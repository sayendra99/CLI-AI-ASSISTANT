# 🚀 Rocket CLI - Easy Installation Guide

## For Your Friends (Super Simple!) 🎉

### One-Command Install

```bash
pip install rocket-cli-ai
```

That's it! 🎊 Now just run:

```bash
rocket
```

---

## Complete Setup Guide

### Step 1: Install Python (if needed)

**Windows:**

- Download from [python.org](https://www.python.org/downloads/)
- During installation, **check "Add Python to PATH"**
- Verify: `python --version`

**Mac:**

```bash
brew install python3
```

**Linux:**

```bash
sudo apt install python3 python3-pip  # Ubuntu/Debian
sudo dnf install python3 python3-pip  # Fedora
```

### Step 2: Install Rocket CLI

Choose any method:

#### Method 1: From PyPI (Recommended ⭐)

```bash
pip install rocket-cli-ai
```

#### Method 2: From GitHub (Latest)

```bash
pip install git+https://github.com/yourusername/CLI-AI-ASSISTANT.git
```

#### Method 3: Using pipx (Isolated)

```bash
# Install pipx first
pip install pipx
pipx ensurepath

# Install Rocket CLI
pipx install rocket-cli-ai
```

### Step 3: Install Local AI (Ollama)

**Windows/Mac/Linux:**

1. Visit [ollama.ai](https://ollama.ai) and download the installer
2. Install Ollama
3. Open a terminal and run:
   ```bash
   ollama pull llama2
   ```

### Step 4: Run Rocket CLI

```bash
rocket
```

Enjoy! 🚀

---

## Alternative: Use Without Ollama

You can use Gemini (Google's free AI):

1. Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set the environment variable:

   ```bash
   # Windows (PowerShell)
   $env:GEMINI_API_KEY="your-key-here"

   # Mac/Linux
   export GEMINI_API_KEY="your-key-here"
   ```

3. Run Rocket CLI:
   ```bash
   rocket --provider gemini
   ```

---

## Troubleshooting

### "rocket: command not found"

**Solution:** The Python scripts directory is not in your PATH.

**Windows:**

```powershell
# Add to PATH (replace USERNAME)
$env:Path += ";C:\Users\USERNAME\AppData\Local\Programs\Python\Python312\Scripts"
```

**Mac/Linux:**

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

Then restart your terminal.

### "Failed to connect to Ollama"

**Solution:**

1. Make sure Ollama is running: `ollama serve`
2. Or use Gemini instead: `rocket --provider gemini`

### Permission Errors on Windows

**Solution:** Run as administrator or use:

```powershell
pip install --user rocket-cli-ai
```

---

## Update Rocket CLI

```bash
pip install --upgrade rocket-cli-ai
```

---

## Uninstall

```bash
pip uninstall rocket-cli-ai
```

---

## Need Help?

- 📖 Read the [Full Guide](ROCKET_CLI_GUIDE.md)
- 🐛 Report issues on [GitHub](https://github.com/yourusername/CLI-AI-ASSISTANT/issues)
- 💬 Ask questions in [Discussions](https://github.com/yourusername/CLI-AI-ASSISTANT/discussions)

---

**Made with ❤️ by developers for developers**
