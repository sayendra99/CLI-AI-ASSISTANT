# 🚀 Rocket CLI - Free Models Quick Reference

## One-Line Setup

```bash
python setup_free_models.py
```

## Best Models (2026)

| Model                | Quality     | Speed       | RAM  | Use Case        |
| -------------------- | ----------- | ----------- | ---- | --------------- |
| **qwen2.5-coder:7b** | ⭐⭐⭐⭐⭐  | ⚡⚡⚡⚡    | 16GB | **BEST CHOICE** |
| qwen2.5-coder:3b     | ⭐⭐⭐⭐    | ⚡⚡⚡⚡⚡  | 8GB  | Daily use       |
| qwen2.5-coder:1.5b   | ⭐⭐⭐      | ⚡⚡⚡⚡⚡+ | 4GB  | Low-end         |
| qwen2.5-coder:14b    | ⭐⭐⭐⭐⭐+ | ⚡⚡⚡      | 24GB | Complex         |

## Quick Commands

```bash
# Auto-setup (recommended)
python setup_free_models.py

# 🆕 Check for model updates
python rocket_models.py check

# 🆕 List all available models
python rocket_models.py list

# 🆕 Auto-upgrade all models
python rocket_models.py upgrade

# 🆕 Install specific model
python rocket_models.py install qwen2.5-coder:7b

# Manual install via Ollama
ollama pull qwen2.5-coder:7b

# Use with Rocket CLI
rocket chat -m "Your question here"

# Use specific model
rocket chat --model ollama_chat/qwen2.5-coder:7b -m "Question"

# List installed models
ollama list
```

## Model Management 🆕

```bash
python rocket_models.py check       # Check for updates
python rocket_models.py list        # List available models
python rocket_models.py installed   # Show installed
python rocket_models.py upgrade     # Upgrade all
python rocket_models.py recommend   # Auto-install best
python rocket_models.py search <term>  # Search models
```

## System Requirements

- **Minimum:** 4GB RAM → qwen2.5-coder:1.5b
- **Recommended:** 16GB RAM → qwen2.5-coder:7b
- **High-end:** 24GB+ RAM → qwen2.5-coder:14b

## Install Ollama

```bash
# Windows
winget install Ollama.Ollama

# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
```

## Auto-Update Features 🆕

- ✅ Automatic update checks (every 7 days)
- ✅ Non-intrusive notifications
- ✅ One-command upgrade: `python rocket_models.py upgrade`
- ✅ Future-proof: New models auto-discovered
- ✅ Smart recommendations based on your system

**See:** [AUTO_UPDATE_GUIDE.md](AUTO_UPDATE_GUIDE.md) for details

## 💰 Cost: $0/month | ♾️ Requests: Unlimited | 🔒 Privacy: 100%
