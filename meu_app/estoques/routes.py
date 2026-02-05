from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import current_user

estoques_bp = Blueprint('estoques', __name__, url_prefix='/estoques')
from .services import EstoqueService
from ..models import Produto, Estoque
from ..time_utils import now_utc, to_utc_iso
from functools import wraps
from ..decorators import login_obrigatorio, permissao_necessaria, admin_necessario

# Decorador login_obrigatorio movido para meu_app/decorators.py
@estoques_bp.route('/', methods=['GET'])
@login_obrigatorio
@permissao_necessaria('acesso_estoques')
def listar_estoques():
    """Lista todos os estoques"""
    try:
        estoques = EstoqueService.listar_estoques()
        current_app.logger.info(f"Listagem de estoques acessada por {session.get('usuario_nome', 'N/A')}")
        return render_template('estoques.html', estoques=estoques)
    except Exception as e:
        current_app.logger.error(f"Erro ao listar estoques: {str(e)}")
        flash(f"Erro ao carregar estoques: {str(e)}", 'error')
        return render_template('estoques.html', estoques=[])

@estoques_bp.route('/novo', methods=['GET', 'POST'])
@login_obrigatorio
@permissao_necessaria('acesso_estoques')
def novo_estoque():
    """Atualiza o estoque de um produto (cria se não existir)"""
    if request.method == 'POST':
        # Extrair dados do formulário
        produto_id = request.form.get('produto_id')
        quantidade = request.form.get('quantidade')
        data_entrada = request.form.get('data_entrada')
        conferente = request.form.get('conferente', session.get('usuario_nome', 'Sistema'))
        status = request.form.get('status')
        observacoes = request.form.get('observacoes', '').strip()
        
        try:
            produto_id = int(produto_id)
            quantidade = int(quantidade)
        except (ValueError, TypeError):
            flash('Dados inválidos fornecidos', 'error')
            produtos = Produto.query.all()
            return render_template('novo_estoque.html', produtos=produtos, now_utc=now_utc())
        
        # Verificar se já existe estoque para este produto
        estoque_existente = Estoque.query.filter_by(produto_id=produto_id).first()
        
        if estoque_existente:
            # Atualizar estoque existente
            sucesso, mensagem, estoque = EstoqueService.atualizar_estoque(
                produto_id=produto_id,
                quantidade=quantidade,
                data_entrada=data_entrada,
                conferente=conferente,
                status=status,
                observacoes=observacoes
            )
        else:
            # Criar novo estoque
            sucesso, mensagem, estoque = EstoqueService.criar_estoque(
                produto_id=produto_id,
                quantidade=quantidade,
                data_entrada=data_entrada,
                conferente=conferente,
                status=status,
                observacoes=observacoes
            )
        
        if sucesso:
            current_app.logger.info(f"Estoque {'atualizado' if estoque_existente else 'criado'} por {session.get('usuario_nome', 'N/A')}")
            flash(mensagem, 'success')
            return redirect(url_for('estoques.listar_estoques'))
        else:
            flash(mensagem, 'error')
            produtos = Produto.query.all()
            return render_template('novo_estoque.html', produtos=produtos, now_utc=now_utc())
    
    # GET: Mostrar formulário
    produtos = Produto.query.all()
    return render_template('novo_estoque.html', produtos=produtos, now_utc=now_utc())

@estoques_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
@permissao_necessaria('acesso_estoques')
def editar_estoque(id):
    """Edita um estoque existente"""
    if request.method == 'POST':
        # Extrair dados do formulário
        quantidade = request.form.get('quantidade')
        data_entrada = request.form.get('data_entrada')
        status = request.form.get('status')
        observacoes = request.form.get('observacoes', '').strip()
        
        try:
            quantidade = int(quantidade)
        except (ValueError, TypeError):
            flash('Dados inválidos fornecidos', 'error')
            estoque = EstoqueService.buscar_estoque(id)
            produtos = Produto.query.all()
            return render_template('editar_estoque.html', estoque=estoque, produtos=produtos)
        
        # Usar o serviço para editar o estoque
        sucesso, mensagem, estoque = EstoqueService.editar_estoque(
            estoque_id=id,
            quantidade=quantidade,
            data_entrada=data_entrada,
            status=status,
            observacoes=observacoes
        )
        
        if sucesso:
            current_app.logger.info(f"Estoque editado por {session.get('usuario_nome', 'N/A')}")
            flash(mensagem, 'success')
            return redirect(url_for('estoques.listar_estoques'))
        else:
            flash(mensagem, 'error')
            estoque = EstoqueService.buscar_estoque(id)
            produtos = Produto.query.all()
            return render_template('editar_estoque.html', estoque=estoque, produtos=produtos)
    
    # GET: Buscar estoque e mostrar formulário
    estoque = EstoqueService.buscar_estoque(id)
    if not estoque:
        flash('Estoque não encontrado', 'error')
        return redirect(url_for('estoques.listar_estoques'))
    
    produtos = Produto.query.all()
    return render_template('editar_estoque.html', estoque=estoque, produtos=produtos)

