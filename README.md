# PixShop - Sistema de Vendas com Mercado Pago

Bem-vindo ao **PixShop**, um sistema de vendas online que permite a um gestor e a um vendedor administrar produtos, estoque e realizar vendas por meio de um link de pagamento do **Mercado Pago**. Este projeto foi criado em Python (Flask) e utiliza um banco de dados **SQLite**.

## Índice
1. [Recursos Principais](#recursos-principais)
2. [Estrutura de Pastas](#estrutura-de-pastas)
3. [Pré-Requisitos](#pré-requisitos)
4. [Instalação](#instalação)
5. [Configuração do Banco de Dados](#configuração-do-banco-de-dados)
6. [Configuração de Ambiente de Teste (Sandbox) do Mercado Pago](#configuração-de-ambiente-de-teste-sandbox-do-mercado-pago)
7. [Execução](#execução)
8. [Uso](#uso)
9. [Licença](#licença)

---

## Recursos Principais

- **Gestão de Usuários**: O sistema possui dois tipos de usuários: Gestor e Vendedor.
- **Gestão de Produtos**: O gestor pode cadastrar novos produtos, atualizar informações e remover produtos indesejados.
- **Gestão de Estoque**: Atualização automática do estoque após uma venda; o gestor pode ajustar estoques manualmente.
- **Vendas**: O vendedor seleciona produtos para venda e gera um link de pagamento do **Mercado Pago**.
- **Comissões**: Possibilidade de cadastrar e visualizar comissões fixas para cada produto.
- **Relatórios**:
  - Vendedor: Histórico de vendas e comissões.
  - Gestor: Relatório de vendas, estoque e comissões pendentes.

---

## Estrutura de Pastas

```
PixShop/
│
├── create_db.py                # Script de criação/configuração das tabelas (SQLite)
├── PixShop.py                  # Arquivo principal do Flask, contendo as rotas do projeto
├── requirements.txt            # Dependências do projeto
├── README.md                   # Este arquivo
└── templates/                  # Templates HTML
    ├── gestor_home.html
    ├── gestor_produtos.html
    ├── vendedor_home.html
    ├── vendedor_produtos.html
    ├── ...
    └── vendedor_mercadopago_qrcode.html
```

---

## Pré-Requisitos

- **Python 3.7+** instalado
- **pip** (ou **pipenv**/**poetry** caso utilize um gerenciador diferente)
- **Virtualenv** (opcional, mas recomendado)
- Dependências informadas no `requirements.txt` (ex. Flask, requests, sqlite3, etc.)

---

## Instalação

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   cd SEU_REPOSITORIO
   ```

2. **Crie e ative o ambiente virtual** (opcional, mas recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuração do Banco de Dados

1. **Crie as tabelas e usuários iniciais**:
   ```bash
   python create_db.py
   ```
   - Este script criará as tabelas (`users`, `products`, `sales`, `commissions`) e inserirá usuários iniciais (gestor e vendedor).

2. **Verifique se o arquivo `pix_store1.db` foi criado** na pasta do projeto.

---

## Configuração de Ambiente de Teste (Sandbox) do Mercado Pago

Para simular pagamentos:
1. **Obtenha as credenciais de teste** (Public Key e Access Token) no painel de [Desenvolvedores do Mercado Pago](https://www.mercadopago.com.br/developers/pt/guides/testing/sandbox).
2. **Atualize as variáveis** `MERCADO_PAGO_PUBLIC_KEY` e `MERCADO_PAGO_ACCESS_TOKEN` no código principal (`PixShop.py` ou arquivo de configuração).
3. **Crie contas de teste** de comprador e vendedor, se ainda não tiver. Faça login como comprador para testar os pagamentos e como vendedor para gerar links de pagamento.

---

## Execução

1. **Execute a aplicação Flask**:
   ```bash
   python PixShop.py
   ```
   Por padrão, a aplicação estará em `http://127.0.0.1:5000`.

2. **Acesse no navegador**:
   ```
   http://127.0.0.1:5000/
   ```
   - Credenciais iniciais:
     - Gestor: `username: sasilverio, password: Sa315800@`
     - Vendedor: `username: juGabriela, password: Ju202400@`

---

## Uso

### Login como Gestor
- **Cadastrar Produtos**: Inserir nome, descrição, quantidade, preço e comissão (se necessário).
- **Visualizar/Remover Produtos**: Acessar a lista de produtos ou relatórios de estoque.
- **Relatórios**:
  - Estoque Baixo, Ajuste de Estoque
  - Vendas e Comissões
- **Exportar Relatórios** em CSV ou PDF

### Login como Vendedor
- **Visualizar Produtos**: Checar estoque e informações do produto.
- **Realizar Vendas**: Gerar link de pagamento do Mercado Pago para o cliente.
- **Histórico de Vendas**: Checar as vendas feitas e cancelar/excluir vendas.
- **Comissões**: Visualizar a comissão por produto (se cadastrada) e total de comissões pendentes ou pagas.

---

## Licença

Este projeto está licenciado sob os termos da **MIT License**. Consulte o arquivo [LICENSE](LICENSE) para obter mais detalhes.

---

### Observação Final
Caso ocorra o erro “Não é possível pagar para você mesmo” ao testar o pagamento, verifique se:
- As credenciais do **Access Token** são de uma conta de vendedor de teste.
- O e-mail do comprador no campo `payer` é de **outra** conta de teste (comprador), sem conflito de credenciais.
