from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, grey, lightgrey
from io import BytesIO
import os
from decimal import Decimal
import pdfkit
import json
from sqlalchemy.sql import func, text
import sys
import logging
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from models import Usuario, Cliente, Pedido, ItemPedido, DadosEmpresa
from database import db
from werkzeug.utils import secure_filename
import stripe

# Criar a aplicação Flask
app = Flask(__name__)

# Configurações
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pedidos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['STATIC_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['STATIC_FOLDER'], 'logos')

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'seu-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'sua-senha-de-app'
app.config['MAIL_DEFAULT_SENDER'] = 'seu-email@gmail.com'

# Configuração do Stripe
stripe.api_key = 'sua-chave-secreta-do-stripe'
STRIPE_PRICES = {
    'mensal': 'price_1234567890',
    'anual': 'price_0987654321'
}

# Inicialização de extensões
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Configuração do logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Classes de formulário
class RecuperarSenhaForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email é obrigatório'),
        Email(message='Email inválido')
    ])
    submit = SubmitField('Enviar Link de Recuperação')

class RedefinirSenhaForm(FlaskForm):
    nova_senha = PasswordField('Nova Senha', validators=[
        DataRequired(message='Nova senha é obrigatória'),
        Length(min=6, message='A senha deve ter pelo menos 6 caracteres')
    ])
    confirmar_senha = PasswordField('Confirmar Nova Senha', validators=[
        DataRequired(message='Confirmação de senha é obrigatória'),
        EqualTo('nova_senha', message='As senhas devem ser iguais')
    ])
    submit = SubmitField('Redefinir Senha')

# Configuração do ambiente
if os.environ.get('FLASK_ENV') == 'production':
    # Configuração para o Render.com
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pedidos.db'
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-padrao-nao-usar-em-producao')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = False
else:
    # Configuração para desenvolvimento local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pedidos.db'
    app.config['SECRET_KEY'] = 'chave-desenvolvimento'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True

# Configuração do e-mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465  # Alterado para porta SSL
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True  # Usando SSL em vez de TLS
app.config['MAIL_USERNAME'] = 'eduardojbarbalho@gmail.com'
app.config['MAIL_PASSWORD'] = 'yvxe yvxw yvxz yvxk'
app.config['MAIL_DEFAULT_SENDER'] = 'eduardojbarbalho@gmail.com'
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# Configuração do Login Manager
login_manager.login_view = 'login'

# Configuração do Stripe
stripe.api_key = 'sua_chave_secreta_stripe'

# Preços do Stripe (você precisará criar estes produtos/preços no dashboard do Stripe)
STRIPE_PRICES = {
    'price_mensal': 'price_xxxxx',  # Substitua pelo ID do preço mensal
    'price_anual': 'price_yyyyy'    # Substitua pelo ID do preço anual
}

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20))
    interesse = db.Column(db.String(50))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

