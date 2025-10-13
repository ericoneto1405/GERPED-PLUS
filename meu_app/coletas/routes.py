"""
Rotas consolidadas do módulo de coletas
Integra funcionalidades do módulo logística
"""
from flask import Blueprint, render_template, current_app, flash, request, redirect, url_for, session, send_file, jsonify
from ..decorators import login_obrigatorio, permissao_necessaria
from app.auth.rbac import requires_logistica
import json
import traceback
from datetime import datetime
import re

coletas_bp = Blueprint('coletas', __name__, url_prefix='/coletas')
from .services.coleta_service import ColetaService
from .receipt_service import ReceiptService
import os

CPF_REGEX = re.compile(r'^\d{11}$')
NAME_REGEX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]*$")


def _normalizar_cpf(valor: str) -> str | None:
    """Remove caracteres não numéricos e valida tamanho."""
    if not valor:
        return None
    apenas_digitos = re.sub(r'\D', '', valor)
    if CPF_REGEX.match(apenas_digitos):
        return apenas_digitos
    return None


def _formatar_cpf(cpf: str) -> str:
    """Formata CPF no padrão XXX.XXX.XXX-XX."""
    if not cpf or len(cpf) != 11:
        return cpf or ''
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def _nome_valido(nome: str) -> bool:
    """Valida nome simples (pelo menos duas letras, apenas letras/espacos)."""
    if not nome:
        return False
    nome_limpo = nome.strip()
    if len(nome_limpo) < 3:
        return False
    return NAME_REGEX.match(nome_limpo) is not None


@coletas_bp.route('/')
@login_obrigatorio
@requires_logistica
@permissao_necessaria('acesso_logistica')
def index():
    """Lista pedidos para coleta - interface simples e direta"""
    try:
        filtro = request.args.get('filtro', 'pendentes')
        pedidos = ColetaService.listar_pedidos_para_coleta(filtro)
        
        current_app.logger.info(f"Lista de coletas acessada por {session.get('usuario_nome', 'N/A')} - Filtro: {filtro}")
        
        return render_template('coletas/lista_coletas.html', pedidos=pedidos, filtro=filtro)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar pedidos para coleta: {str(e)}")
        flash('Erro ao carregar lista de coletas', 'error')
        return render_template('coletas/lista_coletas.html', pedidos=[], filtro='pendentes')


@coletas_bp.route('/dashboard')
@login_obrigatorio
@permissao_necessaria('acesso_logistica')
def dashboard():
    """Dashboard com filtros (funcionalidade do logística)"""
    try:
        filtro = request.args.get('filtro', 'pendentes')
        
        pedidos = ColetaService.listar_pedidos_para_coleta(filtro)
        
        current_app.logger.info(f"Dashboard coletas acessado por {session.get('usuario_nome', 'N/A')} - Filtro: {filtro}")
        
        return render_template('coletas/dashboard.html', pedidos=pedidos, filtro=filtro)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar dashboard: {str(e)}")
        flash(f"Erro ao carregar dashboard: {str(e)}", 'error')
        return render_template('coletas/dashboard.html', pedidos=[], filtro='pendentes')


