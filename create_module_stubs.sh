#!/bin/bash
# Create empty module files if they don't exist

MODULES_DIR="modules"

echo "Creating module directory structure..."
mkdir -p $MODULES_DIR

# Create __init__.py
touch $MODULES_DIR/__init__.py

echo "Module stubs created!"
echo "Modules are now ready in: $MODULES_DIR/"