def init_app():
    with app.app_context():
        try:
            logger.info("Criando tabelas do banco de dados...")
            db.create_all()
            
            # Criar usuário admin se não existir
            admin = Usuario.query.filter_by(email='admin@admin.com').first()
            if not admin:
                logger.info("Criando usuário admin...")
                admin = Usuario(
                    nome='Administrador',
                    email='admin@admin.com',
                    senha=generate_password_hash('admin123'),
                    tipo='admin',
                    ativo=True
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Usuário admin criado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {str(e)}")
            raise

# Inicializar o aplicativo
init_app()

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro 500: {str(error)}")
    return render_template('500.html'), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rotas de autenticação
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        tipo = request.form.get('tipo', 'operacional')  # Define 'operacional' como padrão
        
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado!')
            return redirect(url_for('registro'))
        
        usuario = Usuario(
            nome=nome,
            email=email,
            tipo=tipo,
            ativo=True
        )
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
        
        flash('Registro realizado com sucesso!')
        return redirect(url_for('login'))
    
    return render_template('registro.html')

@app.route('/')
def landing():
    if current_user.is_authenticated:
        if current_user.tipo == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('operacional_dashboard'))
    return render_template('landing/index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.tipo == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('operacional_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.check_senha(senha):
            if not usuario.ativo:
                flash('Usuário inativo. Entre em contato com o administrador.', 'danger')
                return redirect(url_for('login'))
            
            login_user(usuario)
            if usuario.tipo == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('operacional_dashboard'))
        
        flash('Email ou senha inválidos.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rotas de pedidos
@app.route('/pedido/novo', methods=['GET', 'POST'])
@login_required
def novo_pedido():
    if request.method == 'POST':
        data_previsao = request.form.get('data_previsao_entrega')
        data_previsao_entrega = datetime.strptime(data_previsao, '%Y-%m-%d') if data_previsao else None
        
        pedido = Pedido(
            numero=gerar_numero_pedido(),
            data_previsao_entrega=data_previsao_entrega,
            usuario_id=current_user.id
        )
        db.session.add(pedido)
        db.session.commit()
        
        # Processar itens do pedido
        itens = request.form.getlist('item[]')
        descricoes = request.form.getlist('descricao[]')
        quantidades = request.form.getlist('quantidade[]')
        valores = request.form.getlist('valor_unitario[]')
        
        for i in range(len(itens)):
            if itens[i].strip():  # Só adiciona se o item não estiver vazio
                item = ItemPedido(
                    pedido_id=pedido.id,
                    item=itens[i],
                    descricao=descricoes[i],
                    material=valores[i],
                    quantidade=int(quantidades[i]),
                    valor_unitario=float(valores[i].replace(',', '.'))
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Pedido cadastrado com sucesso!')
        return redirect(url_for('lista_pedidos'))
    
    return render_template('formulario_pedido.html')

@app.route('/pedido/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_pedido(id):
    pedido = Pedido.query.get_or_404(id)
    if pedido.usuario_id != current_user.id:
        flash('Você não tem permissão para editar este pedido!')
        return redirect(url_for('lista_pedidos'))
    
    if request.method == 'POST':
        pedido.numero = request.form.get('numero')
        pedido.data_previsao_entrega = datetime.strptime(request.form.get('data_previsao_entrega'), '%Y-%m-%d') if request.form.get('data_previsao_entrega') else None
        pedido.status = request.form.get('status')
        pedido.observacoes = request.form.get('observacoes')
        
        # Remover itens existentes
        for item in pedido.itens:
            db.session.delete(item)
        
        # Adicionar novos itens
        itens = request.form.getlist('item[]')
        descricoes = request.form.getlist('descricao[]')
        quantidades = request.form.getlist('quantidade[]')
        valores = request.form.getlist('valor_unitario[]')
        
        for i in range(len(itens)):
            if itens[i].strip():
                item = ItemPedido(
                    pedido_id=pedido.id,
                    item=itens[i],
                    descricao=descricoes[i],
                    material=valores[i],
                    quantidade=int(quantidades[i]),
                    valor_unitario=float(valores[i].replace(',', '.'))
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Pedido atualizado com sucesso!')
        return redirect(url_for('lista_pedidos'))
    
    return render_template('formulario_pedido.html', pedido=pedido)

@app.route('/pedido/excluir/<int:id>')
@login_required
def excluir_pedido(id):
    pedido = Pedido.query.get_or_404(id)
    if pedido.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir este pedido!')
        return redirect(url_for('lista_pedidos'))
    
    db.session.delete(pedido)
    db.session.commit()
    flash('Pedido excluído com sucesso!')
    return redirect(url_for('lista_pedidos'))

@app.route('/pedido/pdf/<int:id>')
@login_required
def exportar_pdf(id):
    try:
        pedido = Pedido.query.get_or_404(id)
        if pedido.usuario_id != current_user.id:
            flash('Você não tem permissão para exportar este pedido!')
            return redirect(url_for('lista_pedidos'))
        
        # Criar um buffer de memória para o PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Adicionar cabeçalho da empresa
        adicionar_cabecalho_empresa(elements, styles)
        
        # Título do pedido
        elements.append(Paragraph("Talão de Pedido", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=12
        )))
        
        # Informações do pedido
        pedido_info = []
        pedido_info.append(Paragraph(f"Número do Pedido: {pedido.numero}", styles['Normal']))
        pedido_info.append(Paragraph(f"Cliente: {pedido.cliente.nome}", styles['Normal']))
        pedido_info.append(Paragraph(f"Telefone: {pedido.cliente.telefone or 'Não informado'}", styles['Normal']))
        pedido_info.append(Paragraph(f"Endereço: {pedido.cliente.endereco or 'Não informado'}", styles['Normal']))
        pedido_info.append(Paragraph(f"Data do Pedido: {pedido.data_pedido.strftime('%d/%m/%Y')}", styles['Normal']))
        if pedido.data_previsao_entrega:
            pedido_info.append(Paragraph(f"Previsão de Entrega: {pedido.data_previsao_entrega.strftime('%d/%m/%Y')}", styles['Normal']))
        pedido_info.append(Paragraph(f"Criado por: {pedido.usuario.nome}", styles['Normal']))
        
        elements.extend(pedido_info)
        elements.append(Spacer(1, 12))
        
        # Tabela de itens
        elements.append(Paragraph("Itens do Pedido", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6
        )))
        
        # Cabeçalho da tabela
        data = [['Item', 'Descrição', 'Qtd', 'Valor Unit.', 'Valor Total']]
        
        # Itens
        for item in pedido.itens:
            data.append([
                item.item,
                item.descricao,
                str(item.quantidade),
                f"R$ {item.valor_unitario:.2f}",
                f"R$ {item.valor_total:.2f}"
            ])
        
        # Criar tabela
        table = Table(data, colWidths=[80, 200, 50, 80, 80])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#808080')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        # Total do pedido
        elements.append(Paragraph(f"Total do Pedido: R$ {pedido.valor_total:.2f}", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=2
        )))
        
        # Rodapé
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=HexColor('#808080'),
                alignment=1
            )
        ))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'pedido_{pedido.numero}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Erro ao gerar PDF: {str(e)}")
        flash('Erro ao gerar PDF do pedido.', 'danger')
        return redirect(url_for('lista_pedidos'))

@app.route('/pedido/visualizar/<int:id>')
@login_required
def visualizar_pedido(id):
    pedido = Pedido.query.get_or_404(id)
    if pedido.usuario_id != current_user.id:
        flash('Você não tem permissão para visualizar este pedido!')
        return redirect(url_for('lista_pedidos'))
    return render_template('visualizar_pedido.html', pedido=pedido, datetime=datetime)

def gerar_numero_pedido():
    # Pega o último pedido
    ultimo_pedido = Pedido.query.order_by(Pedido.id.desc()).first()
    
    # Se não houver pedidos, começa do 1
    if not ultimo_pedido:
        return f"PED{datetime.now().year}0001"
    
    # Extrai o número do último pedido
    ultimo_numero = int(ultimo_pedido.numero[7:])
    novo_numero = ultimo_numero + 1
    
    # Gera o novo número no formato PED20240001
    return f"PED{datetime.now().year}{novo_numero:04d}"

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    # Obter o período do filtro (padrão: mês atual)
    periodo = request.args.get('periodo', 'mes')
    hoje = datetime.now()
    
    if periodo == 'dia':
        data_inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'semana':
        data_inicio = hoje - timedelta(days=hoje.weekday())
        data_inicio = data_inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # mes
        data_inicio = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Estatísticas gerais
    total_pedidos = Pedido.query.count()
    pedidos_em_aberto = Pedido.query.filter_by(status='Em Aberto').count()
    pedidos_em_producao = Pedido.query.filter_by(status='Em Produção').count()
    pedidos_entregues = Pedido.query.filter_by(status='Entregue').count()
    pedidos_cancelados = Pedido.query.filter_by(status='Cancelado').count()
    
    # Pedidos atrasados
    pedidos_atrasados = Pedido.query.filter(
        Pedido.data_previsao_entrega < hoje,
        Pedido.status.in_(['Em Aberto', 'Em Produção'])
    ).all()
    
    # Pedidos recentes
    pedidos_recentes = Pedido.query.order_by(Pedido.data_pedido.desc()).limit(10).all()
    
    # Dados para o gráfico de tendência
    datas = []
    contagem = []
    data_atual = data_inicio
    
    while data_atual <= hoje:
        datas.append(data_atual.strftime('%d/%m/%Y'))
        count = Pedido.query.filter(
            Pedido.data_pedido >= data_atual,
            Pedido.data_pedido < data_atual + timedelta(days=1)
        ).count()
        contagem.append(count)
        data_atual += timedelta(days=1)
    
    return render_template('admin/dashboard.html',
                         total_pedidos=total_pedidos,
                         pedidos_em_aberto=pedidos_em_aberto,
                         pedidos_em_producao=pedidos_em_producao,
                         pedidos_entregues=pedidos_entregues,
                         pedidos_cancelados=pedidos_cancelados,
                         pedidos_atrasados=pedidos_atrasados,
                         pedidos_recentes=pedidos_recentes,
                         datas_pedidos=datas,
                         contagem_pedidos=contagem)

