import sqlite3

def atualizar_tabela():
    # Conectar ao banco de dados
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()

    try:
        print("Iniciando atualização da tabela...")

        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_pedido'")
        tabela_existe = cursor.fetchone() is not None

        if tabela_existe:
            print("Tabela item_pedido encontrada, atualizando estrutura...")
            
            # Criar uma tabela temporária com a nova estrutura
            cursor.execute('''
                CREATE TABLE item_pedido_new (
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
                INSERT INTO item_pedido_new (id, pedido_id, item, descricao, quantidade, valor_unitario, data_previsao_entrega)
                SELECT id, pedido_id, item, descricao, quantidade, valor_unitario, data_previsao_entrega
                FROM item_pedido
            ''')

            # Remover a tabela antiga
            cursor.execute('DROP TABLE item_pedido')

            # Renomear a nova tabela
            cursor.execute('ALTER TABLE item_pedido_new RENAME TO item_pedido')
            
            print("Tabela atualizada com sucesso!")
        else:
            print("Tabela item_pedido não encontrada, criando nova tabela...")
            
            # Criar a tabela com a estrutura correta
            cursor.execute('''
                CREATE TABLE item_pedido (
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
            print("Nova tabela criada com sucesso!")

        # Commit das alterações
        conn.commit()
        print("Operação concluída com sucesso!")

    except Exception as e:
        print(f"Erro ao atualizar a tabela: {e}")
        conn.rollback()

    finally:
        conn.close()

if __name__ == '__main__':
    atualizar_tabela() 