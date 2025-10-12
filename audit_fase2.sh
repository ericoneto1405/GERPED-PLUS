set -euo pipefail

REPO_URL="${1:-https://SEU_HOST}"  # passe o host de staging/produção, ex.: https://app.seusistema.com

echo "== HEADERS =="
curl -sI "http://${REPO_URL#https://}" | sed -n '1,5p'
curl -sI "$REPO_URL" | egrep -i 'strict-transport-security|content-security-policy|x-content-type-options|x-frame-options|referrer-policy|cross-origin'

echo "== GREP ROTAS =="
rg "@.*route\\(.*excluir|/remover|/delete" -n meu_app || true
rg "methods=\\['POST'|\\\"POST\\\"" -n meu_app || true
rg "WTF_CSRF_ENABLED|WTF_CSRF_METHODS" -n config.py

echo "== LOGIN / REGEN SESSION =="
rg -n "regenerate_session|session\\.clear\\(\\)" meu_app || true

echo "== IDOR =="
rg -n "@owns_resource|owns_resource\\(" meu_app || true

echo "== SUPPLY-CHAIN =="
pre-commit run --all-files || true
pip-audit -r requirements.txt || true
bandit -r . -q || true

echo "== TESTES =="
pytest -q || true

echo "== ZAP (baseline) =="
docker run --rm -u zap -v "$PWD":/zap/wrk -t owasp/zap2docker-stable zap-baseline.py \
  -t "$REPO_URL" -r zap_report.html -x zap_report.xml -w zap_warnings.md || true

echo ">> Artefatos: zap_report.html, zap_report.xml, zap_warnings.md"
