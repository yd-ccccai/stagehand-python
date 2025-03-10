#!/bin/bash

# Define source directories (adjust as needed)
SOURCE_DIRS="evals stagehand"

# Apply Black formatting only to source directories
echo "Applying Black formatting..."
black $SOURCE_DIRS

# Fix import sorting (addresses I001 errors)
echo "Sorting imports..."
isort $SOURCE_DIRS

# Apply Ruff with autofix for remaining issues
echo "Applying Ruff autofixes..."
ruff check --fix $SOURCE_DIRS

echo "Checking for remaining issues..."
ruff check $SOURCE_DIRS

echo "Done! Code has been formatted and linted." 