@coletas_bp.route('/processar/<int:pedido_id>', methods=['GET', 'POST'])
@login_obrigatorio
@permissao_necessaria('acesso_logistica')
def processar_coleta(pedido_id):
    """Processa uma coleta (funcionalidade original)"""
    if request.method == 'POST':
        try:
            # CORREÇÃO: Buscar detalhes ANTES de processar a coleta
            detalhes = ColetaService.buscar_detalhes_pedido(pedido_id)
            if not detalhes:
                flash('Pedido não encontrado ou não disponível para coleta', 'error')
                return redirect(url_for('coletas.dashboard'))
            
            # Extrair dados do formulário
            nome_retirada = request.form.get('nome_retirada', '').strip()
            documento_retirada_raw = request.form.get('documento_retirada', '').strip()
            nome_conferente = request.form.get('nome_conferente', '').strip()
            cpf_conferente_raw = request.form.get('cpf_conferente', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not _nome_valido(nome_retirada):
                flash('Informe o nome completo de quem está retirando (somente letras).', 'error')
                return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

            if not _nome_valido(nome_conferente):
                flash('Informe o nome completo do conferente (somente letras).', 'error')
                return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

            nome_retirada = ' '.join(nome_retirada.split())
            nome_conferente = ' '.join(nome_conferente.split())

            documento_retirada = _normalizar_cpf(documento_retirada_raw)
            if not documento_retirada:
                flash('CPF da pessoa que retira é inválido.', 'error')
                return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

            cpf_conferente = _normalizar_cpf(cpf_conferente_raw)
            if not cpf_conferente:
                flash('CPF do conferente é inválido.', 'error')
                return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

            limites_quantidade = {}
            for item in detalhes['itens']:
                estoque_disp = getattr(item, 'estoque_disponivel', 0) or 0
                pendente = getattr(item, 'quantidade_pendente', 0) or 0
                max_permitido = max(0, min(pendente, estoque_disp))
                limites_quantidade[item.id] = max_permitido
            
            # Extrair itens da coleta
            itens_coleta = []
            for key, value in request.form.items():
                if not key.startswith('quantidade_'):
                    continue

                item_id_str = key.split('quantidade_', 1)[-1]
                try:
                    item_id = int(item_id_str)
                except ValueError:
                    flash('Identificador de item inválido na requisição.', 'error')
                    return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

                raw_valor = (value or '').strip()
                if raw_valor == '':
                    continue

                try:
                    quantidade = int(raw_valor)
                except ValueError:
                    flash('Informe apenas números inteiros para a quantidade de cada item.', 'error')
                    return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

                if quantidade < 0:
                    flash('Quantidade não pode ser negativa.', 'error')
                    return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

                limite = limites_quantidade.get(item_id)
                if limite is None:
                    flash('Item informado não corresponde ao pedido selecionado.', 'error')
                    return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

                if limite == 0:
                    continue

                if quantidade > limite:
                    flash('Quantidade solicitada excede o limite permitido para um dos itens.', 'error')
                    return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

                if quantidade > 0:
                    itens_coleta.append({
                        'item_id': item_id,
                        'quantidade': quantidade
                    })
            
            if not itens_coleta:
                flash('Selecione pelo menos um item para coleta!', 'error')
                return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))
            
            # Processar coleta
            sucesso, mensagem, coleta = ColetaService.processar_coleta(
                pedido_id=pedido_id,
                responsavel_coleta_id=session.get('usuario_id'),
                nome_retirada=nome_retirada,
                documento_retirada=documento_retirada,
                itens_coleta=itens_coleta,
                observacoes=observacoes,
                nome_conferente=nome_conferente,
                cpf_conferente=cpf_conferente
            )
            
            if sucesso:
                # CORREÇÃO: Usar detalhes coletados ANTES da mudança de status
                try:
                    itens_recibo = []
                    for item_data in itens_coleta:
                        for item in detalhes['itens']:
                            if item.id == item_data['item_id']:
                                itens_recibo.append({
                                    'produto_nome': item.produto.nome,
                                    'quantidade': item_data['quantidade']
                                })
                                break
                    
                    coleta_data = {
                        'pedido_id': pedido_id,
                        'data_coleta': coleta.data_coleta if hasattr(coleta, 'data_coleta') else None,
                        'status': coleta.status.value if hasattr(coleta, 'status') else 'PROCESSADA',
                        'nome_retirada': nome_retirada,
                        'documento_retirada': _formatar_cpf(documento_retirada),
                        'nome_conferente': nome_conferente,
                        'cpf_conferente': _formatar_cpf(cpf_conferente),
                        'itens_coleta': itens_recibo
                    }
                    
                    pdf_path = ReceiptService.gerar_recibo_pdf(coleta_data)
                    
                    flash(f'{mensagem} Recibo gerado com sucesso!', 'success')
                    return send_file(pdf_path, as_attachment=True, download_name=f'recibo_coleta_{pedido_id}.pdf')
                    
                except Exception as e:
                    current_app.logger.error(f"Erro ao gerar recibo: {str(e)}")
                    flash(f'{mensagem} (Erro ao gerar recibo)', 'warning')
                    return redirect(url_for('coletas.index'))
            else:
                flash(mensagem, 'error')
                return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))
                
        except Exception as e:
            current_app.logger.error(f"Erro ao processar coleta: {str(e)}")
            flash('Erro interno do servidor ao processar a coleta.', 'error')
            return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))
    
    else:
        # GET - Mostrar formulário
        try:
            detalhes = ColetaService.buscar_detalhes_pedido(pedido_id)
            if not detalhes:
                flash('Pedido não encontrado ou não disponível para coleta', 'error')
                return redirect(url_for('coletas.index'))
            
            return render_template('coletas/processar_coleta.html', detalhes=detalhes)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar detalhes do pedido: {str(e)}")
            flash('Erro ao carregar detalhes do pedido', 'error')
            return redirect(url_for('coletas.index'))


@coletas_bp.route('/detalhes/<int:pedido_id>')
@login_obrigatorio
@permissao_necessaria('acesso_logistica')
def detalhes_pedido(pedido_id):
    """Detalhes do pedido (funcionalidade do logística)"""
    try:
        detalhes = ColetaService.buscar_detalhes_pedido(pedido_id)
        if not detalhes:
            flash('Pedido não encontrado', 'error')
            return redirect(url_for('coletas.dashboard'))
        
        return render_template('coletas/detalhes_pedido.html', detalhes=detalhes)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar detalhes do pedido: {str(e)}")
        flash('Erro ao carregar detalhes do pedido', 'error')
        return redirect(url_for('coletas.dashboard'))


@coletas_bp.route('/historico/<int:pedido_id>')
@login_obrigatorio
@permissao_necessaria('acesso_logistica')
def historico_coletas(pedido_id):
    """Histórico de coletas de um pedido"""
    try:
        historico = ColetaService.buscar_historico_coletas(pedido_id)
        if not historico:
            flash('Nenhuma coleta encontrada para este pedido', 'info')
            return redirect(url_for('coletas.dashboard'))
        
        return render_template('coletas/historico_coletas.html', historico=historico)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar histórico de coletas: {str(e)}")
        flash('Erro ao carregar histórico de coletas', 'error')
        return redirect(url_for('coletas.dashboard'))


@coletas_bp.route('/coletados')
@login_obrigatorio
@permissao_necessaria('acesso_logistica')
def pedidos_coletados():
    """Lista pedidos coletados (funcionalidade do logística)"""
    try:
        pedidos = ColetaService.listar_pedidos_coletados()
        return render_template('coletas/pedidos_coletados.html', pedidos=pedidos)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar pedidos coletados: {str(e)}")
        flash('Erro ao carregar pedidos coletados', 'error')
        return render_template('coletas/pedidos_coletados.html', pedidos=[])


# Rota de compatibilidade com logística
@coletas_bp.route('/coletar/<int:pedido_id>', methods=['GET', 'POST'])
@login_obrigatorio
@permissao_necessaria('acesso_logistica')
def coletar(pedido_id):
    """Rota de compatibilidade - redireciona para processar_coleta"""
    if request.method == 'POST':
        # Redirecionar POST para processar_coleta
        return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id), code=307)
    else:
        # Redirecionar GET para processar_coleta
        return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))
