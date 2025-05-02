from flask import current_app
from flask_mail import Message
from ..extensions import mail
from threading import Thread

def enviar_email_async(app, msg):
    """Envia email de forma assíncrona"""
    with app.app_context():
        mail.send(msg)

def enviar_email(assunto, destinatario, template):
    """Função genérica para envio de emails"""
    msg = Message(assunto,
                 sender=current_app.config['MAIL_DEFAULT_SENDER'],
                 recipients=[destinatario])
    msg.html = template
    
    # Enviar email de forma assíncrona
    Thread(target=enviar_email_async,
           args=(current_app._get_current_object(), msg)).start()

def enviar_email_redefinicao_senha(email, link):
    """Envia email com link para redefinição de senha"""
    template = f'''
    <h1>Redefinição de Senha</h1>
    <p>Para redefinir sua senha, clique no link abaixo:</p>
    <p><a href="{link}">Redefinir Senha</a></p>
    <p>Se você não solicitou a redefinição de senha, ignore este email.</p>
    <p>Este link expirará em 24 horas.</p>
    '''
    
    enviar_email('Redefinição de Senha', email, template) 