@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@login_required
def admin_novo_usuario():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        tipo = request.form.get('tipo')
        
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado!', 'danger')
            return redirect(url_for('admin_novo_usuario'))
        
        usuario = Usuario(
            nome=nome,
            email=email,
            tipo=tipo,
            ativo=True
        )
        usuario.set_senha(senha)
        
        db.session.add(usuario)
        db.session.commit()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('admin_usuarios'))
    
    return render_template('admin/novo_usuario.html')

@app.route('/admin/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def admin_editar_usuario(id):
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.nome = request.form.get('nome')
        usuario.email = request.form.get('email')
        usuario.tipo = request.form.get('tipo')
        
        senha = request.form.get('senha')
        if senha:  # Só atualiza a senha se foi fornecida
            usuario.set_senha(senha)
        
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin_usuarios'))
    
    return render_template('admin/editar_usuario.html', usuario=usuario)

@app.route('/admin/usuarios/<int:id>/toggle', methods=['POST'])
@login_required
def admin_toggle_usuario(id):
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    usuario = Usuario.query.get_or_404(id)
    usuario.ativo = not usuario.ativo
    db.session.commit()
    
    return jsonify({'status': 'success', 'ativo': usuario.ativo})

@app.route('/operacional/dashboard')
@login_required
def operacional_dashboard():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    # Buscar todos os pedidos do usuário atual
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.data_pedido.desc()).all()
    
    # Calcular estatísticas
    pedidos_aguardando_pagamento = Pedido.query.filter_by(
        usuario_id=current_user.id,
        status='Aguardando Pagamento'
    ).count()
    
    pedidos_aguardando_arte = Pedido.query.filter_by(
        usuario_id=current_user.id,
        status='Aguardando Aprovação da Arte'
    ).count()
    
    pedidos_em_producao = Pedido.query.filter_by(
        usuario_id=current_user.id,
        status='Em Produção'
    ).count()
    
    pedidos_entregues = Pedido.query.filter_by(
        usuario_id=current_user.id,
        status='Entregue'
    ).count()
    
    # Pedidos atrasados (com data de previsão menor que hoje e não entregues)
    pedidos_atrasados = Pedido.query.filter(
        Pedido.usuario_id == current_user.id,
        Pedido.data_previsao_entrega < datetime.now(),
        Pedido.status.in_(['Em Aberto', 'Em Produção'])
    ).count()
    
    return render_template('operacional/dashboard.html',
                         pedidos=pedidos,
                         pedidos_aguardando_pagamento=pedidos_aguardando_pagamento,
                         pedidos_aguardando_arte=pedidos_aguardando_arte,
                         pedidos_em_producao=pedidos_em_producao,
                         pedidos_entregues=pedidos_entregues,
                         pedidos_atrasados=pedidos_atrasados)

@app.route('/operacional/clientes')
@login_required
def operacional_clientes():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    clientes = Cliente.query.all()
    return render_template('operacional/lista_clientes.html', clientes=clientes)

