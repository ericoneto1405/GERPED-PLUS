#!/bin/bash
# ==============================================================================
# Script de verificação de segurança completo
# ==============================================================================

set -e

echo "🔒 INICIANDO VERIFICAÇÃO DE SEGURANÇA"
echo "========================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
ERRORS=0
WARNINGS=0

# 1. Verificar SECRET_KEY
echo "1️⃣  Verificando SECRET_KEY..."
if grep -q "dev-key-insecure" config.py; then
    echo -e "${RED}❌ SECRET_KEY padrão detectada em config.py${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✅ SECRET_KEY configurada${NC}"
fi
echo ""

# 2. Bandit - SAST
echo "2️⃣  Executando Bandit (SAST)..."
if command -v bandit &> /dev/null; then
    bandit -c pyproject.toml -r meu_app/ || ((WARNINGS++))
    echo -e "${GREEN}✅ Bandit executado${NC}"
else
    echo -e "${YELLOW}⚠️  Bandit não instalado${NC}"
    ((WARNINGS++))
fi
echo ""

# 3. Safety - CVE check
echo "3️⃣  Verificando vulnerabilidades conhecidas (Safety)..."
if command -v safety &> /dev/null; then
    safety check --json || ((WARNINGS++))
    echo -e "${GREEN}✅ Safety executado${NC}"
else
    echo -e "${YELLOW}⚠️  Safety não instalado${NC}"
    ((WARNINGS++))
fi
echo ""

# 4. Verificar arquivos sensíveis
echo "4️⃣  Verificando arquivos sensíveis..."
SENSITIVE_FILES=(".env" "secrets.py" "*.pem" "*.key" "google-credentials.json")
for file in "${SENSITIVE_FILES[@]}"; do
    if find . -name "$file" -not -path "./venv/*" -not -path "./.venv/*" 2>/dev/null | grep -q .; then
        echo -e "${RED}❌ Arquivo sensível encontrado: $file${NC}"
        ((ERRORS++))
    fi
done
echo -e "${GREEN}✅ Verificação de arquivos sensíveis completa${NC}"
echo ""

# 5. Verificar .gitignore
echo "5️⃣  Verificando .gitignore..."
REQUIRED_IGNORES=(".env" "*.db" "uploads/" "instance/logs/")
for ignore in "${REQUIRED_IGNORES[@]}"; do
    if ! grep -q "$ignore" .gitignore 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Faltando no .gitignore: $ignore${NC}"
        ((WARNINGS++))
    fi
done
echo -e "${GREEN}✅ .gitignore verificado${NC}"
echo ""

# 6. Verificar requirements com hashes
echo "6️⃣  Verificando requirements.txt..."
if [ -f requirements.txt ]; then
    if grep -q "sha256" requirements.txt; then
        echo -e "${GREEN}✅ requirements.txt com hashes SHA256${NC}"
    else
        echo -e "${YELLOW}⚠️  requirements.txt sem hashes (recompile com pip-tools)${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}❌ requirements.txt não encontrado${NC}"
    ((ERRORS++))
fi
echo ""

# 7. Verificar CSRF em templates
echo "7️⃣  Verificando CSRF tokens em templates..."
FORMS_WITHOUT_CSRF=$(grep -r "<form" meu_app/templates --include="*.html" | grep -v "csrf_token" | wc -l)
if [ "$FORMS_WITHOUT_CSRF" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $FORMS_WITHOUT_CSRF formulários sem CSRF token${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}✅ Todos os formulários com CSRF token${NC}"
fi
echo ""

# Resumo final
echo "========================================"
echo "📊 RESUMO DA VERIFICAÇÃO"
echo "========================================"
echo ""
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ TODOS OS CHECKS PASSARAM!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS AVISOS encontrados${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS ERROS e $WARNINGS AVISOS encontrados${NC}"
    exit 1
fi

