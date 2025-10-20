"""
Services para o módulo de Necessidade de Compra
"""

from typing import List, Dict, Tuple, Any
from decimal import Decimal
from flask import current_app
from .repositories import NecessidadeCompraRepository
from .schemas import AnaliseCompraSchema, ResumoAnaliseSchema


class NecessidadeCompraService:
    """Serviço para análise de necessidade de compra"""
    
    def __init__(self):
        self.repository = NecessidadeCompraRepository()
    
    def analisar_necessidades(
        self, 
        margem_seguranca: int = 20,
        considerar_historico: bool = True
    ) -> Tuple[List[AnaliseCompraSchema], ResumoAnaliseSchema]:
        """
        Analisa a necessidade de compra para todos os produtos
        
        Args:
            margem_seguranca: Percentual de margem de segurança para estoque
            considerar_historico: Se deve considerar histórico de vendas
            
        Returns:
            Tuple[List[AnaliseCompraSchema], ResumoAnaliseSchema]: 
                Lista de análises e resumo geral
        """
        try:
            # Obter dados dos produtos
            produtos = self.repository.obter_dados_produtos()
            
            analises = []
            total_produtos = len(produtos)
            produtos_criticos = 0
            produtos_alerta = 0
            valor_total_necessario = Decimal('0.00')
            
            for produto_data in produtos:
                # Calcular análise para cada produto
                analise = self._calcular_analise_produto(
                    produto_data,
                    margem_seguranca,
                    considerar_historico
                )
                
                analises.append(analise)
                
                # Atualizar contadores
                if analise.status == "critico":
                    produtos_criticos += 1
                elif analise.status == "alerta":
                    produtos_alerta += 1
                
                valor_total_necessario += analise.valor_total_sugerido
            
            # Ordenar por status (crítico primeiro)
            status_order = {"critico": 0, "alerta": 1, "normal": 2}
            analises.sort(key=lambda x: (status_order.get(x.status, 3), -x.sugestao_compra))
            
            # Criar resumo
            resumo = ResumoAnaliseSchema(
                total_produtos=total_produtos,
                produtos_criticos=produtos_criticos,
                produtos_alerta=produtos_alerta,
                valor_total_necessario=valor_total_necessario
            )
            
            current_app.logger.info(
                f"Análise de necessidade concluída: {total_produtos} produtos, "
                f"{produtos_criticos} críticos, {produtos_alerta} em alerta"
            )
            
            return analises, resumo
            
        except Exception as e:
            current_app.logger.error(f"Erro ao analisar necessidades: {str(e)}")
            return [], ResumoAnaliseSchema()
    
    def _calcular_analise_produto(
        self,
        produto_data: Dict[str, Any],
        margem_seguranca: int,
        considerar_historico: bool
    ) -> AnaliseCompraSchema:
        """
        Calcula a análise de necessidade para um produto específico
        
        Args:
            produto_data: Dados do produto
            margem_seguranca: Percentual de margem de segurança
            considerar_historico: Se deve considerar histórico
            
        Returns:
            AnaliseCompraSchema: Análise do produto
        """
        estoque_atual = produto_data['estoque_atual']
        quantidade_pendente = produto_data['quantidade_pedidos_pendentes']
        preco_medio = Decimal(str(produto_data['preco_medio_compra']))
        
        # Calcular quantidade necessária
        quantidade_necessaria = quantidade_pendente - estoque_atual
        
        # Adicionar histórico se solicitado
        if considerar_historico:
            media_vendas = self.repository.obter_historico_vendas(
                produto_data['produto_id'],
                dias=30
            )
            # Adicionar 15 dias de estoque baseado no histórico
            quantidade_necessaria += (media_vendas * 15)
        
        # Adicionar margem de segurança
        if quantidade_necessaria > 0:
            margem = int(quantidade_necessaria * (margem_seguranca / 100))
            sugestao_compra = quantidade_necessaria + margem
        else:
            sugestao_compra = 0
        
        # Determinar status
        if quantidade_necessaria > 0 and estoque_atual <= 0:
            status = "critico"
        elif quantidade_necessaria > 0:
            status = "alerta"
        else:
            status = "normal"
        
        # Calcular valor total
        valor_total_sugerido = Decimal(str(sugestao_compra)) * preco_medio
        
        return AnaliseCompraSchema(
            produto_id=produto_data['produto_id'],
            produto_nome=produto_data['produto_nome'],
            estoque_atual=estoque_atual,
            quantidade_pedidos_pendentes=quantidade_pendente,
            quantidade_necessaria=max(0, quantidade_necessaria),
            sugestao_compra=max(0, sugestao_compra),
            preco_medio_compra=preco_medio,
            valor_total_sugerido=valor_total_sugerido,
            status=status
        )
    
    def exportar_lista_compra(
        self,
        analises: List[AnaliseCompraSchema],
        apenas_necessarios: bool = True
    ) -> str:
        """
        Exporta lista de compras em formato texto
        
        Args:
            analises: Lista de análises
            apenas_necessarios: Se deve incluir apenas produtos com necessidade
            
        Returns:
            str: Lista formatada
        """
        linhas = []
        linhas.append("=" * 80)
        linhas.append("LISTA DE NECESSIDADE DE COMPRA")
        linhas.append("=" * 80)
        linhas.append("")
        
        total_itens = 0
        valor_total = Decimal('0.00')
        
        for analise in analises:
            if apenas_necessarios and analise.sugestao_compra <= 0:
                continue
            
            status_emoji = {
                "critico": "🔴",
                "alerta": "🟡",
                "normal": "🟢"
            }.get(analise.status, "⚪")
            
            linhas.append(f"{status_emoji} {analise.produto_nome}")
            linhas.append(f"   Estoque Atual: {analise.estoque_atual}")
            linhas.append(f"   Pedidos Pendentes: {analise.quantidade_pedidos_pendentes}")
            linhas.append(f"   Sugestão de Compra: {analise.sugestao_compra} unidades")
            linhas.append(f"   Valor Estimado: R$ {analise.valor_total_sugerido:.2f}")
            linhas.append("")
            
            total_itens += 1
            valor_total += analise.valor_total_sugerido
        
        linhas.append("=" * 80)
        linhas.append(f"TOTAL: {total_itens} produtos | Valor Total: R$ {valor_total:.2f}")
        linhas.append("=" * 80)
        
        return "\n".join(linhas)

