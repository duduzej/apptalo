from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .extensions import db, login_manager

class Usuario(UserMixin, db.Model):
    """Modelo para usuários do sistema"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128))
    tipo = db.Column(db.String(20), nullable=False, default='operacional')
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    token_redefinicao = db.Column(db.String(100), unique=True)
    
    # Relacionamentos
    pedidos = db.relationship('Pedido', backref='usuario', lazy=True)
    
    @property
    def senha(self):
        raise AttributeError('senha: atributo apenas para escrita')
    
    @senha.setter
    def senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

class Cliente(db.Model):
    """Modelo para clientes"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.String(200))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)
    
    def __repr__(self):
        return f'<Cliente {self.nome}>'

class Pedido(db.Model):
    """Modelo para pedidos"""
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_previsao_entrega = db.Column(db.DateTime)
    status = db.Column(db.String(50), nullable=False, default='Aguardando Pagamento')
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    observacoes = db.Column(db.Text)
    
    # Relacionamentos
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade='all, delete-orphan')
    
    def calcular_total(self):
        """Calcula o valor total do pedido"""
        self.valor_total = sum(item.quantidade * item.valor_unitario for item in self.itens)
        return self.valor_total
    
    def __repr__(self):
        return f'<Pedido {self.numero}>'

class ItemPedido(db.Model):
    """Modelo para itens do pedido"""
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    item = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200))
    material = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)
    data_previsao_entrega = db.Column(db.DateTime)
    
    @property
    def valor_total(self):
        """Calcula o valor total do item"""
        return self.quantidade * self.valor_unitario
    
    def __repr__(self):
        return f'<ItemPedido {self.item}>'

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário pelo ID para o Flask-Login"""
    return Usuario.query.get(int(user_id)) 