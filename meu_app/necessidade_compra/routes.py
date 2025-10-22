"""
Routes para o módulo de Necessidade de Compra
"""

from flask import render_template, request, jsonify, send_file
from flask_login import login_required
from . import necessidade_compra_bp
from .services import NecessidadeCompraService
from io import BytesIO
from datetime import datetime


@necessidade_compra_bp.route('/')
@login_required
def dashboard():
    """Página principal de análise de necessidade de compra"""
    return render_template('necessidade_compra/dashboard.html')


@necessidade_compra_bp.route('/api/analisar', methods=['GET'])
@login_required
def analisar_necessidades():
    """
    API: Analisa necessidade de compra para todos os produtos
    
    Query Parameters:
        margem_seguranca (int): Percentual de margem de segurança (padrão: 20)
        considerar_historico (bool): Se deve considerar histórico de vendas (padrão: true)
    
    Returns:
        JSON: {
            'success': bool,
            'analises': List[dict],
            'resumo': dict
        }
    """
    try:
        # Obter parâmetros
        margem_seguranca = int(request.args.get('margem_seguranca', 20))
        considerar_historico = request.args.get('considerar_historico', 'true').lower() == 'true'
        
        # Validar margem
        if margem_seguranca < 0 or margem_seguranca > 100:
            return jsonify({
                'success': False,
                'message': 'Margem de segurança deve estar entre 0 e 100%'
            }), 400
        
        # Executar análise
        service = NecessidadeCompraService()
        analises, resumo = service.analisar_necessidades(
            margem_seguranca=margem_seguranca,
            considerar_historico=considerar_historico
        )
        
        # Converter para dict
        analises_dict = [analise.model_dump() for analise in analises]
        resumo_dict = resumo.model_dump()
        
        return jsonify({
            'success': True,
            'analises': analises_dict,
            'resumo': resumo_dict,
            'parametros': {
                'margem_seguranca': margem_seguranca,
                'considerar_historico': considerar_historico
            }
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Parâmetro inválido: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao analisar necessidades: {str(e)}'
        }), 500


@necessidade_compra_bp.route('/api/exportar', methods=['POST'])
@login_required
def exportar_lista():
    """
    API: Exporta lista de compras em formato texto
    
    Body JSON:
        analises (List[dict]): Lista de análises
        apenas_necessarios (bool): Incluir apenas produtos com necessidade
    
    Returns:
        Arquivo TXT para download
    """
    try:
        data = request.get_json()
        
        if not data or 'analises' not in data:
            return jsonify({
                'success': False,
                'message': 'Dados de análise não fornecidos'
            }), 400
        
        apenas_necessarios = data.get('apenas_necessarios', True)
        
        # Converter de volta para schemas
        from .schemas import AnaliseCompraSchema
        analises = [AnaliseCompraSchema(**a) for a in data['analises']]
        
        # Gerar texto
        service = NecessidadeCompraService()
        texto = service.exportar_lista_compra(analises, apenas_necessarios)
        
        # Criar arquivo em memória
        buffer = BytesIO()
        buffer.write(texto.encode('utf-8'))
        buffer.seek(0)
        
        # Nome do arquivo com data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'necessidade_compra_{timestamp}.txt'
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao exportar lista: {str(e)}'
        }), 500


@necessidade_compra_bp.route('/api/resumo', methods=['GET'])
@login_required
def obter_resumo():
    """
    API: Obtém apenas o resumo da análise (mais rápido)
    
    Returns:
        JSON: {
            'success': bool,
            'resumo': dict
        }
    """
    try:
        service = NecessidadeCompraService()
        _, resumo = service.analisar_necessidades()
        
        return jsonify({
            'success': True,
            'resumo': resumo.model_dump()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter resumo: {str(e)}'
        }), 500
