import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import qrcode
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import ngrok


app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

from flask import Flask, request, redirect, url_for, session, flash, make_response, jsonify

@app.after_request
def add_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'any_value'
    return response


TEMPLATES_AUTO_RELOAD = True

#Credenciais do Mercado Pago
MERCADO_PAGO_PUBLIC_KEY = "TEST-9c8d4958-116c-4290-a764-ba2334a8bee3"
MERCADO_PAGO_ACCESS_TOKEN_VENDEDOR = "TEST-74617770-vendedor-token"


# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('pix_store1.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para configurar usuários iniciais
def setup_initial_users():
    conn = get_db_connection()
    gestor = conn.execute('SELECT * FROM users WHERE username = ?', ('sasilverio',)).fetchone()
    vendedor = conn.execute('SELECT * FROM users WHERE username = ?', ('juGabriela',)).fetchone()
    if gestor is None:
        conn.execute(
            'INSERT INTO users (username, password, role, pix_key) VALUES (?, ?, ?, ?)',
            ('sasilverio', 'Sa315800@', 'gestor', 'pix_chave_gestor')
        )
    if vendedor is None:
        conn.execute(
            'INSERT INTO users (username, password, role, pix_key) VALUES (?, ?, ?, ?)',
            ('juGabriela', 'Ju202400@', 'vendedor', 'pix_chave_vendedor')
        )
    conn.commit()
    conn.close()