@estoques_bp.route('/excluir/<int:id>')
@login_obrigatorio
@permissao_necessaria('acesso_estoques')
def excluir_estoque(id):
    """Exclui um estoque"""
    # Usar o serviço para excluir o estoque
    sucesso, mensagem = EstoqueService.excluir_estoque(id)
    
    if sucesso:
        current_app.logger.info(f"Estoque excluído (ID: {id}) por {session.get('usuario_nome', 'N/A')}")
        flash(mensagem, 'success')
    else:
        flash(mensagem, 'error')
    
    return redirect(url_for('estoques.listar_estoques'))


@estoques_bp.route('/confirmar-inventario', methods=['POST'])
@login_obrigatorio
@permissao_necessaria('acesso_estoques')
def confirmar_inventario():
    """Confirma o inventário após validação de senha."""
    payload = request.get_json(silent=True) or {}
    senha = (payload.get('password') or '').strip()
    estoque_ids = payload.get('estoque_ids') or []

    if not senha:
        return jsonify({'success': False, 'error': 'Senha obrigatória.'}), 400

    if not current_user or not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Usuário não autenticado.'}), 401

    if not current_user.check_senha(senha):
        return jsonify({'success': False, 'error': 'Senha inválida.'}), 401

    ids_registrados = [row.id for row in Estoque.query.with_entities(Estoque.id).all()]
    total_registros = len(ids_registrados)

    ids_enviados = set()
    for raw_id in estoque_ids:
        try:
            ids_enviados.add(int(raw_id))
        except (TypeError, ValueError):
            continue

    if total_registros > 0 and ids_enviados != set(ids_registrados):
        return jsonify({
            'success': False,
            'error': 'Todos os itens do estoque devem ser confirmados antes de finalizar.'
        }), 400

    sucesso, mensagem, total = EstoqueService.confirmar_inventario(current_user.nome)
    status_code = 200 if sucesso else 400
    resposta = {
        'success': sucesso,
        'message': mensagem,
        'total_itens': total
    }
    if not sucesso:
        resposta['error'] = mensagem
    return jsonify(resposta), status_code

@estoques_bp.route('/historico/<int:produto_id>')
@login_obrigatorio
@permissao_necessaria('acesso_estoques')
def historico_movimentacao(produto_id):
    """Exibe o histórico de movimentação de um produto"""
    try:
        # Buscar produto
        produto = Produto.query.get(produto_id)
        if not produto:
            flash('Produto não encontrado', 'error')
            return redirect(url_for('estoques.listar_estoques'))
        
        # Buscar histórico de movimentação
        movimentacoes = EstoqueService.buscar_historico_movimentacao(produto_id)
        
        # Calcular total no backend (Python)
        total = sum(mov.quantidade_movimentada for mov in movimentacoes)
        
        current_app.logger.info(f"Histórico de movimentação acessado para produto {produto.nome} por {session.get('usuario_nome', 'N/A')}")
        
        return render_template('historico_movimentacao.html', 
                             produto=produto, 
                             movimentacoes=movimentacoes,
                             total=total)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar histórico de movimentação: {str(e)}")
        flash(f"Erro ao carregar histórico: {str(e)}", 'error')
        return redirect(url_for('estoques.listar_estoques'))

@estoques_bp.route('/estoque_atual/<int:produto_id>')
@login_obrigatorio
@permissao_necessaria('acesso_estoques')
def estoque_atual(produto_id):
    """Retorna o estoque atual de um produto em formato JSON"""
    try:
        estoque = Estoque.query.filter_by(produto_id=produto_id).first()
        
        if estoque:
            return jsonify({
                'estoque': {
                    'quantidade': estoque.quantidade,
                    'conferente': estoque.conferente,
                    'status': estoque.status,
                    'data_modificacao': estoque.data_modificacao.strftime('%d/%m/%Y %H:%M') if estoque.data_modificacao else None,
                    'data_modificacao_utc': to_utc_iso(estoque.data_modificacao) if estoque.data_modificacao else None
                }
            })
        else:
            return jsonify({'estoque': None})
            
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar estoque atual: {str(e)}")
        return jsonify({'error': 'Erro ao buscar estoque atual'}), 500
