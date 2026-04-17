#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="airflow"
CONFIGMAP_NAME="my-script"
SCRIPT_DIR="resources/config-map"

# -------- List available scripts --------
echo "Available scripts in $SCRIPT_DIR/:"
mapfile -t scripts < <(ls "$SCRIPT_DIR"/*.py 2>/dev/null)

if [[ ${#scripts[@]} -eq 0 ]]; then
    echo "No Python scripts found in $SCRIPT_DIR"
    exit 1
fi

for i in "${!scripts[@]}"; do
    echo "$((i+1))) ${scripts[$i]}"
done

# -------- Ask user to select a script --------
read -rp "Enter the number of the script you want to mount: " choice

if ! [[ "$choice" =~ ^[0-9]+$ ]] || ((choice < 1 || choice > ${#scripts[@]})); then
    echo "Invalid selection."
    exit 1
fi

SCRIPT_FILE="${scripts[$((choice-1))]}"

if [[ ! -f "$SCRIPT_FILE" ]]; then
    echo "Selected file not found: $SCRIPT_FILE"
    exit 1
fi

echo "Updating ConfigMap '$CONFIGMAP_NAME' in namespace '$NAMESPACE' from $SCRIPT_FILE..."

kubectl create configmap "$CONFIGMAP_NAME" \
    --from-file=script.py="$SCRIPT_FILE" \
    -n "$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "ConfigMap '$CONFIGMAP_NAME' updated successfully from $SCRIPT_FILE."