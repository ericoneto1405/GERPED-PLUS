#!/bin/bash
# Script de teste rápido do OCR

echo "🧪 Teste Rápido - OCR Financeiro"
echo "================================"
echo ""

cd /Users/ericobrandao/Projects/GERPED

echo "1️⃣ Verificando endpoint..."
python3 << 'EOF'
from meu_app import create_app
from config import DevelopmentConfig

app = create_app(DevelopmentConfig)
with app.app_context():
    for rule in app.url_map.iter_rules():
        if 'ocr' in rule.rule.lower():
            print(f"✅ {rule.rule}")
EOF

echo ""
echo "2️⃣ Verificando credenciais Google Vision..."
python3 << 'EOF'
import os
from meu_app.financeiro.config import FinanceiroConfig
cred_path = FinanceiroConfig.GOOGLE_VISION_CREDENTIALS_PATH
exists = os.path.exists(cred_path)
print(f"{'✅' if exists else '❌'} Credenciais: {cred_path}")
EOF

echo ""
echo "3️⃣ Verificando quota OCR..."
python3 << 'EOF'
from meu_app import create_app
from config import DevelopmentConfig
from datetime import datetime

app = create_app(DevelopmentConfig)
with app.app_context():
    from meu_app.models import OcrQuota
    from meu_app.financeiro.config import FinanceiroConfig
    
    agora = datetime.now()
    quota = OcrQuota.query.filter_by(ano=agora.year, mes=agora.month).first()
    limite = FinanceiroConfig.get_ocr_monthly_limit()
    
    if quota:
        print(f"📊 Quota atual: {quota.contador}/{limite}")
        if quota.contador >= limite:
            print("❌ LIMITE ATINGIDO!")
        else:
            print(f"✅ Ainda tem {limite - quota.contador} chamadas disponíveis")
    else:
        print(f"✅ Nenhuma chamada feita este mês (limite: {limite})")
EOF

echo ""
echo "4️⃣ Testando JavaScript está acessível..."
JS_FILE="/Users/ericobrandao/Projects/GERPED/meu_app/static/js/financeiro_pagamento.js"
if [ -f "$JS_FILE" ]; then
    echo "✅ JavaScript existe"
    echo "   Linhas: $(wc -l < "$JS_FILE")"
    echo "   Logs de debug: $(grep -c "console.log" "$JS_FILE") logs"
else
    echo "❌ JavaScript NÃO encontrado!"
fi

echo ""
echo "✅ Teste completo!"
echo ""
echo "📝 Próximo passo:"
echo "   1. Reinicie o servidor: python run.py"
echo "   2. Abra: http://localhost:5004/financeiro"
echo "   3. Abra Console (F12)"
echo "   4. Faça upload de um recibo"
echo "   5. Verifique os logs que aparecem"
