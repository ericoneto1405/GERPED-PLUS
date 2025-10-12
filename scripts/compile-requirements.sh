#!/bin/bash
# ==============================================================================
# Script de compilação de requirements com hashes SHA256
# ==============================================================================
# 
# Este script gera requirements.txt com versões fixadas e hashes SHA256
# para proteção contra supply chain attacks.
# 
# Uso:
#   ./scripts/compile-requirements.sh
# 
# ==============================================================================

set -e

echo "🔒 Compilando requirements.txt com hashes SHA256..."
echo ""

# Verificar se pip-tools está instalado
if ! command -v pip-compile &> /dev/null; then
    echo "❌ pip-tools não encontrado. Instalando..."
    pip install pip-tools
fi

# Backup do requirements.txt anterior
if [ -f requirements.txt ]; then
    echo "📦 Criando backup de requirements.txt..."
    cp requirements.txt requirements.txt.backup
fi

# Compilar requirements
echo "🔧 Compilando requirements.in..."
pip-compile \
    --generate-hashes \
    --allow-unsafe \
    --output-file=requirements.txt \
    requirements.in

echo ""
echo "✅ requirements.txt gerado com sucesso!"
echo ""
echo "📋 Para instalar as dependências:"
echo "   pip install --require-hashes -r requirements.txt"
echo ""
echo "🔄 Para atualizar uma dependência específica:"
echo "   pip-compile --upgrade-package nome-pacote requirements.in"
echo ""
echo "🔄 Para atualizar todas as dependências:"
echo "   pip-compile --upgrade requirements.in"
echo ""

