# GitHub Copilot Instructions

## Project Context
This is a high-performance file comparison tool using Polars and Python 3.14+.

## UV Package Manager - CRITICAL INSTRUCTIONS ⚡

**ALWAYS use `uv` commands - NEVER use pip, venv, virtualenv, or poetry!**

### ❌ NEVER DO THIS:
```bash
pip install package
pip install -r requirements.txt
python -m venv .venv
source .venv/bin/activate           # Legacy - DON'T USE
.venv\Scripts\Activate.ps1          # Legacy - DON'T USE
virtualenv .venv
poetry add package
conda activate env
```

### ✅ ALWAYS DO THIS:

#### Installing Dependencies:
```bash
# Add runtime dependency
uv add polars

# Add development dependency
uv add --dev pytest

# Install project in editable mode (replaces: pip install -e .)
uv pip install -e .

# Sync all dependencies from lockfile (replaces: pip install -r requirements.txt)
uv sync
```

#### Running Commands (NO ACTIVATION NEEDED!):
```bash
# Run any Python script - uv handles venv automatically
uv run python src/data_compare.py --gui
uv run pytest -v
uv run python -m module

# Run installed console scripts
uv run datacompare --gui
uv run datacompare file1.csv file2.csv --keys id
```

#### Python Version Management:
```bash
# Install specific Python version
uv python install 3.14

# Create venv with specific Python
uv venv --python 3.14

# Pin Python version for this project
uv python pin 3.14

# List available Python versions
uv python list
```

#### Running Tools Temporarily (like pipx):
```bash
# Run tool without installing (uvx = uv tool run)
uvx ruff check .
uvx ruff format .
uvx black .
uvx mypy .
```

#### Project Workflow:
```bash
# Initialize new project
uv init project-name

# Add dependency and update lock
uv add package

# Lock dependencies
uv lock

# Sync environment to match lockfile
uv sync

# Remove dependency
uv remove package
```

#### Working with Multiple Python Versions:
```bash
# Run with specific Python version
uv run --python 3.14 python script.py
uv run --python pypy@3.11 pytest

# Create venv with different Python
uv venv --python 3.13
```

### Why uv is Better:
- **10-100x faster** than pip (written in Rust)
- **No activation needed** - `uv run` handles everything
- **Automatic venv management** - creates .venv when needed
- **Universal lockfile** - `uv.lock` for reproducible builds
- **Python version management** - no need for pyenv
- **Single tool** - replaces pip, pip-tools, pipx, poetry, pyenv, virtualenv
- **Disk efficient** - global cache with deduplication

### This Project's Common Commands:
```bash
# Development
uv run python src/data_compare.py --gui
uv run python src/data_compare.py file1.csv file2.csv --keys id
uv run pytest -v

# Using console script (after uv pip install -e .)
uv run datacompare --gui
uv run datacompare tests/data/sales1.csv tests/data/sales2.csv --keys id

# Code quality
uvx ruff format .
uvx ruff check .
uvx ruff check --fix .

# Type checking
uvx mypy src/
```

### Environment Variables:
```bash
# Set Python path for uv
$env:UV_PYTHON = ".venv\Scripts\python.exe"  # Windows
export UV_PYTHON=".venv/bin/python"          # Linux/Mac

# Use specific Python globally
$env:UV_PYTHON_PREFERENCE = "only-system"
```

## Coding Guidelines

1. **Python Version**: Use Python 3.14+ features
   - Modern type hints with `type` statement
   - Use `|` for union types
   - Use built-in generic types (list, dict, tuple)

2. **Data Processing**: Prefer Polars over Pandas
   - Use `polars.DataFrame` for all data operations
   - Leverage Polars' lazy evaluation when possible
   - Use Polars expressions for vectorized operations

3. **Concurrency**: Use ThreadPoolExecutor for all parallel operations
   - Use `concurrent.futures.ThreadPoolExecutor` for optimal performance
   - Polars releases the GIL internally (Rust-based), providing true parallelism
   - ThreadPoolExecutor avoids process spawning overhead (~30x faster than ProcessPoolExecutor)
   - No pickling overhead, shared memory access is efficient

4. **Code Style**:
   - Line length: 120 characters max
   - Use ruff for formatting and linting
   - Follow PEP 8 with modern Python conventions

5. **Testing**:
   - Write pytest tests for new features
   - Keep tests in the `tests/` directory

## Project Structure
```
DataCompare/
├── src/
│   ├── compare.py          # Core comparison logic
│   ├── data_compare.py     # Main application (CLI + GUI)
│   └── __init__.py
├── tests/
│   ├── data/               # Test data files
│   ├── test_cli_json.py
│   └── test_sales_compare.py
├── .vscode/
│   └── settings.json       # VS Code config with Copilot settings
├── .github/
│   ├── copilot-instructions.md  # This file
│   └── workflows/
│       └── ai-refactory.yml     # Archived placeholder workflow
├── benchmarks/
│   └── benchmark_compare.py     # Archived placeholder
├── pyproject.toml          # Project config (uv-managed)
├── uv.lock                 # Lockfile (auto-generated)
└── README.md
```

## Common Tasks

### Running the application:
```bash
# CLI mode
uv run python src/data_compare.py file1.csv file2.csv --keys id

# GUI mode
uv run python src/data_compare.py --gui

# Using console script (cleaner)
uv run datacompare file1.csv file2.csv --keys id
uv run datacompare --gui
```

### Running tests:
```bash
# All tests
uv run pytest -v

# Specific test file
uv run pytest tests/test_sales_compare.py -v

# With coverage
uv run pytest --cov=src --cov-report=html
```

### Code quality:
```bash
# Format code
uvx ruff format .

# Check linting
uvx ruff check .

# Fix auto-fixable issues
uvx ruff check --fix .

# Type checking
uvx mypy src/
```
