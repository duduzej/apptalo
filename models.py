from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from datetime import datetime
import json
from flask_login import UserMixin

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    
    def set_senha(self, senha):
        self.senha = generate_password_hash(senha)
    
    def check_senha(self, senha):
        return check_password_hash(self.senha, senha)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_previsao_entrega = db.Column(db.DateTime)
    itens = db.Column(db.Text, nullable=False)  # JSON string
    valor_total = db.Column(db.Float, nullable=False)
    observacoes = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    cliente = db.relationship('Cliente', backref='pedidos')
    usuario = db.relationship('Usuario', backref='pedidos')
    
    def __init__(self, **kwargs):
        super(Pedido, self).__init__(**kwargs)
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

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text) 