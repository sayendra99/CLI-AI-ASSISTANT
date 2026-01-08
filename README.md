# CLI-AI-ASSISTANT

A small command-line coding assistant that uses OpenAI to provide features
like quick prompts, configuration management, and a simple logging setup.

What we did

- Added a project layout with a `Rocket` package and test utilities.
- Created a virtual environment and installed runtime dependencies.
- Added a `.env` loader for `OPENAI_API_KEY` and a test script to verify
  configuration and logging.

How it works (very short)

- Place your OpenAI key in `.env` as `OPENAI_API_KEY=sk-...` or set the
  environment variable for the session.
- Activate the venv, install dependencies, then run the test script:

  ```powershell
  . .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt  # or pip install packages manually
  python -u test_setup.py
  ```

Security note: never commit `.env` or secret keys; rotate any key pasted
publicly.
