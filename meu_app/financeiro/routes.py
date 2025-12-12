from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify, send_from_directory
import hashlib
import os

financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')
from .services import FinanceiroService
from functools import wraps
from ..decorators import login_obrigatorio, permissao_necessaria, admin_necessario
from ..models import Pagamento, PagamentoAnexo, Pedido, CarteiraCredito
from app.auth.rbac import requires_financeiro
from ..upload_security import FileUploadValidator
from .ocr_service import OcrService
from .config import FinanceiroConfig
from .pytorch_validator import PaymentValidatorService
from .exceptions import (
    FinanceiroValidationError, 
    PagamentoDuplicadoError, 
    PedidoNaoEncontradoError,
    ValorInvalidoError,
    ComprovanteObrigatorioError,
    ArquivoInvalidoError,
    OcrProcessingError
)
from sqlalchemy.exc import SQLAlchemyError

# Decorador login_obrigatorio movido para meu_app/decorators.py
@financeiro_bp.route('/', methods=['GET'])
@login_obrigatorio
@requires_financeiro
@permissao_necessaria('acesso_financeiro')
def listar_financeiro():
    """Lista dados financeiros"""
    try:
        tipo = request.args.get('filtro', 'todos')
        mes = request.args.get('mes', '')
        ano = request.args.get('ano', '')
        ordenar_por = request.args.get('sort', 'data')
        direcao = request.args.get('direction', 'desc')

        campos_validos = ['id', 'cliente', 'data', 'status', 'valor', 'pago', 'saldo']
        if ordenar_por not in campos_validos:
            ordenar_por = 'data'
        if direcao not in ['asc', 'desc']:
            direcao = 'desc'
        
        pedidos = FinanceiroService.listar_pedidos_financeiro(tipo, mes, ano, ordenar_por, direcao)
        
        current_app.logger.info(f"Financeiro acessado por {session.get('usuario_nome', 'N/A')}")
        
        return render_template(
            'financeiro.html',
            pedidos=pedidos,
            filtro=tipo,
            mes=mes,
            ano=ano,
            current_sort=ordenar_por,
            current_direction=direcao
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao listar financeiro: {str(e)}")
        flash(f"Erro ao carregar dados financeiros: {str(e)}", 'error')
        return render_template('financeiro.html', pedidos=[], filtro='pendentes', current_sort='data', current_direction='desc')

@financeiro_bp.route('/exportar', methods=['GET'])
@login_obrigatorio
@requires_financeiro
@permissao_necessaria('acesso_financeiro')
def exportar_financeiro():
    """Exporta dados financeiros"""
    try:
        mes = request.args.get('mes', '')
        ano = request.args.get('ano', '')
        
        dados = FinanceiroService.exportar_dados_financeiro(mes, ano)
        
        current_app.logger.info(f"Exportação financeira solicitada por {session.get('usuario_nome', 'N/A')}")
        
        return jsonify(dados)
    except Exception as e:
        current_app.logger.error(f"Erro ao exportar financeiro: {str(e)}")
        return jsonify({'error': str(e)}), 500

@financeiro_bp.route('/pagamento/<int:pedido_id>', methods=['GET', 'POST'])
@login_obrigatorio
@requires_financeiro
@permissao_necessaria('acesso_financeiro')
def registrar_pagamento(pedido_id):
    """Registra um pagamento"""
    FinanceiroService._ensure_pagamento_anexo_table()
    if request.method == 'POST':
        # Extrair dados do formulário
        valor = request.form.get('valor')
        forma_pagamento = request.form.get('metodo_pagamento')
        observacoes = request.form.get('observacoes', '')
        id_transacao = request.form.get('id_transacao') # Captura o ID da transação do campo oculto
        disponibilizar_para_outro_pedido = request.form.get('disponibilizar_comprovante') == 'on'
        comprovante_compartilhado_id = request.form.get('comprovante_compartilhado_id')
        compartilhar_item_id = request.form.get('compartilhar_item_id')
        compartilhar_item_valor = request.form.get('compartilhar_item_valor')
        compartilhar_item_filename = request.form.get('compartilhar_item_filename')
        carteira_credito_id = request.form.get('carteira_credito_id')
        comprovante_origem = None
        recibos = request.files.getlist('recibo') if not comprovante_compartilhado_id else []
        recibos = [r for r in recibos if r and r.filename]
        caminho_recibo = None
        anexos_payload = []
        uploads_salvos = []
        hashes_vistos = set()
        pedido = Pedido.query.get(pedido_id)
        if not pedido:
            flash('Pedido não encontrado', 'error')
            return redirect(url_for('financeiro.listar_financeiro'))
        cliente_id = pedido.cliente_id
        carteira_credito = None
        compartilhar_meta = None
        compartilhar_item_valor_num = None
        if compartilhar_item_valor:
            try:
                compartilhar_item_valor_num = float(str(compartilhar_item_valor).replace(',', '.'))
            except (ValueError, TypeError):
                compartilhar_item_valor_num = None
        carteira_meta = None
        if carteira_credito_id:
            try:
                carteira_credito = FinanceiroService.obter_credito_disponivel(int(carteira_credito_id))
            except (ValueError, TypeError):
                carteira_credito = None
            if not carteira_credito or carteira_credito.cliente_id != cliente_id:
                flash('Crédito selecionado indisponível para este cliente.', 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
            try:
                carteira_meta = FinanceiroService.preparar_credito_para_pagamento(
                    carteira_credito,
                    session.get('usuario_nome')
                )
                caminho_recibo = carteira_meta['caminho']
                request.recibo_meta = {
                    'recibo_mime': carteira_meta.get('mime'),
                    'recibo_tamanho': carteira_meta.get('tamanho'),
                    'recibo_sha256': carteira_meta.get('sha256')
                }
                anexos_payload.append(carteira_meta)
            except FinanceiroValidationError as err:
                flash(str(err), 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
        
        try:
            valor = float(valor)
            if valor <= 0:
                raise ValueError("Valor deve ser maior que zero")
        except (ValueError, TypeError) as e:
            flash(f'Valor inválido: {str(e)}', 'error')
            return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))

        # Lógica de upload do recibo
        if comprovante_compartilhado_id:
            try:
                comprovante_origem = Pagamento.query.get(int(comprovante_compartilhado_id))
            except (ValueError, TypeError):
                comprovante_origem = None
            if not comprovante_origem or not comprovante_origem.compartilhado_disponivel:
                flash('Comprovante compartilhado não disponível. Recarregue a página e tente novamente.', 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
            try:
                novo_nome, mime_type, tamanho, sha256 = FinanceiroService.duplicar_recibo_compartilhado(
                    comprovante_origem.caminho_recibo
                )
            except PagamentoDuplicadoError as err:
                flash(str(err), 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
            except FinanceiroValidationError as err:
                flash(str(err), 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
            except FileNotFoundError as err:
                current_app.logger.error(f'Falha ao copiar comprovante compartilhado: {err}')
                flash('Arquivo original do comprovante não foi encontrado. Solicite o envio novamente.', 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
            caminho_recibo = novo_nome
            request.recibo_meta = {
                'recibo_mime': mime_type,
                'recibo_tamanho': tamanho,
                'recibo_sha256': sha256
            }
            anexos_payload.append({
                'caminho': novo_nome,
                'mime': mime_type,
                'tamanho': tamanho,
                'sha256': sha256,
                'principal': True
            })
        elif recibos:
            upload_dir = FinanceiroConfig.get_upload_directory('recibos')
            os.makedirs(upload_dir, exist_ok=True)
            try:
                for idx, recibo in enumerate(recibos):
                    file_type = None
                    # Tenta validar como documento ou imagem
                    is_valid, error_msg, metadata = FileUploadValidator.validate_file(recibo, 'document')
                    if is_valid:
                        file_type = 'document'
                    else:
                        # Se falhar, tenta como imagem
                        is_valid, error_msg, metadata = FileUploadValidator.validate_file(recibo, 'image')
                        if is_valid:
                            file_type = 'image'

                    if not is_valid or not file_type:
                        raise ArquivoInvalidoError(f"Erro no upload do recibo: {error_msg}")

                    secure_name = FileUploadValidator.generate_secure_filename(recibo.filename, file_type)
                    file_path = os.path.join(upload_dir, secure_name)

                    file_bytes = recibo.read()
                    recibo.seek(0)
                    sha256 = hashlib.sha256(file_bytes).hexdigest()
                    tamanho = len(file_bytes)

                    if not sha256:
                        raise FinanceiroValidationError('Não foi possível calcular a assinatura do comprovante.')

                    if sha256 in hashes_vistos:
                        raise PagamentoDuplicadoError('Arquivos duplicados foram selecionados na fila de comprovantes.')
                    hashes_vistos.add(sha256)

                    existente = None
                    try:
                        existente_anexo = PagamentoAnexo.query.filter_by(sha256=sha256).first()
                        if existente_anexo:
                            existente = existente_anexo.pagamento
                    except SQLAlchemyError:
                        existente = None
                    if not existente:
                        existente = Pagamento.query.filter_by(recibo_sha256=sha256).first()
                    if existente:
                        raise PagamentoDuplicadoError(f"Este comprovante já foi enviado (ID pagamento #{existente.id}).")

                    recibo.save(file_path)
                    uploads_salvos.append(file_path)

                    meta = {
                        'caminho': secure_name,
                        'mime': metadata.get('mime_type') if metadata else None,
                        'tamanho': tamanho,
                        'sha256': sha256,
                        'principal': idx == 0 and not carteira_meta,
                        'original_name': recibo.filename
                    }

                    if idx == 0 and not carteira_meta:
                        caminho_recibo = secure_name
                        request.recibo_meta = {
                            'recibo_mime': meta.get('mime'),
                            'recibo_tamanho': tamanho,
                            'recibo_sha256': sha256
                        }
                    anexos_payload.append(meta)
                    if compartilhar_item_filename and compartilhar_item_filename == recibo.filename:
                        compartilhar_meta = {
                            **meta,
                            'valor': compartilhar_item_valor,
                            'original_name': recibo.filename
                        }
            except (ArquivoInvalidoError, FinanceiroValidationError, PagamentoDuplicadoError) as err:
                for path in uploads_salvos:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        current_app.logger.warning(f'Falha ao remover upload temporário {path}')
                flash(str(err), 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
            except Exception as e:
                for path in uploads_salvos:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except OSError:
                        current_app.logger.warning(f'Falha ao remover upload temporário {path}')
                flash(f"Erro ao salvar os arquivos de recibo: {str(e)}", 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
        elif not comprovante_origem:
            request.recibo_meta = {}

        # Extrair dados extras do formulário (se fornecidos via OCR)
        data_comprovante = request.form.get('data_comprovante', '')
        banco_emitente = request.form.get('banco_emitente', '')
        agencia_recebedor = request.form.get('agencia_recebedor', '')
        conta_recebedor = request.form.get('conta_recebedor', '')
        chave_pix_recebedor = request.form.get('chave_pix_recebedor', '')

        # Usar o serviço para registrar o pagamento
        try:
            sucesso, mensagem, pagamento = FinanceiroService.registrar_pagamento(
                pedido_id=pedido_id,
                valor=valor,
                forma_pagamento=forma_pagamento,
                observacoes=observacoes,
                caminho_recibo=caminho_recibo,
                recibo_mime=(getattr(request, 'recibo_meta', {}) or {}).get('recibo_mime'),
                recibo_tamanho=(getattr(request, 'recibo_meta', {}) or {}).get('recibo_tamanho'),
                recibo_sha256=(getattr(request, 'recibo_meta', {}) or {}).get('recibo_sha256'),
                id_transacao=id_transacao,
                # NOVOS DADOS EXTRAÍDOS DO COMPROVANTE
                data_comprovante=data_comprovante if data_comprovante else None,
                banco_emitente=banco_emitente if banco_emitente else None,
                agencia_recebedor=agencia_recebedor if agencia_recebedor else None,
                conta_recebedor=conta_recebedor if conta_recebedor else None,
                chave_pix_recebedor=chave_pix_recebedor if chave_pix_recebedor else None,
                comprovante_compartilhado_origem_id=comprovante_origem.id if comprovante_origem else None,
                anexos_detalhes=anexos_payload if anexos_payload else None
            )
            
            if sucesso:
                if comprovante_origem:
                    FinanceiroService.marcar_comprovante_compartilhado_usado(comprovante_origem, pedido_id)
                if compartilhar_meta and pagamento:
                    try:
                        FinanceiroService.criar_credito_carteira(
                            cliente_id=cliente_id,
                            pedido_origem_id=pedido_id,
                            pagamento=pagamento,
                            caminho_anexo=compartilhar_meta.get('caminho'),
                            valor=compartilhar_item_valor_num or valor,
                            usuario_nome=session.get('usuario_nome'),
                            original_name=compartilhar_meta.get('original_name')
                        )
                    except Exception as err:
                        current_app.logger.error(f"Erro ao registrar crédito na carteira: {err}")
                if carteira_credito and pagamento:
                    FinanceiroService.consumir_credito_carteira(
                        carteira_credito,
                        pedido_destino_id=pedido_id,
                        pagamento_destino=pagamento
                    )
                current_app.logger.info(f"Pagamento registrado por {session.get('usuario_nome', 'N/A')}")
                flash(mensagem, 'success')
                return redirect(url_for('financeiro.listar_financeiro'))
            else:
                flash(mensagem, 'error')
                return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
        except (FinanceiroValidationError, PagamentoDuplicadoError, PedidoNaoEncontradoError,
                ValorInvalidoError, ComprovanteObrigatorioError) as e:
            flash(str(e), 'error')
            return redirect(url_for('financeiro.registrar_pagamento', pedido_id=pedido_id))
    
    # GET: Mostrar formulário
    try:
        from ..models import Pedido
        
        # Buscar pedido
        pedido = Pedido.query.get(pedido_id)
        if not pedido:
            flash('Pedido não encontrado', 'error')
            return redirect(url_for('financeiro.listar_financeiro'))
        
        # Usar método centralizado do modelo
        totais = pedido.calcular_totais()
        
        carteira_creditos = FinanceiroService.listar_creditos_cliente(pedido.cliente_id)
        return render_template('lancar_pagamento.html', 
                             pedido=pedido, 
                             total=totais['total_pedido'], 
                             pago=totais['total_pago'], 
                             saldo=totais['saldo'],
                             carteira_creditos=carteira_creditos)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar formulário de pagamento: {str(e)}")
        flash('Erro ao carregar dados do pedido', 'error')
        return redirect(url_for('financeiro.listar_financeiro'))

@financeiro_bp.route('/recibos/<path:filename>')
@login_obrigatorio
def ver_recibo(filename):
    """Serve um arquivo de recibo de forma segura"""
    # Usar configuração centralizada
    directory = FinanceiroConfig.get_upload_directory('recibos')
    return send_from_directory(directory, filename, as_attachment=False)


@financeiro_bp.route('/api/comprovantes-compartilhados', methods=['GET'])
@login_obrigatorio
@permissao_necessaria('acesso_financeiro')
def api_comprovantes_compartilhados():
    """Lista comprovantes compartilhados disponíveis."""
    dados = FinanceiroService.listar_comprovantes_compartilhados()
    for item in dados:
        if item.get('caminho_recibo'):
            item['recibo_url'] = url_for('financeiro.ver_recibo', filename=item['caminho_recibo'])
    return jsonify({'comprovantes': dados})


@financeiro_bp.route('/api/comprovantes-compartilhados/descartar', methods=['POST'])
@login_obrigatorio
@permissao_necessaria('acesso_financeiro')
def api_descartar_comprovante_compartilhado():
    payload = request.get_json(silent=True) or {}
    comp_id = payload.get('id')
    if not comp_id:
        return jsonify({'success': False, 'message': 'ID não informado'}), 400
    sucesso = FinanceiroService.descartar_comprovante_compartilhado(comp_id)
    return jsonify({'success': sucesso})

@financeiro_bp.route('/processar-recibo-ocr', methods=['POST'])
@login_obrigatorio
def processar_recibo_ocr():
    """Processa o upload de um recibo com OCR para encontrar valor e ID da transação."""
    if 'recibo' not in request.files:
        return jsonify({'error': 'Nenhum arquivo de recibo enviado'}), 400

    recibo = request.files['recibo']
    if recibo.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    # Validar arquivo como documento OU imagem
    is_valid, error_msg, metadata = FileUploadValidator.validate_file(recibo, 'document')
    if not is_valid:
        # Se falhar como documento, tenta como imagem
        is_valid, error_msg, metadata = FileUploadValidator.validate_file(recibo, 'image')
    if not is_valid:
        return jsonify({'error': f"Arquivo inválido: {error_msg}"}), 400

    # Salvar arquivo temporariamente usando configuração centralizada
    secure_name = FileUploadValidator.generate_secure_filename(recibo.filename, 'temp_recibo_ocr')
    upload_dir = FinanceiroConfig.get_upload_directory('temp')
    file_path = os.path.join(upload_dir, secure_name)

    try:
        recibo.save(file_path)

        # CORREÇÃO: OCR opcional e não bloqueante
        try:
            # Tentar processar com OCR
            ocr_results = OcrService.process_receipt(file_path)
            
            # Preparar dados para o frontend
            response_data = {
                'valor_encontrado': ocr_results.get('amount'),
                'id_transacao_encontrado': ocr_results.get('transaction_id'),
                # NOVOS DADOS EXTRAÍDOS
                'data_encontrada': ocr_results.get('date'),
                'banco_emitente': ocr_results.get('bank_info', {}).get('banco_emitente'),
                'agencia_recebedor': ocr_results.get('bank_info', {}).get('agencia_recebedor'),
                'conta_recebedor': ocr_results.get('bank_info', {}).get('conta_recebedor'),
                'chave_pix_recebedor': ocr_results.get('bank_info', {}).get('chave_pix_recebedor'),
                # NOVO: Dados do recebedor (validação)
                'nome_recebedor': ocr_results.get('bank_info', {}).get('nome_recebedor'),
                'cnpj_recebedor': ocr_results.get('bank_info', {}).get('cnpj_recebedor'),
                'validacao_recebedor': ocr_results.get('validacao_recebedor'),  # NOVO
                'ocr_backend': ocr_results.get('backend', 'google_vision'),
                'fallback_used': ocr_results.get('fallback_used', False),
                'ocr_status': 'success',  # Indicar que OCR funcionou
                'ocr_texto': ocr_results.get('raw_text'),
            }

            # Ajustar mensagem/status conforme backend
            if ocr_results.get('fallback_used'):
                response_data['ocr_status'] = 'fallback'
                response_data['ocr_message'] = 'Dados extraídos automaticamente (modo offline)'
                fallback_found = any([
                    response_data.get('valor_encontrado'),
                    response_data.get('id_transacao_encontrado'),
                    response_data.get('data_encontrada'),
                    response_data.get('banco_emitente'),
                ])
                if not fallback_found:
                    response_data['ocr_message'] = 'Modo offline não encontrou dados úteis. Digite manualmente.'
            elif ocr_results.get('error'):
                response_data['ocr_status'] = 'failed'
                response_data['ocr_error'] = ocr_results.get('error')
                response_data['ocr_message'] = 'OCR indisponível - digite os dados manualmente'
            else:
                response_data['ocr_message'] = 'Dados extraídos automaticamente!'

            # Integração PyTorch (classificador)
            ml_result = PaymentValidatorService.evaluate_text(ocr_results.get('raw_text'))
            response_data['ml_backend'] = ml_result.get('backend')
            response_data['ml_status'] = ml_result.get('label')
            response_data['ml_confidence'] = ml_result.get('confidence')
            response_data['ml_scores'] = ml_result.get('scores')
            if ml_result.get('error'):
                response_data['ml_error'] = ml_result.get('error')
                
        except Exception as ocr_error:
            # Se OCR falhar completamente, retornar resposta vazia mas não erro
            current_app.logger.warning(f"OCR falhou, mas sistema continua funcionando: {str(ocr_error)}")
            response_data = {
                'valor_encontrado': None,
                'id_transacao_encontrado': None,
                'data_encontrada': None,
                'banco_emitente': None,
                'agencia_recebedor': None,
                'conta_recebedor': None,
                'chave_pix_recebedor': None,
                'ocr_status': 'failed',
                'ocr_message': 'OCR temporariamente indisponível - digite os dados manualmente',
                'ocr_texto': None,
                'ocr_error': str(ocr_error)
            }
            ml_result = PaymentValidatorService.evaluate_text(None)
            response_data['ml_backend'] = ml_result.get('backend')
            response_data['ml_status'] = ml_result.get('label')
            response_data['ml_confidence'] = ml_result.get('confidence')
            response_data['ml_scores'] = ml_result.get('scores')
            if ml_result.get('error'):
                response_data['ml_error'] = ml_result.get('error')

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Erro no processamento OCR: {str(e)}")
        return jsonify({'error': 'Erro interno ao processar o arquivo.'}), 500
    finally:
        # Limpar o arquivo temporário
        if os.path.exists(file_path):
            os.remove(file_path)

@financeiro_bp.route('/editar-pagamento/<int:pedido_id>', methods=['GET', 'POST'])
@login_obrigatorio
@permissao_necessaria('acesso_financeiro')
def editar_pagamento(pedido_id):
    """Edita um pagamento existente"""
    from ..models import Pedido, Pagamento
    from .. import db
    FinanceiroService._ensure_pagamento_anexo_table()
    
    if request.method == 'POST':
        try:
            pagamento_id = request.form.get('pagamento_id')
            if not pagamento_id:
                flash('Selecione um pagamento para editar', 'error')
                return redirect(url_for('financeiro.editar_pagamento', pedido_id=pedido_id))
            
            pagamento = Pagamento.query.get(int(pagamento_id))
            if not pagamento or pagamento.pedido_id != pedido_id:
                flash('Pagamento não encontrado', 'error')
                return redirect(url_for('financeiro.listar_financeiro'))
            
            acao = request.form.get('acao', 'editar')

            if acao == 'excluir':
                # Remover comprovante se existir
                if pagamento.caminho_recibo:
                    try:
                        recibo_path = os.path.join(
                            FinanceiroConfig.get_upload_directory('recibos'),
                            pagamento.caminho_recibo
                        )
                        if os.path.exists(recibo_path):
                            os.remove(recibo_path)
                    except Exception as exc:
                        current_app.logger.warning(
                            "Falha ao remover recibo durante exclusão do pagamento %s: %s",
                            pagamento.id,
                            exc,
                        )

                db.session.delete(pagamento)
                db.session.commit()
                current_app.logger.info(
                    "Pagamento #%s excluído por %s",
                    pagamento.id,
                    session.get('usuario_nome', 'N/A'),
                )
                flash('Pagamento excluído com sucesso!', 'success')
                return redirect(url_for('financeiro.listar_financeiro'))

            # Atualizar dados do pagamento
            valor = request.form.get('valor')
            forma_pagamento = request.form.get('metodo_pagamento')
            observacoes = request.form.get('observacoes', '')
            
            try:
                valor = float(valor)
                if valor <= 0:
                    raise ValueError("Valor deve ser maior que zero")
            except (ValueError, TypeError) as e:
                flash(f'Valor inválido: {str(e)}', 'error')
                return redirect(url_for('financeiro.editar_pagamento', pedido_id=pedido_id))
            
            # Atualizar pagamento
            pagamento.valor = valor
            pagamento.metodo_pagamento = forma_pagamento
            pagamento.observacoes = observacoes
            
            # Processar upload de novo recibo se fornecido
            recibo = request.files.get('recibo')
            if recibo and recibo.filename:
                file_type = None
                is_valid, error_msg, metadata = FileUploadValidator.validate_file(recibo, 'document')
                if is_valid:
                    file_type = 'document'
                else:
                    is_valid, error_msg, metadata = FileUploadValidator.validate_file(recibo, 'image')
                    if is_valid:
                        file_type = 'image'

                if not is_valid or not file_type:
                    flash(f"Erro no upload do recibo: {error_msg}", 'error')
                    return redirect(url_for('financeiro.editar_pagamento', pedido_id=pedido_id))
                
                # Remover recibo antigo se existir
                if pagamento.caminho_recibo:
                    old_path = os.path.join(FinanceiroConfig.get_upload_directory('recibos'), pagamento.caminho_recibo)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # Salvar novo recibo
                secure_name = FileUploadValidator.generate_secure_filename(recibo.filename, file_type)
                upload_dir = FinanceiroConfig.get_upload_directory('recibos')
                file_path = os.path.join(upload_dir, secure_name)
                
                file_bytes = recibo.read()
                recibo.seek(0)
                import hashlib
                sha256 = hashlib.sha256(file_bytes).hexdigest()
                tamanho = len(file_bytes)
                
                recibo.save(file_path)
                pagamento.caminho_recibo = secure_name
                pagamento.recibo_mime = metadata.get('mime_type') if metadata else None
                pagamento.recibo_tamanho = tamanho
                pagamento.recibo_sha256 = sha256
            
            db.session.commit()
            flash('Pagamento atualizado com sucesso!', 'success')
            current_app.logger.info(f"Pagamento #{pagamento.id} editado por {session.get('usuario_nome', 'N/A')}")
            return redirect(url_for('financeiro.listar_financeiro'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao editar pagamento: {str(e)}")
            flash(f'Erro ao editar pagamento: {str(e)}', 'error')
            return redirect(url_for('financeiro.editar_pagamento', pedido_id=pedido_id))
    
    # GET: Mostrar formulário
    try:
        pedido = Pedido.query.get(pedido_id)
        if not pedido:
            flash('Pedido não encontrado', 'error')
            return redirect(url_for('financeiro.listar_financeiro'))
        
        # Buscar pagamentos do pedido
        pagamentos = Pagamento.query.filter_by(pedido_id=pedido_id).all()
        
        totais = pedido.calcular_totais()
        
        return render_template('editar_pagamento.html',
                             pedido=pedido,
                             pagamentos=pagamentos,
                             total=totais['total_pedido'],
                             pago=totais['total_pago'],
                             saldo=totais['saldo'])
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar formulário de edição: {str(e)}")
        flash('Erro ao carregar dados do pagamento', 'error')
        return redirect(url_for('financeiro.listar_financeiro'))

@financeiro_bp.route('/retornar-comercial/<int:pedido_id>', methods=['POST'])
@login_obrigatorio
@permissao_necessaria('acesso_financeiro')
def retornar_para_comercial(pedido_id):
    """Retorna um pedido para o comercial (apenas se não houver pagamentos)"""
    from ..models import Pedido, Pagamento
    from .. import db
    
    try:
        pedido = Pedido.query.get(pedido_id)
        if not pedido:
            return jsonify({'success': False, 'message': 'Pedido não encontrado'}), 404
        
        # Verificar se há pagamentos
        pagamentos = Pagamento.query.filter_by(pedido_id=pedido_id).count()
        if pagamentos > 0:
            return jsonify({
                'success': False, 
                'message': f'Este pedido possui {pagamentos} pagamento(s) registrado(s). Não é possível retorná-lo ao comercial.'
            }), 400
        
        # Remover a confirmação comercial (retornar para pedidos)
        pedido.confirmado_comercial = False
        pedido.confirmado_por = None
        pedido.data_confirmacao = None
        
        db.session.commit()
        
        # Invalidar cache da sessão SQLAlchemy
        db.session.expire_all()
        
        current_app.logger.info(
            f"Pedido #{pedido_id} retornado para comercial por {session.get('usuario_nome', 'N/A')}. "
            f"Confirmado comercial: {pedido.confirmado_comercial}"
        )
        
        return jsonify({
            'success': True, 
            'message': f'Pedido #{pedido_id} retornado com sucesso! Ele agora está disponível no módulo Pedidos.'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao retornar pedido para comercial: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Erro ao processar requisição: {str(e)}'
        }), 500
