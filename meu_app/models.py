from datetime import datetime, timezone
import enum
import secrets
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum as EnumType

from . import db
from sqlalchemy.exc import SQLAlchemyError


def utcnow():
    """Retorna datetime timezone-aware em UTC."""
    return datetime.now(timezone.utc)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    fantasia = db.Column(db.String(255))
    endereco = db.Column(db.String(255))
    cidade = db.Column(db.String(100))
    cpf_cnpj = db.Column(db.String(20))
    data_cadastro = db.Column(db.DateTime, default=utcnow)
    telefone = db.Column(db.String(20))
    retirantes_autorizados = db.relationship(
        'ClienteRetiranteAutorizado',
        backref='cliente',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    codigo_interno = db.Column(db.String(50))
    categoria = db.Column(db.String(20), default='OUTROS')  # CERVEJA, NAB, OUTROS
    preco_medio_compra = db.Column(db.Numeric(10, 2), default=0.00)
    ean = db.Column(db.String(50))
    preco_atualizado_em = db.Column(db.DateTime, nullable=True)

# ENUMS PARA COLETAS
class StatusColeta(enum.Enum):
    PARCIALMENTE_COLETADO = 'Parcialmente Coletado'
    TOTALMENTE_COLETADO = 'Totalmente Coletado'


class StatusPedido(enum.Enum):
    PENDENTE = 'Pendente'
    PAGAMENTO_APROVADO = 'Pagamento Aprovado'
    COLETA_PARCIAL = 'Coleta Parcial'
    COLETA_CONCLUIDA = 'Coleta Concluída'
    CANCELADO = 'Cancelado'


def enum_values(enum_cls):
    # Retorna apenas os valores legíveis do enum
    return [member.value for member in enum_cls]

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    data = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(
        EnumType(
            StatusPedido,
            values_callable=enum_values,
            native_enum=False
        ),
        default=StatusPedido.PENDENTE
    )
    confirmado_comercial = db.Column(db.Boolean, default=False)  # Novo campo
    confirmado_por = db.Column(db.String(100))  # Novo campo
    data_confirmacao = db.Column(db.DateTime)  # Novo campo
    cliente = db.relationship('Cliente', backref=db.backref('pedidos', lazy=True))
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True)
    
    def calcular_totais(self):
        """
        Calcula totais do pedido de forma centralizada
        Returns:
            dict: Dicionário com total_pedido, total_pago e saldo
        """
        from decimal import Decimal
        
        # Garantir que sempre retorna Decimal para evitar problemas de tipo
        total_pedido = sum((i.valor_total_venda for i in self.itens), Decimal('0'))
        total_pago = sum((p.valor for p in self.pagamentos), Decimal('0'))
        saldo = total_pedido - total_pago
        
        return {
            'total_pedido': float(total_pedido),
            'total_pago': float(total_pago),
            'saldo': float(saldo)
        }
    
    def obter_status_pagamento(self):
        """
        Determina o status do pagamento baseado nos totais
        Returns:
            str: Status do pagamento (Pago, Parcial, Pendente, Sem Valor)
        """
        totais = self.calcular_totais()
        total_pedido = totais['total_pedido']
        total_pago = totais['total_pago']
        
        if total_pedido > 0:
            if total_pago >= total_pedido:
                return 'Pago'
            elif total_pago > 0:
                return 'Parcial'
            else:
                return 'Pendente'
        else:
            return 'Sem Valor'

    def sincronizar_status_financeiro(self, total_pedido=None, total_pago=None):
        """
        Ajusta automaticamente o status financeiro do pedido
        com base nos valores pagos vs. valor total.
        Retorna True se o status foi alterado.
        """
        def _as_decimal(valor):
            if isinstance(valor, Decimal):
                return valor
            if valor is None:
                return Decimal('0')
            return Decimal(str(valor))

        if total_pedido is None or total_pago is None:
            totais = self.calcular_totais()
            total_pedido = _as_decimal(totais['total_pedido'])
            total_pago = _as_decimal(totais['total_pago'])
        else:
            total_pedido = _as_decimal(total_pedido)
            total_pago = _as_decimal(total_pago)

        status_original = self.status
        if self.status == StatusPedido.PENDENTE:
            if total_pedido > Decimal('0') and total_pago >= total_pedido:
                self.status = StatusPedido.PAGAMENTO_APROVADO
        elif self.status == StatusPedido.PAGAMENTO_APROVADO:
            if total_pago < total_pedido:
                self.status = StatusPedido.PENDENTE

        return self.status != status_original


