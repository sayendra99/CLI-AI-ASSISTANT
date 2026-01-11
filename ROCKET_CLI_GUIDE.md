# Rocket CLI - Usage Guide

## Installation

```bash
# Install from source with development dependencies
pip install -e ".[dev]"

# Or just base installation
pip install -e .
```

## Commands

### 1. Chat - General Conversation

Ask anything about coding, architecture, or development.

```bash
# Basic chat
rocket chat -m "Explain async/await in Python"

# Stream response
rocket chat -m "What is a REST API?" --stream

# Long questions
rocket chat -m "Design a microservice architecture for a social media platform"
```

**Use Cases:**

- Coding explanations
- Architecture discussions
- Best practices advice
- Problem-solving

---

### 2. Generate - Create Code

Generate production-ready code from descriptions.

```bash
# Generate Python code
rocket generate "FastAPI REST API with JWT authentication" --language python

# Generate and save to file
rocket generate "React component with hooks" -l javascript -o App.jsx

# Generate Docker configuration
rocket generate "Dockerfile for Node.js microservice" --language dockerfile -o Dockerfile

# Generate Kubernetes manifest
rocket generate "K8s deployment for Node.js app" -l yaml -o deployment.yaml

# Without streaming (get full response at once)
rocket generate "Flask app with database" --no-stream
```

**Supported Languages:**

- python, javascript, typescript, java, go, rust, c++, c#, php, ruby
- dockerfile, yaml (for K8s/Docker)
- html, css, sql

**Use Cases:**

- Boilerplate code
- API implementations
- Configuration files
- Docker/K8s manifests

---

### 3. Explain - Understand Code

Get detailed explanations of code files or snippets.

```bash
# Explain a file
rocket explain --file app.py

# Explain a code snippet
rocket explain -c "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"

# Explain JavaScript file
rocket explain --file async-handler.js --language javascript

# Explain SQL query
rocket explain -c "SELECT * FROM users WHERE created_at > NOW() - INTERVAL 30 DAY" --language sql
```

**Use Cases:**

- Understanding legacy code
- Learning programming concepts
- Code review assistance
- Debugging complex logic

---

### 4. Debug - Fix Errors

Analyze errors and get solutions.

```bash
# Debug from error message
rocket debug -c "TypeError: 'NoneType' object is not subscriptable"

# Debug a file
rocket debug --file app.py

# Debug with context
rocket debug -c "CORS error when accessing API from React" --language javascript

# Debug without streaming
rocket debug -c "ImportError: No module named 'tensorflow'" --no-stream
```

**Use Cases:**

- Fixing runtime errors
- API issues
- Configuration problems
- Dependency issues

---

### 5. Optimize - Improve Code

Get suggestions to improve code quality.

```bash
# Optimize for performance
rocket optimize --file heavy-processing.py --focus performance

# Improve readability
rocket optimize -f component.jsx --language javascript --focus readability

# Enhance security
rocket optimize --file authentication.py --focus security

# Better maintainability
rocket optimize --file legacy-code.py --focus maintainability
```

**Focus Areas:**

- `performance` - Speed and efficiency
- `readability` - Code clarity
- `security` - Security vulnerabilities
- `maintainability` - Structure and design patterns

**Use Cases:**

- Code reviews
- Refactoring
- Performance tuning
- Security hardening

---

### 6. Version - Check Version

```bash
rocket version
```

---

### 7. Config - Manage Settings

```bash
# Show current configuration
rocket config show

# Set API key
rocket config set --key api_key --value your_key_here

# Reset to defaults
rocket config reset
```

---

## Advanced Usage

### Piping and Redirection

```bash
# Save response to file
rocket chat -m "Explain callbacks" > explanation.txt

# Use with other tools
rocket generate "REST API" -l python | grep "def " | head -5
```

### Combining Commands

```bash
# Generate code, then explain it
rocket generate "Quick sort algorithm" -l python -o sort.py
rocket explain --file sort.py

# Generate, optimize, then save
rocket generate "Fibonacci" -l python | tee fib.py
rocket optimize --file fib.py --focus performance
```

### With Environment Variables

```bash
# Set API key
export GEMINI_API_KEY="your_key_here"
rocket chat -m "Hello"

# Check it's set
echo $GEMINI_API_KEY
```

---

## Examples by Use Case

### Learning Python

```bash
rocket chat -m "Explain decorators in Python with examples"
rocket generate "Decorator for logging function calls" -l python
rocket explain -c "@decorator\ndef my_function(): pass"
```

### Building a REST API

```bash
rocket generate "FastAPI with PostgreSQL and JWT" -l python -o main.py
rocket optimize --file main.py --focus performance
rocket generate "Unit tests for the API" -l python -o test_api.py
```

### Debugging Issues

```bash
rocket debug -c "RecursionError: maximum recursion depth exceeded"
rocket chat -m "How to prevent infinite recursion?"
rocket generate "Iterative solution instead of recursive" -l python
```

### DevOps Tasks

```bash
rocket generate "Dockerfile for Python FastAPI app" -o Dockerfile
rocket generate "K8s deployment manifest" -l yaml -o deployment.yaml
rocket generate "GitHub Actions CI/CD pipeline" -l yaml -o .github/workflows/ci.yml
rocket optimize --file Dockerfile --focus performance
```

### Code Review

```bash
rocket explain --file problematic_code.py
rocket debug --file problematic_code.py
rocket optimize --file problematic_code.py --focus maintainability
```

---

## Tips & Tricks

### 1. Stream Large Responses

```bash
# Good for long explanations
rocket chat -m "Architecture of a distributed system" --stream
```

### 2. Multiple Languages

```bash
# Switch languages easily
rocket generate "Hello world" -l python
rocket generate "Hello world" -l javascript
rocket generate "Hello world" -l go
```

### 3. Save to File Directly

```bash
rocket generate "REST API" -l python -o api.py
rocket optimize --file api.py --focus security
```

### 4. Quick Debugging

```bash
# Copy-paste error and get fix immediately
rocket debug -c "your_error_message_here"
```

### 5. Learning Mode

```bash
# Get detailed explanations
rocket explain -c "your_code_here"
rocket chat -m "Why does this pattern work?"
```

---

## Configuration

Create a `.env` file in your project root:

```env
GEMINI_API_KEY=your_api_key_here
MODEL=gemini-1.5-flash
TEMPERATURE=0.7
```

Or set environment variables:

```bash
export GEMINI_API_KEY="your_key"
```

---

## Troubleshooting

### API Key Issues

```bash
rocket config show  # Check if API key is set
export GEMINI_API_KEY="your_key"  # Set it
```

### No Output

```bash
# Use --stream to see real-time output
rocket generate "test" --stream
```

### Large Files

```bash
# For very large files, use explain with language flag
rocket explain --file large_file.py --language python
```

---

## Best Practices

1. **Be Specific** - More detail = better answers
2. **Use Language Flags** - Helps AI understand context
3. **Stream for Long Responses** - See output faster
4. **Save Important Code** - Use `-o` to save outputs
5. **Ask Follow-ups** - Use chat for related questions

---

## Support

For issues or feature requests:

- GitHub: https://github.com/sayendra99/CLI-AI-ASSISTANT
- Check existing issues first
- Provide detailed error messages
