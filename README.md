# E-commerce Distribuído com Supabase

Sistema de e-commerce com autenticação, banco de dados em nuvem (Supabase), cálculo de frete via Correios e processamento assíncrono de pedidos por filas SQS (LocalStack).

**Disciplina:** Sistemas Distribuídos — FURB 2026/1

---

## Stack

| Camada | Tecnologia |
|---|---|
| Auth + Banco de dados | Supabase (Auth + PostgreSQL gerenciado) |
| API REST | FastAPI (Python) |
| Mensageria | Amazon SQS via LocalStack |
| Frete | API dos Correios (PAC + SEDEX) |
| Infra como Código | Terraform |
| Nuvem emulada | LocalStack |
| Frontend | HTML/CSS/JS puro |

---

## Estrutura do projeto

```
ecommerce-supabase/
├── api/
│   ├── main.py              # FastAPI — todos os endpoints
│   ├── auth.py              # Validação JWT do Supabase
│   ├── models.py            # Validação Pydantic
│   ├── viacep.py            # Consulta ViaCEP (valida CEP)
│   └── correios.py          # Cálculo de frete PAC + SEDEX
├── config/
│   ├── settings.py          # Variáveis de ambiente
│   ├── supabase_client.py   # Cliente Supabase (anon + admin)
│   └── sqs.py               # Cliente SQS e loop de consumo
├── consumidores/
│   ├── _base.py             # registrar_evento() no Supabase
│   ├── pagamento.py
│   ├── estoque.py           # Desconta estoque no Supabase
│   ├── fiscal.py            # Gera NF-e e salva no S3
│   ├── logistica.py         # Agenda entrega, atualiza status
│   └── notificacao.py       # Notifica cliente, fecha pedido
├── infra/
│   └── main.tf              # Terraform: SQS + S3 no LocalStack
├── app/
│   └── index.html           # Frontend completo do e-commerce
├── docs/
│   └── supabase_schema.sql  # SQL completo para rodar no Supabase
├── scripts/
│   ├── start_all.bat        # Inicia tudo no Windows
│   └── start_all.sh         # Inicia tudo no Linux/Mac
├── launcher_server.py       # Serve o frontend na porta 3000
├── docker-compose.yml       # LocalStack (SQS + S3)
├── requirements.txt
└── .env.example
```

---

## Passo 1 — Instalar as ferramentas

Antes de qualquer coisa, instale as ferramentas abaixo:

| Ferramenta | Link | Por que é necessária |
|---|---|---|
| Docker Desktop | https://www.docker.com/products/docker-desktop/ | Roda o LocalStack (SQS + S3) em container |
| Anaconda Python| https://anaconda.org/anaconda/python | Linguagem dos serviços |
| Terraform CLI | https://developer.hashicorp.com/terraform/install | Provisiona as filas SQS via código |
| AWS CLI | https://aws.amazon.com/cli/ | Inspecionar filas no LocalStack (opcional, mas útil) |

> **Sobre o AWS CLI:** ele não é obrigatório para rodar o projeto. O LocalStack substitui a AWS real — o CLI só serve para inspecionar filas e bucket pelo terminal durante o desenvolvimento. Se não quiser instalar, o projeto funciona normalmente.

Verifique as instalações no terminal:

```bash
docker --version
python --version
terraform --version
aws --version   # só se instalou
```

### Configurar o AWS CLI com credenciais falsas para o LocalStack

```bash
aws configure
# AWS Access Key ID:     test
# AWS Secret Access Key: test
# Default region name:   us-east-1
# Default output format: json
```

> O LocalStack aceita qualquer valor — use `test` mesmo. Não é a AWS real.

---

## Passo 2 — Criar conta e projeto no Supabase

### 2.1 Criar o projeto

1. Acesse **https://supabase.com** e clique em **Start your project**
2. Crie uma conta com Google, GitHub ou e-mail (gratuito)
3. Clique em **New Project** e preencha:
   - **Name:** `ecommerce-sd`
   - **Database Password:** anote esta senha — você precisará dela
   - **Region:** `South America (São Paulo)`
