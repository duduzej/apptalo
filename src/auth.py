from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from .models import Usuario
from .extensions import db
from .utils.email import enviar_email_redefinicao_senha
import secrets

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Rota para login de usuários"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        lembrar = 'lembrar' in request.form
        
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.verificar_senha(senha):
            if not usuario.ativo:
                flash('Esta conta está desativada.', 'danger')
                return redirect(url_for('auth.login'))
                
            login_user(usuario, remember=lembrar)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
            
        flash('Email ou senha inválidos.', 'danger')
    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    """Rota para logout de usuários"""
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/esqueceu-senha', methods=['GET', 'POST'])
def esqueceu_senha():
    """Rota para solicitar redefinição de senha"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario:
            token = secrets.token_urlsafe(32)
            usuario.token_redefinicao = token
            db.session.commit()
            
            link_redefinicao = url_for('auth.redefinir_senha', token=token, _external=True)
            enviar_email_redefinicao_senha(usuario.email, link_redefinicao)
            
            flash('Um email foi enviado com instruções para redefinir sua senha.', 'info')
            return redirect(url_for('auth.login'))
            
        flash('Email não encontrado.', 'danger')
    return render_template('auth/esqueceu_senha.html')

@auth.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    """Rota para redefinir a senha"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    usuario = Usuario.query.filter_by(token_redefinicao=token).first()
    if not usuario:
        flash('Link de redefinição de senha inválido ou expirado.', 'danger')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        senha = request.form.get('senha')
        usuario.senha = senha
        usuario.token_redefinicao = None
        db.session.commit()
        
        flash('Sua senha foi alterada com sucesso.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/redefinir_senha.html') 