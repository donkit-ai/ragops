#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
STATIC_DIR="$PROJECT_ROOT/src/donkit_ragops/web/static"

echo "Building frontend..."

cd "$FRONTEND_DIR"

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm ci
fi

# Build
echo "Running build..."
npm run build

# Copy to static
echo "Copying to static/..."
mkdir -p "$STATIC_DIR"
rm -rf "$STATIC_DIR"/*
cp -r dist/* "$STATIC_DIR/"

# Add __init__.py for poetry to include it
touch "$STATIC_DIR/__init__.py"

echo "Done! Frontend built and copied to src/donkit_ragops/web/static/"