# Função para gerar um link de pagamento no Mercado Pago
def gerar_link_pagamento_mercado_pago(produto, quantidade, total_preco):
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN_VENDEDOR}",
        "Content-Type": "application/json"
    }
    payload = {
        "items": [
            {
                "title": produto['name'],
                "quantity": quantidade,
                "unit_price": float(produto['price']),
                "currency_id": "BRL"
            }
        ],
        "payer": {
            "email": "TESTUSER1349659092@testuser.com"  # Email do cliente (opcional, pode ser coletado dinamicamente)
        },
        "back_urls": {
            "success": "http://localhost:5000/sucesso",
            "failure": "http://localhost:5000/falha",
            "pending": "http://localhost:5000/pendente"
        },
        "auto_return": "approved",
        "payment_methods": {
            "excluded_payment_types": [{"id": "ticket"}],  # Excluir métodos como boleto, se necessário
            "installments": 1  # Número de parcelas permitido
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 201:
        return response.json().get('init_point')
    else:
        print(f"Erro ao gerar link de pagamento: {response.status_code} - {response.text}")
        return None


# Realizar venda e gerar link de pagamento Mercado Pago
@app.route('/venda/realizar', methods=['POST'])
def realizar_venda():
    if 'role' in session and session['role'] == 'vendedor':
        produto_id = request.form['produto_id']
        quantidade_vendida = int(request.form['quantidade'])

        conn = get_db_connection()
        produto = conn.execute('SELECT * FROM products WHERE id = ?', (produto_id,)).fetchone()

        if produto['quantity'] < quantidade_vendida:
            flash('Quantidade insuficiente em estoque!')
            return redirect(url_for('vendedor_produtos'))

        # Atualizar o estoque
        nova_quantidade = produto['quantity'] - quantidade_vendida
        conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (nova_quantidade, produto_id))

        # Registrar a venda no banco de dados
        conn.execute('INSERT INTO sales (produto_id, vendedor_id, quantidade) VALUES (?, ?, ?)',
                     (produto_id, session['user_id'], quantidade_vendida))
        conn.commit()

        total_preco = produto['price'] * quantidade_vendida

        # Gerar o link de pagamento no Mercado Pago
        link_pagamento = gerar_link_pagamento_mercado_pago(produto, quantidade_vendida, total_preco)

        if not link_pagamento:
            flash('Erro ao gerar link de pagamento.')
            return redirect(url_for('vendedor_produtos'))

        conn.close()

        # Exibir o link de pagamento e QR Code
        flash('Venda realizada com sucesso! Mostre o QR Code ao cliente para efetuar o pagamento.')
        return render_template('vendedor_mercadopago_qrcode.html', link_pagamento=link_pagamento, produto=produto,
                               quantidade=quantidade_vendida, total_preco=total_preco)
    else:
        return redirect(url_for('login'))


# Página de sucesso, falha e pendente
@app.route('/sucesso')
def sucesso():
    return render_template('sucesso.html')


@app.route('/falha')
def falha():
    return render_template('falha.html')


@app.route('/pendente')
def pendente():
    return render_template('pendente.html')


# Página de login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'gestor':
                return redirect(url_for('gestor_home'))
            elif user['role'] == 'vendedor':
                return redirect(url_for('vendedor_home'))
        else:
            flash('Credenciais inválidas. Tente novamente.')
    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Inserir novo produto no banco de dados (gestor)
@app.route('/gestor/produtos', methods=['GET', 'POST'])
def gestor_produtos():
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        if request.method == 'POST':
            nome = request.form['name']
            descricao = request.form['description']
            quantidade = int(request.form['quantity'])
            preco = float(request.form['price'])
            comissao = float(request.form['comissao'])  # Recebe o valor da comissão
            if nome and descricao and quantidade > 0 and preco > 0:
                conn.execute('INSERT INTO products (name, description, quantity, price, comissao) VALUES (?, ?, ?, ?, ?)',
                             (nome, descricao, quantidade, preco, comissao))
                conn.commit()
                flash('Produto cadastrado com sucesso!')
            else:
                flash('Preencha todos os campos corretamente.')
        produtos = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        return render_template('gestor_produtos.html', produtos=produtos)
    else:
        return redirect(url_for('login'))

# Rota para atualizar a comissão de um produto
@app.route('/atualizar_comissao/<int:id>', methods=['POST'])
def atualizar_comissao(id):
    comissao = request.form['comissao']
    conn = get_db_connection()
    conn.execute('UPDATE products SET comissao = ? WHERE id = ?', (comissao, id))
    conn.commit()
    conn.close()
    flash("Comissão atualizada com sucesso!", "success")
    return redirect(url_for('gestor_produtos'))


# Rota para remover produto (gestor)
@app.route('/gestor/produto/remover/<int:produto_id>', methods=['POST'])
def remover_produto(produto_id):
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        conn.execute('DELETE FROM products WHERE id = ?', (produto_id,))
        conn.commit()
        conn.close()
        flash('Produto removido com sucesso!')
        return redirect(url_for('gestor_home'))
    else:
        return redirect(url_for('login'))

# Página de produtos do vendedor
@app.route('/vendedor/produtos', methods=['GET'])
def vendedor_produtos():
    if 'role' in session and session['role'] == 'vendedor':
        conn = get_db_connection()
        produtos = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        return render_template('vendedor_produtos.html', produtos=produtos)
    else:
        return redirect(url_for('login'))

#Função para cancelar venda
@app.route('/venda/cancelar/<int:sale_id>', methods=['POST'])
def cancelar_venda(sale_id):
    if 'role' in session and session['role'] in ['vendedor', 'gestor']:
        conn = get_db_connection()

        # Recuperar a venda e o produto relacionado
        venda = conn.execute('SELECT * FROM sales WHERE id = ? AND status = ?', (sale_id, 'completada')).fetchone()
        if not venda:
            flash('Venda não encontrada ou já cancelada.')
            return redirect(url_for('vendedor_home' if session['role'] == 'vendedor' else 'gestor_home'))

        produto = conn.execute('SELECT * FROM products WHERE id = ?', (venda['produto_id'],)).fetchone()

        # Atualizar o estoque
        nova_quantidade = produto['quantity'] + venda['quantidade']
        conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (nova_quantidade, venda['produto_id']))

        # Marcar a venda como cancelada
        conn.execute('UPDATE sales SET status = ? WHERE id = ?', ('cancelada', sale_id))

        conn.commit()
        conn.close()

        flash('Venda cancelada e estoque restaurado com sucesso.')
        return redirect(url_for('vendedor_home' if session['role'] == 'vendedor' else 'gestor_home'))
    else:
        return redirect(url_for('login'))

