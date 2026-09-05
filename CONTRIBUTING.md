# Contributing to Google Lens Scraper

We welcome contributions! Please follow these guidelines to help keep the codebase clean and reliable.

## Development Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/taazkareem/google-lens-scraper.git
   cd google-lens-scraper
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   scrapling install
   ```

3. Run linting and formatting:
   ```bash
   ruff check .
   ruff format .
   ```

4. Run type checking:
   ```bash
   mypy src/google_lens_scraper
   ```

5. Run test suite:
   ```bash
   pytest
   ```

## Pull Request Guidelines

- Ensure all unit tests pass before submitting.
- Write tests for any new features or bug fixes.
- Follow Ruff and Mypy formatting and typing standards.
