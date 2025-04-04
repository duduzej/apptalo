import sqlite3

def recreate_table():
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()
    
    try:
        # 1. Fazer backup dos dados
        cursor.execute('SELECT * FROM item_pedido')
        dados = cursor.fetchall()
        
        # 2. Apagar a tabela antiga
        cursor.execute('DROP TABLE item_pedido')
        
        # 3. Criar a nova tabela
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
        
        # 4. Restaurar os dados
        for dado in dados:
            cursor.execute('''
            INSERT INTO item_pedido (id, pedido_id, item, descricao, quantidade, valor_unitario)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', dado[:6])  # Pegando apenas as 6 primeiras colunas
        
        conn.commit()
        print("Tabela recriada com sucesso!")
        
    except sqlite3.Error as e:
        print(f"Erro: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    recreate_table() 