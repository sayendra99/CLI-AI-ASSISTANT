from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="rocket-cli-ai",  # Unique name for PyPI
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "google-generativeai>=0.3.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "rich>=13.0.0",
        "click>=8.0.0",
        "aiohttp>=3.8.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "rocket=Rocket.CLI.Main:main",
        ],
    },
    python_requires=">=3.8",
    author="Rocket CLI Team",
    author_email="rocket-cli@example.com",
    description="🚀 Free, Open-Source AI-Powered Coding Assistant - Local, Private, No API Keys Required",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/CLI-AI-ASSISTANT",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/CLI-AI-ASSISTANT/issues",
        "Source": "https://github.com/yourusername/CLI-AI-ASSISTANT",
        "Documentation": "https://github.com/yourusername/CLI-AI-ASSISTANT/blob/main/ROCKET_CLI_GUIDE.md",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    keywords="ai, coding-assistant, cli, llm, ollama, gemini, code-generation, developer-tools, free, open-source",
    license="MIT",
)
