#!/bin/bash

set -e  # Exit on any error

# Source directory (current folder)
SOURCE_DIR="$(pwd)/dags/"
echo "Source directory: $SOURCE_DIR"

# Destination directory (Airflow DAGs folder)
DEST_DIR="$HOME/airflow/dags/"
echo "Destination directory: $DEST_DIR"

# Sanity checks
echo ""
echo "Running sanity checks..."

# Check if rsync is installed
if ! command -v rsync &> /dev/null; then
    echo "ERROR: rsync is not installed. Please install rsync to continue."
    exit 1
fi

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "ERROR: Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

# Check if source directory is empty
if [ -z "$(ls -A "$SOURCE_DIR")" ]; then
    echo "WARNING: Source directory is empty: $SOURCE_DIR"
    read -p "Continue with empty source? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Check if destination directory exists, if not create it
if [ ! -d "$DEST_DIR" ]; then
    echo "Destination directory does not exist. Creating: $DEST_DIR"
    mkdir -p "$DEST_DIR"
fi

# Show what will be synchronized
echo ""
echo "Source contents:"
ls -la "$SOURCE_DIR" | head -20

echo ""
echo "This will synchronize files and DELETE anything in the destination that is not in the source."
read -p "Continue with synchronization? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Synchronize the directories
echo ""
echo "Starting synchronization..."
rsync -av --delete "$SOURCE_DIR" "$DEST_DIR"

# Verify synchronization
if [ $? -eq 0 ]; then
    echo ""
    echo "Synchronization complete successfully!"
else
    echo ""
    echo "ERROR: Synchronization failed!"
    exit 1
fi