@app.route('/operacional/clientes/novo', methods=['GET', 'POST'])
@login_required
def operacional_novo_cliente():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    if request.method == 'POST':
        cliente = Cliente(
            nome=request.form['nome'],
            email=request.form['email'],
            telefone=request.form['telefone'],
            endereco=request.form['endereco']
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect(url_for('operacional_clientes'))
    
    return render_template('operacional/formulario_cliente.html')

@app.route('/operacional/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def operacional_editar_cliente(id):
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        cliente.nome = request.form['nome']
        cliente.email = request.form['email']
        cliente.telefone = request.form['telefone']
        cliente.endereco = request.form['endereco']
        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('operacional_clientes'))
    
    return render_template('operacional/formulario_cliente.html', cliente=cliente)

@app.route('/operacional/clientes/<int:id>')
@login_required
def operacional_visualizar_cliente(id):
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    cliente = Cliente.query.get_or_404(id)
    return render_template('operacional/visualizar_cliente.html', cliente=cliente)

@app.route('/operacional/pedidos')
@login_required
def operacional_pedidos():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    return redirect(url_for('operacional_dashboard'))

@app.route('/operacional/pedidos/novo', methods=['GET', 'POST'])
@login_required
def operacional_novo_pedido():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        data_previsao = request.form.get('data_previsao_entrega')
        observacoes = request.form.get('observacoes')
        
        # Converte a data de previsão
        data_previsao_entrega = datetime.strptime(data_previsao, '%Y-%m-%d') if data_previsao else None
        
        # Cria o pedido
        pedido = Pedido(
            numero=gerar_numero_pedido(),
            cliente_id=cliente_id,
            data_pedido=datetime.now(),
            data_previsao_entrega=data_previsao_entrega,
            status='Aguardando Pagamento',
            usuario_id=current_user.id,
            observacoes=observacoes,
            valor_total=0.0  # Inicializa com zero
        )
        
        db.session.add(pedido)
        db.session.commit()
        
        # Processar itens do pedido
        itens = request.form.getlist('item[]')
        materiais = request.form.getlist('material[]')
        descricoes = request.form.getlist('descricao[]')
        quantidades = request.form.getlist('quantidade[]')
        valores_unitarios = request.form.getlist('valor_unitario[]')
        
        valor_total_pedido = 0
        for i in range(len(itens)):
            if itens[i].strip():  # Só adiciona se o item não estiver vazio
                quantidade = float(quantidades[i])
                valor_unitario = float(valores_unitarios[i].replace(',', '.'))
                
                item = ItemPedido(
                    pedido_id=pedido.id,
                    item=itens[i],
                    material=materiais[i],
                    descricao=descricoes[i],
                    quantidade=quantidade,
                    valor_unitario=valor_unitario
                )
                item.calcular_total()  # Calcula o valor total do item
                valor_total_pedido += item.valor_total
                db.session.add(item)
        
        # Atualiza o valor total do pedido
        pedido.valor_total = valor_total_pedido
        db.session.commit()
        
        flash('Pedido criado com sucesso!', 'success')
        return redirect(url_for('operacional_dashboard'))
    
    clientes = Cliente.query.all()
    return render_template('operacional/novo_pedido.html', clientes=clientes)

@app.route('/operacional/pedidos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def operacional_editar_pedido(id):
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    pedido = Pedido.query.get_or_404(id)
    
    if request.method == 'POST':
        pedido.cliente_id = request.form.get('cliente_id')
        pedido.data_previsao_entrega = datetime.strptime(request.form.get('data_previsao_entrega'), '%Y-%m-%d') if request.form.get('data_previsao_entrega') else None
        pedido.observacoes = request.form.get('observacoes')
        
        # Remover itens existentes
        for item in pedido.itens:
            db.session.delete(item)
        
        # Adicionar novos itens
        itens = request.form.getlist('item[]')
        descricoes = request.form.getlist('descricao[]')
        quantidades = request.form.getlist('quantidade[]')
        valores = request.form.getlist('valor_unitario[]')
        
        for i in range(len(itens)):
            if itens[i].strip():  # Só adiciona se o item não estiver vazio
                item = ItemPedido(
                    pedido_id=pedido.id,
                    item=itens[i],
                    descricao=descricoes[i],
                    quantidade=int(quantidades[i]),
                    valor_unitario=float(valores[i].replace(',', '.'))
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Pedido atualizado com sucesso!', 'success')
        return redirect(url_for('operacional_pedidos'))
    
    clientes = Cliente.query.all()
    return render_template('operacional/formulario_pedido.html', pedido=pedido, clientes=clientes)

@app.route('/operacional/pedidos/<int:id>/visualizar')
@login_required
def operacional_visualizar_pedido(id):
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    pedido = Pedido.query.get_or_404(id)
    if pedido.usuario_id != current_user.id:
        flash('Você não tem permissão para visualizar este pedido!', 'danger')
        return redirect(url_for('operacional_pedidos'))
        
    return render_template('operacional/visualizar_pedido.html', pedido=pedido)

@app.route('/operacional/pedidos/<int:id>/pdf')
@login_required
def operacional_exportar_pdf(id):
    try:
        pedido = Pedido.query.get_or_404(id)
        if pedido.usuario_id != current_user.id:
            flash('Você não tem permissão para exportar este pedido!')
            return redirect(url_for('operacional_pedidos'))
        
        # Criar um buffer de memória para o PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Adicionar cabeçalho da empresa
        adicionar_cabecalho_empresa(elements, styles)
        
        # Título do pedido
        elements.append(Paragraph("Talão de Pedido", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=12
        )))
        
        # Informações do pedido
        pedido_info = []
        pedido_info.append(Paragraph(f"Número do Pedido: {pedido.numero}", styles['Normal']))
        pedido_info.append(Paragraph(f"Cliente: {pedido.cliente.nome}", styles['Normal']))
        pedido_info.append(Paragraph(f"Telefone: {pedido.cliente.telefone or 'Não informado'}", styles['Normal']))
        pedido_info.append(Paragraph(f"Endereço: {pedido.cliente.endereco or 'Não informado'}", styles['Normal']))
        pedido_info.append(Paragraph(f"Data do Pedido: {pedido.data_pedido.strftime('%d/%m/%Y')}", styles['Normal']))
        if pedido.data_previsao_entrega:
            pedido_info.append(Paragraph(f"Previsão de Entrega: {pedido.data_previsao_entrega.strftime('%d/%m/%Y')}", styles['Normal']))
        pedido_info.append(Paragraph(f"Criado por: {pedido.usuario.nome}", styles['Normal']))
        
        elements.extend(pedido_info)
        elements.append(Spacer(1, 12))
        
        # Tabela de itens
        elements.append(Paragraph("Itens do Pedido", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6
        )))
        
        # Cabeçalho da tabela
        data = [['Item', 'Descrição', 'Qtd', 'Valor Unit.', 'Valor Total']]
        
        # Itens
        for item in pedido.itens:
            data.append([
                item.item,
                item.descricao,
                str(item.quantidade),
                f"R$ {item.valor_unitario:.2f}",
                f"R$ {item.valor_total:.2f}"
            ])
        
        # Criar tabela
        table = Table(data, colWidths=[80, 200, 50, 80, 80])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#808080')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        # Total do pedido
        elements.append(Paragraph(f"Total do Pedido: R$ {pedido.valor_total:.2f}", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=2
        )))
        
        # Rodapé
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=HexColor('#808080'),
                alignment=1
            )
        ))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'pedido_{pedido.numero}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Erro ao gerar PDF: {str(e)}")
        flash('Erro ao gerar PDF do pedido.', 'danger')
        return redirect(url_for('operacional_pedidos'))

@app.route('/admin/clientes')
@login_required
def admin_clientes():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    clientes = Cliente.query.all()
    return render_template('admin/clientes.html', clientes=clientes)

@app.route('/admin/clientes/novo', methods=['GET', 'POST'])
@login_required
def admin_novo_cliente():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        endereco = request.form.get('endereco')
        
        cliente = Cliente(
            nome=nome,
            email=email,
            telefone=telefone,
            endereco=endereco
        )
        
        db.session.add(cliente)
        db.session.commit()
        
        flash('Cliente criado com sucesso!', 'success')
        return redirect(url_for('admin_clientes'))
    
    return render_template('admin/novo_cliente.html')

