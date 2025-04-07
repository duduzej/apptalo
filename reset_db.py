import os
from app import db, app, Usuario
from werkzeug.security import generate_password_hash

def reset_database():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pedidos.db')
    print(f"Caminho do banco de dados: {db_path}")
    
    # Remover o banco de dados existente
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Banco de dados antigo removido.")
        except Exception as e:
            print(f"Erro ao remover banco de dados: {e}")
            return
    
    # Criar novo banco de dados
    try:
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            print("Tabelas criadas com sucesso!")

            # Verificar se o usuário admin já existe
            admin = Usuario.query.filter_by(email='admin@admin.com').first()
            if not admin:
                # Criar usuário admin
                admin = Usuario(
                    nome='Administrador',
                    email='admin@admin.com',
                    tipo='admin'
                )
                admin.senha = generate_password_hash('admin123')
                db.session.add(admin)
                db.session.commit()
                print("Usuário admin criado com sucesso!")
            else:
                print("Usuário admin já existe")

            print("Banco de dados recriado com sucesso!")
    except Exception as e:
        print(f"Erro ao criar banco de dados: {e}")

if __name__ == "__main__":
    reset_database() 