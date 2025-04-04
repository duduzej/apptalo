CREATE TABLE IF NOT EXISTS item_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER,
    item TEXT NOT NULL,
    descricao TEXT,
    quantidade INTEGER NOT NULL,
    valor_unitario DECIMAL(10,2) NOT NULL,
    data_previsao_entrega DATETIME,
    FOREIGN KEY (pedido_id) REFERENCES pedido(id)
); 