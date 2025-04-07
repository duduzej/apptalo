from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from io import BytesIO
import os
from decimal import Decimal
import pdfkit
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, grey, lightgrey
from sqlalchemy.sql import func, text
import sys
import logging
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from models import Usuario, Cliente, Pedido, ItemPedido
from database import db

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

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Inicialização do banco de dados
db.init_app(app)

# Configuração do Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.check_senha(senha):
            if not usuario.ativo:
                flash('Usuário inativo. Entre em contato com o administrador.', 'danger')
                return redirect(url_for('login'))
            
            login_user(usuario)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        
        flash('Email ou senha inválidos.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rotas de pedidos
@app.route('/')
@login_required
def index():
    if current_user.tipo == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('operacional_dashboard'))

@app.route('/')
@login_required
def lista_pedidos():
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.data_pedido.desc()).all()
    return render_template('lista_pedidos.html', pedidos=pedidos)

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
    pedido = Pedido.query.get_or_404(id)
    if pedido.usuario_id != current_user.id:
        flash('Você não tem permissão para exportar este pedido!')
        return redirect(url_for('lista_pedidos'))
    
    # Criar um buffer de memória para o PDF
    buffer = BytesIO()
    
    # Criar o PDF
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Adicionar conteúdo ao PDF usando fontes padrão
    p.setFont("Times-Bold", 16)
    p.drawString(1*inch, 10*inch, "Talão de Pedido")
    
    p.setFont("Times-Bold", 12)
    p.drawString(1*inch, 9*inch, "Informações do Pedido:")
    
    p.setFont("Times-Roman", 12)
    p.drawString(1*inch, 8.5*inch, f"Número do Pedido: {pedido.numero}")
    p.drawString(1*inch, 8*inch, f"Cliente: {pedido.cliente.nome}")
    p.drawString(1*inch, 7.5*inch, f"Telefone: {pedido.cliente.telefone or 'Não informado'}")
    p.drawString(1*inch, 7*inch, f"Endereço: {pedido.cliente.endereco or 'Não informado'}")
    p.drawString(1*inch, 6.5*inch, f"Data do Pedido: {pedido.data_pedido.strftime('%d/%m/%Y')}")
    if pedido.data_previsao_entrega:
        p.drawString(1*inch, 6*inch, f"Previsão de Entrega: {pedido.data_previsao_entrega.strftime('%d/%m/%Y')}")
        y_start = 5.5*inch
    else:
        y_start = 6*inch
    p.drawString(1*inch, y_start, f"Criado por: {pedido.usuario.nome}")
    
    # Adicionar tabela de itens
    p.setFont("Times-Bold", 12)
    p.drawString(1*inch, y_start - 0.5*inch, "Itens do Pedido:")
    
    # Cabeçalho da tabela
    y_position = y_start - 1*inch
    p.setFont("Times-Bold", 10)
    p.drawString(1*inch, y_position, "Item")
    p.drawString(2.5*inch, y_position, "Descrição")
    p.drawString(4.5*inch, y_position, "Qtd")
    p.drawString(5.5*inch, y_position, "Valor Unit.")
    p.drawString(6.5*inch, y_position, "Valor Total")
    
    # Linha separadora
    y_position -= 0.2*inch
    p.line(1*inch, y_position, 7.5*inch, y_position)
    y_position -= 0.2*inch
    
    # Itens
    p.setFont("Times-Roman", 10)
    for item in pedido.itens:
        if y_position < 1*inch:  # Se não houver espaço, criar nova página
            p.showPage()
            p.setFont("Times-Roman", 10)
            y_position = 10*inch
        
        p.drawString(1*inch, y_position, str(item.item)[:20])
        p.drawString(2.5*inch, y_position, str(item.descricao)[:30])
        p.drawString(4.5*inch, y_position, str(item.quantidade))
        p.drawString(5.5*inch, y_position, f"R$ {item.valor_unitario:.2f}")
        p.drawString(6.5*inch, y_position, f"R$ {item.valor_total:.2f}")
        y_position -= 0.3*inch
    
    # Linha separadora
    y_position -= 0.2*inch
    p.line(1*inch, y_position, 7.5*inch, y_position)
    y_position -= 0.3*inch
    
    # Total do pedido
    p.setFont("Times-Bold", 12)
    p.drawString(5*inch, y_position, "Total do Pedido:")
    p.drawString(6.5*inch, y_position, f"R$ {pedido.valor_total:.2f}")
    
    # Adicionar rodapé
    p.setFont("Times-Roman", 8)
    p.drawString(1*inch, 0.5*inch, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    p.save()
    
    # Preparar o buffer para leitura
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'pedido_{pedido.numero}.pdf',
        mimetype='application/pdf'
    )

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
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@login_required
def admin_novo_usuario():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
    # Buscar todos os pedidos do usuário atual
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.data_pedido.desc()).all()
    
    # Calcular estatísticas
    pedidos_em_aberto = Pedido.query.filter_by(
        usuario_id=current_user.id,
        status='Em Aberto'
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
                         pedidos_em_aberto=pedidos_em_aberto,
                         pedidos_em_producao=pedidos_em_producao,
                         pedidos_entregues=pedidos_entregues,
                         pedidos_atrasados=pedidos_atrasados)

