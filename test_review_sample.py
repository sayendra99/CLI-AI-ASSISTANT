# Test Python file with intentional issues for rocket review

import os

# ISSUE 1: Hardcoded secret (HIGH severity)
api_key = "sk-1234567890abcdef"
password = "admin123"

# ISSUE 2: Unsafe eval (MEDIUM severity)
user_input = input("Enter code: ")
result = eval(user_input)

# ISSUE 3: Broad except clause (LOW severity)
try:
    risky_operation()
except:
    pass

# ISSUE 4: Missing docstring (LOW severity)
def calculate_total(items):
    total = 0
    for item in items:
        total += item
    return total

# ISSUE 5: String concatenation in loop (LOW severity)
def build_string(words):
    result = ""
    for word in words:
        result += word + " "
    return result
