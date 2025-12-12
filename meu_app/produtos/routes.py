from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file, session, flash, current_app

produtos_bp = Blueprint('produtos', __name__, url_prefix='/produtos')
from ..models import Produto
from .. import db
from .services import ProdutoService, ImportacaoService, ExportacaoService, ImportacaoServiceSeguro
from functools import wraps
from ..decorators import login_obrigatorio, permissao_necessaria
from ..upload_security import validate_excel_upload, validate_csv_upload

def registrar_atividade(tipo_atividade, titulo, descricao, modulo, dados_extras=None):
    """Função para registrar atividades (será implementada posteriormente)"""
    current_app.logger.info(f"Atividade registrada: {tipo_atividade} - {titulo}")

@produtos_bp.route('/')
@login_obrigatorio
@permissao_necessaria('acesso_produtos')
def listar_produtos():
    produtos = Produto.query.all()
    categorias = [
        row[0]
        for row in db.session.query(Produto.categoria)
        .distinct()
        .filter(Produto.categoria.isnot(None))
        .order_by(Produto.categoria)
    ]
    current_app.logger.info(f"Listagem de produtos acessada por {session.get('usuario_nome', 'N/A')}")
    return render_template('produtos.html', produtos=produtos, categorias=categorias)

@produtos_bp.route('/novo', methods=['GET', 'POST'])
@login_obrigatorio
@permissao_necessaria('acesso_produtos')
def novo_produto():
    categorias = [
        row[0]
        for row in db.session.query(Produto.categoria)
        .distinct()
        .filter(Produto.categoria.isnot(None))
        .order_by(Produto.categoria)
    ]
    if not categorias:
        categorias = ['CERVEJA', 'NAB', 'OUTROS']
    
    if request.method == 'POST':
        nome = request.form['nome']
        categoria = request.form.get('categoria', 'OUTROS')
        codigo_interno = request.form.get('codigo_interno')
        ean = request.form.get('ean')
        
        # Usar o serviço para criar o produto
        service = ProdutoService()
        sucesso, mensagem, produto = service.criar_produto(nome, categoria, codigo_interno, ean)
        
        if sucesso:
            # Registrar atividade
            registrar_atividade(
                tipo_atividade="Criação de Produto",
                titulo="Produto Criado",
                descricao=f"Produto: {nome} (Código: {codigo_interno})",
                modulo="Produtos",
                dados_extras={"produto_id": produto.id, "nome": nome, "codigo_interno": codigo_interno}
            )
            
            current_app.logger.info(f"Produto criado: {nome} por {session.get('usuario_nome', 'N/A')}")
            flash(mensagem, 'success')
            return redirect(url_for('produtos.listar_produtos'))
        else:
            flash(mensagem, 'error')
            return render_template('novo_produto.html', erro=mensagem, categorias=categorias)
    
    return render_template('novo_produto.html', categorias=categorias)

@produtos_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_obrigatorio
@permissao_necessaria('acesso_produtos')
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    
    if request.method == 'POST':
        nome = request.form['nome']
        categoria = request.form.get('categoria', 'OUTROS')
        codigo_interno = request.form.get('codigo_interno')
        ean = request.form.get('ean')
        
        # Usar o serviço para atualizar o produto
        service = ProdutoService()
        sucesso, mensagem = service.atualizar_produto(id, nome, categoria, codigo_interno, ean)
        
        if sucesso:
            current_app.logger.info(f"Produto editado: {produto.nome} por {session.get('usuario_nome', 'N/A')}")
            flash(mensagem, 'success')
            return redirect(url_for('produtos.listar_produtos'))
        else:
            flash(mensagem, 'error')
            return render_template('novo_produto.html', produto=produto, erro=mensagem, categorias=categorias)
    
    # Garantir que a categoria atual apareça na lista mesmo se não existir no conjunto
    categorias_set = set(categorias)
    if produto.categoria and produto.categoria not in categorias_set:
        categorias.insert(0, produto.categoria)
    return render_template('novo_produto.html', produto=produto, categorias=categorias)

@produtos_bp.route('/excluir/<int:id>')
@login_obrigatorio
@permissao_necessaria('acesso_produtos')
def excluir_produto(id):
    # Usar o serviço para excluir o produto
    service = ProdutoService()
    sucesso, mensagem = service.excluir_produto(id)
    
    if sucesso:
        current_app.logger.info(f"Produto excluído (ID: {id}) por {session.get('usuario_nome', 'N/A')}")
        flash(mensagem, 'success')
    else:
        flash(mensagem, 'error')
    
    return redirect(url_for('produtos.listar_produtos'))

