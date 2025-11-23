"""
Rotas consolidadas do módulo de coletas
Integra funcionalidades do módulo logística
"""
from flask import Blueprint, render_template, current_app, flash, request, redirect, url_for, session, send_file, abort
from ..decorators import login_obrigatorio
from app.auth.rbac import requires_logistica
import re
from typing import Optional
from pathlib import Path

coletas_bp = Blueprint('coletas', __name__, url_prefix='/coletas')
from .services.coleta_service import ColetaService
from .receipt_service import ReceiptService
import os
from ..clientes.services import ClienteService
from meu_app.exceptions import ConfigurationError, FileProcessingError
from meu_app.queue import get_job_status

CPF_REGEX = re.compile(r'^\d{11}$')
NAME_REGEX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]*$")


def _normalizar_cpf(valor: str) -> str | None:
    """Remove caracteres não numéricos e valida tamanho."""
    if not valor:
        return None
    apenas_digitos = re.sub(r'\D', '', valor)
    if CPF_REGEX.match(apenas_digitos) and _cpf_valido(apenas_digitos):
        return apenas_digitos
    return None


def _formatar_cpf(cpf: str) -> str:
    """Formata CPF no padrão XXX.XXX.XXX-XX."""
    if not cpf or len(cpf) != 11:
        return cpf or ''
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def _mascarar_cpf(cpf: str) -> str:
    """Masca CPF para logs, mostrando apenas início e fim."""
    if not cpf:
        return '***'
    digits = re.sub(r'\D', '', cpf)
    if len(digits) != 11:
        return f'***{digits[-2:]}' if len(digits) >= 2 else '***'
    return f'{digits[:3]}.***.***-{digits[-2:]}'


def _cpf_valido(cpf: str) -> bool:
    """Valida dígitos verificadores de um CPF."""
    if not cpf or len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[indice]) * ((tamanho + 1) - indice) for indice in range(tamanho))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[tamanho]):
            return False
    return True


