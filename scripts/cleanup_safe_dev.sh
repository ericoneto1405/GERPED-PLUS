#!/usr/bin/env bash
set -euo pipefail

# Limpeza segura para desenvolvimento: apenas caches e arquivos temporários
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Limpando caches e arquivos temporários em: $ROOT_DIR"

rm -rf "$ROOT_DIR/.pytest_cache" || true
rm -f "$ROOT_DIR/.coverage" || true

find "$ROOT_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} + || true
find "$ROOT_DIR" -name "*.pyc" -type f -delete || true
find "$ROOT_DIR" -name ".DS_Store" -type f -delete || true

echo "Limpeza segura concluída."
