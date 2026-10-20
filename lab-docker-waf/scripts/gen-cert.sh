#!/bin/bash
# Generates a self-signed certificate for the asset host.
# Usage: scripts/gen-cert.sh [hostname]   (default docker.example.com)
set -euo pipefail
HOST=${1:-docker.example.com}
DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/certs"
mkdir -p "$DIR"
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout "$DIR/server.key" -out "$DIR/server.crt" \
  -subj "/CN=$HOST" -addext "subjectAltName=DNS:$HOST,DNS:localhost,IP:127.0.0.1"
echo "Certificate created in $DIR for $HOST"
