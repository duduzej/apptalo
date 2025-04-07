import sqlite3

def update_database():
    # Conectar ao banco de dados
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()

    try:
        # Verificar se a coluna material existe
        cursor.execute("PRAGMA table_info(item_pedido)")
        colunas = cursor.fetchall()
        tem_coluna_material = any(coluna[1] == 'material' for coluna in colunas)

        if not tem_coluna_material:
            print("Adicionando coluna material...")
            # Criar uma tabela temporária com a nova estrutura
            cursor.execute('''
                CREATE TABLE item_pedido_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER NOT NULL,
                    item TEXT NOT NULL,
                    descricao TEXT,
                    material TEXT NOT NULL DEFAULT 'Não especificado',
                    quantidade INTEGER NOT NULL,
                    valor_unitario FLOAT NOT NULL,
                    data_previsao_entrega DATE,
                    FOREIGN KEY (pedido_id) REFERENCES pedido(id)
                )
            ''')

            # Copiar dados da tabela antiga para a nova
            cursor.execute('''
                INSERT INTO item_pedido_temp (id, pedido_id, item, descricao, quantidade, valor_unitario, data_previsao_entrega)
                SELECT id, pedido_id, item, descricao, quantidade, valor_unitario, data_previsao_entrega
                FROM item_pedido
            ''')

            # Remover a tabela antiga
            cursor.execute('DROP TABLE item_pedido')

            # Renomear a tabela temporária
            cursor.execute('ALTER TABLE item_pedido_temp RENAME TO item_pedido')

            print("Coluna material adicionada com sucesso!")

        conn.commit()
        print("Banco de dados atualizado com sucesso!")

    except Exception as e:
        print(f"Erro ao atualizar o banco de dados: {e}")
        conn.rollback()

    finally:
        conn.close()

if __name__ == '__main__':
    update_database() 