class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_venda = db.Column(db.Numeric(10, 2), nullable=False)
    preco_compra = db.Column(db.Numeric(10, 2), nullable=False)
    valor_total_venda = db.Column(db.Numeric(10, 2), nullable=False)
    valor_total_compra = db.Column(db.Numeric(10, 2), nullable=False)
    lucro_bruto = db.Column(db.Numeric(10, 2), nullable=False)
    produto = db.relationship('Produto')

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_pagamento = db.Column(db.DateTime, default=db.func.current_timestamp())
    metodo_pagamento = db.Column(db.String(255))
    id_transacao = db.Column(db.String(255), unique=True, nullable=True) # ID da transação para evitar duplicidade
    observacoes = db.Column(db.Text, nullable=True)
    caminho_recibo = db.Column(db.String(255), nullable=True)  # Caminho para o arquivo do recibo
    # Metadados do recibo para integridade e deduplicação
    recibo_mime = db.Column(db.String(50), nullable=True)
    recibo_tamanho = db.Column(db.Integer, nullable=True)
    recibo_sha256 = db.Column(db.String(64), unique=True, nullable=True)
    
    # NOVOS CAMPOS - Dados extraídos do comprovante via OCR
    data_comprovante = db.Column(db.Date, nullable=True)  # Data extraída do comprovante
    banco_emitente = db.Column(db.String(100), nullable=True)  # Banco de quem enviou
    agencia_recebedor = db.Column(db.String(20), nullable=True)  # Agência do recebedor
    conta_recebedor = db.Column(db.String(50), nullable=True)  # Conta ou PIX do recebedor
    chave_pix_recebedor = db.Column(db.String(255), nullable=True)  # Chave PIX específica
    
    # Campos OCR existentes (manter compatibilidade)
    ocr_json = db.Column(db.Text, nullable=True)
    ocr_confidence = db.Column(db.Numeric(5, 2), nullable=True)

    @property
    def anexos_extra(self):
        anexos_rel = self._safe_anexos_rel()
        extras_rel = []
        if anexos_rel:
            extras_rel = [anexo.to_dict() for anexo in anexos_rel if not anexo.principal]

        extras_legado = []
        try:
            import json
            data = json.loads(self.ocr_json or "{}")
            extras_legado = data.get("anexos_extra") or []
        except Exception:
            extras_legado = []

        if not extras_rel and not extras_legado:
            return []

        resultado = []
        existentes = set()

        for extra in extras_rel:
            caminho = extra.get('caminho')
            if not caminho:
                continue
            resultado.append(extra)
            existentes.add(caminho)

        for extra in extras_legado:
            caminho = extra.get('caminho')
            if not caminho or caminho in existentes:
                continue
            resultado.append(extra)
            existentes.add(caminho)

        return resultado

    @property
    def anexo_principal(self):
        anexos_rel = self._safe_anexos_rel()
        if anexos_rel:
            for anexo in anexos_rel:
                if anexo.principal:
                    return anexo.to_dict()
            if anexos_rel:
                return anexos_rel[0].to_dict()
        if self.caminho_recibo:
            return {
                'caminho': self.caminho_recibo,
                'mime': self.recibo_mime,
                'tamanho': self.recibo_tamanho,
                'sha256': self.recibo_sha256,
                'principal': True
            }
        return None

    @property
    def todos_anexos(self):
        anexos_rel = self._safe_anexos_rel()
        resultado = []
        if anexos_rel:
            resultado = [anexo.to_dict() for anexo in anexos_rel]
        else:
            principal = self.anexo_principal
            if principal:
                resultado.append(principal)
        extras = self.anexos_extra or []
        if extras:
            existentes = {anexo.get('caminho') for anexo in resultado if anexo.get('caminho')}
            for extra in extras:
                caminho = extra.get('caminho')
                if not caminho or caminho in existentes:
                    continue
                resultado.append(extra)
                existentes.add(caminho)
        return resultado

    def _safe_anexos_rel(self):
        try:
            return list(self.anexos)
        except SQLAlchemyError:
            return []
        except Exception:
            return []

    # Compartilhamento de comprovante
    compartilhado_disponivel = db.Column(db.Boolean, default=False, nullable=False)
    compartilhado_por = db.Column(db.String(120), nullable=True)
    compartilhado_em = db.Column(db.DateTime, nullable=True)
    compartilhado_usado_em = db.Column(db.DateTime, nullable=True)
    compartilhado_destino_pedido_id = db.Column(db.Integer, nullable=True)
    comprovante_compartilhado_origem_id = db.Column(db.Integer, db.ForeignKey('pagamento.id'), nullable=True)
    comprovante_compartilhado_origem = db.relationship(
        'Pagamento',
        remote_side=[id],
        backref='copias_compartilhadas',
        foreign_keys=[comprovante_compartilhado_origem_id]
    )
    pedido = db.relationship('Pedido', backref=db.backref('pagamentos', lazy=True))
    anexos = db.relationship(
        'PagamentoAnexo',
        back_populates='pagamento',
        cascade='all, delete-orphan',
        order_by='PagamentoAnexo.id'
    )


