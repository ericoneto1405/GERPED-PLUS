#!/usr/bin/env python3
"""
Teste End-to-End: Fluxo Financeiro → Coleta
Simula o fluxo completo desde criação de pedido até liberação para coleta
"""

from meu_app import create_app
from meu_app.models import db, Pedido, ItemPedido, Cliente, Produto, Pagamento, StatusPedido
from meu_app.financeiro.services import FinanceiroService
from config import DevelopmentConfig
from decimal import Decimal
from datetime import datetime

def limpar_dados_teste():
    """Remove dados de teste anteriores"""
    print("\n🧹 Limpando dados de teste anteriores...")
    
    # Buscar e remover pedidos de teste
    pedidos_teste = Pedido.query.filter(Pedido.cliente_id == 9999).all()
    for p in pedidos_teste:
        # Remover itens e pagamentos
        ItemPedido.query.filter_by(pedido_id=p.id).delete()
        Pagamento.query.filter_by(pedido_id=p.id).delete()
        db.session.delete(p)
    
    # Remover cliente teste
    Cliente.query.filter_by(id=9999).delete()
    
    db.session.commit()
    print("✅ Dados limpos")

def criar_dados_teste():
    """Cria cliente, produto e pedido de teste"""
    print("\n📦 Criando dados de teste...")
    
    # Cliente teste
    cliente = Cliente(
        nome="Cliente Teste OCR",
        cpf_cnpj="00000000000000"
    )
    cliente.id = 9999  # Força ID específico
    db.session.add(cliente)
    
    # Verificar se produto teste existe
    produto = Produto.query.filter_by(nome="Produto Teste OCR").first()
    if not produto:
        produto = Produto(
            nome="Produto Teste OCR",
            categoria="OUTROS",
            preco_medio_compra=Decimal("50.00")
        )
        db.session.add(produto)
        db.session.flush()
    
    # Pedido teste
    pedido = Pedido(
        cliente_id=9999,
        status=StatusPedido.PENDENTE,
        data=datetime.now()
    )
    db.session.add(pedido)
    db.session.flush()
    
    # Itens do pedido (total = R$ 100.00)
    preco_venda = Decimal("50.00")
    preco_compra = Decimal("40.00")
    quantidade = 2
    
    item1 = ItemPedido(
        pedido_id=pedido.id,
        produto_id=produto.id,
        quantidade=quantidade,
        preco_venda=preco_venda,
        preco_compra=preco_compra,
        valor_total_venda=preco_venda * quantidade,
        valor_total_compra=preco_compra * quantidade,
        lucro_bruto=(preco_venda - preco_compra) * quantidade
    )
    db.session.add(item1)
    
    db.session.commit()
    
    print(f"✅ Cliente criado: ID {cliente.id}")
    print(f"✅ Produto criado: ID {produto.id}")
    print(f"✅ Pedido criado: ID {pedido.id} - Total: R$ 100.00")
    
    return pedido.id, produto.id

