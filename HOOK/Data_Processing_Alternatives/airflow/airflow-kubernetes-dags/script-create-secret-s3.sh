#!/usr/bin/env bash
set -euo pipefail

# ---- Config ----
ENV_FILE=".env"
SECRET_NAME="my-s3-credentials"
NAMESPACE="airflow"

# Mapping: .env key -> Kubernetes secret key
declare -A KEY_MAP=(
  ["MY_S3_ACCESS_KEY_ID"]="my_s3_access_key_id"
  ["MY_S3_SECRET_ACCESS_KEY"]="my_s3_secret_access_key"
)

# ---- Checks ----
if [[ ! -f "$ENV_FILE" ]]; then
  echo "$ENV_FILE not found"
  exit 1
fi

# ---- Guardrail: block quoted values ----
if grep -nE '="|="' "$ENV_FILE"; then
  echo "Quoted values detected in $ENV_FILE."
  echo "   Remove quotes for Kubernetes compatibility."
  exit 1
fi

# ---- Helper: read raw value from .env without shell parsing ----
get_env_value() {
  local key="$1"
  # Extract everything after first '=' for exact value
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return 1
  fi
  printf '%s' "${line#*=}"
}

# ---- Build kubectl args safely ----
KUBECTL_ARGS=()

for env_key in "${!KEY_MAP[@]}"; do
  k8s_key="${KEY_MAP[$env_key]}"
  value="$(get_env_value "$env_key")"

  if [[ -z "$value" ]]; then
    echo "Missing required key in $ENV_FILE: $env_key"
    exit 1
  fi

  KUBECTL_ARGS+=( "--from-literal=${k8s_key}=${value}" )
done

echo "Syncing Kubernetes secret '$SECRET_NAME' in namespace '$NAMESPACE'..."

kubectl create secret generic "$SECRET_NAME" \
  "${KUBECTL_ARGS[@]}" \
  -n "$NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret synced successfully."

# Safe confirmation
kubectl get secret "$SECRET_NAME" -n "$NAMESPACE"