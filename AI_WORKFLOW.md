# AI Daily Refactor Workflow

This document describes the automated AI refactoring workflow set up for the DataCompare project.

## Overview

The workflow runs daily at 2 AM UTC and uses AI (via the `aider` tool) to make small, focused improvements to the codebase following best practices for Polars data processing.

## How It Works

1. **Scheduled Execution**: Runs automatically every day at 2 AM UTC
2. **Manual Trigger**: Can also be triggered manually via GitHub Actions UI
3. **Test-First Approach**: Tests are run before any changes are made
4. **AI Refactoring**: Uses `aider` with the objectives defined in `ai/prompts/daily_objectives.md`
5. **Test Validation**: Tests are run again after refactoring
6. **Branch Creation**: Only creates a new branch if:
   - AI made changes to the code
   - All tests pass after refactoring
7. **Pull Request**: Automatically creates a PR with the changes

## Setup Requirements

To enable the workflow, you need to:

1. **Set up OpenAI API Key**:
   - Go to repository Settings → Secrets and variables → Actions
   - Add a secret named `OPENAI_API_KEY` with your OpenAI API key
   - The workflow will skip AI refactoring if this secret is not set

2. **Configure Branch Protection** (recommended):
   - Enable branch protection for the main/master branch
   - Require PR reviews before merging
   - Enable status checks to ensure tests pass

## Workflow Steps

### 1. Checkout and Setup
- Checks out the repository code
- Sets up Python 3.11 environment
- Installs all dependencies from `requirements.txt` and `requirements-dev.txt`

### 2. Pre-Refactor Tests
- Runs the full test suite with `pytest -v`
- Ensures the codebase is in a good state before any changes

### 3. AI Refactoring
- Creates a new branch with timestamp: `ai-refactor/daily-YYYYMMDD-HHMMSS`
- Reads the refactoring objectives from `ai/prompts/daily_objectives.md`
- Uses `aider` to apply improvements to `compare.py` and `data_compare.py`
- Focuses on:
  - Using lazy evaluation and pipeline chaining
  - Filtering early and minimizing conversions
  - Optimizing memory usage
  - Being mindful of parallelism
  - Keeping changes minimal (< 200 lines)

### 4. Post-Refactor Tests
- Runs the test suite again after AI changes
- Ensures no functionality was broken

### 5. Commit and Push
- Only proceeds if:
  - Tests passed
  - Changes were made
- Commits changes with descriptive message
- Pushes to the new branch

### 6. Create Pull Request
- Automatically creates a PR with:
  - Clear title indicating AI refactor and date
  - Detailed description of objectives applied
  - Test status confirmation
  - Labels: `ai-refactor`, `automated`

## Refactoring Objectives

The AI follows these guidelines (defined in `ai/prompts/daily_objectives.md`):

1. **Use lazy evaluation and pipeline chaining**: Prefer `scan_*` functions and `LazyFrame` pipelines
2. **Filter early and minimize conversions**: Apply filters ASAP, avoid unnecessary type conversions
3. **Optimize memory usage**: Select only needed columns, use appropriate data types
4. **Be mindful of parallelism**: Don't force extra parallelism without proven benefits
5. **Keep changes minimal**: Limit to fewer than 200 lines of change
6. **Run tests and benchmarks**: Verify no regressions

## Permissions

The workflow requires:
- `contents: write` - To create branches and push commits
- `pull-requests: write` - To create pull requests

## Security Considerations

- The workflow only runs on the scheduled trigger or manual dispatch
- It doesn't run on pull requests from forks
- OpenAI API key is stored as a GitHub secret (encrypted)
- All changes go through a PR review process
- Tests must pass before any changes are committed

## Monitoring

You can monitor the workflow:
1. Go to the repository's Actions tab
2. Look for "Daily AI Refactor" workflow runs
3. Click on any run to see detailed logs of each step

## Customization

To customize the workflow:

1. **Change Schedule**: Edit the `cron` expression in the workflow file
2. **Add More Files**: Add file paths to the `aider` command
3. **Modify Objectives**: Edit `ai/prompts/daily_objectives.md`
4. **Change AI Model**: Configure aider to use different models via environment variables

## Troubleshooting

### Workflow doesn't run
- Check if OPENAI_API_KEY is set in repository secrets
- Verify the workflow file syntax is valid
- Check GitHub Actions quota for your account

### Tests fail after refactoring
- The workflow will not create a branch or PR
- Check the logs to see what changed
- May need to adjust the refactoring objectives

### No changes made
- AI determined no improvements were needed
- No branch or PR will be created
- This is normal and expected behavior

## Manual Testing

To test the workflow locally:

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests before
pytest -v

# Use aider for refactoring (requires OPENAI_API_KEY)
export OPENAI_API_KEY="your-key-here"
aider --yes --message "$(cat ai/prompts/daily_objectives.md)" \
  compare.py data_compare.py

# Run tests after
pytest -v
```

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Aider Documentation](https://aider.chat/)
- [Polars Best Practices](https://pola-rs.github.io/polars/user-guide/)