# Página de histórico de vendas do vendedor
@app.route('/vendedor/historico_vendas')
def vendedor_historico_vendas():
    if 'role' in session and session['role'] == 'vendedor':
        vendedor_id = session['user_id']
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row

        vendas = conn.execute('''
            SELECT s.id, p.name, s.quantidade, s.data_venda, p.price * s.quantidade AS total, s.status
            FROM sales s
            JOIN products p ON s.produto_id = p.id
            WHERE s.vendedor_id = ?
        ''', (vendedor_id,)).fetchall()

        conn.close()
        return render_template('vendedor_historico_vendas.html', vendas=vendas)
    else:
        return redirect(url_for('login'))

@app.route('/vendedor/comissoes')
def vendedor_comissoes():
    if 'role' in session and session['role'] == 'vendedor':
        vendedor_id = session['user_id']
        conn = get_db_connection()

        # Consulta para buscar as comissões associadas ao vendedor logado
        comissoes = conn.execute('''
            SELECT s.id, p.name, s.quantidade, p.comissao, c.status
            FROM sales s
            JOIN products p ON s.produto_id = p.id
            JOIN commissions c ON c.venda_id = s.id
            WHERE s.vendedor_id = ?
        ''', (vendedor_id,)).fetchall()

        conn.close()

        # Renderiza o template HTML, passando os dados das comissões
        return render_template('vendedor_comissoes.html', comissoes=comissoes)
    else:
        return redirect(url_for('login'))

#Rota para excluir venda
@app.route('/vendedor/excluir_venda/<int:venda_id>', methods=['POST'])
def excluir_venda(venda_id):
    if 'role' in session and session['role'] == 'vendedor':
        conn = get_db_connection()

        # Excluir a venda pelo ID
        conn.execute('DELETE FROM sales WHERE id = ? AND vendedor_id = ?', (venda_id, session['user_id']))
        conn.commit()
        conn.close()

        flash('Venda excluída com sucesso.')
        return redirect(url_for('vendedor_historico_vendas'))
    else:
        return redirect(url_for('login'))


# Relatório de vendas do gestor - todas as vendas
@app.route('/gestor/relatorio_vendas')
def relatorio_vendas_gestor():
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        vendas = conn.execute('''
            SELECT s.id, p.name AS produto, u.username AS vendedor, s.quantidade, s.data_venda, 
                   p.price * s.quantidade AS total_venda, s.status
            FROM sales s
            JOIN products p ON s.produto_id = p.id
            JOIN users u ON s.vendedor_id = u.id
        ''').fetchall()
        conn.close()
        return render_template('gestor_relatorio_vendas.html', vendas=vendas)
    else:
        return redirect(url_for('login'))


@app.route('/gestor/venda/remover/<int:venda_id>', methods=['POST'])
def remover_venda(venda_id):
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()

        # Verifica se a venda realmente existe antes de excluir
        venda = conn.execute('SELECT * FROM sales WHERE id = ?', (venda_id,)).fetchone()
        if venda is None:
            flash('Venda não encontrada.')
            return redirect(url_for('relatorio_vendas_gestor'))

            # Permitir exclusão para qualquer status
            conn.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
            conn.commit()
            conn.close()

            flash('Venda removida com sucesso!')
            return redirect(url_for('relatorio_vendas_gestor'))



