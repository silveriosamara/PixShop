import sqlite3
from werkzeug.security import generate_password_hash
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('pix_store1.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para criar as tabelas
def create_tables():
    conn = get_db_connection()
    c = conn.cursor()

    # Criação da tabela de usuários
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        pix_key TEXT
    )
    ''')

    # Criação da tabela de produtos
    c.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        comissao REAL NOT NULL,
        price REAL NOT NULL
    )
    ''')

    # Criação da tabela de vendas
    c.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        vendedor_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'completada',
        FOREIGN KEY (produto_id) REFERENCES products (id),
        FOREIGN KEY (vendedor_id) REFERENCES users (id)
    )
    ''')

    # Criação da tabela de comissões
    c.execute('''
    CREATE TABLE IF NOT EXISTS commissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendedor_id INTEGER NOT NULL,
        venda_id INTEGER NOT NULL,
        comissao REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pendente',
        FOREIGN KEY(vendedor_id) REFERENCES users(id),
        FOREIGN KEY(venda_id) REFERENCES sales(id)
    )
    ''')

    conn.commit()
    conn.close()
    logging.info("Tabelas criadas com sucesso.")

#Função para criar coluna comissao
def add_comissao_column():
    conn = sqlite3.connect('pix_store1.db')
    try:
        conn.execute('ALTER TABLE products ADD COLUMN comissao REAL NOT NULL DEFAULT 0')
        conn.commit()
        print("Coluna 'comissao' adicionada com sucesso.")
    except sqlite3.OperationalError as e:
        print("Erro ao adicionar coluna:", e)
    conn.close()

add_comissao_column()


# Função para adicionar a coluna status à tabela sales, caso ela ainda não exista
def add_status_column():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE sales ADD COLUMN status TEXT DEFAULT "completada"')
        conn.commit()
        logging.info("Coluna 'status' adicionada com sucesso à tabela 'sales'.")
    except sqlite3.OperationalError:
        logging.warning("A coluna 'status' já existe na tabela 'sales'.")
    conn.close()

# Função para adicionar a coluna pix_key à tabela existente (caso não exista)
def add_pix_key_column():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE users ADD COLUMN pix_key TEXT')
        conn.commit()
        logging.info("Coluna 'pix_key' adicionada com sucesso à tabela 'users'.")
    except sqlite3.OperationalError:
        logging.warning("A coluna 'pix_key' já existe na tabela 'users'.")
    conn.close()

# Função para inserir os usuários inicializadores
def setup_initial_users():
    conn = get_db_connection()
    gestor = conn.execute('SELECT * FROM users WHERE username = ?', ('sasilverio',)).fetchone()
    vendedor = conn.execute('SELECT * FROM users WHERE username = ?', ('juGabriela',)).fetchone()

    # Inserir usuários com senha hash
    if gestor is None:
        conn.execute(
            'INSERT INTO users (username, password, role, pix_key) VALUES (?, ?, ?, ?)',
            ('sasilverio', generate_password_hash('Sa315800@'), 'gestor', 'pix_chave_gestor')
        )
        logging.info("Usuário 'sasilverio' adicionado como gestor.")
    if vendedor is None:
        conn.execute(
            'INSERT INTO users (username, password, role, pix_key) VALUES (?, ?, ?, ?)',
            ('juGabriela', generate_password_hash('Ju202400@'), 'vendedor', 'pix_chave_vendedor')
        )
        logging.info("Usuário 'juGabriela' adicionado como vendedor.")
    conn.commit()
    conn.close()


# Executar a criação de tabelas e inserção de usuários
if __name__ == '__main__':
    create_tables()
    add_pix_key_column()
    add_status_column()  # Adiciona a coluna 'status' à tabela sales
    setup_initial_users()
    logging.info("Banco de dados atualizado com sucesso.")
