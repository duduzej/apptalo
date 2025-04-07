import sqlite3

def listar_tabelas(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [tabela[0] for tabela in cursor.fetchall()]

def limpar_dados():
    # Conectar ao banco de dados
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()

    try:
        print("Iniciando limpeza do banco de dados...")
        
        # Listar todas as tabelas
        tabelas = listar_tabelas(cursor)
        print(f"Tabelas encontradas: {tabelas}")

        # Deletar itens de pedidos (incluindo tabela temporária)
        if 'item_pedido' in tabelas:
            cursor.execute('DELETE FROM item_pedido')
            print("Itens de pedidos deletados")
        elif 'item_pedido_temp' in tabelas:
            cursor.execute('DELETE FROM item_pedido_temp')
            print("Itens de pedidos temporários deletados")
        else:
            print("Nenhuma tabela de itens de pedido encontrada")

        # Deletar pedidos
        if 'pedido' in tabelas:
            cursor.execute('DELETE FROM pedido')
            print("Pedidos deletados")
        else:
            print("Tabela pedido não existe")

        # Deletar usuários operacionais
        if 'usuario' in tabelas:
            cursor.execute('DELETE FROM usuario WHERE tipo = "operacional"')
            print("Usuários operacionais deletados")
        else:
            print("Tabela usuario não existe")

        # Commit das alterações
        conn.commit()
        print("Operação concluída com sucesso!")

    except Exception as e:
        print(f"Erro ao limpar o banco de dados: {e}")
        conn.rollback()

    finally:
        conn.close()

if __name__ == '__main__':
    limpar_dados() 