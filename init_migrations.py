from app import app, db
from flask_migrate import init, migrate, upgrade

def init_migrations():
    with app.app_context():
        # Inicializar as migrações
        init()
        
        # Criar a primeira migração
        migrate(message='Migração inicial')
        
        # Aplicar a migração
        upgrade()

if __name__ == '__main__':
    init_migrations() 