class PagamentoAnexo(db.Model):
    __tablename__ = 'pagamento_anexo'

    id = db.Column(db.Integer, primary_key=True)
    pagamento_id = db.Column(db.Integer, db.ForeignKey('pagamento.id', ondelete='CASCADE'), nullable=False, index=True)
    caminho = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(50), nullable=True)
    tamanho = db.Column(db.Integer, nullable=True)
    sha256 = db.Column(db.String(64), unique=True, nullable=True)
    principal = db.Column(db.Boolean, default=False, nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=True)
    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    pagamento = db.relationship('Pagamento', back_populates='anexos')

    def to_dict(self):
        return {
            'id': self.id,
            'pagamento_id': self.pagamento_id,
            'caminho': self.caminho,
            'mime': self.mime,
            'tamanho': self.tamanho,
            'sha256': self.sha256,
            'principal': self.principal,
            'valor': float(self.valor) if self.valor is not None else None
        }


class CarteiraCredito(db.Model):
    __tablename__ = 'carteira_credito'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False, index=True)
    pedido_origem_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=True)
    pagamento_origem_id = db.Column(db.Integer, db.ForeignKey('pagamento.id'), nullable=True)
    pagamento_anexo_id = db.Column(db.Integer, db.ForeignKey('pagamento_anexo.id'), nullable=True)
    caminho_anexo = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(50), nullable=True)
    tamanho = db.Column(db.Integer, nullable=True)
    sha256 = db.Column(db.String(64), nullable=True)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    saldo_disponivel = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='disponivel', nullable=False)
    criado_por = db.Column(db.String(120), nullable=True)
    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    utilizado_em = db.Column(db.DateTime, nullable=True)
    pedido_destino_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=True)
    pagamento_destino_id = db.Column(db.Integer, db.ForeignKey('pagamento.id'), nullable=True)

    cliente = db.relationship('Cliente', backref=db.backref('creditos_carteira', lazy='dynamic'))
    pedido_origem = db.relationship('Pedido', foreign_keys=[pedido_origem_id])
    pedido_destino = db.relationship('Pedido', foreign_keys=[pedido_destino_id])
    pagamento_origem = db.relationship('Pagamento', foreign_keys=[pagamento_origem_id])
    pagamento_destino = db.relationship('Pagamento', foreign_keys=[pagamento_destino_id])
    anexo = db.relationship('PagamentoAnexo')


class ClienteRetiranteAutorizado(db.Model):
    __tablename__ = 'cliente_retirante_autorizado'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(11), nullable=False)
    observacoes = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=utcnow)
    atualizado_em = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'cpf', name='uq_cliente_retirante_cpf'),
    )

    def cpf_formatado(self) -> str:
        if not self.cpf or len(self.cpf) != 11:
            return self.cpf or ''
        return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"

