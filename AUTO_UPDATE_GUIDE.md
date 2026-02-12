# 🔄 Auto-Update System for Rocket CLI Models

## Overview

Rocket CLI now includes an **intelligent auto-update system** that:

- ✅ Automatically discovers new models
- ✅ Checks for model upgrades
- ✅ One-command upgrade for all models
- ✅ Non-intrusive notifications
- ✅ Future-proof architecture

**No more manual installation!** Your models stay up-to-date automatically.

---

## 🚀 Quick Commands

```bash
# Check for new models and updates
python rocket_models.py check

# List all available models
python rocket_models.py list

# Upgrade all installed models
python rocket_models.py upgrade

# Install recommended model for your system
python rocket_models.py recommend

# Install specific model
python rocket_models.py install qwen2.5-coder:7b

# Search for models
python rocket_models.py search coding
```

---

## 🎯 How It Works

### 1. **Centralized Model Registry**

All models are tracked in `Rocket/Utils/model_registry.py`:

```python
# Model catalog with metadata
- qwen2.5-coder:7b (State-of-the-art, Jan 2025)
- deepseek-coder-v2:16b (Excellent quality)
- codegemma:7b (Google's specialist)
- ... and more
```

Each model includes:

- Version tracking
- Quality tier (SOTA, Excellent, Good, Fast)
- RAM requirements
- Release date
- Specialty/use case
- Upgrade path

### 2. **Automatic Update Checks**

The system checks for updates every **7 days** automatically:

```python
# Happens in background when you use Rocket CLI
updater.check_and_notify(auto_check=True)
```

**Non-intrusive:** Only shows notification if updates available.

### 3. **Smart Recommendations**

Suggests upgrades based on:

- Newer versions of installed models
- Better quality alternatives
- Same model family improvements

---

## 📋 Model Management Commands

### List All Available Models

```bash
python rocket_models.py list
```

**Output:**

```
📦 Available Free Models (10 total)
================================

🏆 STATE-OF-THE-ART
-------------------
✅ qwen2.5-coder:7b       |   7B | RAM: 10-16 GB | fast
   └─ State-of-the-art free coding model

  qwen2.5-coder:14b      |  14B | RAM: 20-32 GB | medium
   └─ Highest quality for complex tasks

🏆 EXCELLENT
------------
✅ deepseek-coder-v2:16b  |  16B | RAM: 24-32 GB | medium
   └─ Excellent code generation and debugging
```

**Filter by quality:**

```bash
python rocket_models.py list --quality sota
python rocket_models.py list --quality excellent
```

### Check for Updates

```bash
python rocket_models.py check
```

**Output:**

```
🔍 Checking for updates...

🆕 2 new model(s) available:
   • qwen2.5-coder:32b - Ultimate quality for servers
   • phi4:latest - Microsoft's latest efficient model

⬆️  1 upgrade(s) recommended:
   • codellama:7b → qwen2.5-coder:7b
     Reason: Newer version with better performance
```

### Upgrade All Models

```bash
# Preview what would be upgraded
python rocket_models.py upgrade --dry-run

# Actually upgrade
python rocket_models.py upgrade
```

**Safe:** Always shows what will be upgraded before doing it.

### List Installed Models

```bash
python rocket_models.py installed
```

**Output:**

```
📦 Installed Models (3 total)
=============================

✅ qwen2.5-coder:7b
   └─ State-of-the-art free coding model
      Quality: state-of-the-art | RAM: 10-16 GB | Speed: fast

✅ qwen2.5-coder:3b
   └─ Perfect balance of speed and quality
      Quality: excellent | RAM: 6-8 GB | Speed: very_fast
```

### Install Specific Model

```bash
python rocket_models.py install qwen2.5-coder:14b
```

**Shows before installing:**

- Model description
- Quality tier
- Download size
- RAM requirements

### Smart Recommendation

```bash
python rocket_models.py recommend
```

**Auto-detects:**

- Available RAM
- GPU presence
- CPU capabilities

**Then installs** the optimal model for your system!

### Search for Models

```bash
python rocket_models.py search coding
python rocket_models.py search debugging
python rocket_models.py search fast
```

---

## 🔮 Future-Proof Architecture

### When New Models Release

**Scenario:** In March 2026, a new model `qwen3-coder:7b` is released.

**What happens:**

1. **Registry Update** (automatic or manual):

   ```python
   # Add to model_registry.py
   ModelEntry(
       name="qwen3-coder:7b",
       version="2026.03",
       quality=ModelQuality.SOTA,
       supersedes="qwen2.5-coder:7b",  # Marks old version
       ...
   )
   ```

2. **User Runs Check**:

   ```bash
   python rocket_models.py check
   ```

3. **System Notifies**:

   ```
   🆕 1 new model available:
      • qwen3-coder:7b - Next-gen coding model (15% faster!)

   ⬆️  Upgrade available:
      • qwen2.5-coder:7b → qwen3-coder:7b
        Reason: Superseded by newer version
   ```

4. **One-Click Upgrade**:
   ```bash
   python rocket_models.py upgrade
   ```

**No manual work required!**

---

## 🌐 Remote Registry Updates (Future)

### Current: Local Registry

Models are defined in `model_registry.py`.

### Future: Remote Updates