def _is_ajax_request() -> bool:
    """Detecta requisições AJAX/Fetch."""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _parse_quantidade(raw_valor: str) -> Optional[int]:
    """Converte entrada bruta de quantidade em inteiro válido."""
    valor = (raw_valor or '').strip()
    if valor == '':
        return None
    try:
        quantidade = int(valor)
    except ValueError as exc:
        raise ValueError('Informe apenas números inteiros para a quantidade de cada item.') from exc
    if quantidade < 0:
        raise ValueError('Quantidade não pode ser negativa.')
    return quantidade


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
@requires_logistica
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
@requires_logistica
def processar_coleta(pedido_id):
    """Processa uma coleta (funcionalidade original)"""
    if request.method == 'POST':
        is_ajax = _is_ajax_request()

        def respond_error(message: str, category: str = 'error', status: int = 400):
            if is_ajax:
                return {'success': False, 'message': message}, status
            flash(message, category)
            return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))

        try:
            detalhes = ColetaService.buscar_detalhes_pedido(pedido_id)
            if not detalhes:
                if is_ajax:
                    return {'success': False, 'message': 'Pedido não encontrado ou não disponível para coleta.'}, 404
                flash('Pedido não encontrado ou não disponível para coleta', 'error')
                return redirect(url_for('coletas.dashboard'))

            cliente_service = ClienteService()
            retirantes_autorizados = cliente_service.listar_retirantes_autorizados(detalhes['cliente'].id)
            
            nome_retirada = request.form.get('nome_retirada', '').strip()
            documento_retirada_raw = request.form.get('documento_retirada', '').strip()
            nome_conferente = request.form.get('nome_conferente', '').strip()
            cpf_conferente_raw = request.form.get('cpf_conferente', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not _nome_valido(nome_retirada):
                return respond_error('Informe o nome completo de quem está retirando (somente letras).')

            if not _nome_valido(nome_conferente):
                return respond_error('Informe o nome completo do conferente (somente letras).')

            nome_retirada = ' '.join(nome_retirada.split())
            nome_conferente = ' '.join(nome_conferente.split())

            documento_retirada = _normalizar_cpf(documento_retirada_raw)
            if not documento_retirada:
                return respond_error('CPF da pessoa que retira é inválido.')

            cpf_conferente = _normalizar_cpf(cpf_conferente_raw)
            if not cpf_conferente:
                return respond_error('CPF do conferente é inválido.')

            limites_quantidade = {}
            for item in detalhes['itens']:
                estoque_disp = getattr(item, 'estoque_disponivel', 0) or 0
                pendente = getattr(item, 'quantidade_pendente', 0) or 0
                max_permitido = max(0, min(pendente, estoque_disp))
                limites_quantidade[item.id] = max_permitido
            
            itens_coleta = []
            try:
                for key, value in request.form.items():
                    if not key.startswith('quantidade_'):
                        continue

                    item_id_str = key.split('quantidade_', 1)[-1]
                    try:
                        item_id = int(item_id_str)
                    except ValueError as exc:
                        raise ValueError('Identificador de item inválido na requisição.') from exc

                    limite = limites_quantidade.get(item_id)
                    if limite is None:
                        raise ValueError('Item informado não corresponde ao pedido selecionado.')

                    quantidade = _parse_quantidade(value)
                    if quantidade is None or limite == 0:
                        continue

                    if quantidade > limite:
                        raise ValueError('Quantidade solicitada excede o limite permitido para um dos itens.')

                    itens_coleta.append({
                        'item_id': item_id,
                        'quantidade': quantidade
                    })
            except ValueError as value_error:
                current_app.logger.warning(
                    "Quantidade inválida durante processamento de coleta",
                    extra={
                        "pedido_id": pedido_id,
                        "erro": str(value_error),
                        "responsavel": session.get('usuario_nome', 'N/A'),
                        "documento_mascarado": _mascarar_cpf(documento_retirada),
                        "conferente_mascarado": _mascarar_cpf(cpf_conferente),
                    },
                )
                return respond_error(str(value_error))
            
            if not itens_coleta:
                return respond_error('Selecione pelo menos um item para coleta!', status=422)
            
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
            
            alerta_autorizacao = None
            autorizados_ativos = {r.cpf for r in retirantes_autorizados if r.ativo}
            if documento_retirada not in autorizados_ativos:
                alerta_autorizacao = '⚠️ Retirante informado não está na lista autorizada. Confirme com o cliente antes de liberar.'
                current_app.logger.warning(
                    "Tentativa de retirada por CPF não autorizado",
                    extra={
                        "pedido_id": pedido_id,
                        "documento_mascarado": _mascarar_cpf(documento_retirada),
                    },
                )
                if not is_ajax:
                    flash(alerta_autorizacao, 'warning')

            if not sucesso:
                return respond_error(mensagem)

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
                    'cliente_nome': detalhes.get('cliente').nome if detalhes.get('cliente') else 'N/A',
                    'nome_retirada': nome_retirada,
                    'documento_retirada': _formatar_cpf(documento_retirada),
                    'nome_conferente': nome_conferente,
                    'cpf_conferente': _formatar_cpf(cpf_conferente),
                    'itens_coleta': itens_recibo
                }
                
                try:
                    job_id = ReceiptService.enfileirar_recibo_imagem(coleta_data)
                    if job_id:
                        status_url = url_for('coletas.status_recibo', job_id=job_id, pedido_id=pedido_id)
                        msg = f'{mensagem} Recibo em processamento. O download será liberado em instantes.'
                        if is_ajax:
                            return {'success': True, 'message': msg, 'status_url': status_url}
                        flash(msg, 'info')
                        return redirect(status_url)
                    
                    imagem_path = ReceiptService.gerar_recibo_imagem(coleta_data)
                    download_url = url_for(
                        'coletas.visualizar_recibo',
                        filename=os.path.basename(imagem_path),
                        _external=True
                    )
                    
                    sucesso_msg = f'{mensagem} Recibo gerado com sucesso!'
                    if alerta_autorizacao and is_ajax:
                        sucesso_msg = f"{sucesso_msg} {alerta_autorizacao}"
                    elif alerta_autorizacao:
                        flash(alerta_autorizacao, 'warning')

                    if is_ajax:
                        return {
                            'success': True,
                            'message': sucesso_msg,
                            'download_url': download_url,
                        }
                    
                    flash(sucesso_msg, 'success')
                    return send_file(
                        imagem_path,
                        mimetype='image/jpeg'
                    )
                
                except ConfigurationError as e:
                    current_app.logger.error("Dependência ausente para geração de recibo", exc_info=e)
                    return respond_error('Dependência para geração de recibos não encontrada. Contate o administrador.', status=500)
                except FileProcessingError as e:
                    current_app.logger.error("Erro ao processar geração de recibo", exc_info=e)
                    return respond_error(f'{mensagem} (Erro ao gerar recibo)', category='warning', status=500)
                except Exception as e:
                    current_app.logger.error(f"Erro inesperado ao gerar recibo: {str(e)}", exc_info=e)
                    return respond_error(f'{mensagem} (Erro ao gerar recibo)', category='warning', status=500)
            
            except Exception as e:
                current_app.logger.error(f"Erro ao preparar dados do recibo: {str(e)}", exc_info=e)
                return respond_error(f'{mensagem} (Erro ao preparar recibo)', category='warning', status=500)
                
        except Exception as e:
            current_app.logger.error(f"Erro ao processar coleta: {str(e)}")
            if is_ajax:
                return {'success': False, 'message': 'Erro interno do servidor ao processar a coleta.'}, 500
            flash('Erro interno do servidor ao processar a coleta.', 'error')
            return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))
    
    else:
        # GET - Mostrar formulário
        try:
            detalhes = ColetaService.buscar_detalhes_pedido(pedido_id)
            if not detalhes:
                flash('Pedido não encontrado ou não disponível para coleta', 'error')
                return redirect(url_for('coletas.index'))
            
            cliente_service = ClienteService()
            retirantes_autorizados = cliente_service.listar_retirantes_autorizados(detalhes['cliente'].id)
            return render_template('coletas/processar_coleta.html', detalhes=detalhes, retirantes_autorizados=retirantes_autorizados)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar detalhes do pedido: {str(e)}")
            flash('Erro ao carregar detalhes do pedido', 'error')
            return redirect(url_for('coletas.index'))

