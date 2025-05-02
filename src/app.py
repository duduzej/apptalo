from flask import Flask
from .config import get_config
from .extensions import init_extensions
from .models import Usuario, Cliente, Pedido, ItemPedido
from .auth import auth as auth_blueprint
from .routes.admin import admin as admin_blueprint
from .routes.operacional import operacional as operacional_blueprint
from .routes.main import main as main_blueprint

def create_app(config_name='default'):
    """Fábrica de aplicação Flask"""
    app = Flask(__name__)
    
    # Carregar configurações
    app.config.from_object(get_config())
    
    # Inicializar extensões
    init_extensions(app)
    
    # Registrar blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    app.register_blueprint(operacional_blueprint, url_prefix='/operacional')
    app.register_blueprint(main_blueprint)
    
    # Registrar funções de template
    from .utils.helpers import formatar_moeda, get_cor_status
    app.jinja_env.filters['moeda'] = formatar_moeda
    app.jinja_env.globals.update(get_cor_status=get_cor_status)
    
    return app 