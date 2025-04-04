from app import db

# Recria todas as tabelas
db.drop_all()
db.create_all()

print("Banco de dados recriado com sucesso!") 