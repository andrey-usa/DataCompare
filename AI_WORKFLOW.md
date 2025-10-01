# AI Daily Refactor Workflow with Self-Healing

This document describes the automated AI refactoring workflow with self-healing capabilities set up for the DataCompare project.

## Overview

The workflow runs daily at 2 AM UTC and uses AI (via the `aider` tool) to continuously improve the codebase by exploring new approaches, techniques, and optimizations. Each day, the AI discovers fresh ways to enhance performance, code quality, and maintainability.

**New in this version:** The workflow now includes intelligent self-healing capabilities that automatically detect and fix failures, ensuring maximum success rate within a 15-minute time budget.

## How It Works

1. **Scheduled Execution**: Runs automatically every day at 2 AM UTC
2. **Manual Trigger**: Can also be triggered manually via GitHub Actions UI
3. **Test-First Approach**: Tests are run before any changes are made
4. **AI Refactoring**: Uses `aider` with the objectives defined in `ai/prompts/daily_objectives.md`
5. **Intelligent Retry Loop**: If tests fail, automatically switches to self-healing mode
6. **Self-Healing**: Uses AI to analyze failures and apply surgical fixes (up to 5 attempts)
7. **Time-Boxed Execution**: Enforces a 15-minute maximum time limit
8. **Test Validation**: Tests are run after each attempt until they pass
9. **Branch Creation**: Only creates a new branch if:
   - AI made changes to the code
   - All tests pass after refactoring (potentially with self-healing)
10. **Pull Request**: Automatically creates a PR with the changes, noting if self-healing was used

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

### 3. AI Refactoring Loop with Self-Healing
- Sets a 15-minute time budget for the entire workflow
- Creates a new branch with timestamp: `ai-refactor/daily-YYYYMMDD-HHMMSS`
- Implements an intelligent retry loop (up to 5 attempts):

  **Attempt 1 (Initial Refactoring):**
  - Reads the refactoring objectives from `ai/prompts/daily_objectives.md`
  - Uses `aider` to explore and apply improvements to `compare.py` and `data_compare.py`
  - Runs tests to validate changes
  - Each day explores different focus areas:
    - Performance optimization and new Polars features
    - Code quality and modern Python patterns
    - New libraries and alternative implementations
    - Testing coverage and reliability enhancements
    - Keeping changes minimal (< 200 lines)

  **Attempts 2-5 (Self-Healing Mode, if needed):**
  - Triggered only if previous attempt's tests failed
  - Switches to failure recovery mode using `ai/prompts/failure_recovery.md`
  - Analyzes test failure output to identify root cause
  - Applies surgical fixes to restore functionality
  - Runs tests again to validate the fix
  - Repeats until tests pass or attempts exhausted

- **Time Budget Management:**
  - Monitors elapsed time before each attempt
  - Stops if 13-minute threshold reached (leaving 2-minute buffer)
  - Reports timeout if time budget exceeded

### 4. Check for Changes
- Only proceeds if:
  - Tests passed (either on first try or after self-healing)
  - Changes were made to the codebase

### 5. Commit and Push
- Commits changes with descriptive message
- Indicates if self-healing was used and how many attempts were needed
- Pushes to the new branch

### 6. Create Pull Request
- Automatically creates a PR with:
  - Clear title indicating AI refactor and date
  - Note if self-healing was applied (with attempt count)
  - Detailed description of objectives applied
  - Test status confirmation
  - Labels: `ai-refactor`, `automated`

### 7. Failure Reporting (if applicable)
- If all attempts fail or time limit exceeded:
  - Generates a detailed failure report
  - Includes test output and AI agent logs
  - Reports error to GitHub Actions
  - Workflow fails visibly for human review

## Refactoring Objectives

The AI follows a continuous improvement approach with two distinct modes:

### Primary Mode: Daily Refactoring (defined in `ai/prompts/daily_objectives.md`)

Encourages exploring NEW techniques each day:

**Core Mission**: Don't repeat the same improvements—discover fresh optimizations daily

