"""
Teste de integração para concorrência no módulo coletas
"""
import pytest
import threading
import time
from flask import Flask
from meu_app import create_app
from meu_app.models import db, Pedido, ItemPedido, Produto, Cliente, Estoque, StatusPedido
from meu_app.coletas.services.coleta_service import ColetaService
from config import TestingConfig


class ColetaTestConfig(TestingConfig):
    TESTING = True
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}


@pytest.mark.integration
def test_coleta_concorrencia_real():
    """
    Teste de integração real para verificar controle de concorrência
    Simula múltiplas tentativas de coleta simultâneas
    """
    app = create_app(ColetaTestConfig)
    
    with app.app_context():
        db.create_all()
        try:
            # Setup: Criar dados de teste
            cliente = Cliente(
                nome="Cliente Teste Concorrência",
                telefone="11999999999",
                cidade="São Paulo",
                cpf_cnpj="12345678901"
            )
            db.session.add(cliente)
            db.session.flush()
            
            produto = Produto(
                nome="Produto Teste Concorrência",
                codigo_interno="PROD-CONC",
                categoria="OUTROS",
                preco_medio_compra=10.00,
                ean="1234567890123"
            )
            db.session.add(produto)
            db.session.flush()
            
            estoque = Estoque(
                produto_id=produto.id,
                quantidade=5,  # Apenas 5 unidades disponíveis
                conferente="Sistema",
                status="Contagem"
            )
            db.session.add(estoque)
            db.session.flush()
            
            pedido = Pedido(
                cliente_id=cliente.id,
                status=StatusPedido.PAGAMENTO_APROVADO
            )
            db.session.add(pedido)
            db.session.flush()
            
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                produto_id=produto.id,
                quantidade=3,  # Pedido de 3 unidades
                preco_venda=10.00,
                preco_compra=7.00,
                valor_total_venda=30.00,
                valor_total_compra=21.00,
                lucro_bruto=9.00
            )
            db.session.add(item_pedido)
            db.session.commit()
            
            # Teste: Simular 3 tentativas simultâneas de coleta
            resultados = []
            threads = []

            def processar_coleta_thread(thread_id):
                """Função executada em cada thread"""
                try:
                    resultado = ColetaService.processar_coleta(
                        pedido_id=pedido.id,
                        responsavel_coleta_id=1,
                        nome_retirada=f'Teste {thread_id}',
                        documento_retirada=f'123456{thread_id}',
                        itens_coleta=[{'item_id': item_pedido.id, 'quantidade': 2}]  # Tentativa de coletar 2 unidades
                    )
                    resultados.append({
                        'thread_id': thread_id,
                        'sucesso': resultado[0],
                        'mensagem': resultado[1],
                        'coleta': resultado[2]
                    })
                except Exception as e:
                    resultados.append({
                        'thread_id': thread_id,
                        'sucesso': False,
                        'mensagem': str(e),
                        'coleta': None
                    })

            # Criar e iniciar threads
            for i in range(3):
                thread = threading.Thread(target=processar_coleta_thread, args=(i,))
                threads.append(thread)
                thread.start()

            # Aguardar todas as threads terminarem
            for thread in threads:
                thread.join()
            
            # Verificações
            sucessos = [r for r in resultados if r['sucesso']]
            falhas = [r for r in resultados if not r['sucesso']]
            
            # Apenas uma coleta deve ser bem-sucedida
            assert len(sucessos) <= 1, f"Múltiplas coletas simultâneas não devem ser permitidas. Sucessos: {len(sucessos)}"
            
            # Pelo menos uma deve falhar (devido ao controle de concorrência)
            assert len(falhas) >= 2, f"Pelo menos 2 tentativas devem falhar. Falhas: {len(falhas)}"
            
            # Verificar consistência do estoque
            db.session.refresh(estoque)
            assert estoque.quantidade >= 0, "Estoque não pode ficar negativo"
        
        finally:
            db.session.remove()
            db.drop_all()


@pytest.mark.integration
def test_coleta_estoque_insuficiente():
    """
    Teste de integração para verificar controle de estoque insuficiente
    """
    app = create_app(ColetaTestConfig)
    
    with app.app_context():
        db.create_all()
        try:
            # Setup: Criar dados com estoque insuficiente
            cliente = Cliente(
                nome="Cliente Teste Estoque",
                telefone="11999999999",
                cidade="São Paulo",
                cpf_cnpj="98765432100"
            )
            db.session.add(cliente)
            db.session.flush()
            
            produto = Produto(
                nome="Produto Teste Estoque",
                codigo_interno="PROD-ESTOQUE",
                categoria="OUTROS",
                preco_medio_compra=10.00,
                ean="0987654321098"
            )
            db.session.add(produto)
            db.session.flush()
            
            estoque = Estoque(
                produto_id=produto.id,
                quantidade=1,  # Apenas 1 unidade disponível
                conferente="Sistema",
                status="Contagem"
            )
            db.session.add(estoque)
            db.session.flush()
            
            pedido = Pedido(
                cliente_id=cliente.id,
                status=StatusPedido.PAGAMENTO_APROVADO
            )
            db.session.add(pedido)
            db.session.flush()
            
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                produto_id=produto.id,
                quantidade=5,  # Pedido de 5 unidades
                preco_venda=12.00,
                preco_compra=8.00,
                valor_total_venda=60.00,
                valor_total_compra=40.00,
                lucro_bruto=20.00
            )
            db.session.add(item_pedido)
            db.session.commit()
            
            # Teste: Tentar coletar mais que o estoque disponível
            sucesso, mensagem, coleta = ColetaService.processar_coleta(
                pedido_id=pedido.id,
                responsavel_coleta_id=1,
                nome_retirada="Teste Estoque",
                documento_retirada="12345678901",
                itens_coleta=[{'item_id': item_pedido.id, 'quantidade': 3}]  # Tentativa de coletar 3 unidades
            )
            
            # Verificações
            assert sucesso is False, "Coleta deve falhar com estoque insuficiente"
            assert "estoque" in mensagem.lower(), "Mensagem deve mencionar estoque"
            
            # Verificar que o estoque não foi alterado
            db.session.refresh(estoque)
            assert estoque.quantidade == 1, "Estoque não deve ter sido alterado"
        
        finally:
            db.session.remove()
            db.drop_all()


@pytest.mark.integration
def test_coleta_pedido_inexistente():
    """
    Teste de integração para verificar tratamento de pedido inexistente
    """
    app = create_app(ColetaTestConfig)
    
    with app.app_context():
        db.create_all()
        try:
            # Teste: Tentar coletar pedido que não existe
            sucesso, mensagem, coleta = ColetaService.processar_coleta(
                pedido_id=99999,  # ID inexistente
                responsavel_coleta_id=1,
                nome_retirada="Teste Pedido",
                documento_retirada="12345678901",
                itens_coleta=[{'item_id': 1, 'quantidade': 1}]
            )
            
            # Verificações
            assert sucesso is False, "Coleta deve falhar com pedido inexistente"
            assert "não encontrado" in mensagem.lower() or "não disponível" in mensagem.lower(), "Mensagem deve indicar pedido não encontrado"

        finally:
            db.session.remove()
            db.drop_all()
