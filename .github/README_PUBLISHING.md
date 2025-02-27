# Publishing stagehand-python to PyPI

This repository is configured with a GitHub Actions workflow to automate the process of publishing new versions to PyPI.

## Prerequisites

Before using the publishing workflow, ensure you have:

1. Set up the following secrets in your GitHub repository settings:
   - `PYPI_USERNAME`: Your PyPI username
   - `PYPI_API_TOKEN`: Your PyPI API token (not your password)

## How to Publish a New Version

### Manual Trigger

1. Go to the "Actions" tab in your GitHub repository
2. Select the "Publish to PyPI" workflow from the list
3. Click "Run workflow" on the right side
4. Configure the workflow:
   - Choose the release type:
     - `patch` (e.g., 0.3.0 → 0.3.1) for bug fixes
     - `minor` (e.g., 0.3.0 → 0.4.0) for backward-compatible features
     - `major` (e.g., 0.3.0 → 1.0.0) for breaking changes
   - Toggle "Create GitHub Release" if you want to create a GitHub release
5. Click "Run workflow" to start the process

### What Happens During Publishing

The workflow will:

1. Checkout the repository
2. Set up Python environment
3. Install dependencies
4. **Run Ruff linting checks**:
   - Checks for code style and quality issues
   - Verifies formatting according to project standards
   - Fails the workflow if issues are found
5. Run tests to ensure everything works
6. Update the version number using bumpversion
7. Build the package
8. Upload to PyPI
9. Push the version bump commit and tag
10. Create a GitHub release (if selected)

## Code Quality Standards

This project uses Ruff for linting and formatting. The workflow enforces these standards before publishing:

- Style checks following configured rules in `pyproject.toml`
- Format verification without making changes
- All linting issues must be fixed before a successful publish

To run the same checks locally:
```bash
# Install Ruff
pip install ruff

# Run linting
ruff check .

# Check formatting
ruff format --check .

# Auto-fix issues where possible
ruff check --fix .
ruff format .

# Use Black to format the code
black .
```

## Troubleshooting

If the workflow fails, check the following:

1. **Linting errors**: Fix any issues reported by Ruff
2. Ensure all secrets are properly set
3. Verify that tests pass locally
4. Check if you have proper permissions on the repository
5. Make sure you have a PyPI account with publishing permissions 