4. Clique em **Create new project** e aguarde ~2 minutos

### 2.2 Coletar as 4 chaves da API

No painel do projeto: menu lateral → **Settings (engrenagem)** → **API**

| Variável | Onde está no painel |
|---|---|
| `SUPABASE_URL` | Seção **Project URL** → campo `URL` |
| `SUPABASE_ANON_KEY` | Seção **Project API Keys** → `anon public` |
| `SUPABASE_SERVICE_ROLE_KEY` | Seção **Project API Keys** → `service_role` → clique em Reveal |
| `JWT_SECRET` | Seção **JWT Settings** → `JWT Secret` → clique em Reveal |

> Copie esses 4 valores agora — você vai colá-los no arquivo `.env` no Passo 4.

### 2.3 Desativar confirmação de e-mail (para testes)

1. Menu lateral → **Authentication** → **Providers** → **Email**
2. Desative a opção **Confirm email**
3. Clique em **Save**

> Em produção real, mantenha essa opção ativada.

---

## Passo 3 — Criar as tabelas no Supabase (SQL)

1. No painel do Supabase, clique em **SQL Editor** (menu lateral)
2. Clique em **New Query**
3. Abra o arquivo `docs/supabase_schema.sql` do projeto
4. Cole o conteúdo completo no editor
5. Clique em **Run** (ou `Ctrl+Enter`)
6. Você verá: `Success. No rows returned`

### Tabelas criadas

| Tabela | O que armazena |
|---|---|
| `produtos` | Catálogo com 8 produtos já inseridos |
| `enderecos` | Endereços de entrega por usuário |
| `pedidos` | Cada compra realizada |
| `eventos_pedido` | Linha do tempo de processamento dos consumidores |

### Confirmar no Table Editor

Menu lateral → **Table Editor** → você deve ver as 4 tabelas. Em `produtos` deve ter 8 linhas.

---

## Passo 4 — Configurar o arquivo `.env`

### 4.1 Criar o arquivo a partir do exemplo

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

### 4.2 Preencher com os valores do Supabase

Abra o `.env` e substitua pelos valores coletados no Passo 2:

```env
# ── Supabase (cole os valores do painel) ──────────────────
SUPABASE_URL=https://xxxxxxxxxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
JWT_SECRET=sua-jwt-secret-aqui

# ── LocalStack (não mude nada aqui) ───────────────────────
AWS_ENDPOINT_URL=http://localhost:4566
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
S3_BUCKET_NOTAS=ecommerce-notas-fiscais
MAX_RETRIES=3
```

### 4.3 Instalar dependências Python

```bash
# Recomendado: usar ambiente virtual
python -m venv venv

# Ativar o ambiente virtual
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

# Instalar dependências
pip install -r requirements.txt
pip install uvicorn fastapi supabase httpx pydantic python-dotenv python-jose passlib boto3 python-multipart
```

---

## Passo 5 — Subir o Docker (LocalStack)

### 5.1 Garantir que o Docker Desktop está aberto

O ícone da baleia deve aparecer na barra de tarefas antes de continuar.

### 5.2 Subir o container

```bash
docker-compose up -d
```

> Aguarde ~15 segundos para o LocalStack inicializar antes de continuar.

### 5.3 Verificar se está rodando

```bash
docker ps
# Deve aparecer uma linha com "localstack/localstack"

# Verificar saúde do LocalStack
curl http://localhost:4566/_localstack/health
```

Resposta esperada:
```json
{"services": {"sqs": "available", "s3": "available"}, ...}
```

> O PostgreSQL foi removido deste projeto — agora é o Supabase (nuvem). Só o LocalStack precisa de container local.

---

## Passo 6 — Provisionar com Terraform

O Terraform cria as filas SQS e o bucket S3 dentro do LocalStack.

