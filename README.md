# Sistema de Pedidos

Sistema para gerenciamento de pedidos, clientes e relatórios.

## Deploy no Render

1. Crie uma conta no [Render](https://render.com)

2. Clique em "New +" e selecione "Web Service"

3. Conecte com seu repositório Git ou use a opção de deploy manual

4. Configure o serviço:
   - Nome: escolha um nome para seu aplicativo
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Plano: Free

5. Configure as variáveis de ambiente:
   - SECRET_KEY: gere uma chave secreta
   - FLASK_ENV: production

6. Clique em "Create Web Service"

O deploy será feito automaticamente e você receberá uma URL para acessar o sistema.

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes do Python)

## Instalação Local

1. Clone ou baixe este repositório para sua máquina

2. Abra o terminal/prompt de comando e navegue até a pasta do projeto

3. Crie um ambiente virtual Python:
```bash
python -m venv venv
```

4. Ative o ambiente virtual:

No Windows:
```bash
venv\Scripts\activate
```

No Linux/Mac:
```bash
source venv/bin/activate
```

5. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Executando o Sistema

1. Com o ambiente virtual ativado, execute:
```bash
python app.py
```

2. Abra seu navegador e acesse:
```
http://localhost:5000
```

3. Na primeira execução, será criado um usuário administrador:
- Usuário: admin@admin.com
- Senha: admin123

## Funcionalidades

- Gerenciamento de Pedidos
- Cadastro de Clientes
- Relatórios Gerenciais
- Exportação de PDF
- Controle de Status de Pedidos
- Dashboard Operacional

## Suporte

Em caso de dúvidas ou problemas, entre em contato: 