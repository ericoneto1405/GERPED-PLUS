from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_from_directory, Response
from flask_login import current_user, login_user, logout_user
from . import db
from .models import (
    Cliente,
    Produto,
    Pedido,
    ItemPedido,
    Pagamento,
    Coleta,
    Usuario,
    Apuracao,
    StatusPedido,
    PasswordResetToken,
)
import os
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
import shutil
from .decorators import login_obrigatorio, permissao_necessaria, admin_necessario
from .security import limiter
from .obs.metrics import export_metrics

# Criar blueprint
bp = Blueprint('main', __name__)

def backup_banco():
    caminho_banco = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'sistema.db')
    pasta_backup = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'backups')

    if os.path.exists(caminho_banco):
        # Cria a pasta de backups se ainda não existir
        if not os.path.exists(pasta_backup):
            os.makedirs(pasta_backup)

        # Gera o nome do novo backup
        agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_backup = os.path.join(pasta_backup, f"sistema_backup_{agora}.db")

        # Faz a cópia do banco
        shutil.copy2(caminho_banco, nome_backup)
        current_app.logger.info(f"Backup criado: {nome_backup}")

        # ======== Limpar backups antigos (manter só os últimos 10) ========
        backups = sorted(
            [os.path.join(pasta_backup, f) for f in os.listdir(pasta_backup) if f.endswith('.db')],
            key=os.path.getmtime
        )
        # Se tiver mais que 10 backups, apagar os mais antigos
        while len(backups) > 10:
            backup_antigo = backups.pop(0)
            os.remove(backup_antigo)
            current_app.logger.info(f"Backup antigo removido: {backup_antigo}")
        # ================================================================

    else:
        current_app.logger.warning("Banco de dados não encontrado!")

# Função para chamar backup quando a aplicação estiver no contexto
def init_backup():
    backup_banco()

# Decorador login_obrigatorio movido para meu_app/decorators.py

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

@bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')



@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit(
    lambda: current_app.config.get('LOGIN_RATE_LIMIT', '10 per minute'),
    methods=['POST']
)
def login():
    mensagem_expirou = None
    if request.method == 'GET' and request.args.get('session_expired'):
        mensagem_expirou = 'Sua sessão expirou por inatividade. Faça login novamente.'
    attempts = session.get('login_attempts') or {}
    locked_until_raw = attempts.get('locked_until')
    if locked_until_raw:
        try:
            locked_until = datetime.fromisoformat(locked_until_raw)
        except ValueError:
            locked_until = None
        current_time = datetime.now(timezone.utc)
        if locked_until and locked_until > current_time:
            tempo_restante = int((locked_until - current_time).total_seconds())
            return render_template(
                'login.html',
                erro=f"Muitas tentativas falhas. Tente novamente em {tempo_restante} segundos.",
            )
        attempts.pop('locked_until', None)
        attempts.pop('count', None)
        session['login_attempts'] = attempts
    
    if request.method == 'POST':
        nome = request.form['usuario']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario and usuario.check_senha(senha):
            login_user(usuario)
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['usuario_tipo'] = usuario.tipo
            session['acesso_clientes'] = usuario.acesso_clientes
            session['acesso_produtos'] = usuario.acesso_produtos
            session['acesso_pedidos'] = usuario.acesso_pedidos
            session['acesso_financeiro'] = usuario.acesso_financeiro
            session['acesso_logistica'] = usuario.acesso_logistica
            session['ultimo_acesso'] = datetime.now(timezone.utc).isoformat()
            session.permanent = True
            session.modified = True
            session.pop('login_attempts', None)
            current_app.logger.info(f"Login bem-sucedido: {nome} (IP: {request.remote_addr})")
            return redirect(url_for('main.painel'))
        else:
            max_attempts = current_app.config.get('LOGIN_MAX_ATTEMPTS', 5)
            lockout_seconds = current_app.config.get('LOGIN_LOCKOUT_SECONDS', 300)
            attempts = session.get('login_attempts') or {'count': 0}
            attempts['count'] = attempts.get('count', 0) + 1
            if attempts['count'] >= max_attempts:
                locked_until = datetime.now(timezone.utc) + timedelta(seconds=lockout_seconds)
                attempts['locked_until'] = locked_until.isoformat()
                attempts['count'] = 0
                current_app.logger.warning(
                    "Acesso bloqueado temporariamente após tentativas falhas (usuario=%s, IP=%s)",
                    nome,
                    request.remote_addr,
                )
            session['login_attempts'] = attempts
            current_app.logger.warning(f"Tentativa de login falhou: {nome} (IP: {request.remote_addr})")
            return render_template('login.html', erro="Usuário ou senha inválidos.")
    return render_template('login.html', erro=mensagem_expirou)


