import sqlite3
import os

def check_database():
    print(f"Diretório atual: {os.getcwd()}")
    print(f"Arquivos no diretório: {os.listdir('.')}")
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect('pedidos.db')
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\nTabelas existentes em pedidos.db:")
        for table in tables:
            print(f"- {table[0]}")
            # Mostra a estrutura de cada tabela
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  * {col[1]} ({col[2]})")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")

if __name__ == "__main__":
    check_database() 