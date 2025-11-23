#!/usr/bin/env bash
# Automação de deploy com rollback seguro para o Sistema GERPED
# Uso: deploy_with_rollback.sh /caminho/artefato.tar.gz

set -euo pipefail
shopt -s nullglob

APP_NAME="${APP_NAME:-gerped}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/${APP_NAME}}"
RELEASES_DIR="${RELEASES_DIR:-${DEPLOY_ROOT}/releases}"
SHARED_DIR="${SHARED_DIR:-${DEPLOY_ROOT}/shared}"
CURRENT_LINK="${CURRENT_LINK:-${DEPLOY_ROOT}/current}"
BACKUP_DIR="${BACKUP_DIR:-${DEPLOY_ROOT}/backups}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
ARTIFACT_PATH="${1:-${ARTIFACT_PATH:-}}"
PRE_DEPLOY_HOOK="${PRE_DEPLOY_HOOK:-}"
POST_DEPLOY_HOOK="${POST_DEPLOY_HOOK:-}"
MIGRATION_CMD="${MIGRATION_CMD:-flask db upgrade}"
ROLLBACK_CMD="${ROLLBACK_CMD:-flask db downgrade -1}"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

abort() {
    log "ERRO: $*"
    exit 1
}

ensure_dirs() {
    mkdir -p "${RELEASES_DIR}" "${SHARED_DIR}" "${BACKUP_DIR}"
}

run_hook() {
    local hook_cmd="$1"
    local stage="$2"
    if [[ -n "${hook_cmd}" ]]; then
        log "Executando hook ${stage}: ${hook_cmd}"
        bash -lc "${hook_cmd}"
    fi
}

perform_rollback() {
    log "Iniciando rollback automático..."
    if [[ -L "${CURRENT_LINK}" ]]; then
        local previous_release
        previous_release="$(readlink "${CURRENT_LINK}")"
        if [[ -n "${previous_release}" && -d "${previous_release}" ]]; then
            log "Voltando para release anterior: ${previous_release}"
            ln -sfn "${previous_release}" "${CURRENT_LINK}"
        fi
    fi

    if [[ -n "${ROLLBACK_CMD}" ]]; then
        log "Executando comando de rollback de banco: ${ROLLBACK_CMD}"
        (cd "${CURRENT_LINK}" && bash -lc "${ROLLBACK_CMD}") || \
            log "Aviso: rollback de banco falhou, verifique manualmente."
    fi

    log "Rollback concluído."
}

trap 'perform_rollback' ERR

[[ -n "${ARTIFACT_PATH}" ]] || abort "Informe o caminho para o artefato empacotado."
[[ -f "${ARTIFACT_PATH}" ]] || abort "Artefato não encontrado em: ${ARTIFACT_PATH}"

ensure_dirs

TIMESTAMP="$(date '+%Y%m%d%H%M%S')"
NEW_RELEASE="${RELEASES_DIR}/${TIMESTAMP}"
log "Preparando nova release em ${NEW_RELEASE}"
mkdir -p "${NEW_RELEASE}"

log "Extraindo artefato..."
tar -xzf "${ARTIFACT_PATH}" -C "${NEW_RELEASE}"

if [[ -d "${SHARED_DIR}" ]]; then
    log "Atualizando links simbólicos do diretório compartilhado..."
    for shared_path in "${SHARED_DIR}"/*; do
        [[ -e "${shared_path}" ]] || continue
        shared_item="$(basename "${shared_path}")"
        target="${NEW_RELEASE}/${shared_item}"
        rm -rf "${target}"
        ln -s "${shared_path}" "${target}"
    done
fi

run_hook "${PRE_DEPLOY_HOOK}" "pré-deploy"

log "Executando migrações de banco de dados..."
(cd "${NEW_RELEASE}" && bash -lc "${MIGRATION_CMD}")

if [[ -L "${CURRENT_LINK}" ]]; then
    backup_snapshot="${BACKUP_DIR}/$(date '+%Y%m%d%H%M%S')"
    log "Criando backup lógico do release atual em ${backup_snapshot}"
    mkdir -p "${backup_snapshot}"
    rsync -a --delete "${CURRENT_LINK}/" "${backup_snapshot}/" || log "Aviso: backup do release atual falhou."
fi

log "Atualizando link simbólico para nova release..."
ln -sfn "${NEW_RELEASE}" "${CURRENT_LINK}"

run_hook "${POST_DEPLOY_HOOK}" "pós-deploy"

log "Nova release ativa: ${NEW_RELEASE}"

log "Limpando releases antigas, mantendo as últimas ${KEEP_RELEASES}..."
old_releases="$(ls -1dt "${RELEASES_DIR}"/* 2>/dev/null | tail -n +"$((KEEP_RELEASES + 1))")"
if [[ -n "${old_releases}" ]]; then
    while IFS= read -r release_path; do
        [[ -z "${release_path}" ]] && continue
        rm -rf "${release_path}"
    done <<< "${old_releases}"
fi

trap - ERR
log "Deploy finalizado com sucesso."