def testar_fluxo_completo():
    """Executa teste end-to-end do fluxo"""
    print("=" * 70)
    print("🧪 TESTE END-TO-END: FLUXO FINANCEIRO → COLETA")
    print("=" * 70)
    
    app = create_app(DevelopmentConfig)
    
    with app.app_context():
        try:
            # Limpar dados anteriores
            limpar_dados_teste()
            
            # 1. Criar dados de teste
            pedido_id, produto_id = criar_dados_teste()
            
            # 2. Verificar pedido criado
            print("\n" + "=" * 70)
            print("ETAPA 1: Verificar Pedido Criado")
            print("=" * 70)
            
            pedido = db.session.get(Pedido, pedido_id)
            totais = pedido.calcular_totais()
            
            print(f"📊 Status inicial: {pedido.status.value}")
            print(f"💰 Total do pedido: R$ {totais['total_pedido']}")
            print(f"💵 Total pago: R$ {totais['total_pago']}")
            print(f"💸 Saldo: R$ {totais['saldo']}")
            
            assert pedido.status == StatusPedido.PENDENTE, "Status deve ser PENDENTE"
            assert totais['total_pedido'] == Decimal("100.00"), "Total deve ser R$ 100.00"
            assert totais['total_pago'] == Decimal("0.00"), "Pago deve ser R$ 0.00"
            print("✅ Pedido verificado com sucesso")
            
            # 3. Registrar pagamento parcial (R$ 50.00)
            print("\n" + "=" * 70)
            print("ETAPA 2: Pagamento Parcial (R$ 50.00)")
            print("=" * 70)
            
            sucesso, mensagem, pag1 = FinanceiroService.registrar_pagamento(
                pedido_id=pedido_id,
                valor=50.00,
                forma_pagamento="PIX",
                observacoes="Pagamento parcial teste",
                id_transacao="TEST001"
            )
            
            assert sucesso, f"Pagamento parcial falhou: {mensagem}"
            print(f"✅ {mensagem}")
            
            # Refresh e verificar
            db.session.refresh(pedido)
            totais = pedido.calcular_totais()
            
            print(f"📊 Status após pagamento parcial: {pedido.status.value}")
            print(f"💵 Total pago: R$ {totais['total_pago']}")
            print(f"💸 Saldo: R$ {totais['saldo']}")
            
            assert totais['total_pago'] == Decimal("50.00"), "Deve ter R$ 50.00 pago"
            assert pedido.status == StatusPedido.PENDENTE, "Status ainda deve ser PENDENTE"
            print("✅ Pagamento parcial registrado corretamente")
            
            # 4. Registrar pagamento final (R$ 50.00) - Deve liberar para coleta
            print("\n" + "=" * 70)
            print("ETAPA 3: Pagamento Final (R$ 50.00) → Liberar para Coleta")
            print("=" * 70)
            
            sucesso, mensagem, pag2 = FinanceiroService.registrar_pagamento(
                pedido_id=pedido_id,
                valor=50.00,
                forma_pagamento="Cartão",
                observacoes="Pagamento final teste",
                id_transacao="TEST002"
            )
            
            assert sucesso, f"Pagamento final falhou: {mensagem}"
            print(f"✅ {mensagem}")
            
            # Refresh e verificar status
            db.session.refresh(pedido)
            totais = pedido.calcular_totais()
            
            print(f"📊 Status após pagamento completo: {pedido.status.value}")
            print(f"💵 Total pago: R$ {totais['total_pago']}")
            print(f"💸 Saldo: R$ {totais['saldo']}")
            
            assert totais['total_pago'] == Decimal("100.00"), "Deve ter R$ 100.00 pago"
            assert totais['saldo'] == Decimal("0.00"), "Saldo deve ser R$ 0.00"
            
            # VERIFICAÇÃO CRÍTICA: Status deve mudar para PAGAMENTO_APROVADO
            if pedido.status == StatusPedido.PAGAMENTO_APROVADO:
                print("✅ Status mudou para PAGAMENTO_APROVADO corretamente!")
            else:
                print(f"❌ ERRO: Status é '{pedido.status.value}' mas deveria ser 'Pagamento Aprovado'")
                print("⚠️ Pedido NÃO será liberado para coleta!")
                return False
            
            # 5. Verificar se pedido aparece em coletas
            print("\n" + "=" * 70)
            print("ETAPA 4: Verificar Disponibilidade em Coletas")
            print("=" * 70)
            
            from meu_app.coletas.services.coleta_service import ColetaService
            
            pedidos_disponiveis = ColetaService.listar_pedidos_para_coleta()
            # Retorna dict com 'pedido' como chave
            ids_disponiveis = [p['pedido'].id for p in pedidos_disponiveis]
            
            print(f"📋 Pedidos disponíveis para coleta: {len(pedidos_disponiveis)}")
            print(f"🔍 IDs disponíveis: {ids_disponiveis}")
            
            if pedido_id in ids_disponiveis:
                print(f"✅ Pedido {pedido_id} ESTÁ DISPONÍVEL para coleta!")
            else:
                print(f"❌ ERRO: Pedido {pedido_id} NÃO está disponível para coleta")
                print(f"   Status atual: {pedido.status.value}")
                print(f"   Esperado: PAGAMENTO_APROVADO ou COLETA_PARCIAL")
                return False
            
            # 6. Resumo final
            print("\n" + "=" * 70)
            print("RESUMO FINAL")
            print("=" * 70)
            
            print(f"✅ Pedido: #{pedido_id}")
            print(f"✅ Status: {pedido.status.value}")
            print(f"✅ Total: R$ {totais['total_pedido']}")
            print(f"✅ Pago: R$ {totais['total_pago']}")
            print(f"✅ Pagamentos registrados: 2")
            print(f"✅ Disponível em Coletas: SIM")
            
            print("\n" + "=" * 70)
            print("🎉 TESTE COMPLETO: TODOS OS PASSOS OK!")
            print("=" * 70)
            
            return True
            
        except AssertionError as e:
            print(f"\n❌ ERRO DE ASSERÇÃO: {str(e)}")
            return False
        except Exception as e:
            print(f"\n❌ ERRO INESPERADO: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Opcional: limpar dados de teste
            print("\n🧹 Mantendo dados de teste para inspeção manual")
            print(f"   Para limpar: DELETE FROM pedido WHERE cliente_id = 9999;")

if __name__ == "__main__":
    import sys
    sucesso = testar_fluxo_completo()
    sys.exit(0 if sucesso else 1)