@app.route('/operacional/clientes')
@login_required
def operacional_clientes():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    clientes = Cliente.query.all()
    return render_template('operacional/lista_clientes.html', clientes=clientes)

@app.route('/operacional/clientes/novo', methods=['GET', 'POST'])
@login_required
def operacional_novo_cliente():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
    cliente = Cliente.query.get_or_404(id)
    return render_template('operacional/visualizar_cliente.html', cliente=cliente)

@app.route('/operacional/pedidos')
@login_required
def operacional_pedidos():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
    # Buscar todos os pedidos do usuário atual
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.data_pedido.desc()).all()
    
    # Calcular o valor total de cada pedido
    for pedido in pedidos:
        pedido.valor_total = sum(item.quantidade * item.valor_unitario for item in pedido.itens)
    
    return render_template('operacional/dashboard.html', pedidos=pedidos)

@app.route('/operacional/pedidos/novo', methods=['GET', 'POST'])
@login_required
def operacional_novo_pedido():
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
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
            valor_total=0
        )
        
        db.session.add(pedido)
        db.session.commit()
        
        # Adicionar itens se houver
        itens = request.form.getlist('item[]')
        descricoes = request.form.getlist('descricao[]')
        materiais = request.form.getlist('material[]')  # Novo campo
        quantidades = request.form.getlist('quantidade[]')
        valores = request.form.getlist('valor_unitario[]')
        
        total_pedido = 0
        for i in range(len(itens)):
            if itens[i].strip():  # Só adiciona se o item não estiver vazio
                quantidade = int(quantidades[i])
                valor_unitario = float(valores[i].replace(',', '.'))
                valor_total = quantidade * valor_unitario
                total_pedido += valor_total
                
                item = ItemPedido(
                    pedido_id=pedido.id,
                    item=itens[i],
                    descricao=descricoes[i],
                    material=materiais[i],  # Novo campo
                    quantidade=quantidade,
                    valor_unitario=valor_unitario
                )
                db.session.add(item)
        
        # Atualizar o valor total do pedido
        pedido.valor_total = total_pedido
        db.session.commit()
        
        flash('Pedido criado com sucesso!', 'success')
        return redirect(url_for('operacional_editar_pedido', id=pedido.id))
    
    clientes = Cliente.query.all()
    return render_template('operacional/formulario_pedido.html', clientes=clientes)