@coletas_bp.route('/recibos/status/<job_id>')
@login_obrigatorio
@requires_logistica
def status_recibo(job_id):
    """Acompanha o status de geração do recibo e libera download quando concluído."""
    status_info = get_job_status(job_id)
    
    if status_info.get('status') == 'unavailable':
        flash('Fila de processamento indisponível no momento. Tente novamente mais tarde.', 'warning')
        return redirect(url_for('coletas.index'))
    
    if status_info.get('status') == 'error':
        flash(status_info.get('message', 'Erro ao consultar status do recibo.'), 'error')
        return redirect(url_for('coletas.index'))
    
    if status_info.get('status') == 'finished':
        result = status_info.get('result') or {}
        arquivo_path = result.get('image_path') or result.get('pdf_path')
        if arquivo_path and os.path.exists(arquivo_path):
            return send_file(arquivo_path, mimetype='image/jpeg')
        
        current_app.logger.error(
            "Recibo finalizado, mas arquivo não encontrado",
            extra={"job_id": job_id, "arquivo_path": arquivo_path},
        )
        flash('Recibo finalizado, mas o arquivo não foi localizado no servidor.', 'error')
        return redirect(url_for('coletas.index'))
    
    if status_info.get('status') == 'failed':
        error_message = status_info.get('error') or 'Erro ao gerar recibo.'
        flash(error_message, 'error')
        return redirect(url_for('coletas.index'))
    
    try:
        progress = int(status_info.get('progress', 0))
    except (TypeError, ValueError):
        progress = 0
    stage = status_info.get('stage', 'Processo iniciado')
    
    return render_template(
        'coletas/recibo_processando.html',
        job_id=job_id,
        progress=progress,
        stage=stage,
    )


@coletas_bp.route('/recibos/arquivo/<path:filename>')
@login_obrigatorio
@requires_logistica
def visualizar_recibo(filename):
    """Exibe o recibo gerado em formato JPG."""
    recibos_dir = Path(current_app.instance_path) / 'recibos'
    try:
        safe_dir = recibos_dir.resolve()
        file_path = (safe_dir / filename).resolve()
        file_path.relative_to(safe_dir)
    except (FileNotFoundError, ValueError):
        abort(404)

    if not file_path.exists():
        abort(404)

    return send_file(str(file_path), mimetype='image/jpeg')


@coletas_bp.route('/detalhes/<int:pedido_id>')
@login_obrigatorio
@requires_logistica
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
@requires_logistica
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
@requires_logistica
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
@requires_logistica
def coletar(pedido_id):
    """Rota de compatibilidade - redireciona para processar_coleta"""
    if request.method == 'POST':
        # Redirecionar POST para processar_coleta
        return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id), code=307)
    else:
        # Redirecionar GET para processar_coleta
        return redirect(url_for('coletas.processar_coleta', pedido_id=pedido_id))
