import os
from app import db, app

# Remove o arquivo do banco de dados se existir
if os.path.exists('pedidos.db'):
    os.remove('pedidos.db')

# Cria todas as tabelas
with app.app_context():
    db.create_all()
    print("Banco de dados recriado com sucesso!") 