from flask import render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask import Blueprint
from .services import ApuracaoService
from meu_app.cache import cached_with_invalidation, invalidate_cache

apuracao_bp = Blueprint('apuracao', __name__, url_prefix='/apuracao')
from functools import wraps
from datetime import datetime
from ..models import Apuracao, db
from ..decorators import login_obrigatorio
from app.auth.rbac import requires_financeiro

@apuracao_bp.route('/', methods=['GET'])
@login_obrigatorio
@requires_financeiro
@cached_with_invalidation(
    timeout=600,  # 10 minutos
    key_prefix='apuracao_lista',
    invalidate_on=['apuracao.criada', 'apuracao.atualizada', 'pedido.criado', 'pagamento.aprovado']
)
def listar_apuracao():
    """
    Lista apurações com cache
    
    Cache: 10 minutos (cálculos pesados)
    Invalidação: apuração, pedidos e pagamentos atualizados
    """
    try:
        # Filtros de mês e ano
        mes = request.args.get('mes', datetime.now().month, type=int)
        ano = request.args.get('ano', datetime.now().year, type=int)
        
        # Buscar apurações filtradas
        apuracoes = ApuracaoService.listar_apuracoes(mes, ano)
        
        # Lista de anos para o filtro
        anos_disponiveis = db.session.query(Apuracao.ano).distinct().order_by(Apuracao.ano.desc()).all()
        anos_disponiveis = [ano[0] for ano in anos_disponiveis]
        if not anos_disponiveis:
            anos_disponiveis = [datetime.now().year]
        
        # Calcular dados do período atual para exibição
        dados_periodo = ApuracaoService.calcular_dados_periodo(mes, ano)
        
        current_app.logger.info(f"Apuração acessada por {session.get('usuario_nome', 'N/A')}")
        
        return render_template('apuracao.html', 
                             apuracoes=apuracoes,
                             mes_selecionado=mes,
                             ano_selecionado=ano,
                             anos_disponiveis=anos_disponiveis,
                             receita_calculada=dados_periodo['receita_calculada'],
                             cpv_calculado=dados_periodo['cpv_calculado'],
                             apuracao_existente=apuracoes[0] if apuracoes else None)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar apuração: {str(e)}")
        flash(f"Erro ao carregar apuração: {str(e)}", 'error')
        return render_template('apuracao.html', apuracoes=[], mes_selecionado=1, ano_selecionado=datetime.now().year)



@apuracao_bp.route('/nova', methods=['GET', 'POST'])
@login_obrigatorio
def nova_apuracao():
    """Cria uma nova apuração"""
    if request.method == 'POST':
        # Extrair dados do formulário
        mes = request.form.get('mes', type=int)
        ano = request.form.get('ano', type=int)
        receita = request.form.get('receita', type=float)
        cpv = request.form.get('cpv', type=float)
        verbas = request.form.get('verbas', type=float)
        margem_manobra = request.form.get('margem_manobra', type=float)
        percentual_margem = request.form.get('percentual_margem', type=float)
        total_pedidos = request.form.get('total_pedidos', type=int)
        pedidos_pagos = request.form.get('pedidos_pagos', type=int)
        
        dados = {
            'receita': receita or 0.0,
            'cpv': cpv or 0.0,
            'verbas': verbas or 0.0,
            'margem_manobra': margem_manobra or 0.0,
            'percentual_margem': percentual_margem or 0.0,
            'total_pedidos': total_pedidos or 0,
            'pedidos_pagos': pedidos_pagos or 0
        }
        
        # Usar o serviço para criar a apuração
        sucesso, mensagem, apuracao = ApuracaoService.criar_apuracao(mes, ano, dados)
        
        if sucesso:
            current_app.logger.info(f"Apuração criada por {session.get('usuario_nome', 'N/A')}")
            flash(mensagem, 'success')
            return redirect(url_for('apuracao.listar_apuracao'))
        else:
            flash(mensagem, 'error')
            return render_template('nova_apuracao.html', mes=mes, ano=ano, dados=dados)
    
    # GET: Mostrar formulário
    return render_template('nova_apuracao.html')

@apuracao_bp.route('/tornar_definitiva/<int:id>', methods=['POST'])
@login_obrigatorio
def tornar_definitiva(id):
    """Torna uma apuração definitiva"""
    # Usar o serviço para tornar a apuração definitiva
    sucesso, mensagem = ApuracaoService.tornar_definitiva(id)
    
    if sucesso:
        current_app.logger.info(f"Apuração tornada definitiva (ID: {id}) por {session.get('usuario_nome', 'N/A')}")
        flash(mensagem, 'success')
    else:
        flash(mensagem, 'error')
    
    return redirect(url_for('apuracao.listar_apuracao'))

@apuracao_bp.route('/excluir/<int:id>')
@login_obrigatorio
def excluir_apuracao(id):
    """Exclui uma apuração"""
    # Usar o serviço para excluir a apuração
    sucesso, mensagem = ApuracaoService.excluir_apuracao(id)
    
    if sucesso:
        current_app.logger.info(f"Apuração excluída (ID: {id}) por {session.get('usuario_nome', 'N/A')}")
        flash(mensagem, 'success')
    else:
        flash(mensagem, 'error')
    
    return redirect(url_for('apuracao.listar_apuracao'))