@produtos_bp.route('/upload', methods=['POST'])
@login_obrigatorio
@permissao_necessaria('acesso_produtos')
def upload_produtos():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        
        # Validar e salvar arquivo de forma segura
        sucesso_upload, mensagem_upload, file_path = validate_excel_upload(file)
        
        if not sucesso_upload:
            return jsonify({'success': False, 'message': f'Erro no upload: {mensagem_upload}'}), 400
        
        # Usar o serviço para importar produtos com arquivo seguro
        sucesso, mensagem, dados = ImportacaoServiceSeguro.importar_produtos_planilha_seguro(file_path)
        
        if sucesso:
            current_app.logger.info(f"Upload de produtos por {session.get('usuario_nome', 'N/A')}")
            
            resposta = {
                'success': True,
                'message': mensagem,
                'duplicados': dados.get('produtos_duplicados', []),
                'invalidos': dados.get('produtos_invalidos', []),
                'atualizados': dados.get('produtos_atualizados', []),
                'categorias_alteradas': dados.get('categorias_alteradas', []),
                'criados': dados.get('produtos_criados', 0),
                'erros': dados.get('erros', [])
            }
            return jsonify(resposta)
        else:
            return jsonify({
                'success': False,
                'message': mensagem,
                'duplicados': dados.get('produtos_duplicados', []),
                'invalidos': dados.get('produtos_invalidos', []),
                'atualizados': dados.get('produtos_atualizados', []),
                'categorias_alteradas': dados.get('categorias_alteradas', []),
                'criados': dados.get('produtos_criados', 0),
                'erros': dados.get('erros', [])
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Erro no upload de produtos: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'}), 500

@produtos_bp.route('/atualizar_preco', methods=['POST'])
@login_obrigatorio
def atualizar_preco_produto():
    """Atualiza o preço médio de compra de um produto"""
    if not session.get('acesso_produtos'):
        return jsonify({'success': False, 'message': 'Acesso negado!'})
    
    try:
        produto_id = request.form.get('produto_id')
        preco_medio = request.form.get('preco_medio')
        
        if not produto_id or not preco_medio:
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        # Usar o serviço para atualizar o preço
        service = ProdutoService()
        sucesso, mensagem, preco_anterior = service.atualizar_preco_produto(int(produto_id), float(preco_medio))
        
        if sucesso:
            # Registrar atividade
            produto = Produto.query.get(produto_id)
            registrar_atividade(
                tipo_atividade="Atualização de Preço",
                titulo=f"Preço atualizado para {produto.nome}",
                descricao=f"Preço médio alterado para R$ {float(preco_medio):.2f}",
                modulo="Produtos",
                dados_extras={"produto_id": produto_id, "produto_nome": produto.nome, "preco_anterior": preco_anterior, "preco_novo": float(preco_medio)}
            )
            
            current_app.logger.info(f"Preço atualizado para produto {produto.nome} por {session.get('usuario_nome', 'N/A')}")
            return jsonify({'success': True, 'message': mensagem})
        else:
            return jsonify({'success': False, 'message': mensagem})
        
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar preço: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao atualizar preço: {str(e)}'})

@produtos_bp.route('/upload_precos', methods=['POST'])
@login_obrigatorio
def upload_precos_produtos():
    """Upload de planilha com preços médios de produtos"""
    if not session.get('acesso_produtos'):
        return jsonify({'success': False, 'message': 'Acesso negado!'})
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
        
        file = request.files['file']
        
        # Usar o serviço para importar preços
        sucesso, mensagem, dados = ImportacaoService.importar_precos_planilha(file)
        
        if sucesso:
            # Registrar atividade
            registrar_atividade(
                tipo_atividade="Upload de Preços",
                titulo="Preços médios importados",
                descricao=f"{dados['produtos_atualizados']} produtos atualizados via planilha",
                modulo="Produtos",
                dados_extras=dados
            )
            
            current_app.logger.info(f"Upload de preços por {session.get('usuario_nome', 'N/A')}")
            
            # Se há produtos não encontrados, incluir na mensagem
            if dados.get('produtos_nao_encontrados'):
                mensagem += f" {len(dados['produtos_nao_encontrados'])} produtos não foram encontrados."
            
            resposta = {
                'success': True,
                'message': mensagem,
                'atualizados': dados.get('produtos_atualizados', 0),
                'nao_encontrados': dados.get('produtos_nao_encontrados', []),
                'invalidos': dados.get('produtos_invalidos', [])
            }
            
            return jsonify(resposta)
        else:
            return jsonify({'success': False, 'message': mensagem})
        
    except Exception as e:
        current_app.logger.error(f"Erro no upload de preços: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'})

# Rotas para download de modelos (fora do prefixo /produtos)
@produtos_bp.route('/download_modelo_produtos')
@login_obrigatorio
def download_modelo_produtos():
    if not session.get('acesso_produtos'):
        return jsonify({'error': 'Acesso negado!'}), 403
    
    try:
        # Usar o serviço para gerar o modelo
        output = ExportacaoService.gerar_modelo_produtos()
        
        current_app.logger.info(f"Modelo de produtos baixado por {session.get('usuario_nome', 'N/A')}")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='modelo_produtos.xlsx'
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar modelo de produtos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@produtos_bp.route('/download_modelo_precos')
@login_obrigatorio
def download_modelo_precos():
    """Download do modelo de planilha para preços médios"""
    if not session.get('acesso_produtos'):
        return jsonify({'error': 'Acesso negado!'}), 403
    
    try:
        # Usar o serviço para gerar o modelo
        output = ExportacaoService.gerar_modelo_precos()
        
        current_app.logger.info(f"Modelo de preços baixado por {session.get('usuario_nome', 'N/A')}")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='modelo_precos_medios.xlsx'
        )
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar modelo de preços: {str(e)}")
        return jsonify({'error': str(e)}), 500

@produtos_bp.route('/api/produtos')
@login_obrigatorio
@permissao_necessaria('acesso_produtos')
def api_produtos():
    """
    Endpoint de API para buscar produtos para o Select2.
    Responde ao parâmetro 'q' para busca.
    """
    search = request.args.get('q')
    
    if search:
        # Busca por nome ou código interno que contenha o termo de busca
        produtos_query = Produto.query.filter(
            Produto.nome.ilike(f'%{search}%') | 
            Produto.codigo_interno.ilike(f'%{search}%')
        )
    else:
        produtos_query = Produto.query

    # Limitar a um número razoável de resultados para não sobrecarregar
    produtos = produtos_query.limit(50).all()
    
    # Formatar para o padrão que o Select2 espera (id, text)
    results = [
        {'id': produto.id, 'text': f"{produto.nome} ({produto.codigo_interno or 'N/A'})"}
        for produto in produtos
    ]
    
    return jsonify({'results': results})
