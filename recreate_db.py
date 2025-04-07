import os
from app import db, app, Usuario
from werkzeug.security import generate_password_hash

def recreate_database():
    print("Iniciando recriação do banco de dados...")
    
    # Remove o arquivo do banco de dados se existir
    if os.path.exists('pedidos.db'):
        try:
            os.remove('pedidos.db')
            print("Banco de dados antigo removido.")
        except Exception as e:
            print(f"Erro ao remover banco de dados: {e}")
            return

    # Cria todas as tabelas
    with app.app_context():
        try:
            db.create_all()
            print("Tabelas criadas com sucesso!")

            # Criar usuário admin se não existir
            admin = Usuario.query.filter_by(email='admin@admin.com').first()
            if not admin:
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
                print("Usuário admin já existe.")

            print("Banco de dados recriado com sucesso!")
        except Exception as e:
            print(f"Erro ao criar banco de dados: {e}")
            raise

if __name__ == "__main__":
    recreate_database() 