### Recursos criados

- `sqs-pedidos-pagamento`
- `sqs-pedidos-estoque`
- `sqs-pedidos-fiscal`
- `sqs-pedidos-logistica`
- `sqs-pedidos-notificacao`
- `sqs-dead-letter` (DLQ — recebe mensagens que falharam 3 vezes)
- Bucket S3: `ecommerce-notas-fiscais`

### Comandos

```bash
# Entrar na pasta infra
cd infra

# Inicializar (baixa o provider AWS — só precisa rodar uma vez)
terraform init

# Ver o que vai ser criado
terraform plan

# Criar os recursos no LocalStack
terraform apply -auto-approve

# Criar bucket para salvar NF-es
aws --endpoint-url=http://localhost:4566 s3 mb s3://ecommerce-notas-fiscais

# Voltar para a raiz
cd ..
```

### Verificar filas criadas

```bash
python -c "import boto3; boto3.client('s3', endpoint_url='http://localhost:4566', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test').create_bucket(Bucket='ecommerce-notas-fiscais')"
```

Deve listar 6 URLs com `sqs-pedidos-*` e `sqs-dead-letter`.

> **Importante:** Se reiniciar o Docker, o LocalStack perde todos os dados. Rode `terraform apply` de novo sempre que restartar os containers.

---

## Passo 7 — Iniciar a API e os consumidores

### Opção A — Script automático (recomendado para a apresentação)

```bash
# Windows
scripts\start_all.bat

# Mac/Linux
bash scripts/start_all.sh
```

Isso abre 7 processos automaticamente e o navegador no `http://localhost:3000`.

### Opção B — Manual (um terminal por processo)

| Terminal | Comando | O que faz |
|---|---|---|
| 1 | `uvicorn api.main:app --reload --port 8000` | API FastAPI |
| 2 | `python launcher_server.py` | Frontend (porta 3000) |
| 3 | `python consumidores/pagamento.py` | Consumidor de pagamento |
| 4 | `python consumidores/estoque.py` | Consumidor de estoque |
| 5 | `python consumidores/fiscal.py` | Consumidor fiscal + S3 |
| 6 | `python consumidores/logistica.py` | Consumidor de logística |
| 7 | `python consumidores/notificacao.py` | Consumidor de notificação |

### Verificar a API no ar

```bash
curl http://localhost:8000/
# Resposta: {"status": "ok", "versao": "2.0.0", ...}
```

Documentação Swagger: **http://localhost:8000/docs**

---

## Passo 8 — Testar o sistema

### Via frontend (recomendado)

Acesse **http://localhost:3000** e siga o fluxo:

1. Clique em **Entrar** → **Criar conta** → preencha nome, e-mail e senha
2. Faça login com as credenciais criadas
3. Na tela de **Produtos**, clique em um produto para abrir os detalhes
4. Adicione ao carrinho
5. Vá para o **Carrinho**
6. Cadastre um **Endereço** (o CEP é preenchido automaticamente via ViaCEP)
7. Selecione o endereço — o frete PAC e SEDEX é calculado automaticamente
8. Escolha a forma de pagamento e clique em **Finalizar Pedido**
9. Em **Meus Pedidos**, clique em **Ver detalhes** para acompanhar o processamento de cada serviço

### Via curl (linha de comando)

```bash
# 1. Cadastrar usuário
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@email.com","senha":"Senha123!","nome":"João Silva"}'

# 2. Login (guarde o access_token da resposta)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@email.com","senha":"Senha123!"}'

# 3. Ver produtos (copie o "id" de um produto)
curl http://localhost:8000/produtos

# 4. Calcular frete
curl "http://localhost:8000/frete?cep=89010000"

# 5. Cadastrar endereço (substitua TOKEN pelo access_token do login)
curl -X POST http://localhost:8000/enderecos \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"apelido":"Casa","cep":"89010000","logradouro":"Rua Sete de Setembro",
       "numero":"100","bairro":"Centro","cidade":"Blumenau","uf":"SC","principal":true}'

# 6. Criar pedido (substitua PRODUTO_ID e ENDERECO_ID pelos IDs retornados acima)
curl -X POST http://localhost:8000/pedidos \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"produto_id":"PRODUTO_ID","quantidade":1,
       "endereco_id":"ENDERECO_ID","forma_pagamento":"pix"}'

# 7. Ver status do pedido (substitua PEDIDO_ID pelo id retornado acima)
curl http://localhost:8000/pedidos/PEDIDO_ID \
  -H "Authorization: Bearer TOKEN"
```

