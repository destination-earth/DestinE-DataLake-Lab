#!/usr/bin/env bash
set -euo pipefail

PROJECT_DAGS_DIR="$(pwd)/dags"
AIRFLOW_DAGS_DIR="${AIRFLOW_HOME:-$HOME/airflow}/dags"

echo "Project DAGs:  $PROJECT_DAGS_DIR"
echo "Airflow DAGs:  $AIRFLOW_DAGS_DIR"
echo

# Ensure project dags folder exists
if [ ! -d "$PROJECT_DAGS_DIR" ]; then
  echo "No ./dags directory found in current folder:"
  echo "   $(pwd)"
  exit 1
fi

# If airflow/dags exists and is not a symlink, back it up
if [ -e "$AIRFLOW_DAGS_DIR" ] && [ ! -L "$AIRFLOW_DAGS_DIR" ]; then
  BACKUP="$AIRFLOW_DAGS_DIR.bak.$(date +%Y%m%d-%H%M%S)"
  echo "$AIRFLOW_DAGS_DIR exists and is not a symlink."
  echo "Backing it up to: $BACKUP"
  mv "$AIRFLOW_DAGS_DIR" "$BACKUP"
fi

# If symlink already exists, verify it
if [ -L "$AIRFLOW_DAGS_DIR" ]; then
  TARGET="$(readlink "$AIRFLOW_DAGS_DIR")"
  if [ "$TARGET" = "$PROJECT_DAGS_DIR" ]; then
    echo "Symlink already exists and is correct."
    exit 0
  else
    echo "Symlink exists but points to: $TARGET"
    echo "Replacing symlink..."
    rm "$AIRFLOW_DAGS_DIR"
  fi
fi

# Ensure airflow home exists
mkdir -p "$(dirname "$AIRFLOW_DAGS_DIR")"

# Create symlink
ln -s "$PROJECT_DAGS_DIR" "$AIRFLOW_DAGS_DIR"

echo "Symlink created:"
ls -l "$AIRFLOW_DAGS_DIR"

echo
echo "Done! Restart Airflow scheduler & webserver if they are running."