# Relatório de vendas do vendedor - vendas feitas por ele
@app.route('/vendedor/relatorio_vendas')
def relatorio_vendas_vendedor():
    if 'role' in session and session['role'] == 'vendedor':
        vendedor_id = session['user_id']
        conn = get_db_connection()
        vendas = conn.execute('''
            SELECT s.id, p.name AS produto, s.quantidade, s.data_venda, 
                   p.price * s.quantidade AS total_venda, s.status
            FROM sales s
            JOIN products p ON s.produto_id = p.id
            WHERE s.vendedor_id = ?
        ''', (vendedor_id,)).fetchall()
        conn.close()
        return render_template('vendedor_relatorio_vendas.html', vendas=vendas)
    else:
        return redirect(url_for('login'))

# Relatório de comissões do gestor - todas as comissões
@app.route('/gestor/relatorio_comissoes')
def relatorio_comissoes_gestor():
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        comissoes = conn.execute('''
            SELECT c.id, u.username AS vendedor, p.name AS produto, s.quantidade, 
                   c.comissao, c.status
            FROM commissions c
            JOIN sales s ON c.venda_id = s.id
            JOIN products p ON s.produto_id = p.id
            JOIN users u ON c.vendedor_id = u.id
            WHERE c.status = 'pendente'
        ''').fetchall()
        conn.close()
        return render_template('gestor_relatorio_comissoes.html', comissoes=comissoes)
    else:
        return redirect(url_for('login'))

# Relatório detalhado de estoque para o gestor
@app.route('/gestor/relatorio_estoque')
def relatorio_estoque():
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        produtos = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        return render_template('gestor_relatorio_estoque.html', produtos=produtos)
    else:
        return redirect(url_for('login'))

# Definir o limite mínimo para notificar sobre o estoque baixo
LIMITE_ESTOQUE_BAIXO = 5

@app.route('/gestor/notificacao_estoque_baixo')
def notificacao_estoque_baixo():
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        produtos_baixo_estoque = conn.execute('SELECT * FROM products WHERE quantity < ?', (LIMITE_ESTOQUE_BAIXO,)).fetchall()
        conn.close()
        return render_template('gestor_notificacao_estoque_baixo.html', produtos=produtos_baixo_estoque)
    else:
        return redirect(url_for('login'))

# Rota para ajustar manualmente o estoque de um produto
@app.route('/gestor/ajustar_estoque/<int:produto_id>', methods=['POST'])
def ajustar_estoque(produto_id):
    if 'role' in session and session['role'] == 'gestor':
        nova_quantidade = int(request.form['nova_quantidade'])
        conn = get_db_connection()
        conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (nova_quantidade, produto_id))
        conn.commit()
        conn.close()
        flash('Estoque atualizado com sucesso!')
        return redirect(url_for('relatorio_estoque'))
    else:
        return redirect(url_for('login'))


# Relatório de comissões do vendedor - comissões próprias
@app.route('/vendedor/relatorio_comissoes')
def relatorio_comissoes_vendedor():
    if 'role' in session and session['role'] == 'vendedor':
        vendedor_id = session['user_id']
        conn = get_db_connection()
        comissoes = conn.execute('''
            SELECT p.name AS produto, s.quantidade, c.comissao, c.status
            FROM commissions c
            JOIN sales s ON c.venda_id = s.id
            JOIN products p ON s.produto_id = p.id
            WHERE c.vendedor_id = ?
        ''', (vendedor_id,)).fetchall()
        conn.close()
        return render_template('vendedor_relatorio_comissoes.html', comissoes=comissoes)
    else:
        return redirect(url_for('login'))

#Rota para vendas recentes
@app.route('/vendedor')
def vendedor_home():
    if 'role' in session and session['role'] == 'vendedor':
        conn = get_db_connection()

        # Obter vendas recentes do vendedor
        vendas_recentes = conn.execute('''
            SELECT p.name, s.quantidade, s.data_venda 
            FROM sales s
            JOIN products p ON s.produto_id = p.id
            WHERE s.vendedor_id = ?
            ORDER BY s.data_venda DESC
            LIMIT 5
        ''', (session['user_id'],)).fetchall()

        conn.close()
        return render_template('vendedor_home.html', username=session['username'], vendas_recentes=vendas_recentes)
    else:
        return redirect(url_for('login'))


