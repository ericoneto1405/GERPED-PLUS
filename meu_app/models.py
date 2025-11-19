from datetime import datetime
import enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum as EnumType

from . import db

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    fantasia = db.Column(db.String(255))
    endereco = db.Column(db.String(255))
    cidade = db.Column(db.String(100))
    cpf_cnpj = db.Column(db.String(20))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
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
    pedido = db.relationship('Pedido', backref=db.backref('pagamentos', lazy=True))


class ClienteRetiranteAutorizado(db.Model):
    __tablename__ = 'cliente_retirante_autorizado'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(11), nullable=False)
    observacoes = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    data_coleta = db.Column(db.DateTime, default=datetime.utcnow)
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
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    
    # IP do usuário (para auditoria)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 ou IPv6
    
    def __repr__(self):
        return f'<LogAtividade {self.tipo_atividade} - {self.usuario.nome} - {self.data_hora}>'


class Estoque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False, unique=True)
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    conferente = db.Column(db.String(100), nullable=False)
    data_conferencia = db.Column(db.DateTime, default=datetime.utcnow)
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    data_modificacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
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
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice único para ano/mês
    __table_args__ = (db.UniqueConstraint('ano', 'mes', name='uq_ocr_quota_ano_mes'),)
    
    def __repr__(self):
        return f'<OcrQuota {self.mes}/{self.ano}: {self.contador} chamadas>'