---

## Fluxo do sistema

```
Usuário (login via Supabase Auth)
    │
    ▼
POST /pedidos  (JWT no header Authorization)
    │
    ├─► Supabase: busca produto e valida estoque
    ├─► Supabase: busca endereço do usuário
    ├─► Correios: calcula frete PAC e SEDEX
    ├─► Supabase: salva pedido (status = PENDENTE)
    └─► SQS (LocalStack): publica em 5 filas simultâneas
              │
    ┌─────────┴──────────────────────────────────┐
    ▼         ▼         ▼          ▼             ▼
 Pagamento Estoque   Fiscal    Logística     Notificação
    │         │         │          │             │
    │         │      salva NF-e    │        status = CONCLUIDO
    │      desconta    no S3   status =         (Supabase)
    │      estoque             EM_TRANSITO
    │      (Supabase)          (Supabase)
    │
    └─── todos registram eventos em eventos_pedido (Supabase)
```

---

## Requisitos do trabalho atendidos

| Requisito | Tecnologia | Status |
|---|---|---|
| Banco de dados (não SQLite) | Supabase — PostgreSQL gerenciado em nuvem | ✅ |
| Mensageria | Amazon SQS via LocalStack | ✅ |
| API externa | ViaCEP (validação de CEP) + API dos Correios (frete) | ✅ |
| Mínimo 2 serviços | FastAPI + 5 consumidores Python independentes | ✅ |
| Uso de nuvem | Supabase (nuvem real) + LocalStack + Terraform | ✅ |

---

## Checklist antes da apresentação

- [ ] Docker Desktop aberto e rodando
- [ ] `docker-compose up -d` executado
- [ ] `terraform apply` executado e 6 filas criadas
- [ ] `.env` preenchido com as 4 chaves do Supabase
- [ ] `pip install -r requirements.txt` concluído sem erros
- [ ] API respondendo em http://localhost:8000
- [ ] Frontend abrindo em http://localhost:3000
- [ ] 5 consumidores rodando (aguardando mensagens nos terminais)
- [ ] Cadastro e login de usuário funcionando
- [ ] Endereço cadastrado com busca de CEP automática
- [ ] Cálculo de frete retornando PAC e SEDEX
- [ ] Pedido criado e processado pelos 5 consumidores
- [ ] Eventos aparecendo em "Meus Pedidos"

---

## Problemas comuns

**`401 Unauthorized` em rotas protegidas**
O `JWT_SECRET` no `.env` está errado. Copie exatamente de Settings → API → JWT Settings → JWT Secret.

**Filas SQS não encontradas**
O LocalStack foi reiniciado e perdeu os dados. Rode `terraform apply -auto-approve` novamente.

**`pip install` falha com erro de permissão**
Ative o ambiente virtual antes: `venv\Scripts\activate` (Windows) ou `source venv/bin/activate` (Mac/Linux).

**`docker: command not found`**
Inicie o Docker Desktop antes de rodar qualquer comando docker.

**Produto sem `produto_id`**
Acesse `http://localhost:8000/produtos` para ver os IDs reais dos produtos inseridos pelo SQL.

**Frete retorna valores simulados**
A API dos Correios pode estar fora do ar ou bloqueando a requisição. O sistema usa um fallback automático com valores estimados por região — isso não impede o funcionamento.