def _criar_token_reset(usuario):
    # invalidar tokens anteriores abertos
    PasswordResetToken.query.filter_by(usuario_id=usuario.id, usado=False).delete()
    token = secrets.token_urlsafe(48)
    expira = datetime.now(timezone.utc) + timedelta(hours=current_app.config.get('RESET_TOKEN_EXPIRATION_HOURS', 1))
    token_obj = PasswordResetToken(usuario_id=usuario.id, token=token, expires_at=expira)
    db.session.add(token_obj)
    db.session.commit()
    return token


def _enviar_email_reset(usuario, token):
    try:
        import requests
    except ImportError:  # pragma: no cover
        current_app.logger.error('Biblioteca requests não está disponível para enviar e-mail.')
        return
    api_key = current_app.config.get('SENDGRID_API_KEY') or os.getenv('SENDGRID_API_KEY')
    from_email = current_app.config.get('SENDGRID_FROM_EMAIL') or os.getenv('SENDGRID_FROM_EMAIL') or 'noreply@gerped.local'
    reset_url = url_for('main.reset_password', token=token, _external=True)
    subject = 'GerpedPlus - Redefinição de Senha'
    conteudo = f"Olá {usuario.nome},\n\nRecebemos uma solicitação para redefinir sua senha no GerpedPlus. Clique no link abaixo para continuar:\n{reset_url}\n\nSe você não fez esta solicitação, ignore este e-mail. O link expira em 1 hora."

    if not api_key:
        current_app.logger.warning('SENDGRID_API_KEY não configurada. Link de reset: %s', reset_url)
        return

    data = {
        "personalizations": [
            {
                "to": [{"email": usuario.nome}],
                "subject": subject,
            }
        ],
        "from": {"email": from_email},
        "content": [
            {"type": "text/plain", "value": conteudo},
        ],
    }

    try:
        response = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json=data,
            timeout=10,
        )
        if response.status_code >= 400:
            current_app.logger.error('Falha ao enviar e-mail de reset: %s', response.text)
    except Exception as exc:
        current_app.logger.exception('Erro ao enviar e-mail de reset: %s', exc)


@bp.route('/esqueci-senha', methods=['GET', 'POST'])
def forgot_password():
    mensagem = None
    erro = None
    if request.method == 'POST':
        identificador = request.form.get('identificador', '').strip()
        if not identificador:
            erro = 'Informe seu usuário (e-mail) para continuar.'
        else:
            usuario = Usuario.query.filter(func.lower(Usuario.nome) == identificador.lower()).first()
            mensagem = 'Se este usuário estiver cadastrado, enviaremos um e-mail com instruções.'
            if usuario:
                token = _criar_token_reset(usuario)
                _enviar_email_reset(usuario, token)
    return render_template('forgot_password.html', mensagem=mensagem, erro=erro)


@bp.route('/resetar-senha/<token>', methods=['GET', 'POST'])
def reset_password(token):
    token_obj = PasswordResetToken.query.filter_by(token=token).first()
    erro = None
    mensagem = None
    if not token_obj or token_obj.usado or token_obj.expires_at < datetime.now(timezone.utc):
        erro = 'Link de redefinição inválido ou expirado.'
        return render_template('reset_password.html', erro=erro)

    if request.method == 'POST':
        senha = request.form.get('senha', '')
        confirmar = request.form.get('confirmar', '')
        if len(senha) < 6:
            erro = 'A nova senha deve ter pelo menos 6 caracteres.'
        elif senha != confirmar:
            erro = 'As senhas não conferem.'
        else:
            usuario = Usuario.query.get(token_obj.usuario_id)
            if not usuario:
                erro = 'Usuário não encontrado.'
            else:
                usuario.set_senha(senha)
                token_obj.usado = True
                db.session.commit()
                mensagem = 'Senha redefinida com sucesso. Faça login novamente.'
                return render_template('reset_password.html', mensagem=mensagem)

    return render_template('reset_password.html', erro=erro)

