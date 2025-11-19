#!/bin/bash
# Smoke Test Script
# ==================
# Testa endpoints críticos da aplicação
#
# Uso:
#   ./scripts/smoke_test.sh
#   make smoke

set -e

# Configuração
BASE_URL="${BASE_URL:-http://localhost:5004}"
TIMEOUT=5

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Sistema GERPED - Smoke Tests${NC}"
echo -e "${BLUE}Base URL: ${BASE_URL}${NC}"
echo ""

# Contador de falhas
FAILED=0
TOTAL=0

# Função de teste
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    TOTAL=$((TOTAL + 1))
    echo -n "  ${name}... "
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "${BASE_URL}${url}" || echo "000")
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ ($http_code)${NC}"
    else
        echo -e "${RED}❌ (esperado: $expected_status, obtido: $http_code)${NC}"
        FAILED=$((FAILED + 1))
    fi
}

echo "📊 Healthchecks"
test_endpoint "healthz" "/healthz" "200"
test_endpoint "readiness" "/readiness" "200"

echo ""
echo "📈 Monitoramento"
test_endpoint "metrics" "/metrics" "200"
test_endpoint "docs (Swagger UI)" "/docs" "200"

echo ""
echo "🔐 Autenticação"
test_endpoint "login page" "/login" "200"

echo ""
echo "📱 Aplicação"
test_endpoint "dashboard (redirect)" "/" "302"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Todos os testes passaram! (${TOTAL}/${TOTAL})${NC}"
    exit 0
else
    echo -e "${RED}❌ ${FAILED}/${TOTAL} testes falharam${NC}"
    exit 1
fi