@app.route('/admin/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def admin_editar_cliente(id):
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        cliente.nome = request.form.get('nome')
        cliente.email = request.form.get('email')
        cliente.telefone = request.form.get('telefone')
        cliente.endereco = request.form.get('endereco')
        
        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('admin_clientes'))
    
    return render_template('admin/editar_cliente.html', cliente=cliente)

@app.route('/admin/clientes/<int:id>')
@login_required
def admin_visualizar_cliente(id):
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    cliente = Cliente.query.get_or_404(id)
    return render_template('admin/visualizar_cliente.html', cliente=cliente)

@app.route('/operacional/pedidos/<int:id>/status', methods=['POST'])
@login_required
def operacional_alterar_status_pedido(id):
    if current_user.tipo != 'operacional':
        return jsonify({'status': 'error', 'message': 'Acesso não autorizado!'}), 403
    
    pedido = Pedido.query.get_or_404(id)
    if pedido.usuario_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Você não tem permissão para alterar este pedido!'}), 403
    
    data = request.get_json()
    novo_status = data.get('status')
    
    # Validar o status
    status_validos = [
        'Aguardando Pagamento',
        'Aguardando aprovação da arte',
        'Em Aberto',
        'Em Produção',
        'Entregue',
        'Cancelado'
    ]
    if novo_status not in status_validos:
        return jsonify({'status': 'error', 'message': 'Status inválido!'}), 400
    
    # Atualizar o status
    pedido.status = novo_status
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Status atualizado com sucesso!',
        'novo_status': novo_status
    })

@app.route('/admin/relatorios/pedidos')
@login_required
def admin_relatorio_pedidos():
    if current_user.tipo != 'admin':
        return jsonify({'status': 'error', 'message': 'Acesso não autorizado!'}), 403
    
    # Obter parâmetros do relatório
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    status = request.args.get('status')
    
    # Converter datas
    try:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d') if data_inicio else datetime.now().replace(day=1)
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else datetime.now()
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Formato de data inválido!'}), 400
    
    # Construir query base
    query = Pedido.query.filter(Pedido.data_pedido.between(data_inicio, data_fim))
    
    # Filtrar por status se especificado
    if status:
        query = query.filter_by(status=status)
    
    # Buscar pedidos
    pedidos = query.order_by(Pedido.data_pedido.desc()).all()
    
    # Criar PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Adicionar cabeçalho da empresa
    adicionar_cabecalho_empresa(elements, styles)
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )
    
    # Adicionar título
    titulo = f"Relatório de Pedidos - {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
    if status:
        titulo += f" - Status: {status}"
    elements.append(Paragraph(titulo, title_style))
    
    # Adicionar resumo
    resumo_style = ParagraphStyle(
        'Resumo',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20
    )
    
    total_valor = sum(pedido.valor_total for pedido in pedidos)
    resumo = f"""
    Total de Pedidos: {len(pedidos)}
    Valor Total: R$ {total_valor:.2f}
    """
    elements.append(Paragraph(resumo, resumo_style))
    elements.append(Spacer(1, 20))
    
    # Criar tabela de pedidos
    data = [['Número', 'Cliente', 'Data', 'Status', 'Valor']]
    for pedido in pedidos:
        data.append([
            pedido.numero,
            pedido.cliente.nome,
            pedido.data_pedido.strftime('%d/%m/%Y'),
            pedido.status,
            f"R$ {pedido.valor_total:.2f}"
        ])
    
    # Estilo da tabela
    table = Table(data, colWidths=[80, 200, 80, 100, 80])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#808080')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(table)
    
    # Adicionar rodapé
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#808080'),
        alignment=1
    )
    elements.append(Spacer(1, 30))
    
    now = datetime.now()
    footer_text = f"Relatório gerado por {current_user.nome} em {now.strftime('%d/%m/%Y às %H:%M:%S')} | TaloApp"
    elements.append(Paragraph(footer_text, footer_style))
    
    # Gerar PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Preparar resposta
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    
    # Nome do arquivo
    filename = f"relatorio_pedidos_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}"
    if status:
        filename += f"_{status.lower().replace(' ', '_')}"
    filename += ".pdf"
    
    response.headers['Content-Disposition'] = f'inline; filename={filename}'
    return response

@app.route('/admin/relatorios')
@login_required
def admin_relatorios():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    return render_template('admin/relatorios.html', hoje=datetime.now())

@app.route('/operacional/pedidos/<int:id>/excluir', methods=['POST'])
@login_required
def operacional_excluir_pedido(id):
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    pedido = Pedido.query.get_or_404(id)
    
    # Verificar se o pedido pertence ao usuário atual
    if pedido.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir este pedido!', 'danger')
        return redirect(url_for('operacional_pedidos'))
    
    # Excluir o pedido (os itens serão excluídos automaticamente devido ao cascade)
    db.session.delete(pedido)
    db.session.commit()
    
    flash('Pedido excluído com sucesso!', 'success')
    return redirect(url_for('operacional_pedidos'))

@app.route('/admin/relatorios/pedidos/visualizar')
@login_required
def admin_visualizar_relatorio_pedidos():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    # Obter parâmetros do relatório
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Converter datas
    try:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d') if data_inicio else datetime.now().replace(day=1)
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else datetime.now()
        # Ajustar data_fim para incluir todo o dia
        data_fim = data_fim.replace(hour=23, minute=59, second=59)
    except ValueError:
        flash('Formato de data inválido!', 'danger')
        return redirect(url_for('admin_relatorios'))
    
    # Construir query base
    query = Pedido.query
    
    # Aplicar filtros
    query = query.filter(Pedido.data_pedido >= data_inicio)
    query = query.filter(Pedido.data_pedido <= data_fim)
    
    # Buscar pedidos
    pedidos = query.order_by(Pedido.data_pedido.desc()).all()
    
    # Calcular estatísticas
    valor_total = sum(pedido.valor_total for pedido in pedidos)
    valor_medio = valor_total / len(pedidos) if pedidos else 0
    
    # Contar pedidos atrasados
    hoje = datetime.now()
    pedidos_atrasados = sum(1 for p in pedidos if p.data_previsao_entrega and p.data_previsao_entrega < hoje and p.status in ['Em Aberto', 'Em Produção'])
    
    # Debug para verificar os parâmetros
    print(f"Data Início: {data_inicio}")
    print(f"Data Fim: {data_fim}")
    
    return render_template('admin/visualizar_relatorio_pedidos.html',
                         pedidos=pedidos,
                         data_inicio=data_inicio.strftime('%Y-%m-%d'),
                         data_fim=data_fim.strftime('%Y-%m-%d'),
                         data_inicio_formatada=data_inicio.strftime('%d/%m/%Y'),
                         data_fim_formatada=data_fim.strftime('%d/%m/%Y'),
                         valor_total=valor_total,
                         valor_medio=valor_medio,
                         pedidos_atrasados=pedidos_atrasados)

