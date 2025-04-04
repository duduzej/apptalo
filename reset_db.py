import os
from app import db, app

def reset_database():
    # Remover o banco de dados existente
    if os.path.exists('pedidos.db'):
        try:
            os.remove('pedidos.db')
            print("Banco de dados antigo removido.")
        except Exception as e:
            print(f"Erro ao remover banco de dados: {e}")
            return
    
    # Criar novo banco de dados
    try:
        with app.app_context():
            db.create_all()
            print("Novo banco de dados criado com sucesso!")
    except Exception as e:
        print(f"Erro ao criar novo banco de dados: {e}")

if __name__ == "__main__":
    reset_database() 