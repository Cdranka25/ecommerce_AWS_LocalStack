# E-commerce Distribuído com Supabase, SQS e LocalStack

Sistema de **e-commerce** desenvolvido para fins acadêmicos, simulando uma loja virtual completa: cadastro/login de usuários, catálogo de produtos, cálculo de frete, finalização de pedidos e processamento assíncrono em segundo plano (pagamento, baixa de estoque, emissão fiscal, logística e notificação ao cliente).

A arquitetura reproduz, em pequena escala, um sistema real de e-commerce distribuído: a API recebe o pedido e o publica em **filas de mensagens (SQS)**, enquanto **5 serviços consumidores independentes** processam cada etapa do pedido em paralelo, sem travar a resposta ao usuário.

**Disciplina:** Sistemas Distribuídos — FURB, 2026/1

---

## Sumário

- [Sobre o projeto](##-Sobre-o-projeto)
- [Arquitetura e stack](#-arquitetura-e-stack)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Pré-requisitos](#-pré-requisitos--o-que-baixar-e-instalar)
- [Passo 1 — Obter o projeto](#passo-1--obter-o-projeto)
- [Passo 2 — Ambiente Python (Anaconda)](#passo-2--criar-o-ambiente-python-com-anaconda)
- [Passo 3 — Criar o projeto no Supabase](#passo-3--criar-conta-e-projeto-no-supabase)
- [Passo 4 — Criar as tabelas no Supabase](#passo-4--criar-as-tabelas-no-supabase-sql)
- [Passo 5 — Configurar o arquivo .env](#passo-5--configurar-o-arquivo-env)
- [Passo 6 — Subir o Docker (LocalStack)](#passo-6--subir-o-docker-localstack)
- [Passo 7 — Provisionar com Terraform](#passo-7--provisionar-a-infraestrutura-com-terraform)
- [Passo 8 — Iniciar a aplicação](#passo-8--iniciar-a-api-o-frontend-e-os-consumidores)
- [Passo 9 — Testar o sistema](#passo-9--testar-o-sistema)
- [Endpoints da API](#-endpoints-da-api)
- [Fluxo do sistema](#-fluxo-do-sistema)
- [Como parar tudo](#-como-parar-tudo)
- [Solução de problemas comuns](#-solução-de-problemas-comuns)
- [Checklist antes da apresentação](#-checklist-antes-da-apresentação)
- [Requisitos do trabalho atendidos](#-requisitos-do-trabalho-atendidos)

---

## Sobre o projeto

O objetivo é simular, de ponta a ponta, o fluxo de compra de um e-commerce real:

1. O cliente cria conta e faz login (autenticação JWT via **Supabase Auth**).
2. Navega pelo catálogo de produtos (armazenado no **Supabase/PostgreSQL**).
3. Cadastra um endereço de entrega — o CEP é validado/preenchido automaticamente via **API ViaCEP**.
4. O sistema calcula o frete (**PAC** e **SEDEX**) consultando a **API dos Correios**.
5. Ao finalizar a compra, a API salva o pedido no banco e o publica em **5 filas SQS** (rodando localmente via **LocalStack**, que emula a nuvem AWS).
6. **5 serviços consumidores** (processos Python independentes) escutam essas filas e processam o pedido em paralelo:
   - **Pagamento** — valida e aprova/recusa o pagamento;
   - **Estoque** — dá baixa na quantidade do produto;
   - **Fiscal** — gera a nota fiscal e salva um arquivo no **S3** (LocalStack);
   - **Logística** — define transportadora e agenda a entrega;
   - **Notificação** — notifica o cliente e conclui o pedido.
7. Cada etapa registra um evento na tabela `eventos_pedido`, permitindo acompanhar em tempo real, pelo frontend, todo o processamento do pedido (como uma linha do tempo).

Esse desenho demonstra, na prática, conceitos de **sistemas distribuídos**: comunicação assíncrona via mensageria, desacoplamento de serviços, infraestrutura como código (Terraform) e uso de nuvem (real + emulada).

---

## Arquitetura e stack

| Camada | Tecnologia |
|---|---|
| Autenticação + Banco de dados | **Supabase** (Auth + PostgreSQL gerenciado, em nuvem real) |
| API REST | **FastAPI** (Python) |
| Mensageria assíncrona | **Amazon SQS** via **LocalStack** (emulação local da AWS) |
| Armazenamento de arquivos | **Amazon S3** via LocalStack (notas fiscais) |
| Cálculo de frete | **API dos Correios** (PAC + SEDEX) |
| Validação de CEP | **API ViaCEP** |
| Infraestrutura como código | **Terraform** |
| Frontend | HTML + CSS + JavaScript puro |
| Ambiente Python | **Anaconda** |

---

## Estrutura do projeto

```
ecommerce_AWS_LocalStack/
├── api/
│   ├── main.py              # FastAPI — todos os endpoints
│   ├── auth.py               # Validação do JWT do Supabase
│   ├── models.py              # Schemas de validação (Pydantic)
│   ├── viacep.py               # Consulta ViaCEP (valida/completa CEP)
│   └── correios.py              # Cálculo de frete PAC + SEDEX
├── config/
│   ├── settings.py           # Leitura das variáveis de ambiente (.env)
│   ├── supabase_client.py     # Cliente Supabase (anon + admin)
│   └── sqs.py                  # Cliente SQS, publicação e consumo de filas
├── consumidores/                # Os 5 serviços assíncronos
│   ├── _base.py               # registrar_evento() — grava histórico no Supabase
│   ├── pagamento.py
│   ├── estoque.py
│   ├── fiscal.py                # Gera NF-e e salva no S3 (LocalStack)
│   ├── logistica.py
│   └── notificacao.py
├── infra/
│   └── main.tf                # Terraform: cria as filas SQS no LocalStack
├── app/
│   └── index.html             # Frontend completo do e-commerce
├── docs/
│   ├── supabase_schema.sql        # Script SQL para criar as tabelas no Supabase
│   └── supabase_insert_product.sql # Inserts extras de produtos (opcional)
├── scripts/
│   ├── start_all.bat          # Inicia tudo no Windows (Anaconda base)
│   └── start_all.sh           # Inicia tudo no Linux/Mac
├── logs/                       # Logs gerados pelos serviços
├── launcher_server.py          # Inicia TUDO automaticamente (recomendado)
├── check_env.py                 # Utilitário de debug do token JWT (opcional)
├── docker-compose.yml           # Sobe o LocalStack (SQS + S3)
├── requirements.txt
└── .env_example                  # Modelo do arquivo de variáveis de ambiente
```

---

## Pré-requisitos — o que baixar e instalar

Instale as ferramentas abaixo **antes de começar**:

| Ferramenta | Link de download | Para que serve |
|---|---|---|
| **Anaconda** (Python) | https://www.anaconda.com/download | Ambiente e dependências Python do projeto |
| **Docker Desktop** | https://www.docker.com/products/docker-desktop/ | Roda o LocalStack (SQS + S3) em container |
| **Terraform CLI** | https://developer.hashicorp.com/terraform/install | Provisiona as filas SQS via código |
| **AWS CLI** *(opcional)* | https://aws.amazon.com/cli/ | Inspecionar filas/bucket no LocalStack pelo terminal |
| **Conta no Supabase** | https://supabase.com | Banco de dados + autenticação em nuvem (gratuito) |

> **Sobre o AWS CLI:** não é obrigatório para o projeto funcionar — o LocalStack substitui a AWS real e o `boto3` (já incluso no `requirements.txt`) é quem fala com ele. O AWS CLI serve apenas como ferramenta extra para inspecionar filas e o bucket manualmente.

Depois de instalar, abra o **Anaconda Prompt** (Windows) ou um terminal com o conda inicializado (Mac/Linux) e confira as versões:

```bash
conda --version
python --version
docker --version
docker-compose --version
terraform --version
aws --version          # apenas se você instalou o AWS CLI
```

---

## Passo 1 — Obter o projeto

Se você recebeu o projeto como `.zip`, apenas extraia em uma pasta de sua preferência. Se for clonar do Git:

```bash
git clone <url-do-repositorio>
cd ecommerce_AWS_LocalStack
```

Todos os comandos a seguir devem ser executados **dentro da pasta raiz do projeto**.

---

## Passo 2 — Criar o ambiente Python com Anaconda

Abra o **Anaconda Prompt** (Windows) ou o terminal (Mac/Linux) na pasta do projeto.

### 2.1 Criar um ambiente conda dedicado (recomendado)

```bash
conda create -n ecommerce-sd python=3.11 -y
conda activate ecommerce-sd
```

> Mantenha esse ambiente **ativado** (`conda activate ecommerce-sd`) em **todo terminal novo** que você abrir para rodar qualquer parte do projeto (API, consumidores, scripts).

### 2.2 Instalar as dependências

```bash
pip install -r requirements.txt
```

Isso instala: FastAPI, Uvicorn, Supabase SDK, httpx, Pydantic, python-dotenv, python-jose, passlib, boto3 e python-multipart.

> **Sobre o `scripts\start_all.bat`:** esse script localiza automaticamente o Python do **ambiente base** do Anaconda (não de um ambiente conda customizado). Se você criar um ambiente próprio (`ecommerce-sd`), use o `launcher_server.py` (Passo 8) ou o modo manual para iniciar os serviços — eles funcionam corretamente com qualquer ambiente ativado. Alternativamente, instale as dependências direto no ambiente `base` do Anaconda para usar o `.bat` sem ajustes.

---

## Passo 3 — Criar conta e projeto no Supabase

### 3.1 Criar o projeto

1. Acesse **https://supabase.com** e clique em **Start your project**.
2. Crie uma conta com Google, GitHub ou e-mail (gratuito).
3. Clique em **New Project** e preencha:
   - **Name:** `ecommerce-sd`
   - **Database Password:** anote esta senha — você vai usá-la (opcionalmente) no `.env`.
   - **Region:** `South America (São Paulo)`
4. Clique em **Create new project** e aguarde cerca de 2 minutos.

### 3.2 Coletar as chaves da API

No painel do projeto: menu lateral → **Settings** (ícone de engrenagem) → **API**.

| Variável | Onde encontrar no painel |
|---|---|
| `SUPABASE_URL` | Seção **Project URL** → campo `URL` |
| `SUPABASE_ANON_KEY` | Seção **Project API Keys** → `anon public` |
| `SUPABASE_SERVICE_ROLE_KEY` | Seção **Project API Keys** → `service_role` → clique em **Reveal** |
| `JWT_SECRET` | Seção **JWT Settings** → `JWT Secret` → clique em **Reveal** |

> Copie esses 4 valores agora — você vai colá-los no arquivo `.env` no Passo 5.

### 3.3 Desativar confirmação de e-mail (somente para testes/apresentação)

1. Menu lateral → **Authentication** → **Providers** → **Email**.
2. Desative a opção **Confirm email**.
3. Clique em **Save**.

> Em um ambiente de produção real, mantenha essa opção ativada.

---

## Passo 4 — Criar as tabelas no Supabase (SQL)

1. No painel do Supabase, abra **SQL Editor** (menu lateral).
2. Clique em **New Query**.
3. Abra o arquivo `docs/supabase_schema.sql` do projeto, copie todo o conteúdo e cole no editor.
4. Clique em **Run** (ou `Ctrl+Enter`).
5. Deve aparecer: `Success. No rows returned`.

### Tabelas criadas

| Tabela | O que armazena |
|---|---|
| `produtos` | Catálogo de produtos (já vem com itens inseridos pelo script) |
| `enderecos` | Endereços de entrega cadastrados por cada usuário |
| `pedidos` | Cada compra realizada, com status do processamento |
| `eventos_pedido` | Linha do tempo de eventos gerados pelos 5 consumidores |

Confirme em **Table Editor** (menu lateral) que as 4 tabelas existem e que `produtos` tem linhas. Se quiser produtos extras, rode também `docs/supabase_insert_product.sql` no SQL Editor.

---

## Passo 5 — Configurar o arquivo `.env`

### 5.1 Criar o arquivo a partir do modelo

O arquivo de modelo se chama **`.env_example`** (sem ponto antes de `example`). Copie-o para `.env`:

```bash
# Windows (cmd / Anaconda Prompt)
copy .env_example .env

# Mac/Linux
cp .env_example .env
```

### 5.2 Preencher com os valores do Supabase

Abra o `.env` em um editor de texto e preencha:

```env
# ── Supabase (cole os valores coletados no Passo 3.2) ──────
SUPABASE_URL=https://xxxxxxxxxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
JWT_SECRET=sua-jwt-secret-aqui
PROJECT_PASSWORD=senha-do-banco-no-supabase   # apenas anotação, não é lida pelo código

# ── LocalStack / AWS (em geral não precisa alterar) ─────────
AWS_ENDPOINT_URL=http://localhost:4566
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
S3_BUCKET_NOTAS=ecommerce-notas-fiscais
MAX_RETRIES=3
```

> O arquivo `.env` contém segredos e já está no `.gitignore` — nunca o suba para um repositório público.

---

## Passo 6 — Subir o Docker (LocalStack)

O `docker-compose.yml` sobe **apenas o LocalStack**, responsável por emular as filas SQS e o bucket S3 (não há mais PostgreSQL local — o banco agora é o Supabase, na nuvem).

### 6.1 Abrir o Docker Desktop

Garanta que o ícone da baleia esteja ativo na barra de tarefas/menu antes de continuar.

### 6.2 Subir o container

No terminal (com o ambiente conda ativado, dentro da pasta do projeto):

```bash
docker-compose up -d
```

> Aguarde ~15 segundos para o LocalStack terminar de inicializar.

### 6.3 Verificar se está rodando

```bash
docker ps
```

Deve aparecer uma linha com `localstack/localstack` e o container `ecommerce_localstack`.

```bash
curl http://localhost:4566/_localstack/health
```

Resposta esperada (resumida):
```json
{"services": {"sqs": "available", "s3": "available"}, ...}
```

### 6.4 (Opcional) Configurar o AWS CLI com credenciais falsas

Só necessário se você instalou o AWS CLI e quer inspecionar filas/bucket manualmente:

```bash
aws configure
# AWS Access Key ID:     test
# AWS Secret Access Key: test
# Default region name:   us-east-1
# Default output format: json
```

> O LocalStack aceita qualquer valor — use `test`. Não é a AWS real, então nenhuma cobrança é gerada.

---

## Passo 7 — Provisionar a infraestrutura com Terraform

O Terraform cria, dentro do LocalStack, as filas SQS usadas pelos 5 consumidores.

### Recursos criados (`infra/main.tf`)

- `sqs-pedidos-pagamento`
- `sqs-pedidos-estoque`
- `sqs-pedidos-fiscal`
- `sqs-pedidos-logistica`
- `sqs-pedidos-notificacao`
- `sqs-dead-letter` (DLQ — recebe mensagens que falharam 3 vezes)

### Comandos

```bash
# Entrar na pasta de infraestrutura
cd infra

# Inicializar o provider AWS (só precisa rodar uma vez)
terraform init

# (opcional) ver o que será criado
terraform plan

# Criar os recursos no LocalStack
terraform apply -auto-approve

# Voltar para a raiz do projeto
cd ..
```

### Criar o bucket S3 para as notas fiscais

O bucket não é criado pelo Terraform — crie via AWS CLI ou via Python:

```bash
# Com AWS CLI instalado
aws --endpoint-url=http://localhost:4566 s3 mb s3://ecommerce-notas-fiscais

# Alternativa via Python (sem precisar do AWS CLI)
python -c "import boto3; boto3.client('s3', endpoint_url='http://localhost:4566', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test').create_bucket(Bucket='ecommerce-notas-fiscais')"
```

### Verificar as filas criadas

```bash
aws --endpoint-url=http://localhost:4566 sqs list-queues
```

Devem aparecer 6 URLs: as 5 filas `sqs-pedidos-*` e a `sqs-dead-letter`.

> **Importante:** sempre que o container do Docker for reiniciado, o LocalStack perde os dados (incluindo as filas). Rode `terraform apply -auto-approve` novamente após qualquer `docker-compose down`/restart. O `launcher_server.py` (próximo passo) já faz isso automaticamente para você.

---

## Passo 8 — Iniciar a API, o frontend e os consumidores

Existem três formas de iniciar o sistema. Escolha a que preferir.

### Opção A — `launcher_server.py` (recomendado, multiplataforma quando ativado em conda)

Com o ambiente conda **ativado**, na raiz do projeto:

```bash
python launcher_server.py
```

Esse script faz tudo sozinho:
1. Aguarda o LocalStack ficar disponível e roda `terraform apply` automaticamente;
2. Sobe a API FastAPI (porta 8000);
3. Sobe os 5 consumidores em segundo plano (logs em `logs/`);
4. Sobe o frontend (porta 3000) e **abre o navegador automaticamente**.

Para encerrar, pressione `CTRL+C` no terminal onde ele está rodando.

> Funciona em Windows — usa recursos específicos do Windows (`taskkill`, processos sem janela) para gerenciar os serviços em segundo plano.

### Opção B — Scripts `start_all`

```bash
# Windows (Anaconda Prompt, ambiente "base")
scripts\start_all.bat

# Mac/Linux (com o ambiente conda ativado)
bash scripts/start_all.sh
```

Abre um processo/janela por serviço (API, frontend e os 5 consumidores).

> No Windows, o `start_all.bat` localiza automaticamente o Python do ambiente **base** do Anaconda — não de ambientes conda customizados.

### Opção C — Manual (um terminal por processo)

Útil para depurar um serviço específico. Em **cada terminal**, ative o ambiente conda (`conda activate ecommerce-sd`) e rode:

| Terminal | Comando | O que faz |
|---|---|---|
| 1 | `uvicorn api.main:app --reload --port 8000` | API FastAPI |
| 2 | `python launcher_server.py` *(ou um servidor estático simples)* | Frontend, porta 3000 |
| 3 | `python consumidores/pagamento.py` | Consumidor de pagamento |
| 4 | `python consumidores/estoque.py` | Consumidor de estoque |
| 5 | `python consumidores/fiscal.py` | Consumidor fiscal + S3 |
| 6 | `python consumidores/logistica.py` | Consumidor de logística |
| 7 | `python consumidores/notificacao.py` | Consumidor de notificação |

### Verificar a API no ar

```bash
curl http://localhost:8000/
# Resposta esperada: {"status": "ok", "versao": "2.0.0", ...}
```

Documentação interativa (Swagger): **http://localhost:8000/docs**

---

## Passo 9 — Testar o sistema

### Via frontend (recomendado)

Acesse **http://localhost:3000** e siga o fluxo:

1. Clique em **Entrar** → **Criar conta** → preencha nome, e-mail e senha.
2. Faça login com as credenciais criadas.
3. Na tela de **Produtos**, clique em um produto para ver os detalhes.
4. Adicione ao carrinho.
5. Vá até o **Carrinho**.
6. Cadastre um **Endereço** (o CEP é preenchido automaticamente via ViaCEP).
7. Selecione o endereço — o frete PAC e SEDEX é calculado automaticamente.
8. Escolha a forma de pagamento e clique em **Finalizar Pedido**.
9. Em **Meus Pedidos**, clique em **Ver detalhes** para acompanhar, em tempo real, o processamento por cada um dos 5 serviços.

### Via curl (linha de comando)

```bash
# 1. Cadastrar usuário
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"teste@email.com\",\"senha\":\"Senha123!\",\"nome\":\"João Silva\"}"

# 2. Login (guarde o access_token retornado)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"teste@email.com\",\"senha\":\"Senha123!\"}"

# 3. Ver produtos (copie o "id" de um produto)
curl http://localhost:8000/produtos

# 4. Calcular frete
curl "http://localhost:8000/frete?cep=89010000"

# 5. Cadastrar endereço (substitua TOKEN pelo access_token do login)
curl -X POST http://localhost:8000/enderecos \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"apelido\":\"Casa\",\"cep\":\"89010000\",\"logradouro\":\"Rua Sete de Setembro\",\"numero\":\"100\",\"bairro\":\"Centro\",\"cidade\":\"Blumenau\",\"uf\":\"SC\",\"principal\":true}"

# 6. Criar pedido (substitua PRODUTO_ID e ENDERECO_ID pelos IDs retornados acima)
curl -X POST http://localhost:8000/pedidos \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"produto_id\":\"PRODUTO_ID\",\"quantidade\":1,\"endereco_id\":\"ENDERECO_ID\",\"forma_pagamento\":\"pix\"}"

# 7. Ver status do pedido (substitua PEDIDO_ID pelo id retornado acima)
curl http://localhost:8000/pedidos/PEDIDO_ID \
  -H "Authorization: Bearer TOKEN"
```

> No Windows (cmd), aspas duplas escapadas (`\"`) funcionam como acima. No PowerShell ou Git Bash, prefira aspas simples envolvendo o JSON.

---

## Endpoints da API

| Método | Rota | Autenticação | Descrição |
|---|---|---|---|
| `POST` | `/auth/register` | Cadastro de usuário |
| `POST` | `/auth/login`  | Login (retorna JWT) |
| `POST` | `/auth/logout`  | Logout |
| `POST` | `/auth/refresh` | Renova o token de acesso |
| `GET` | `/produtos`  | Lista os produtos disponíveis |
| `GET` | `/produtos/{id}` | Detalha um produto |
| `GET` | `/enderecos`  | Lista endereços do usuário logado |
| `POST` | `/enderecos`  | Cadastra um endereço |
| `DELETE` | `/enderecos/{id}`  | Remove um endereço |
| `GET` | `/frete?cep=XXXXXXXX` | — | Calcula frete PAC e SEDEX |
| `POST` | `/pedidos`  | Cria um pedido (publica nas filas SQS) |
| `GET` | `/pedidos`  | Lista pedidos do usuário logado |
| `GET` | `/pedidos/{id}`  | Detalha o pedido e os eventos de processamento |
| `GET` | `/` | Health check da API |

Documentação interativa completa em **http://localhost:8000/docs**.

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
    └─► SQS (LocalStack): publica em 5 filas simultaneamente
              │
    ┌─────────┴──────────────────────────────────┐
    ▼         ▼         ▼          ▼              ▼
Pagamento  Estoque    Fiscal    Logística     Notificação
    │         │         │          │              │
    │      desconta   gera NF-e  agenda        marca pedido
 aprova/   estoque     e salva   entrega        como
 recusa   (Supabase)   no S3   (Supabase)      CONCLUIDO
                                                (Supabase)
    │
    └──── todos os serviços registram eventos em eventos_pedido (Supabase)
```

---

## Como parar tudo

```bash
# Encerrar a API, o frontend e os consumidores: CTRL+C no(s) terminal(is) ou,
# se usou o launcher_server.py / start_all.bat, feche as janelas/processos abertos.

# Parar as tarefas
taskkill /F /IM python.exe

# Derrubar o LocalStack
docker-compose down

# Sair do ambiente conda
conda deactivate
```

> Lembre-se: ao subir o LocalStack novamente, é preciso rodar `terraform apply -auto-approve` de novo (ou usar o `launcher_server.py`, que faz isso automaticamente).

---

## Solução de problemas comuns

**`401 Unauthorized` em rotas protegidas**
O `JWT_SECRET` no `.env` está errado. Copie exatamente de **Settings → API → JWT Settings → JWT Secret** no painel do Supabase.

**Filas SQS não encontradas / erro ao publicar nas filas**
O LocalStack foi reiniciado e perdeu os dados em memória. Rode `terraform apply -auto-approve` novamente dentro da pasta `infra`.

**`docker-compose: command not found` ou erro de conexão com o Docker**
Abra o Docker Desktop e aguarde ele inicializar completamente antes de rodar qualquer comando `docker`.

**`pip install` falha ou pacotes não são encontrados ao rodar os scripts**
Confirme que o ambiente conda está ativado no terminal: `conda activate ecommerce-sd`. Se usar o `start_all.bat`, lembre-se que ele usa o Python do ambiente **base** do Anaconda.

**`terraform: command not found`**
O Terraform não está no PATH do sistema. Reinstale seguindo o site oficial e reabra o terminal.

**Produto sem `produto_id`**
Acesse `http://localhost:8000/produtos` para ver os IDs reais inseridos pelo script SQL.

**Frete retorna valores simulados**
A API dos Correios/BrasilAPI pode estar fora do ar ou bloqueando a requisição. O sistema possui um fallback automático com valores estimados — isso não impede o funcionamento do fluxo de compra.

**Porta 3000 ou 8000 já em uso**
Feche processos anteriores (`CTRL+C` nos terminais antigos) ou, no Windows, finalize via Gerenciador de Tarefas processos `python.exe`/`uvicorn.exe` pendentes.

---

## Checklist para utilização

- [ ] Anaconda instalado e ambiente conda ativado (`conda activate ecommerce-sd`)
- [ ] `pip install -r requirements.txt` concluído sem erros
- [ ] Docker Desktop aberto e rodando
- [ ] `docker-compose up -d` executado
- [ ] `terraform apply -auto-approve` executado — 6 filas SQS criadas
- [ ] Bucket S3 `ecommerce-notas-fiscais` criado
- [ ] Projeto Supabase criado e SQL (`docs/supabase_schema.sql`) executado
- [ ] `.env` preenchido com as chaves do Supabase (a partir do `.env_example`)
- [ ] API respondendo em http://localhost:8000
- [ ] Frontend abrindo em http://localhost:3000
- [ ] 5 consumidores rodando (verificar logs em `logs/` ou os terminais)
- [ ] Cadastro e login de usuário funcionando
- [ ] Endereço cadastrado com busca de CEP automática
- [ ] Cálculo de frete retornando PAC e SEDEX
- [ ] Pedido criado e processado pelos 5 consumidores
- [ ] Eventos aparecendo em "Meus Pedidos"

---

## Requisitos do trabalho atendidos

| Requisito | Tecnologia utilizada |
|---|---|
| Banco de dados (não SQLite) | Supabase — PostgreSQL gerenciado em nuvem |
| Mensageria assíncrona | Amazon SQS via LocalStack |
| API externa | ViaCEP (validação de CEP) + API dos Correios (frete) |
| Mínimo de 2 serviços independentes | FastAPI + 5 consumidores Python independentes |
| Uso de nuvem | Supabase (nuvem real) + LocalStack + Terraform (IaC) |
