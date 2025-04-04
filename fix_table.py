import sqlite3

def fix_table():
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()
    
    try:
        # 1. Criar tabela temporária com a nova estrutura
        cursor.execute('''
        CREATE TABLE item_pedido_new (
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
        
        # 2. Copiar dados da tabela antiga para a nova
        cursor.execute('''
        INSERT INTO item_pedido_new (id, pedido_id, item, descricao, quantidade, valor_unitario)
        SELECT id, pedido_id, item, descricao, quantidade, valor_unitario
        FROM item_pedido
        ''')
        
        # 3. Apagar tabela antiga
        cursor.execute('DROP TABLE item_pedido')
        
        # 4. Renomear tabela nova
        cursor.execute('ALTER TABLE item_pedido_new RENAME TO item_pedido')
        
        conn.commit()
        print("Tabela item_pedido corrigida com sucesso!")
        
    except sqlite3.Error as e:
        print(f"Erro ao corrigir tabela: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_table() 