#!/usr/bin/env bash
set -euo pipefail

# ---- Config ----
ENV_FILE=".env"
SECRET_NAME="my-env-secret"
NAMESPACE="airflow"

# ---- Check if .env exists ----
if [[ ! -f "$ENV_FILE" ]]; then
  echo "$ENV_FILE not found"
  exit 1
fi

# ---- Guardrail: prevent quoted values ----
if grep -nE '="|="' "$ENV_FILE"; then
  echo "Quoted values detected in $ENV_FILE."
  echo "   Remove quotes for Kubernetes compatibility."
  exit 1
fi

echo "Syncing Kubernetes secret '$SECRET_NAME' in namespace '$NAMESPACE' from $ENV_FILE ..."

kubectl create secret generic "$SECRET_NAME" \
  --from-env-file="$ENV_FILE" \
  -n "$NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret synced successfully."

# Safe confirmation (does not print secret values)
kubectl get secret "$SECRET_NAME" -n "$NAMESPACE"