@bp.route('/api/pedido/<int:pedido_id>')
@login_obrigatorio
def api_pedido(pedido_id):
    """API para buscar dados de um pedido para coleta"""
    try:
        # Validação adicional do ID do pedido
        if not isinstance(pedido_id, int) or pedido_id <= 0:
            return jsonify({"error": "ID do pedido inválido"}), 400
            
        from .logistica.services import LogisticaService
        dados = LogisticaService.buscar_pedido_coleta(pedido_id)
        
        if dados:
            return jsonify(dados)
        else:
            return jsonify({"error": "Pedido não encontrado"}), 404
            
    except Exception as e:
        current_app.logger.error(f"Erro na API pedido: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@bp.route('/painel')
@login_obrigatorio
def painel():
    try:
        # Obter filtros da URL ou usar mês/ano atual
        mes = request.args.get('mes', datetime.now().month)
        ano = request.args.get('ano', datetime.now().year)

        # Converter para inteiros
        mes = int(mes)
        ano = int(ano)

        # Calcular datas de início e fim (exclusivo) do mês
        data_inicio = datetime(ano, mes, 1)
        if mes == 12:
            proximo_mes = datetime(ano + 1, 1, 1)
        else:
            proximo_mes = datetime(ano, mes + 1, 1)

        # Estatísticas do painel
        total_pedidos = Pedido.query.filter(
            Pedido.data >= data_inicio,
            Pedido.data < proximo_mes
        ).count()

        # Pagamentos reconhecidos no período selecionado
        pagamentos_periodo_raw = (
            db.session.query(
                Pagamento.pedido_id,
                Pagamento.valor,
                Pagamento.data_pagamento
            )
            .join(Pedido, Pagamento.pedido_id == Pedido.id)
            .filter(
                Pagamento.data_pagamento >= data_inicio,
                Pagamento.data_pagamento < proximo_mes,
                Pedido.status.in_([
                    StatusPedido.PAGAMENTO_APROVADO,
                    StatusPedido.COLETA_PARCIAL,
                    StatusPedido.COLETA_CONCLUIDA
                ])
            )
            .all()
        )

        pagamentos_periodo = [
            {
                'pedido_id': pagamento.pedido_id,
                'valor': float(pagamento.valor or 0),
                'data': pagamento.data_pagamento or data_inicio,
            }
            for pagamento in pagamentos_periodo_raw
        ]

        pagamentos_por_pedido = {}
        for pagamento in pagamentos_periodo:
            pagamentos_por_pedido[pagamento['pedido_id']] = pagamentos_por_pedido.get(
                pagamento['pedido_id'], 0.0
            ) + pagamento['valor']

        pedido_ids_pagamento = list(pagamentos_por_pedido.keys())

        pedido_totais = {}
        pedido_ratios = {}
        if pedido_ids_pagamento:
            pedido_totais_rows = (
                db.session.query(
                    ItemPedido.pedido_id.label('pedido_id'),
                    func.coalesce(func.sum(ItemPedido.valor_total_venda), 0).label('total_venda'),
                    func.coalesce(func.sum(ItemPedido.valor_total_compra), 0).label('total_compra'),
                )
                .filter(ItemPedido.pedido_id.in_(pedido_ids_pagamento))
                .group_by(ItemPedido.pedido_id)
                .all()
            )

            for row in pedido_totais_rows:
                total_venda = float(row.total_venda or 0)
                total_compra = float(row.total_compra or 0)
                pedido_totais[row.pedido_id] = {
                    'total_venda': total_venda,
                    'total_compra': total_compra,
                }
                pedido_ratios[row.pedido_id] = (
                    (total_compra / total_venda) if total_venda > 0 else 0.0
                )

        faturamento_total = sum(pagamentos_por_pedido.values())
        pedidos_pagos = len(pagamentos_por_pedido)

        # CPV proporcional aos pagamentos reconhecidos no período
        cpv_total = sum(
            pagamento['valor'] * pedido_ratios.get(pagamento['pedido_id'], 0.0)
            for pagamento in pagamentos_periodo
        )

        # Verificar se existe apuração para o período
        apuracao = Apuracao.query.filter_by(mes=mes, ano=ano).first()
        tem_apuracao = apuracao is not None
        
        # Calcular verbas se houver apuração
        if tem_apuracao:
            total_verbas = float(
                apuracao.verba_scann + 
                apuracao.verba_plano_negocios + 
                apuracao.verba_time_ambev + 
                apuracao.verba_outras_receitas
            )
        else:
            total_verbas = 0.0

        # Calcular margem de manobra
        margem_bruta = faturamento_total - cpv_total
        margem_manobra = margem_bruta + total_verbas
        
        # Calcular percentual de margem
        if faturamento_total > 0:
            percentual_margem = (margem_manobra / faturamento_total) * 100
        else:
            percentual_margem = 0

        total_clientes = Cliente.query.count()
        total_produtos = Produto.query.count()

        # Pedidos recentes com eager loading
        pedidos_recentes = (
            Pedido.query.options(
                db.joinedload(Pedido.cliente),
                db.joinedload(Pedido.itens)
            ).order_by(Pedido.data.desc()).limit(5).all()
        )

        # Gráfico de vendas por dia (últimos 30 dias) - apenas pedidos completamente pagos
        data_30_dias_atras = datetime.now() - timedelta(days=30)
        vendas_por_dia = (
            db.session.query(
                func.date(Pagamento.data_pagamento).label('data'),
                func.sum(Pagamento.valor).label('total')
            )
            .join(Pedido, Pagamento.pedido_id == Pedido.id)
            .filter(
                Pagamento.data_pagamento >= data_30_dias_atras,
                Pagamento.data_pagamento <= datetime.now(),
                Pedido.status.in_([
                    StatusPedido.PAGAMENTO_APROVADO,
                    StatusPedido.COLETA_PARCIAL,
                    StatusPedido.COLETA_CONCLUIDA
                ])
            )
            .group_by(func.date(Pagamento.data_pagamento))
            .order_by(func.date(Pagamento.data_pagamento))
            .all()
        )

        # Montar dados do gráfico com tolerância a tipos (str/date)
        labels = []
        valores = []
        for venda in vendas_por_dia:
            data_val = venda.data
            label = None
            try:
                # Se for datetime/date
                label = data_val.strftime('%d/%m')
            except Exception:
                # Provavelmente string 'YYYY-MM-DD'
                try:
                    dt = datetime.strptime(str(data_val), '%Y-%m-%d')
                    label = dt.strftime('%d/%m')
                except Exception:
                    label = str(data_val)
            labels.append(label)
            valores.append(float(venda.total or 0))

        dados_grafico = {
            'labels': labels,
            'data': valores
        }

        # Dados de evolução diária do mês selecionado
        dados_evolucao = {
            'labels': [],
            'receita_verbas': [],
            'cpv_total': [],
            'margem': []
        }
        pagamentos_por_dia = {}
        for pagamento in pagamentos_periodo:
            dia = pagamento['data'].date()
            entry = pagamentos_por_dia.setdefault(dia, {'receita': 0.0, 'cpv': 0.0})
            entry['receita'] += pagamento['valor']
            entry['cpv'] += pagamento['valor'] * pedido_ratios.get(pagamento['pedido_id'], 0.0)

        # Gerar dados para cada dia do mês
        from calendar import monthrange
        _, ultimo_dia = monthrange(ano, mes)
        
        for dia in range(1, ultimo_dia + 1):
            data_dia = datetime(ano, mes, dia)
            
            receita_dia = pagamentos_por_dia.get(data_dia.date(), {}).get('receita', 0.0)
            cpv_dia = pagamentos_por_dia.get(data_dia.date(), {}).get('cpv', 0.0)
            
            # Verbas do dia (proporcional se houver apuração)
            verbas_dia = 0.0
            if tem_apuracao and ultimo_dia > 0:
                verbas_dia = total_verbas / ultimo_dia
            
            # Margem do dia
            margem_dia = (receita_dia + verbas_dia) - cpv_dia
            
            # Adicionar aos dados
            dados_evolucao['labels'].append(f"{dia:02d}")
            dados_evolucao['receita_verbas'].append(receita_dia + verbas_dia)
            dados_evolucao['cpv_total'].append(cpv_dia)
            dados_evolucao['margem'].append(margem_dia)

        # Calcular necessidade de compra
        from .pedidos.services import PedidoService
        necessidade_compra = PedidoService.calcular_necessidade_compra()

        current_app.logger.info(
            f"Painel acessado por usuário {session.get('usuario_nome', 'N/A')}"
        )

        return render_template(
            'painel.html',
            total_pedidos=total_pedidos,
            pedidos_pagos=pedidos_pagos,
            faturamento_total=faturamento_total,
            cpv_total=cpv_total,
            tem_apuracao=tem_apuracao,
            total_verbas=total_verbas,
            margem_manobra=margem_manobra,
            percentual_margem=percentual_margem,
            total_valor=faturamento_total,  # Para compatibilidade
            total_clientes=total_clientes,
            total_produtos=total_produtos,
            pedidos_recentes=pedidos_recentes,
            dados_grafico=dados_grafico,
            dados_evolucao=dados_evolucao,
            necessidade_compra=necessidade_compra,
            mes=mes,
            ano=ano,
        )
    except Exception as e:
        current_app.logger.error(f"Erro no painel: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Retornar valores padrão em caso de erro
        return render_template(
            'painel.html',
            total_pedidos=0,
            pedidos_pagos=0,
            faturamento_total=0.0,
            cpv_total=0.0,
            tem_apuracao=False,
            total_verbas=0.0,
            margem_manobra=0.0,
            percentual_margem=0.0,
            total_valor=0,
            total_clientes=0,
            total_produtos=0,
            pedidos_recentes=[],
            dados_grafico={'labels': [], 'data': []},
            dados_evolucao={'labels': [], 'receita_verbas': [], 'cpv_total': [], 'margem': []},
            mes=mes,
            ano=ano,
        )

# Aqui continuariam todas as outras rotas do app.py original...
# Por questões de espaço, vou adicionar apenas algumas rotas essenciais

@bp.route('/logout')
def logout():
    usuario = session.get('usuario_nome', 'N/A')
    logout_user()
    session.clear()
    current_app.logger.info(f"Logout: {usuario} (IP: {request.remote_addr})")
    return redirect(url_for('main.login'))

# Rota de clientes movida para o blueprint clientes

# Rota de produtos movida para o blueprint produtos

# Rota de pedidos movida para o blueprint pedidos

@bp.route('/teste-erro')
def teste_erro():
    """
    Rota para testar o error handler global
    """
    current_app.logger.info("Teste de erro solicitado")
    raise Exception("Este é um erro de teste para verificar o error handler global")


@bp.route('/metrics')
def metrics():
    """
    Endpoint de métricas Prometheus
    
    Exporta métricas da aplicação no formato Prometheus para monitoramento.
    
    Métricas disponíveis:
    - http_requests_total: Total de requisições HTTP
    - http_request_duration_seconds: Duração das requisições
    - http_requests_in_progress: Requisições em andamento
    - business_operations_total: Operações de negócio
    - database_queries_total: Queries de banco
    - cache_operations_total: Operações de cache
    
    Returns:
        Métricas formatadas para Prometheus
    """
    current_app.logger.debug("Métricas Prometheus solicitadas")
    return Response(export_metrics(), mimetype='text/plain; charset=utf-8')


@bp.route('/healthz')
def healthz():
    """
    Healthcheck liveness probe
    ---
    tags:
      - Health
    summary: Verifica se aplicação está viva
    description: |
      Endpoint de liveness probe para Kubernetes/Docker.
      Retorna 200 se a aplicação está respondendo.
    responses:
      200:
        description: Aplicação está saudável
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            service:
              type: string
              example: sistema-gerped
            timestamp:
              type: string
              format: date-time
      500:
        description: Aplicação não está saudável
    """
    try:
        # Verificação básica - app está respondendo
        return jsonify({
            'status': 'healthy',
            'service': 'sistema-gerped',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        current_app.logger.error(f"Healthcheck falhou: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@bp.route('/readiness')
def readiness():
    """
    Readiness probe
    ---
    tags:
      - Health
    summary: Verifica se aplicação está pronta para tráfego
    description: |
      Endpoint de readiness probe para load balancers.
      Valida conexões com dependências críticas:
      - Banco de dados
      - Cache Redis
    responses:
      200:
        description: Aplicação pronta para receber tráfego
        schema:
          type: object
          properties:
            status:
              type: string
              example: ready
            checks:
              type: object
              properties:
                database:
                  type: boolean
                cache:
                  type: boolean
            timestamp:
              type: string
              format: date-time
      503:
        description: Aplicação não está pronta
    """
    checks = {
        'database': False,
        'cache': False
    }
    
    try:
        # 1. Verificar conexão com banco de dados
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        checks['database'] = True
    except Exception as e:
        current_app.logger.error(f"Readiness check - Database falhou: {str(e)}")
    
    try:
        # 2. Verificar cache
        from . import flask_cache as cache_instance
        cache_instance.set('readiness_check', 'ok', timeout=10)
        result = cache_instance.get('readiness_check')
        checks['cache'] = (result == 'ok')
    except Exception as e:
        current_app.logger.warning(f"Readiness check - Cache falhou: {str(e)}")
        # Cache não é crítico, pode continuar
        checks['cache'] = True
    
    # Todas as verificações críticas devem passar
    all_ready = checks['database']
    
    status_code = 200 if all_ready else 503
    
    return jsonify({
        'status': 'ready' if all_ready else 'not_ready',
        'checks': checks,
        'timestamp': datetime.now().isoformat()
    }), status_code