# NOVOS MODELOS DE COLETA
class Coleta(db.Model):
    """Modelo para registrar coletas de mercadorias"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Relacionamento com pedido
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    
    # Dados da coleta
    data_coleta = db.Column(db.DateTime, default=utcnow)
    responsavel_coleta_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    nome_retirada = db.Column(db.String(100), nullable=False)
    documento_retirada = db.Column(db.String(20), nullable=False)
    
    # STATUS COM ENUM - MUITO MAIS ROBUSTO!
    status = db.Column(
        EnumType(
            StatusColeta,
            values_callable=enum_values,
            native_enum=False
        ),
        nullable=False
    )
    
    # Uploads de documentos
    recibo_assinatura = db.Column(db.String(255), nullable=True)  # Caminho do arquivo
    recibo_documento = db.Column(db.String(255), nullable=True)  # Caminho do arquivo
    
    # Campo opcional
    observacoes = db.Column(db.Text, nullable=True)
    nome_conferente = db.Column(db.String(100), nullable=True)
    cpf_conferente = db.Column(db.String(20), nullable=True)
    
    # Relacionamentos
    pedido = db.relationship('Pedido', backref=db.backref('coletas', lazy=True))
    responsavel_coleta = db.relationship('Usuario', backref=db.backref('coletas_realizadas', lazy=True))
    
    def __repr__(self):
        return f'<Coleta {self.id} - Pedido {self.pedido_id} - Status: {self.status.value}>'

class ItemColetado(db.Model):
    """Modelo para registrar itens coletados em cada coleta"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Relacionamentos
    coleta_id = db.Column(db.Integer, db.ForeignKey('coleta.id'), nullable=False)
    item_pedido_id = db.Column(db.Integer, db.ForeignKey('item_pedido.id'), nullable=False)
    
    # Quantidade coletada nesta coleta específica
    quantidade_coletada = db.Column(db.Integer, nullable=False)
    
    # Relacionamentos
    coleta = db.relationship('Coleta', backref=db.backref('itens_coletados', lazy=True))
    item_pedido = db.relationship('ItemPedido', backref=db.backref('coletas_parciais', lazy=True))
    
    def __repr__(self):
        return f'<ItemColetado {self.id} - Qtd: {self.quantidade_coletada}>'

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    senha_hash = db.Column(db.String(128), nullable=False)  # Renomeado de 'senha' para 'senha_hash'
    tipo = db.Column(db.String(20), nullable=False)  # admin ou comum
    acesso_clientes = db.Column(db.Boolean, default=False)
    acesso_produtos = db.Column(db.Boolean, default=False)
    acesso_pedidos = db.Column(db.Boolean, default=False)
    acesso_financeiro = db.Column(db.Boolean, default=False)
    acesso_logistica = db.Column(db.Boolean, default=False)
    
    def set_senha(self, senha):
        """
        Gera e armazena o hash da senha usando werkzeug.security
        """
        self.senha_hash = generate_password_hash(senha)
    
    def check_senha(self, senha):
        """
        Verifica se a senha fornecida corresponde ao hash armazenado
        """
        return check_password_hash(self.senha_hash, senha)
    
    @property
    def senha(self):
        """
        Propriedade para compatibilidade - NUNCA deve retornar a senha real
        """
        raise AttributeError('Acesso direto à senha não é permitido. Use set_senha() e check_senha()')


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(48))
    expires_at = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False)

    usuario = db.relationship('Usuario', backref=db.backref('reset_tokens', lazy='dynamic'))


class Apuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.Integer, nullable=False)  # 1-12
    ano = db.Column(db.Integer, nullable=False)
    
    # Dados financeiros básicos
    receita_total = db.Column(db.Float, default=0.0)
    custo_produtos = db.Column(db.Float, default=0.0)
    
    # Verbas
    verba_scann = db.Column(db.Float, default=0.0)
    verba_plano_negocios = db.Column(db.Float, default=0.0)
    verba_time_ambev = db.Column(db.Float, default=0.0)
    verba_outras_receitas = db.Column(db.Float, default=0.0)
    
    # Outros custos
    outros_custos = db.Column(db.Float, default=0.0)
    
    # Status da apuração
    definitivo = db.Column(db.Boolean, default=False)  # True = não pode ser editada
    
    # Timestamps
    data_criacao = db.Column(db.DateTime, default=utcnow)
    data_atualizacao = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Relacionamento com usuário que criou
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario = db.relationship('Usuario', backref='apuracoes')
    
    @property
    def total_verbas(self):
        """Calcula o total das verbas"""
        return (self.verba_scann + self.verba_plano_negocios + 
                self.verba_time_ambev + self.verba_outras_receitas)
    
    @property
    def margem_bruta(self):
        """Calcula a margem bruta (Receita - Custo Produtos)"""
        return self.receita_total - self.custo_produtos
    
    @property
    def resultado_liquido(self):
        """Calcula o resultado líquido (Margem Bruta + Total Verbas - Outros Custos)"""
        return self.margem_bruta + self.total_verbas - self.outros_custos
    
    @property
    def percentual_margem(self):
        """Calcula o percentual de margem"""
        if self.receita_total > 0:
            return (self.margem_bruta / self.receita_total) * 100
        return 0
    
    @property
    def mes_nome(self):
        """Retorna o nome do mês"""
        meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        return meses[self.mes] if 1 <= self.mes <= 12 else ''
    
    def __repr__(self):
        return f'<Apuracao {self.mes_nome}/{self.ano}>'

class LogAtividade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete='SET NULL'), nullable=True)  # Pode ser None para atividades do sistema
    usuario = db.relationship('Usuario', backref='atividades')
    
    # Informações da atividade
    tipo_atividade = db.Column(db.String(100), nullable=False)  # Ex: 'Criação de Pedido', 'Aprovação de Pedido', etc.
    titulo = db.Column(db.String(200), nullable=False)  # Título da atividade
    descricao = db.Column(db.Text, nullable=False)  # Descrição detalhada
    modulo = db.Column(db.String(50), nullable=False)  # Módulo onde ocorreu (Pedidos, Clientes, etc.)
    
    # Dados adicionais (JSON para flexibilidade)
    dados_extras = db.Column(db.Text)  # JSON com dados adicionais
    
    # Timestamp
    data_hora = db.Column(db.DateTime, default=utcnow)
    
    # IP do usuário (para auditoria)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 ou IPv6
    
    def __repr__(self):
        return f'<LogAtividade {self.tipo_atividade} - {self.usuario.nome} - {self.data_hora}>'


class Estoque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False, unique=True)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    conferente = db.Column(db.String(100), nullable=False)
    data_conferencia = db.Column(db.DateTime, default=utcnow)
    data_entrada = db.Column(db.DateTime, default=utcnow)
    data_modificacao = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    status = db.Column(db.String(50), nullable=False, default='Contagem')
    
    # Relacionamento com produto
    produto = db.relationship('Produto', backref=db.backref('estoque', lazy=True, uselist=False))
    
    def __repr__(self):
        return f'<Estoque {self.produto.nome}: {self.quantidade}>'


class MovimentacaoEstoque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    tipo_movimentacao = db.Column(db.String(50), nullable=False)  # 'Entrada', 'Saída', 'Ajuste'
    quantidade_anterior = db.Column(db.Integer, nullable=False)
    quantidade_movimentada = db.Column(db.Integer, nullable=False)
    quantidade_atual = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(200), nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    data_movimentacao = db.Column(db.DateTime, default=utcnow)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamento com produto
    produto = db.relationship('Produto', backref=db.backref('movimentacoes', lazy=True))
    
    def __repr__(self):
        return f'<MovimentacaoEstoque {self.produto.nome}: {self.tipo_movimentacao} {self.quantidade_movimentada}>'


class OcrQuota(db.Model):
    """Modelo para controle de quota mensal de OCR"""
    id = db.Column(db.Integer, primary_key=True)
    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)  # 1-12
    contador = db.Column(db.Integer, default=0, nullable=False)
    data_atualizacao = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    
    # Índice único para ano/mês
    __table_args__ = (db.UniqueConstraint('ano', 'mes', name='uq_ocr_quota_ano_mes'),)
    
    def __repr__(self):
        return f'<OcrQuota {self.mes}/{self.ano}: {self.contador} chamadas>'