# Rota para marcar uma comissão como paga
@app.route('/gestor/pagar_comissao/<int:comissao_id>', methods=['POST'])
def pagar_comissao(comissao_id):
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        conn.execute('UPDATE commissions SET status = ? WHERE id = ?', ('pago', comissao_id))
        conn.commit()
        conn.close()
        flash('Comissão marcada como paga.')
        return redirect(url_for('relatorio_comissoes_gestor'))
    else:
        return redirect(url_for('login'))


@app.route('/gestor')
def gestor_home():
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()

        # Obter todos os produtos
        produtos = conn.execute('SELECT * FROM products').fetchall()

        # Verificar estoque baixo
        produtos_baixo_estoque = conn.execute('SELECT * FROM products WHERE quantity < ?',
                                              (LIMITE_ESTOQUE_BAIXO,)).fetchall()

        # Obter vendas recentes de todos os vendedores
        vendas_recentes = conn.execute('''
            SELECT u.username, p.name, s.quantidade, s.data_venda 
            FROM sales s
            JOIN products p ON s.produto_id = p.id
            JOIN users u ON s.vendedor_id = u.id
            ORDER BY s.data_venda DESC
            LIMIT 5
        ''').fetchall()

        conn.close()
        return render_template('gestor_home.html', username=session['username'], vendas_recentes=vendas_recentes)
    else:
        return redirect(url_for('login'))

import csv
from io import StringIO
from flask import make_response
import pdfkit


@app.route('/gestor/relatorio_vendas_csv')
def exportar_relatorio_vendas_csv():
    if 'role' in session and session['role'] == 'gestor':
        conn = get_db_connection()
        vendas = conn.execute('''
            SELECT s.id, p.name AS produto, u.username AS vendedor, s.quantidade, 
                   s.data_venda, p.price * s.quantidade AS total_venda, s.status
            FROM sales s
            JOIN products p ON s.produto_id = p.id
            JOIN users u ON s.vendedor_id = u.id
        ''').fetchall()
        conn.close()

        # Criar um CSV
        output = StringIO()
        writer = csv.writer(output)

        # Cabeçalhos do CSV
        writer.writerow(['ID Venda', 'Produto', 'Vendedor', 'Quantidade', 'Data Venda', 'Total Venda', 'Status'])

        # Escrever as vendas no CSV
        for venda in vendas:
            writer.writerow([venda['id'], venda['produto'], venda['vendedor'], venda['quantidade'],
                             venda['data_venda'], venda['total_venda'], venda['status']])

        # Preparar a resposta HTTP
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=relatorio_vendas.csv'
        response.headers['Content-Type'] = 'text/csv'

@app.route('/gestor/exportar_relatorio_vendas_pdf')
def exportar_relatorio_vendas_pdf():
            if 'role' in session and session['role'] == 'gestor':
                conn = get_db_connection()
                vendas = conn.execute('''
                    SELECT s.id, p.name AS produto, u.username AS vendedor, s.quantidade, s.data_venda, 
                           p.price * s.quantidade AS total_venda, s.status
                    FROM sales s
                    JOIN products p ON s.produto_id = p.id
                    JOIN users u ON s.vendedor_id = u.id
                ''').fetchall()
                conn.close()

                # Gerar o conteúdo do PDF a partir de um template HTML
                rendered = render_template('relatorio_vendas_pdf.html', vendas=vendas)

                # Usar pdfkit para converter HTML em PDF
                pdf = pdfkit.from_string(rendered, False)

                response = make_response(pdf)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = 'inline; filename=relatorio_vendas.pdf'

                return response


if __name__ == '__main__':
    setup_initial_users()  # Configura usuários iniciais, se necessário
    print(app.url_map)  # Adicione esta linha para ver as rotas definidas
    app.run(debug=True)

