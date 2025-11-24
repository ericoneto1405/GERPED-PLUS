#!/usr/bin/env bash
set -euo pipefail

# Diretórios base
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_ROOT="${REPO_DIR}/backups"
BANCO_SRC="${REPO_DIR}/instance/sistema.db"
BANCO_DEST_DIR="${REPO_DIR}/instance/backups"
RECIBOS_SRC="${REPO_DIR}/uploads/recibos_pagamento"

# Nome do backup
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
DEST_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "${DEST_DIR}" "${BANCO_DEST_DIR}" "${RECIBOS_SRC}"

if [[ ! -f "${BANCO_SRC}" ]]; then
    echo "Banco ${BANCO_SRC} não encontrado." >&2
    exit 1
fi

# Backup do banco (mantém também a rotina existente em instance/backups)
cp "${BANCO_SRC}" "${BANCO_DEST_DIR}/sistema_backup_${TIMESTAMP}.db"
cp "${BANCO_SRC}" "${DEST_DIR}/sistema.db"

# Backup dos recibos
tar -czf "${DEST_DIR}/recibos_pagamento.tar.gz" -C "${RECIBOS_SRC}" .

echo "Backup financeiro criado em ${DEST_DIR}"
