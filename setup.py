from setuptools import setup, find_packages

setup(
    name="rocket-cli",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "google-generativeai>=0.3.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "rich>=13.0.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "rocket=Rocket.CLI.Main:main",
        ],
    },
    python_requires=">=3.8",
    author="Rocket CLI Team",
    description="AI-powered coding assistant CLI",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
