from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from datetime import datetime
import json
from flask_login import UserMixin

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='operacional')  # 'admin' ou 'operacional'
    ativo = db.Column(db.Boolean, default=True)
    pedidos = db.relationship('Pedido', backref='usuario', lazy=True)

    def set_senha(self, senha):
        self.senha = generate_password_hash(senha)
    
    def check_senha(self, senha):
        return check_password_hash(self.senha, senha)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_previsao_entrega = db.Column(db.DateTime)
    status = db.Column(db.String(50), nullable=False, default='Aguardando Pagamento')
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    observacoes = db.Column(db.Text)
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade='all, delete-orphan')

    def calcular_total(self):
        self.valor_total = sum(item.valor_total for item in self.itens)
        return self.valor_total

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    item = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    material = db.Column(db.String(100))
    quantidade = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    data_previsao_entrega = db.Column(db.Date)

    def to_dict(self):
        return {
            'id': self.id,
            'pedido_id': self.pedido_id,
            'item': self.item,
            'descricao': self.descricao,
            'quantidade': self.quantidade,
            'valor_unitario': self.valor_unitario,
            'valor_total': self.valor_total,
            'material': self.material,
            'data_previsao_entrega': self.data_previsao_entrega.strftime('%Y-%m-%d') if self.data_previsao_entrega else None
        }

    def calcular_total(self):
        self.valor_total = self.quantidade * self.valor_unitario
        return self.valor_total

class DadosEmpresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), nullable=False)
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    email = db.Column(db.String(120))
    logo = db.Column(db.String(200))  # Caminho para o arquivo da logo
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @staticmethod
    def get_dados():
        """Retorna os dados da empresa ou cria um registro vazio se não existir"""
        dados = DadosEmpresa.query.first()
        if not dados:
            dados = DadosEmpresa(
                razao_social="",
                cnpj="",
                endereco="",
                telefone="",
                whatsapp="",
                email=""
            )
            db.session.add(dados)
            db.session.commit()
        return dados 