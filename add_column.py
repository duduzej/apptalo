import sqlite3

# Conecta ao banco de dados
conn = sqlite3.connect('pedidos.db')
cursor = conn.cursor()

# Cria a tabela pedido se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL,
    data_pedido DATETIME NOT NULL,
    data_previsao_entrega DATETIME,
    status TEXT DEFAULT 'Em Aberto',
    valor_total FLOAT NOT NULL DEFAULT 0,
    usuario_id INTEGER NOT NULL,
    observacoes TEXT
)
''')

# Cria a tabela item_pedido se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS item_pedido (
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

print("Tabelas criadas/atualizadas com sucesso!")

# Salva as alterações e fecha a conexão
conn.commit()
conn.close() 