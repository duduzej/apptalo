import sqlite3
import os
from datetime import datetime
from app import db, app

def backup_data():
    data = {'usuarios': [], 'clientes': [], 'pedidos': [], 'itens_pedido': []}
    
    conn = sqlite3.connect('pedidos.db')
    cursor = conn.cursor()
    
    # Backup usuários
    try:
        cursor.execute('SELECT * FROM usuario')
        data['usuarios'] = cursor.fetchall()
    except:
        pass
    
    # Backup clientes
    try:
        cursor.execute('SELECT * FROM cliente')
        data['clientes'] = cursor.fetchall()
    except:
        pass
    
    # Backup pedidos
    try:
        cursor.execute('SELECT * FROM pedido')
        data['pedidos'] = cursor.fetchall()
    except:
        pass
    
    # Backup itens_pedido
    try:
        cursor.execute('SELECT * FROM item_pedido')
        data['itens_pedido'] = cursor.fetchall()
    except:
        pass
    
    conn.close()
    return data

def restore_data(data):
    with app.app_context():
        from app import Usuario, Cliente, Pedido, ItemPedido
        
        # Restaura usuários
        for user in data['usuarios']:
            u = Usuario(
                id=user[0],
                nome=user[1],
                email=user[2],
                senha=user[3],
                tipo=user[4],
                ativo=bool(user[5])
            )
            db.session.add(u)
        
        # Restaura clientes
        for cliente in data['clientes']:
            c = Cliente(
                id=cliente[0],
                nome=cliente[1],
                email=cliente[2],
                telefone=cliente[3],
                endereco=cliente[4]
            )
            db.session.add(c)
        
        # Restaura pedidos
        for pedido in data['pedidos']:
            p = Pedido(
                id=pedido[0],
                numero=pedido[1],
                cliente_id=pedido[2],
                data_pedido=datetime.strptime(pedido[3], '%Y-%m-%d %H:%M:%S') if pedido[3] else None,
                data_previsao_entrega=datetime.strptime(pedido[4], '%Y-%m-%d %H:%M:%S') if pedido[4] else None,
                status=pedido[5],
                valor_total=pedido[6],
                usuario_id=pedido[7],
                observacoes=pedido[8]
            )
            db.session.add(p)
        
        # Restaura itens_pedido
        for item in data['itens_pedido']:
            i = ItemPedido(
                id=item[0],
                pedido_id=item[1],
                item=item[2],
                descricao=item[3],
                quantidade=item[4],
                valor_unitario=item[5],
                data_previsao_entrega=datetime.strptime(item[6], '%Y-%m-%d %H:%M:%S') if item[6] else None
            )
            db.session.add(i)
        
        try:
            db.session.commit()
            print("Dados restaurados com sucesso!")
        except Exception as e:
            print(f"Erro ao restaurar dados: {e}")
            db.session.rollback()

def rebuild_database():
    print("Fazendo backup dos dados...")
    data = backup_data()
    
    print("Removendo banco de dados antigo...")
    if os.path.exists('pedidos.db'):
        os.remove('pedidos.db')
    
    print("Criando novo banco de dados...")
    with app.app_context():
        db.create_all()
    
    print("Restaurando dados...")
    restore_data(data)
    
    print("Processo concluído!")

if __name__ == "__main__":
    rebuild_database() 