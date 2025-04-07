from app import app
from database import db
from models import Usuario, Cliente, Pedido, ItemPedido
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        # Verificar se o usuário admin já existe
        admin = Usuario.query.filter_by(email='admin@admin.com').first()
        if not admin:
            admin = Usuario(
                nome='Administrador',
                email='admin@admin.com',
                senha=generate_password_hash('admin123'),
                tipo='admin',
                ativo=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Usuário admin criado com sucesso!")
        else:
            print("Usuário admin já existe.")

if __name__ == '__main__':
    init_db()
    print("Banco de dados inicializado com sucesso!") 