```python
# Will fetch from: https://api.rocket-cli.dev/models/registry.json
{
  "version": "2026.03",
  "models": [
    {
      "name": "qwen3-coder:7b",
      "version": "2026.03",
      "quality": "state-of-the-art",
      ...
    }
  ]
}
```

**Benefits:**

- Instant model discovery
- No code changes needed
- Community-driven additions
- Rollback capability

**To enable:**

```bash
rocket config set auto_update_registry true
```

---

## 📊 Update Frequency

| Check Type    | Frequency        | Trigger                 |
| ------------- | ---------------- | ----------------------- |
| **Automatic** | Every 7 days     | When you use Rocket CLI |
| **Manual**    | On-demand        | `rocket models check`   |
| **Startup**   | First run of day | Non-blocking background |

**Configurable:**

```bash
# Change update interval (in days)
rocket config set update_check_interval 3
```

---

## 🛡️ Safety Features

### 1. **Dry Run Mode**

Always test upgrades first:

```bash
python rocket_models.py upgrade --dry-run
```

### 2. **Version Tracking**

Keeps history of installed versions:

```
~/.rocket-cli/model-cache/
  ├── last_update_check.json
  ├── installed_versions.json
  └── registry_cache.json
```

### 3. **Rollback Support** (Future)

```bash
# Coming soon
python rocket_models.py rollback qwen2.5-coder:7b
```

### 4. **Notifications Only**

Updates are **opt-in** - you choose when to upgrade.

---

## 💡 Best Practices

### For Regular Users

1. **Check monthly:**

   ```bash
   python rocket_models.py check
   ```

2. **Upgrade when convenient:**

   ```bash
   python rocket_models.py upgrade
   ```

3. **Use recommended:**
   ```bash
   python rocket_models.py recommend
   ```

### For Power Users

1. **Install multiple versions:**

   ```bash
   python rocket_models.py install qwen2.5-coder:7b
   python rocket_models.py install qwen2.5-coder:14b
   ```

2. **Track quality tiers:**

   ```bash
   python rocket_models.py list --quality sota
   ```

3. **Set update reminders:**
   ```bash
   # Add to crontab (Linux/Mac)
   0 9 * * 1 cd /path/to/rocket && python rocket_models.py check
   ```

---

## 🧪 Technical Details

### Model Metadata Schema

```python
@dataclass
class ModelEntry:
    name: str                    # "qwen2.5-coder:7b"
    version: str                 # "2025.01"
    quality: ModelQuality        # SOTA, EXCELLENT, GOOD, FAST, LEGACY
    params: str                  # "7B"
    ram_min_gb: int             # Minimum RAM needed
    ram_optimal_gb: int         # Recommended RAM
    size_gb: float              # Download size
    speed_rating: str           # "ultra_fast", "fast", "medium"
    specialty: str              # Description
    release_date: str           # ISO format
    supersedes: Optional[str]   # Model it replaces
    recommended_for: List[str]  # Use cases
```

### Update Algorithm

```python
def get_upgrade_recommendations():
    for installed_model in get_installed():
        # Find newer models in same family
        newer = [
            m for m in registry
            if m.family == installed_model.family
            and m.release_date > installed_model.release_date
        ]

        # Recommend best quality upgrade
        if newer:
            recommend(max(newer, key=lambda m: m.quality))
```

---

## 🎓 Examples

### Scenario 1: New User Setup

```bash
# Initial setup
python setup_free_models.py
# → Installs qwen2.5-coder:7b (recommended)

# Month later, check for updates
python rocket_models.py check
# → Shows: qwen2.5-coder:14b available (better quality)

# Install additional model
python rocket_models.py install qwen2.5-coder:14b
```

### Scenario 2: Existing User Upgrade

```bash
# Currently using: codellama:7b (2023 model)

# Check for upgrades
python rocket_models.py check
# → Recommends: qwen2.5-coder:7b (2025 model, better)

# Upgrade
python rocket_models.py upgrade
# → Installs qwen2.5-coder:7b
# → Keeps codellama:7b (doesn't remove old)
```

### Scenario 3: System Upgrade

```bash
# Upgraded RAM: 8GB → 32GB

# Get new recommendation
python rocket_models.py recommend
# → Detects 32GB RAM
# → Recommends: qwen2.5-coder:14b (was using 7b)

# Install
# → Downloads and configures automatically
```

---

## ❓ FAQ

**Q: How often should I check for updates?**  
A: Once a month is sufficient. Auto-check happens every 7 days.

**Q: Will updates remove my old models?**  
A: No, they install alongside. You can manually remove old ones.

**Q: Do I need internet for updates?**  
A: Only to download new models. Local models work offline.

**Q: Can I disable auto-update checks?**  
A: Yes, set `auto_check=False` in config or simply ignore notifications.

**Q: What if a new model doesn't work well?**  
A: Keep using the old model! Multiple versions can coexist.

**Q: Can I contribute new models to the registry?**  
A: Yes! Submit PR to `model_registry.py` or suggest via GitHub issues.

---

## 🚀 Summary

**Before Auto-Update:**

- ❌ Manual model discovery
- ❌ Miss new releases
- ❌ Outdated models
- ❌ Complex upgrade process

**With Auto-Update:**

- ✅ Automatic discovery
- ✅ Update notifications
- ✅ One-command upgrade
- ✅ Always current models
- ✅ Future-proof system

**Your models stay current automatically!** 🎉