@apuracao_bp.route('/salvar', methods=['POST'])
@login_obrigatorio
@requires_financeiro
def salvar_previsao():
    """Salva nova previsão de verbas (rascunho)"""
    try:
        mes = request.form.get('mes', type=int)
        ano = request.form.get('ano', type=int)
        tipo = request.form.get('tipo', '')
        
        if tipo != 'previsao':
            return jsonify({'success': False, 'message': 'Tipo inválido'}), 400
        
        # Validar mês e ano
        if not mes or not ano or mes < 1 or mes > 12:
            return jsonify({'success': False, 'message': 'Mês ou ano inválido'}), 400
        
        # Verificar se já existe apuração para este período
        existente = Apuracao.query.filter_by(mes=mes, ano=ano).first()
        if existente:
            return jsonify({
                'success': False,
                'message': f'Já existe uma apuração para {mes}/{ano}. Edite a existente.'
            }), 400
        
        # Extrair verbas
        verba_scann = request.form.get('verba_scann', 0, type=float)
        verba_plano_negocios = request.form.get('verba_plano_negocios', 0, type=float)
        verba_time_ambev = request.form.get('verba_time_ambev', 0, type=float)
        verba_outras_receitas = request.form.get('verba_outras_receitas', 0, type=float)
        
        # Calcular dados do período para preencher campos obrigatórios
        dados_periodo = ApuracaoService.calcular_dados_periodo(mes, ano)
        
        # Criar apuração (previsão = definitivo False)
        nova_apuracao = Apuracao(
            mes=mes,
            ano=ano,
            usuario_id=session.get('usuario_id'),
            receita_total=dados_periodo.get('receita_calculada', 0.0),
            custo_produtos=dados_periodo.get('cpv_calculado', 0.0),
            verba_scann=verba_scann,
            verba_plano_negocios=verba_plano_negocios,
            verba_time_ambev=verba_time_ambev,
            verba_outras_receitas=verba_outras_receitas,
            outros_custos=0,  # Previsões não têm custos
            definitivo=False  # Previsão é sempre rascunho
        )
        
        db.session.add(nova_apuracao)
        db.session.commit()
        
        invalidate_cache('apuracao_lista')
        
        current_app.logger.info(f"Previsão criada (ID: {nova_apuracao.id}) por {session.get('usuario_nome', 'N/A')}")
        
        return jsonify({
            'success': True,
            'message': 'Previsão criada com sucesso!',
            'id': nova_apuracao.id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar previsão: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao salvar: {str(e)}'
        }), 500


@apuracao_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
@requires_financeiro
def editar_apuracao(id):
    """Edita uma apuração existente"""
    try:
        # Buscar a apuração
        apuracao = ApuracaoService.buscar_apuracao(id)
        if not apuracao:
            flash('Apuração não encontrada', 'error')
            return redirect(url_for('apuracao.listar_apuracao'))
        
        if request.method == 'POST':
            # Extrair dados do formulário
            mes = request.form.get('mes', type=int)
            ano = request.form.get('ano', type=int)
            receita = request.form.get('receita', type=float)
            cpv = request.form.get('cpv', type=float)
            verbas = request.form.get('verbas', type=float)
            margem_manobra = request.form.get('margem_manobra', type=float)
            percentual_margem = request.form.get('percentual_margem', type=float)
            total_pedidos = request.form.get('total_pedidos', type=int)
            pedidos_pagos = request.form.get('pedidos_pagos', type=int)
            
            dados = {
                'receita': receita or 0.0,
                'cpv': cpv or 0.0,
                'verbas': verbas or 0.0,
                'margem_manobra': margem_manobra or 0.0,
                'percentual_margem': percentual_margem or 0.0,
                'total_pedidos': total_pedidos or 0,
                'pedidos_pagos': pedidos_pagos or 0
            }
            
            # Usar o serviço para atualizar a apuração
            sucesso, mensagem = ApuracaoService.atualizar_apuracao(id, mes, ano, dados)
            
            if sucesso:
                current_app.logger.info(f"Apuração editada (ID: {id}) por {session.get('usuario_nome', 'N/A')}")
                flash(mensagem, 'success')
                return redirect(url_for('apuracao.listar_apuracao'))
            else:
                flash(mensagem, 'error')
                return render_template('editar_apuracao.html', apuracao=apuracao, dados=dados)
        
        # GET: Mostrar formulário com dados da apuração
        dados = {
            'receita': apuracao.receita_total,
            'cpv': apuracao.custo_produtos,
            'verbas': apuracao.total_verbas,
            'margem_manobra': apuracao.margem_bruta,
            'percentual_margem': apuracao.percentual_margem,
            'total_pedidos': 0,  # Campo não existe no modelo
            'pedidos_pagos': 0   # Campo não existe no modelo
        }
        
        return render_template('editar_apuracao.html', apuracao=apuracao, dados=dados)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao editar apuração (ID: {id}): {str(e)}")
        flash(f'Erro ao editar apuração: {str(e)}', 'error')
        return redirect(url_for('apuracao.listar_apuracao'))