@app.route('/operacional/pedidos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def operacional_editar_pedido(id):
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
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
        materiais = request.form.getlist('material[]')  # Novo campo
        quantidades = request.form.getlist('quantidade[]')
        valores = request.form.getlist('valor_unitario[]')
        
        total_pedido = 0
        for i in range(len(itens)):
            if itens[i].strip():  # Só adiciona se o item não estiver vazio
                quantidade = int(quantidades[i])
                valor_unitario = float(valores[i].replace(',', '.'))
                valor_total = quantidade * valor_unitario
                total_pedido += valor_total
                
                item = ItemPedido(
                    pedido_id=pedido.id,
                    item=itens[i],
                    descricao=descricoes[i],
                    material=materiais[i],  # Novo campo
                    quantidade=quantidade,
                    valor_unitario=valor_unitario
                )
                db.session.add(item)
        
        # Atualizar o valor total do pedido
        pedido.valor_total = total_pedido
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
        return redirect(url_for('index'))
    
    pedido = Pedido.query.get_or_404(id)
    if pedido.usuario_id != current_user.id:
        flash('Você não tem permissão para visualizar este pedido!', 'danger')
        return redirect(url_for('operacional_pedidos'))
        
    return render_template('operacional/visualizar_pedido.html', pedido=pedido)

@app.route('/operacional/pedidos/<int:id>/pdf')
@login_required
def operacional_exportar_pdf(id):
    pedido = Pedido.query.get_or_404(id)
    
    # Criar um buffer de bytes para o PDF
    buffer = BytesIO()
    
    # Criar o PDF com ReportLab
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Centralizado
    )
    
    # Título
    elements.append(Paragraph("Pedido #" + str(pedido.numero), title_style))
    
    # Informações do cliente e pedido
    data = [
        ["Cliente:", pedido.cliente.nome],
        ["Telefone:", pedido.cliente.telefone or "Não informado"],
        ["Endereço:", pedido.cliente.endereco or "Não informado"],
        ["Data do Pedido:", pedido.data_pedido.strftime('%d/%m/%Y')]
    ]
    
    if pedido.data_previsao_entrega:
        data.append(["Previsão de Entrega:", pedido.data_previsao_entrega.strftime('%d/%m/%Y')])
        
    if pedido.observacoes:
        data.append(["Observações:", pedido.observacoes])
    
    # Criar tabela com informações
    info_table = Table(data, colWidths=[120, 400])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Tabela de itens
    items_data = [['Item', 'Material', 'Descrição', 'Qtd', 'Valor Unit.', 'Total']]
    total_pedido = 0
    
    for item in pedido.itens:
        valor_total = item.quantidade * item.valor_unitario
        total_pedido += valor_total
        items_data.append([
            item.item,
            item.material or "Não informado",
            item.descricao,
            str(item.quantidade),
            f"R$ {item.valor_unitario:.2f}",
            f"R$ {valor_total:.2f}"
        ])
    
    # Adicionar linha do total
    items_data.append(['', '', '', '', 'Total:', f"R$ {total_pedido:.2f}"])
    
    # Criar tabela de itens
    items_table = Table(items_data, colWidths=[80, 80, 180, 50, 80, 80])
    items_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -2), 1, black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#808080')),  # Cinza
        ('TEXTCOLOR', (0, 0), (-1, 0), white),  # Branco
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Alinhar números à direita
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),  # Total em negrito
    ]))
    elements.append(items_table)
    
    # Adicionar rodapé com informações extras
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#808080'),  # Cinza
        alignment=1  # Centralizado
    )
    elements.append(Spacer(1, 30))
    
    # Criar texto do rodapé com nome do usuário, data/hora e nome do app
    now = datetime.now()
    footer_text = f"Gerado por {current_user.nome} em {now.strftime('%d/%m/%Y às %H:%M:%S')} | TaloApp"
    elements.append(Paragraph(footer_text, footer_style))
    
    # Gerar PDF
    doc.build(elements)
    
    # Preparar resposta
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=pedido_{pedido.numero}.pdf'
    
    return response