@app.route('/admin/relatorios/clientes')
@login_required
def admin_relatorio_clientes():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('landing'))

    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    # Query base para clientes com pedidos
    query = db.session.query(
        Cliente,
        func.count(Pedido.id).label('total_pedidos'),
        func.sum(Pedido.valor_total).label('valor_total'),
        func.max(Pedido.data_pedido).label('ultimo_pedido')
    ).outerjoin(Pedido)

    # Aplicar filtros de data se fornecidos
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        query = query.filter(Pedido.data_pedido >= data_inicio)
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
        query = query.filter(Pedido.data_pedido <= data_fim)

    # Agrupar por cliente
    resultados = query.group_by(Cliente.id).all()

    # Processar resultados
    clientes_data = []
    total_pedidos = 0
    total_valor = 0

    for cliente, total_ped, valor_total, ultimo_pedido in resultados:
        # Calcular status predominante
        status_query = db.session.query(
            Pedido.status,
            func.count(Pedido.status).label('count')
        ).filter(
            Pedido.cliente_id == cliente.id
        ).group_by(Pedido.status).order_by(text('count DESC')).first()

        status_predominante = status_query[0] if status_query else None
        valor_total = valor_total or 0
        ticket_medio = valor_total / total_ped if total_ped > 0 else 0

        cliente_dict = {
            'nome': cliente.nome,
            'telefone': cliente.telefone,
            'total_pedidos': total_ped,
            'valor_total': valor_total,
            'ultimo_pedido': ultimo_pedido,
            'status_predominante': status_predominante,
            'ticket_medio': ticket_medio
        }
        clientes_data.append(cliente_dict)
        total_pedidos += total_ped
        total_valor += valor_total

    ticket_medio_geral = total_valor / total_pedidos if total_pedidos > 0 else 0

    return render_template(
        'admin/relatorio_clientes.html',
        clientes=clientes_data,
        total_pedidos=total_pedidos,
        total_valor=total_valor,
        ticket_medio_geral=ticket_medio_geral
    )

@app.route('/admin/relatorios/clientes/pdf')
@login_required
def exportar_relatorio_clientes_pdf():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('landing'))

    try:
        # Criar um buffer para o PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        elements = []

        # Estilos
        styles = getSampleStyleSheet()
        
        # Adicionar cabeçalho da empresa
        adicionar_cabecalho_empresa(elements, styles)
        
        # Título do relatório
        elements.append(Paragraph("Relatório de Clientes", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=12
        )))
        
        # Dados da tabela
        data = [['Nome', 'Telefone', 'Endereço', 'Total Pedidos', 'Valor Total', 'Último Pedido', 'Status Predominante', 'Ticket Médio']]
        
        # Obter dados dos clientes
        query = db.session.query(
            Cliente,
            func.count(Pedido.id).label('total_pedidos'),
            func.sum(Pedido.valor_total).label('valor_total'),
            func.max(Pedido.data_pedido).label('ultimo_pedido')
        ).outerjoin(Pedido).group_by(Cliente.id).all()

        for cliente, total_ped, valor_total, ultimo_pedido in query:
            status_query = db.session.query(
                Pedido.status,
                func.count(Pedido.status).label('count')
            ).filter(
                Pedido.cliente_id == cliente.id
            ).group_by(Pedido.status).order_by(text('count DESC')).first()

            status_predominante = status_query[0] if status_query else 'N/A'
            valor_total = valor_total or 0
            ticket_medio = valor_total / total_ped if total_ped > 0 else 0

            data.append([
                cliente.nome,
                cliente.telefone or 'N/A',
                cliente.endereco or 'N/A',
                str(total_ped),
                f'R$ {valor_total:.2f}',
                ultimo_pedido.strftime('%d/%m/%Y') if ultimo_pedido else 'N/A',
                status_predominante,
                f'R$ {ticket_medio:.2f}'
            ])

        # Criar tabela
        table = Table(data, colWidths=[120, 80, 150, 60, 80, 80, 100, 80])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#808080')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F0F0F0')]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Rodapé
        elements.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=HexColor('#808080'),
                alignment=1
            )
        ))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'relatorio_clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Erro ao gerar relatório de clientes: {str(e)}")
        flash('Erro ao gerar relatório de clientes.', 'danger')
        return redirect(url_for('admin_relatorio_clientes'))

@app.route('/admin/pedidos')
@login_required
def admin_pedidos():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    # Buscar todos os pedidos de todos os usuários
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    return render_template('admin/pedidos.html', pedidos=pedidos)

@app.route('/admin/pedidos/<int:id>/excluir', methods=['POST'])
@login_required
def admin_excluir_pedido(id):
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    pedido = Pedido.query.get_or_404(id)
    
    # Excluir o pedido e seus itens
    db.session.delete(pedido)
    db.session.commit()
    
    flash('Pedido excluído com sucesso!', 'success')
    return redirect(url_for('admin_pedidos'))

@app.route('/admin/pedidos/excluir-multiplos', methods=['POST'])
@login_required
def admin_excluir_multiplos_pedidos():
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    data = request.get_json()
    pedidos_ids = data.get('pedidos', [])
    
    try:
        # Excluir os pedidos selecionados
        Pedido.query.filter(Pedido.id.in_(pedidos_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'message': 'Pedidos excluídos com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir pedidos'}), 500

@app.route('/admin/pedidos/excluir-todos', methods=['POST'])
@login_required
def admin_excluir_todos_pedidos():
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    try:
        # Excluir todos os pedidos
        Pedido.query.delete()
        db.session.commit()
        return jsonify({'message': 'Todos os pedidos foram excluídos com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir pedidos'}), 500

