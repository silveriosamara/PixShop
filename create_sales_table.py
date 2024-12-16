import sqlite3

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('pix_store1.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para criar a tabela sales
def recreate_sales_table():
    conn = get_db_connection()
    # Apagar a tabela existente, se houver
    conn.execute('DROP TABLE IF EXISTS sales')
    # Recriar a tabela com a estrutura correta
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            vendedor_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES products (id),
            FOREIGN KEY (vendedor_id) REFERENCES users (id)
        );
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    recreate_sales_table()  # Recria a tabela sales
    print("Tabela 'sales' recriada com sucesso.")