@app.route('/admin/clientes')
@login_required
def admin_clientes():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
    clientes = Cliente.query.all()
    return render_template('admin/clientes.html', clientes=clientes)

@app.route('/admin/clientes/novo', methods=['GET', 'POST'])
@login_required
def admin_novo_cliente():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
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
    
    # Título
    styles = getSampleStyleSheet()
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
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
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
        return redirect(url_for('index'))
    return render_template('admin/relatorios.html')

@app.route('/operacional/pedidos/<int:id>/excluir', methods=['POST'])
@login_required
def operacional_excluir_pedido(id):
    if current_user.tipo != 'operacional':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
    # Obter parâmetros do relatório
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    status = request.args.get('status')
    
    # Converter datas
    try:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d') if data_inicio else datetime.now().replace(day=1)
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d') if data_fim else datetime.now()
    except ValueError:
        flash('Formato de data inválido!', 'danger')
        return redirect(url_for('admin_relatorios'))
    
    # Construir query base
    query = Pedido.query.filter(Pedido.data_pedido.between(data_inicio, data_fim))
    
    # Filtrar por status se especificado
    if status:
        query = query.filter_by(status=status)
    
    # Buscar pedidos
    pedidos = query.order_by(Pedido.data_pedido.desc()).all()
    
    # Calcular estatísticas
    valor_total = sum(pedido.valor_total for pedido in pedidos)
    valor_medio = valor_total / len(pedidos) if pedidos else 0
    
    # Contar pedidos atrasados
    hoje = datetime.now()
    pedidos_atrasados = sum(1 for p in pedidos if p.data_previsao_entrega and p.data_previsao_entrega < hoje and p.status in ['Em Aberto', 'Em Produção'])
    
    return render_template('admin/visualizar_relatorio_pedidos.html',
                         pedidos=pedidos,
                         data_inicio=data_inicio.strftime('%Y-%m-%d'),
                         data_fim=data_fim.strftime('%Y-%m-%d'),
                         data_inicio_formatada=data_inicio.strftime('%d/%m/%Y'),
                         data_fim_formatada=data_fim.strftime('%d/%m/%Y'),
                         status=status,
                         valor_total=valor_total,
                         valor_medio=valor_medio,
                         pedidos_atrasados=pedidos_atrasados)

@app.route('/admin/relatorios/clientes')
@login_required
def admin_relatorio_clientes():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('index'))

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
        return redirect(url_for('index'))

    # Criar um buffer para o PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    # Título
    styles = getSampleStyleSheet()
    elements.append(Paragraph('Relatório de Clientes', styles['Heading1']))
    elements.append(Spacer(1, 20))

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
            cliente.telefone,
            cliente.endereco,
            str(total_ped),
            f'R$ {valor_total:.2f}',
            ultimo_pedido.strftime('%d/%m/%Y') if ultimo_pedido else 'N/A',
            status_predominante,
            f'R$ {ticket_medio:.2f}'
        ])

    # Criar tabela
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), white),
        ('TEXTCOLOR', (0, 1), (-1, -1), black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Alinhar números à direita
        ('ALIGN', (0, 0), (2, -1), 'LEFT'),    # Alinhar texto à esquerda
    ]))

    elements.append(table)

    # Gerar PDF
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='relatorio_clientes.pdf',
        mimetype='application/pdf'
    )

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
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
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

@app.route('/admin/pedidos')
@login_required
def admin_pedidos():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
    # Buscar todos os pedidos de todos os usuários
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    return render_template('admin/pedidos.html', pedidos=pedidos)

@app.route('/admin/pedidos/<int:id>/excluir', methods=['POST'])
@login_required
def admin_excluir_pedido(id):
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('index'))
    
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

if __name__ == '__main__':
    if os.environ.get('FLASK_ENV') == 'production':
        app.run()
    else:
        app.run(debug=True) 