def enviar_email_recuperacao(email):
    token = serializer.dumps(email, salt='recuperar-senha')
    link = url_for('redefinir_senha', token=token, _external=True)
    
    msg = Message('Recuperação de Senha',
                 sender=app.config['MAIL_USERNAME'],
                 recipients=[email])
    msg.body = f'''Para redefinir sua senha, acesse o link abaixo:

{link}

Se você não solicitou a redefinição de senha, ignore este email.

O link expira em 1 hora.
'''
    try:
        logger.info(f"Tentando enviar email para {email}")
        mail.send(msg)
        logger.info(f"Email enviado com sucesso para {email}")
        return True
    except Exception as e:
        logger.error(f"Erro detalhado ao enviar email: {str(e)}")
        logger.error(f"Tipo do erro: {type(e)}")
        return False

@app.route('/esqueceu-senha', methods=['GET', 'POST'])
def esqueceu_senha():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    form = RecuperarSenhaForm()
    if form.validate_on_submit():
        email = form.email.data
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario:
            if enviar_email_recuperacao(email):
                flash('Um email com instruções para redefinir sua senha foi enviado.', 'info')
                return redirect(url_for('login'))
            else:
                flash('Erro ao enviar email. Por favor, tente novamente mais tarde.', 'danger')
        else:
            flash('Email não encontrado.', 'danger')
    
    return render_template('esqueceu_senha.html', form=form)

@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    try:
        email = serializer.loads(token, salt='recuperar-senha', max_age=3600)  # 1 hora
    except:
        flash('O link de recuperação é inválido ou expirou.', 'danger')
        return redirect(url_for('esqueceu_senha'))
    
    form = RedefinirSenhaForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.senha = generate_password_hash(form.nova_senha.data)
            db.session.commit()
            flash('Sua senha foi alterada com sucesso!', 'success')
            return redirect(url_for('login'))
    
    return render_template('redefinir_senha.html', form=form)

@app.route('/admin/minha-conta', methods=['GET', 'POST'])
@login_required
def admin_minha_conta():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    dados = DadosEmpresa.get_dados()
    
    if request.method == 'POST':
        dados.razao_social = request.form.get('razao_social')
        dados.cnpj = request.form.get('cnpj')
        dados.endereco = request.form.get('endereco')
        dados.telefone = request.form.get('telefone')
        dados.whatsapp = request.form.get('whatsapp')
        dados.email = request.form.get('email')
        
        # Processar o upload da logo
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo.filename != '':
                # Validar tipo de arquivo
                allowed_extensions = {'png', 'jpg', 'jpeg'}
                if '.' not in logo.filename or logo.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                    flash('Tipo de arquivo não permitido. Use apenas PNG, JPG ou JPEG.', 'danger')
                    return redirect(url_for('admin_minha_conta'))
                
                # Validar tamanho do arquivo (2MB)
                if len(logo.read()) > 2 * 1024 * 1024:
                    flash('Arquivo muito grande. O tamanho máximo permitido é 2MB.', 'danger')
                    return redirect(url_for('admin_minha_conta'))
                logo.seek(0)  # Resetar o ponteiro do arquivo
                
                # Criar diretório para logos se não existir
                logo_dir = os.path.join(app.static_folder, 'logos')
                if not os.path.exists(logo_dir):
                    os.makedirs(logo_dir)
                
                # Salvar arquivo
                filename = secure_filename(logo.filename)
                logo_path = os.path.join('logos', filename)
                full_path = os.path.join(app.static_folder, logo_path)
                logo.save(full_path)
                print(f"Logo salva em: {full_path}")
                
                # Se já existia uma logo, remover a antiga
                if dados.logo:
                    old_logo_path = os.path.normpath(os.path.join(app.static_folder, dados.logo))
                    if os.path.exists(old_logo_path):
                        try:
                            os.remove(old_logo_path)
                            print(f"Logo antiga removida: {old_logo_path}")
                        except Exception as e:
                            print(f"Erro ao remover logo antiga: {str(e)}")
                
                dados.logo = logo_path
        
        db.session.commit()
        flash('Dados da empresa atualizados com sucesso!', 'success')
        return redirect(url_for('admin_minha_conta'))
    
    return render_template('admin/minha_conta.html', dados=dados)

@app.route('/admin/remover-logo')
@login_required
def admin_remover_logo():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('landing'))
    
    dados = DadosEmpresa.get_dados()
    if dados.logo:
        # Remover arquivo da logo
        logo_path = os.path.normpath(os.path.join(app.static_folder, dados.logo))
        print(f"Tentando remover logo do caminho: {logo_path}")
        
        if os.path.exists(logo_path):
            try:
                os.remove(logo_path)
                print("Logo removida com sucesso")
            except Exception as e:
                print(f"Erro ao remover logo: {str(e)}")
                flash('Erro ao remover logo.', 'danger')
                return redirect(url_for('admin_minha_conta'))
        
        # Atualizar banco de dados
        dados.logo = None
        db.session.commit()
        flash('Logo removida com sucesso!', 'success')
    else:
        flash('Não há logo para remover.', 'info')
    
    return redirect(url_for('admin_minha_conta'))

