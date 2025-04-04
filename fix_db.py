import sqlite3
import os

def fix_database():
    # Remove o banco de dados existente
    if os.path.exists('pedidos.db'):
        os.remove('pedidos.db')
    
    # Conecta ao novo banco de dados
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()
    
    try:
        # Cria a tabela cliente
        cursor.execute('''
        CREATE TABLE cliente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            endereco TEXT
        )
        ''')
        
        # Cria a tabela usuario
        cursor.execute('''
        CREATE TABLE usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            ativo BOOLEAN DEFAULT 1
        )
        ''')
        
        # Cria a tabela pedido
        cursor.execute('''
        CREATE TABLE pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE,
            cliente_id INTEGER NOT NULL,
            data_pedido DATETIME NOT NULL,
            data_previsao_entrega DATETIME,
            status TEXT DEFAULT 'Em Aberto',
            valor_total FLOAT NOT NULL DEFAULT 0,
            usuario_id INTEGER NOT NULL,
            observacoes TEXT,
            FOREIGN KEY (cliente_id) REFERENCES cliente(id),
            FOREIGN KEY (usuario_id) REFERENCES usuario(id)
        )
        ''')
        
        # Cria a tabela item_pedido
        cursor.execute('''
        CREATE TABLE item_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            descricao TEXT,
            quantidade INTEGER NOT NULL,
            valor_unitario FLOAT NOT NULL,
            data_previsao_entrega DATETIME,
            FOREIGN KEY (pedido_id) REFERENCES pedido(id)
        )
        ''')
        
        conn.commit()
        print("Banco de dados recriado com sucesso!")
        
    except sqlite3.Error as e:
        print(f"Erro ao recriar banco de dados: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database() 