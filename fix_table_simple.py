import sqlite3

def fix_table():
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()
    
    try:
        # Verificar se a coluna existe
        cursor.execute("PRAGMA table_info(item_pedido)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'data_previsao_entrega' not in columns:
            # Adicionar a coluna
            cursor.execute('ALTER TABLE item_pedido ADD COLUMN data_previsao_entrega DATETIME')
            print("Coluna adicionada com sucesso!")
        else:
            print("A coluna já existe!")
        
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"Erro: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_table() 