**Dynamic Focus Areas**:
1. **Performance Optimization**: Profile code, explore new Polars features, try alternative algorithms
2. **Code Quality Enhancement**: Apply modern Python patterns, improve type hints, refactor for clarity
3. **Library and Tooling Updates**: Introduce new utility libraries, explore async opportunities
4. **Testing and Reliability**: Enhance coverage, add edge case handling, improve error messages

**Foundational Guidelines**:
- Preserve functionality (all tests must pass)
- Keep changes focused (< 200 lines)
- Maintain public APIs
- Verify improvements with tests and benchmarks
- Document the reasoning behind changes

### Secondary Mode: Self-Healing (defined in `ai/prompts/failure_recovery.md`)

Activated automatically when tests fail:

**Core Mission**: Diagnose and fix failures with surgical precision

**Recovery Process**:
1. **Analyze**: Read test output and identify root cause
2. **Locate**: Find the exact code causing the failure
3. **Design**: Plan minimal fix without introducing new issues
4. **Validate**: Run tests to confirm the fix works

**Recovery Strategies**:
- **Surgical Fix**: Targeted changes to broken code
- **Partial Rollback**: Revert only the problematic changes
- **Safe Fallback**: Return to last known good state if unclear

**Time Management**:
- 2-3 minutes: Analyze the failure
- 5-7 minutes: Implement the fix
- 3-5 minutes: Test and validate
- Maximum 5 attempts within 15-minute budget

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

### Tests fail after refactoring (now with self-healing)
- The workflow will automatically attempt to fix the issue (up to 5 attempts)
- Each recovery attempt uses AI to analyze and fix the failure
- If all attempts fail, the workflow will report the failure
- Check the failure report in the workflow logs for details
- May need to adjust the refactoring objectives if failures persist

### Workflow exceeds time limit
- The workflow has a hard 15-minute timeout
- If exceeded, the workflow will stop and report failure
- Check logs to see which step consumed the most time
- Consider adjusting the complexity of refactoring objectives

### No changes made
- AI determined no improvements were needed
- No branch or PR will be created
- This is normal and expected behavior

### Self-healing was triggered
- Check the PR description to see how many attempts were needed
- Review the changes carefully as they include both refactoring and fixes
- The commit message will explain what was fixed
- Consider if the daily objectives need adjustment to prevent future failures

## Manual Testing

To test the workflow locally:

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests before
pytest -v

# Test normal refactoring mode
export OPENAI_API_KEY="your-key-here"
aider --yes --message "$(cat ai/prompts/daily_objectives.md)" \
  compare.py data_compare.py

# Run tests after
pytest -v

# If tests fail, test self-healing mode
aider --yes --message "$(cat ai/prompts/failure_recovery.md)

## Current Failure Context
[Paste test failure output here]

Please analyze the failure and apply a minimal fix." \
  compare.py data_compare.py

# Verify fix
pytest -v
```

## Key Features

### 🔄 Automatic Retry Loop
- Up to 5 attempts to complete successfully
- First attempt uses normal refactoring objectives
- Subsequent attempts switch to self-healing mode
- Each attempt gets fresh analysis of what went wrong

### 🔧 Intelligent Self-Healing
- Analyzes test failure output automatically
- Identifies root cause of failures
- Applies surgical fixes to restore functionality
- Learns from each attempt to improve next one

### ⏱️ Time Budget Management
- Hard 15-minute timeout for entire workflow
- Monitors time usage before each attempt
- Stops gracefully if time budget exceeded
- Ensures workflow doesn't run indefinitely

### 📊 Detailed Failure Reporting
- Generates comprehensive failure report if all attempts fail
- Includes test output from last attempt
- Includes AI agent logs for debugging
- Surfaces as workflow error for visibility

### 🎯 Adaptive Strategy
- Starts optimistic with full refactoring
- Becomes conservative with targeted fixes if needed
- Can rollback changes and retry with different approach
- Prioritizes stability over ambitious improvements

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Aider Documentation](https://aider.chat/)
- [Polars Best Practices](https://pola-rs.github.io/polars/user-guide/)
