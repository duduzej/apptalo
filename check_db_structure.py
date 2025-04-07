from app import db, app, ItemPedido
from sqlalchemy import inspect

def check_database_structure():
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("Verificando estrutura do banco de dados...")
        
        # Listar todas as tabelas
        tables = inspector.get_table_names()
        print("\nTabelas encontradas:")
        for table in tables:
            print(f"\n{table}:")
            columns = inspector.get_columns(table)
            for column in columns:
                print(f"  - {column['name']}: {column['type']}")

if __name__ == "__main__":
    check_database_structure() 