def adicionar_cabecalho_empresa(elements, styles):
    """Adiciona o cabeçalho com dados da empresa ao PDF"""
    try:
        dados = DadosEmpresa.get_dados()
        if not dados or not dados.razao_social:
            print("Dados da empresa não encontrados")
            return
        
        header_data = []
        
        # Adicionar logo se existir
        if dados.logo:
            try:
                # Normalizar o caminho da logo
                logo_path = os.path.normpath(os.path.join(app.static_folder, dados.logo))
                print(f"Tentando carregar logo do caminho: {logo_path}")
                
                if os.path.exists(logo_path):
                    img = Image(logo_path)
                    img.drawHeight = 0.5*inch
                    img.drawWidth = 0.5*inch
                    header_data.append([img])
                    print("Logo carregada com sucesso")
                else:
                    print(f"Arquivo da logo não encontrado em: {logo_path}")
            except Exception as e:
                print(f"Erro ao carregar a logo: {str(e)}")
        
        # Dados da empresa com fonte menor
        empresa_info = []
        try:
            empresa_info.append(Paragraph(dados.razao_social, ParagraphStyle(
                'CustomTitle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            )))
            
            if dados.cnpj:
                empresa_info.append(Paragraph(f"CNPJ: {dados.cnpj}", ParagraphStyle(
                    'CustomText',
                    parent=styles['Normal'],
                    fontSize=8,
                    spaceAfter=2
                )))
            
            if dados.endereco:
                empresa_info.append(Paragraph(dados.endereco, ParagraphStyle(
                    'CustomText',
                    parent=styles['Normal'],
                    fontSize=8,
                    spaceAfter=2
                )))
            
            if dados.telefone or dados.whatsapp:
                contatos = []
                if dados.telefone:
                    contatos.append(f"Tel: {dados.telefone}")
                if dados.whatsapp:
                    contatos.append(f"WhatsApp: {dados.whatsapp}")
                empresa_info.append(Paragraph(" | ".join(contatos), ParagraphStyle(
                    'CustomText',
                    parent=styles['Normal'],
                    fontSize=8,
                    spaceAfter=2
                )))
            
            if dados.email:
                empresa_info.append(Paragraph(dados.email, ParagraphStyle(
                    'CustomText',
                    parent=styles['Normal'],
                    fontSize=8,
                    spaceAfter=2
                )))
        except Exception as e:
            print(f"Erro ao criar informações da empresa: {str(e)}")
            return
        
        header_data.append(empresa_info)
        
        # Criar tabela do cabeçalho com linhas menores
        header_table = Table([header_data], colWidths=[50, '*'])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 10))  # Reduzindo o espaço após o cabeçalho
    except Exception as e:
        print(f"Erro ao adicionar cabeçalho da empresa: {str(e)}")

@app.route('/criar-checkout-session', methods=['POST'])
def criar_checkout_session():
    price_id = request.form.get('price_id')
    stripe_price_id = STRIPE_PRICES.get(price_id)
    
    if not stripe_price_id:
        flash('Plano inválido', 'error')
        return redirect(url_for('landing'))

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('sucesso_pagamento', _external=True),
            cancel_url=url_for('landing', _external=True),
        )
        return redirect(checkout_session.url)
    except Exception as e:
        flash('Erro ao processar pagamento', 'error')
        return redirect(url_for('landing'))

@app.route('/sucesso-pagamento')
def sucesso_pagamento():
    flash('Pagamento processado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/capturar-lead', methods=['POST'])
def capturar_lead():
    try:
        novo_lead = Lead(
            nome=request.form['nome'],
            email=request.form['email'],
            telefone=request.form.get('telefone'),
            interesse=request.form.get('interesse')
        )
        db.session.add(novo_lead)
        db.session.commit()
        
        # Enviar e-mail de boas-vindas
        msg = Message(
            'Bem-vindo ao TaloApp!',
            sender='seu-email@dominio.com',
            recipients=[novo_lead.email]
        )
        msg.body = f"""
        Olá {novo_lead.nome},
        
        Obrigado por se interessar pelo TaloApp! 
        Em breve nossa equipe entrará em contato.
        
        Atenciosamente,
        Equipe TaloApp
        """
        mail.send(msg)
        
        flash('Obrigado pelo interesse! Em breve entraremos em contato.', 'success')
    except Exception as e:
        flash('Erro ao processar sua solicitação. Tente novamente.', 'error')
    
    return redirect(url_for('landing'))

@app.route('/admin/relatorios/pedidos/pdf')
@login_required
def exportar_relatorio_pedidos_pdf():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('landing'))

    try:
        # Obter parâmetros do relatório
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        status = request.args.get('status')
        
        # Criar query base
        query = Pedido.query
        
        # Aplicar filtros
        if data_inicio:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Pedido.data_pedido >= data_inicio)
        
        if data_fim:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(Pedido.data_pedido <= data_fim)
        
        if status:
            query = query.filter(Pedido.status == status)
        
        # Executar query
        pedidos = query.all()
        
        # Criar um buffer para o PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Adicionar cabeçalho da empresa
        adicionar_cabecalho_empresa(elements, styles)
        
        # Título do relatório
        elements.append(Paragraph("Relatório de Pedidos", ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=12
        )))
        
        # Período do relatório
        periodo = []
        if data_inicio:
            periodo.append(f"De: {data_inicio.strftime('%d/%m/%Y')}")
        if data_fim:
            periodo.append(f"Até: {data_fim.strftime('%d/%m/%Y')}")
        if status:
            periodo.append(f"Status: {status}")
        
        if periodo:
            elements.append(Paragraph(" | ".join(periodo), styles['Normal']))
            elements.append(Spacer(1, 12))
        
        # Resumo
        total_valor = sum(p.valor_total for p in pedidos)
        resumo = f"""
        Total de Pedidos: {len(pedidos)}
        Valor Total: R$ {total_valor:.2f}
        """
        elements.append(Paragraph(resumo, ParagraphStyle(
            'CustomText',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=12
        )))
        
        # Dados da tabela
        data = [['Número', 'Cliente', 'Data', 'Status', 'Valor Total', 'Usuário']]
        
        for pedido in pedidos:
            data.append([
                pedido.numero,
                pedido.cliente.nome,
                pedido.data_pedido.strftime('%d/%m/%Y'),
                pedido.status,
                f"R$ {pedido.valor_total:.2f}",
                pedido.usuario.nome
            ])
        
        # Criar tabela
        table = Table(data, colWidths=[80, 150, 80, 100, 80, 100])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#808080')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Rodapé
        elements.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=HexColor('#808080'),
                alignment=1
            )
        ))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Nome do arquivo
        filename = f"relatorio_pedidos_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}"
        if status:
            filename += f"_{status.lower().replace(' ', '_')}"
        filename += ".pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Erro ao gerar relatório de pedidos: {str(e)}")
        flash('Erro ao gerar relatório de pedidos.', 'danger')
        return redirect(url_for('admin_relatorio_pedidos'))

if __name__ == '__main__':
    if os.environ.get('FLASK_ENV') == 'production':
        app.run()
    else:
        app.run(debug=True) 