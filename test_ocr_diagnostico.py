#!/usr/bin/env python3
"""
Script de Diagnóstico Completo do OCR e PyTorch
================================================
Executa verificações em todas as camadas do sistema de OCR
"""
import sys
import os

# Configurar app context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meu_app import create_app
app = create_app()

def print_section(title):
    """Imprime cabeçalho de seção"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def check_mark(condition):
    """Retorna emoji baseado na condição"""
    return "✅" if condition else "❌"

with app.app_context():
    print_section("DIAGNÓSTICO OCR - MÓDULO FINANCEIRO")
    
    # 1. Verificar PyTorch
    print_section("1. PYTORCH")
    try:
        import torch
        print(f"   ✅ PyTorch instalado: {torch.__version__}")
        print(f"   CUDA disponível: {torch.cuda.is_available()}")
        
        from meu_app.financeiro.pytorch_validator import PaymentValidatorService
        test_text = "Comprovante de pagamento PIX no valor de R$ 150,00 para teste"
        result = PaymentValidatorService.evaluate_text(test_text)
        
        print(f"   {check_mark(result.get('label'))} Modelo funciona")
        print(f"   Label: {result.get('label', 'N/A')}")
        print(f"   Confiança: {result.get('confidence', 0):.1%}")
        print(f"   Backend: {result.get('backend', 'N/A')}")
        
        if result.get('error'):
            print(f"   ⚠️ Erro: {result.get('error')}")
            
    except ImportError as e:
        print(f"   ❌ PyTorch não instalado: {e}")
    except Exception as e:
        print(f"   ❌ Erro ao testar PyTorch: {e}")
    
    # 2. Verificar Google Vision
    print_section("2. GOOGLE VISION API")
    try:
        from google.cloud import vision
        
        # Verificar credenciais
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        print(f"   Variável ambiente: {creds_path or 'NÃO SETADA'}")
        
        from meu_app.financeiro.config import FinanceiroConfig
        config_path = FinanceiroConfig.get_google_credentials_path()
        print(f"   Path configurado: {config_path}")
        
        if config_path and os.path.exists(config_path):
            print(f"   ✅ Arquivo de credenciais existe")
            
            # Tentar criar client
            client = vision.ImageAnnotatorClient()
            print(f"   ✅ Cliente Vision criado com sucesso")
        else:
            print(f"   ❌ Arquivo de credenciais NÃO EXISTE")
            
    except ImportError:
        print(f"   ❌ google-cloud-vision não instalado")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Verificar Quota
    print_section("3. QUOTA OCR")
    try:
        from meu_app.models import OcrQuota
        from datetime import datetime
        from meu_app.financeiro.config import FinanceiroConfig
        
        now = datetime.now()
        quota = OcrQuota.query.filter_by(ano=now.year, mes=now.month).first()
        
        limite = FinanceiroConfig.get_ocr_monthly_limit()
        enforce = FinanceiroConfig.is_ocr_limit_enforced()
        
        print(f"   Limite mensal: {limite}")
        print(f"   Enforced: {enforce}")
        
        if quota:
            print(f"   Uso atual: {quota.contador}/{limite}")
            if quota.contador >= limite:
                print(f"   ❌ QUOTA ESGOTADA!")
            else:
                print(f"   ✅ Quota disponível: {limite - quota.contador}")
        else:
            print(f"   ✅ Nenhum uso registrado este mês")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. Analisar Métricas do Modelo
    print_section("4. MÉTRICAS DO MODELO PYTORCH")
    try:
        import json
        report_path = 'models/pytorch_validator/training_report.json'
        
        if os.path.exists(report_path):
            with open(report_path) as f:
                report = json.load(f)
            
            val_acc = report['val_metrics']['accuracy']
            train_acc = report['history']['train_acc'][-1]
            dataset = report['label_distribution']
            total_exemplos = sum(dataset.values())
            
            print(f"   Acurácia treino: {train_acc:.1%}")
            print(f"   Acurácia validação: {val_acc:.1%}")
            
            if val_acc < 0.7:
                print(f"   ⚠️ MODELO MAL TREINADO! (Mínimo recomendado: 70%)")
            else:
                print(f"   ✅ Modelo adequado")
            
            if train_acc > 0.95 and val_acc < 0.7:
                print(f"   ⚠️ OVERFITTING DETECTADO! (treino >> validação)")
            
            print(f"\n   Dataset:")
            for label, count in dataset.items():
                print(f"     - {label}: {count} exemplos")
            print(f"   Total: {total_exemplos} exemplos")
            
            if total_exemplos < 100:
                print(f"   ⚠️ DATASET MUITO PEQUENO! (Mínimo recomendado: 200)")
        else:
            print(f"   ❌ Arquivo de relatório não encontrado")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 5. Verificar Associação Pagamento-Cliente
    print_section("5. ASSOCIAÇÃO PAGAMENTO-CLIENTE")
    try:
        from meu_app.models import Pagamento
        
        # Pegar últimos 5 pagamentos
        pagamentos = Pagamento.query.order_by(Pagamento.data_pagamento.desc()).limit(5).all()
        
        print(f"   Últimos {len(pagamentos)} pagamentos:")
        for pag in pagamentos:
            cliente_nome = pag.pedido.cliente.nome if pag.pedido and pag.pedido.cliente else "N/A"
            print(f"     #{pag.id}: R$ {pag.valor:.2f} → Pedido #{pag.pedido_id} → Cliente: {cliente_nome}")
        
        if pagamentos:
            print(f"   ✅ Relacionamentos íntegros")
        else:
            print(f"   ⚠️ Nenhum pagamento encontrado")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 6. Verificar Diretórios
    print_section("6. DIRETÓRIOS E ARQUIVOS")
    try:
        from meu_app.financeiro.config import FinanceiroConfig
        
        recibos_dir = FinanceiroConfig.get_upload_directory('recibos')
        temp_dir = FinanceiroConfig.get_upload_directory('temp')
        
        print(f"   Diretório recibos: {recibos_dir}")
        print(f"   Existe: {check_mark(os.path.exists(recibos_dir))}")
        
        if os.path.exists(recibos_dir):
            count = len([f for f in os.listdir(recibos_dir) if os.path.isfile(os.path.join(recibos_dir, f))])
            print(f"   Arquivos: {count}")
        
        print(f"\n   Diretório temp: {temp_dir}")
        print(f"   Existe: {check_mark(os.path.exists(temp_dir))}")
        
        model_dir = 'models/pytorch_validator'
        print(f"\n   Diretório modelo: {model_dir}")
        print(f"   Existe: {check_mark(os.path.exists(model_dir))}")
        
        if os.path.exists(model_dir):
            files = os.listdir(model_dir)
            required = ['payment_validator.pt', 'vocab.json', 'labels.json']
            for req in required:
                exists = req in files
                print(f"     {check_mark(exists)} {req}")
                
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # RESUMO FINAL
    print_section("RESUMO DO DIAGNÓSTICO")
    print("\n⚠️ AÇÕES RECOMENDADAS:")
    print("  1. Verificar credenciais Google Vision")
    print("  2. Verificar/resetar quota OCR se necessário")
    print("  3. Re-treinar modelo PyTorch com mais dados")
    print("  4. Melhorar padrões regex de extração")
    print("  5. Adicionar logs detalhados para debug")
    
    print("\n" + "=" * 60)
    print("Execute este script para diagnóstico completo:")
    print("  python test_ocr_diagnostico.py")
    print("=" * 60 + "\n")

