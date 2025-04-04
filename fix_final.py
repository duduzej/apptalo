import sqlite3

def fix_final():
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()
    
    try:
        # 1. Criar uma nova tabela com a estrutura correta
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS item_pedido_new (
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
        
        # 2. Copiar dados da tabela antiga
        cursor.execute('''
        INSERT INTO item_pedido_new (id, pedido_id, item, descricao, quantidade, valor_unitario)
        SELECT id, pedido_id, item, descricao, quantidade, valor_unitario
        FROM item_pedido
        ''')
        
        # 3. Remover a tabela antiga
        cursor.execute('DROP TABLE item_pedido')
        
        # 4. Renomear a nova tabela
        cursor.execute('ALTER TABLE item_pedido_new RENAME TO item_pedido')
        
        # 5. Verificar a estrutura final
        cursor.execute("PRAGMA table_info(item_pedido)")
        columns = cursor.fetchall()
        print("\nEstrutura final da tabela:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        conn.commit()
        print("\nTabela recriada com sucesso!")
        
    except sqlite3.Error as e:
        print(f"Erro: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_final() 