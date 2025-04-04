from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from datetime import datetime
import json
from flask_login import UserMixin

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='operacional')  # 'admin' ou 'operacional'

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_previsao_entrega = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default='Em Aberto')
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.String(200))
    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    item = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)

    def set_senha(self, senha):
        self.senha = generate_password_hash(senha)
    
    def check_senha(self, senha):
        return check_password_hash(self.senha, senha)

    def __init__(self, **kwargs):
        super(ItemPedido, self).__init__(**kwargs)
        self.numero = self.gerar_numero()
    
    def gerar_numero(self):
        ultimo_pedido = Pedido.query.order_by(Pedido.id.desc()).first()
        if ultimo_pedido:
            numero = int(ultimo_pedido.numero) + 1
        else:
            numero = 1
        return f"{numero:04d}"
    
    @property
    def itens(self):
        return json.loads(self._itens)
    
    @itens.setter
    def itens(self, value):
        self._itens = json.dumps(value) 