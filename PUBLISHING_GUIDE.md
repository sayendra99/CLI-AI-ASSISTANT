# 📦 Publishing Rocket CLI to PyPI - Complete Guide

This guide will help you publish Rocket CLI to PyPI so anyone can install it with `pip install rocket-cli-ai`.

## 🎯 Prerequisites

1. **PyPI Account**: Create accounts on:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [Test PyPI](https://test.pypi.org/account/register/) (testing)

2. **GitHub Repository**: Make sure your code is on GitHub

3. **Required Tools**: Install locally:
   ```bash
   pip install build twine
   ```

## 📝 Step-by-Step Publishing

### Step 1: Update Version Number

Edit `setup.py` and `pyproject.toml`:

```python
version="1.0.0"  # Change to your version
```

### Step 2: Update GitHub URL

Replace `yourusername` with your actual GitHub username in:

- `setup.py`
- `pyproject.toml`
- `README.md`

Example:

```python
url="https://github.com/your-actual-username/CLI-AI-ASSISTANT",
```

### Step 3: Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build
```

This creates files in `dist/`:

- `rocket-cli-ai-1.0.0.tar.gz` (source distribution)
- `rocket_cli_ai-1.0.0-py3-none-any.whl` (wheel distribution)

### Step 4: Test on Test PyPI (Recommended)

```bash
# Upload to Test PyPI
python -m twine upload --repository testpypi dist/*
```

**Login credentials**: Use your Test PyPI username and password

**Test the installation**:

```bash
pip install --index-url https://test.pypi.org/simple/ rocket-cli-ai
```

### Step 5: Publish to Real PyPI

```bash
# Upload to PyPI
python -m twine upload dist/*
```

**Login credentials**: Use your PyPI username and password

### Step 6: Verify Installation

```bash
# Install from PyPI
pip install rocket-cli-ai

# Test it works
rocket --version
```

## 🤖 Automatic Publishing with GitHub Actions

### Setup GitHub Secrets

1. Go to your GitHub repository
2. Navigate to: **Settings → Secrets and variables → Actions**
3. Add these secrets:

   **For Test PyPI** (optional):
   - Name: `TEST_PYPI_API_TOKEN`
   - Value: Your Test PyPI API token

   **For PyPI** (required):
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token

### Get API Tokens

**PyPI API Token**:

1. Log in to [PyPI](https://pypi.org)
2. Go to Account Settings → API tokens
3. Click "Add API token"
4. Name: "GitHub Actions"
5. Scope: "Entire account" or specific project
6. Copy the token (starts with `pypi-`)

**Test PyPI API Token** (same steps):

1. Log in to [Test PyPI](https://test.pypi.org)
2. Follow same steps as above

### Create a Release

The GitHub Action will automatically publish when you create a release:

```bash
# Tag the release
git tag v1.0.0
git push origin v1.0.0

# Or create release on GitHub UI:
# Go to: Releases → Draft a new release → Tag: v1.0.0
```

## 🔄 Updating After Publication

When you want to release a new version:

1. **Update version number**:

   ```python
   # In setup.py and pyproject.toml
   version="1.0.1"  # Increment version
   ```

2. **Commit changes**:

   ```bash
   git add .
   git commit -m "Release v1.0.1"
   git push
   ```

3. **Create new release**:

   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

4. GitHub Actions will automatically publish to PyPI!

## 📋 Pre-Publication Checklist

- [ ] Updated version numbers
- [ ] Updated GitHub URLs
- [ ] Added LICENSE file
- [ ] README.md is complete
- [ ] Tested locally: `pip install -e .`
- [ ] All tests pass: `python -m pytest TEST/`
- [ ] Built package: `python -m build`
- [ ] Checked package: `twine check dist/*`
- [ ] Tested on Test PyPI
- [ ] GitHub secrets configured

## 🎨 Package Naming

**Current name**: `rocket-cli-ai`

If the name is taken, alternatives:

- `rocket-ai-cli`
- `rocket-code-assistant`
- `rocket-ai-assistant`

Change in:

- `setup.py` → `name="new-name"`
- `pyproject.toml` → `name = "new-name"`

## 🐛 Troubleshooting

### "Package name already exists"

**Solution**: Choose a different name (see Package Naming above)

### "Invalid credentials"

**Solution**: Use API tokens instead of username/password:

```bash
twine upload -u __token__ -p pypi-YOUR_TOKEN_HERE dist/*
```

### "File already exists"

**Solution**: PyPI doesn't allow re-uploading same version. Increment version number.

### "README not rendering properly"

**Solution**: Ensure README.md has proper markdown and is referenced in setup.py

## 🌟 After Publishing

Share your package:

```bash
# Install command
pip install rocket-cli-ai

# PyPI page
https://pypi.org/project/rocket-cli-ai/

# Installation statistics
https://pypistats.org/packages/rocket-cli-ai
```

## 📊 Monitor Your Package

- **Downloads**: [PyPI Stats](https://pypistats.org)
- **Issues**: GitHub Issues tab
- **Dependencies**: [Libraries.io](https://libraries.io)

## 🎉 You're Done!

Your friends can now install with:

```bash
pip install rocket-cli-ai
rocket
```

**No cloning, no setup, just one command!** 🚀

---

**Questions?** Open an issue on GitHub or check [PyPI Documentation](https://packaging.python.org/tutorials/packaging-projects/)
