# Assistente Cidadão DF — Guia Completo do Zero

Backend do assistente cidadão via WhatsApp para o Distrito Federal.
Feito para o hackathon — tudo gratuito, tudo explicado passo a passo.

---

## O que esse sistema faz

- Cidadão manda mensagem no WhatsApp
- O bot responde com menus e orienta sobre saúde, denúncias e serviços digitais
- Denúncias são classificadas com IA (RAG com normas do TCU) e salvas no banco
- Painel público mostra denúncias agregadas por categoria e região do DF

---

## Arquitetura resumida

```
WhatsApp do Cidadão
       ↓
Evolution API (Docker local)
       ↓ webhook
FastAPI (seu backend Python)
       ↓
   Orquestrador
   ├── Agente Saúde    → CNES API + scraping IGES
   ├── Agente Ouvidoria → ChromaDB RAG + Supabase
   └── Agente Educativo → Groq Vision (lê prints)
       ↓
    Groq (LLM) + Redis (contexto) + Supabase (banco)
```

---

## Pré-requisitos — instale antes de tudo

### 1. Python 3.11+
Verifique se já tem: abra o terminal e digite:
```bash
python --version
```
Se não tiver, baixe em: https://python.org/downloads
Instale marcando a opção "Add Python to PATH"

### 2. Docker Desktop
Baixe em: https://docker.com/products/docker-desktop
Instale e abra — precisa estar rodando no fundo.

Para verificar se funcionou:
```bash
docker --version
```

### 3. Git (opcional mas recomendado)
Baixe em: https://git-scm.com

### 4. ngrok (expõe seu servidor local para a internet)
Baixe em: https://ngrok.com/download
Crie conta gratuita em ngrok.com — você vai precisar do token.

---

## Passo 1 — Criar as contas gratuitas

### Groq (IA — a mais importante)
1. Acesse: https://console.groq.com
2. Clique em "Sign Up" e crie conta com seu email
3. Vá em "API Keys" no menu lateral esquerdo
4. Clique em "Create API Key"
5. Copie a chave — começa com `gsk_`
6. Guarde essa chave, vai precisar ela depois

**Limite gratuito:** 1.000 requisições/dia — suficiente para o hackathon.

### Supabase (banco de dados)
1. Acesse: https://supabase.com
2. Clique em "Start your project"
3. Crie conta com GitHub ou email
4. Clique em "New project"
5. Escolha um nome (ex: cidadao-df), senha forte, região São Paulo
6. Aguarde criar (1-2 minutos)
7. Vá em "Project Settings" → "API"
8. Copie:
   - **Project URL** (parece: https://xxxx.supabase.co)
   - **service_role key** (a chave longa — não a anon key)

### Redis — Upstash (cache gratuito)
1. Acesse: https://upstash.com
2. Crie conta gratuita
3. Clique em "Create Database"
4. Escolha Redis, nome "cidadao-df", região "São Paulo"
5. Clique em "Details" → copie a **Redis URL** (começa com redis://)

---

## Passo 2 — Baixar e configurar o projeto

### Abra o terminal
- **Windows:** pressione `Win + R`, digite `cmd`, Enter
- **Mac:** pressione `Cmd + Espaço`, digite `terminal`, Enter

### Entre na pasta do projeto
```bash
cd cidadao-df
```

### Crie o arquivo .env
Copie o arquivo de exemplo:
```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Abra o arquivo `.env` em qualquer editor de texto (Notepad, VS Code, etc.)
e preencha com as chaves que você copiou no passo anterior:

```env
GROQ_API_KEY=gsk_sua_chave_aqui
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJxxxxx...
REDIS_URL=redis://default:senha@xxxx.upstash.io:6379
EVOLUTION_API_KEY=minha-chave-secreta-123
EVOLUTION_INSTANCE=cidadao-df
WEBHOOK_BASE_URL=https://xxxx.ngrok.io  ← preencher depois
```

Salve o arquivo.

---

## Passo 3 — Criar o ambiente Python e instalar dependências

No terminal, dentro da pasta `cidadao-df`:

```bash
# Cria ambiente virtual (isola as dependências do projeto)
python -m venv venv

# Ativa o ambiente virtual
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

Você vai ver `(venv)` no início da linha do terminal — significa que funcionou.

Agora instala todas as dependências:
```bash
pip install -r requirements.txt
```

Isso vai demorar 2-5 minutos na primeira vez. É normal.

**O que o ChromaDB faz e como instala:**
O ChromaDB é um banco de vetores que roda 100% local no seu computador.
Ele não precisa do Groq nem de nenhuma API externa.
O `pip install -r requirements.txt` já instala ele automaticamente.
Não precisa configurar nada extra.

---

## Passo 4 — Criar as tabelas no Supabase

1. Acesse seu projeto no Supabase
2. No menu lateral, clique em "SQL Editor"
3. Clique em "New query"
4. Abra o arquivo `scripts/supabase_schema.sql` deste projeto
5. Copie todo o conteúdo e cole no editor do Supabase
6. Clique em "Run" (botão verde)
7. Deve aparecer "Success" — as tabelas foram criadas

---

## Passo 5 — Subir o Docker (Evolution API + Redis local)

Com o Docker Desktop aberto, no terminal:

```bash
docker compose up -d
```

**O que acontece:**
- Docker baixa as imagens necessárias (só na primeira vez, demora ~2 min)
- Sobe a Evolution API na porta 8080
- Sobe o Redis local na porta 6379

Para verificar se subiu:
```bash
docker compose ps
```
Deve aparecer dois containers com status "running".

**Se der erro de porta ocupada:**
```bash
# Veja o que está usando a porta
# Windows:
netstat -ano | findstr :8080

# Mac/Linux:
lsof -i :8080
```

---

## Passo 6 — Expor o servidor com ngrok

A Evolution API precisa enviar mensagens para o seu backend.
Como seu backend roda no seu computador, você precisa do ngrok para
criar uma URL pública que aponta para ele.

**Terminal 1** — deixe rodando o backend:
```bash
# (certifique-se que o ambiente venv está ativo)
uvicorn main:app --reload --port 8000
```

Deve aparecer: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2** — abre o ngrok:
```bash
ngrok http 8000
```

Vai aparecer algo como:
```
Forwarding  https://abc123.ngrok.io → http://localhost:8000
```

Copie a URL `https://abc123.ngrok.io`.

Abra o `.env` e coloque:
```env
WEBHOOK_BASE_URL=https://abc123.ngrok.io
```

**Importante:** a URL do ngrok muda cada vez que você reinicia.
No hackathon, deixe o ngrok rodando o tempo todo.

---

## Passo 7 — Conectar o WhatsApp

Com tudo rodando, abra um terceiro terminal e execute:

```bash
python scripts/setup_whatsapp.py
```

Esse script:
1. Cria a instância do WhatsApp na Evolution API
2. Configura o webhook para receber mensagens
3. Gera o QR Code para conectar

Para ver o QR Code visualmente, acesse no browser:
```
http://localhost:8080/instance/connect/cidadao-df
```

No seu WhatsApp:
1. Abra o WhatsApp no celular
2. Vá em Configurações → Aparelhos Conectados
3. Toque em "Conectar aparelho"
4. Escaneie o QR Code

Pronto! O WhatsApp está conectado.

---

## Passo 8 — Testar

Mande uma mensagem para o número conectado:
```
oi
```

Deve receber o menu inicial:
```
Olá! 👋

Sou o assistente do cidadão do DF. Como posso ajudar?

1️⃣ Saúde — filas, unidades próximas, orientação
2️⃣ Denúncia — relatar problema a um órgão público
3️⃣ Ajuda com Gov.br / INSS / serviços digitais
4️⃣ Outros
```

---

## Como o Groq funciona (explicação simples)

O Groq é um serviço na internet que tem um modelo de IA (Llama 3.3 70B).
Você manda um texto para ele e ele responde.

No nosso código, toda vez que o usuário manda mensagem:
1. O backend recebe a mensagem
2. Manda para o Groq com um "sistema" (instruções do agente)
3. O Groq responde
4. O backend envia a resposta de volta pelo WhatsApp

Você não precisa "instalar o Groq" — ele fica na nuvem deles.
Você só precisa da chave API que gerou no passo 1.

O ChromaDB é diferente: ele roda no seu computador.
É como um banco de dados que entende o significado dos textos.
Você instala com `pip install chromadb` (já está no requirements.txt).

---

## Estrutura do projeto

```
cidadao-df/
├── main.py                    ← ponto de entrada do servidor
├── requirements.txt           ← dependências Python
├── docker-compose.yml         ← Evolution API + Redis
├── .env.example               ← modelo do arquivo de configuração
│
├── app/
│   ├── agents/
│   │   ├── orchestrator.py    ← menu principal e roteamento
│   │   ├── health.py          ← triagem Manchester + CNES + IGES
│   │   ├── complaint.py       ← ouvidoria + RAG TCU
│   │   └── educational.py     ← guia de sistemas digitais + visão
│   │
│   ├── core/
│   │   ├── config.py          ← lê o arquivo .env
│   │   ├── context.py         ← salva/busca contexto no Redis
│   │   ├── groq_client.py     ← chama a IA (Groq)
│   │   └── whatsapp.py        ← envia mensagens via Evolution API
│   │
│   ├── routers/
│   │   └── webhook.py         ← recebe mensagens do WhatsApp
│   │
│   └── services/
│       ├── health_data.py     ← dados CNES + scraping IGES
│       ├── rag.py             ← ChromaDB + classificação TCU
│       └── database.py        ← salva/busca no Supabase
│
├── data/
│   ├── chroma_db/             ← banco vetorial (criado automaticamente)
│   └── tcu_docs/
│       └── normas_tcu_df.txt  ← documentos do TCU para o RAG
│
└── scripts/
    ├── setup_whatsapp.py      ← configura o WhatsApp
    └── supabase_schema.sql    ← cria as tabelas no banco
```

---

## Comandos úteis do dia a dia

```bash
# Ver logs do backend em tempo real
uvicorn main:app --reload --port 8000

# Ver logs da Evolution API
docker compose logs -f evolution-api

# Parar o Docker
docker compose down

# Reiniciar o Docker
docker compose restart

# Ver se o backend está respondendo
curl http://localhost:8000/health
```

---

## Problemas comuns e soluções

**"ModuleNotFoundError"**
O ambiente virtual não está ativo. Execute:
```bash
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

**"Connection refused" na Evolution API**
O Docker não está rodando. Abra o Docker Desktop e execute:
```bash
docker compose up -d
```

**O bot não responde no WhatsApp**
1. Verifique se o ngrok está rodando
2. Verifique se a URL do ngrok no .env está correta
3. Execute `python scripts/setup_whatsapp.py` novamente
4. Verifique os logs: `docker compose logs evolution-api`

**"GROQ_API_KEY not found"**
O arquivo .env não foi criado ou a chave está errada.
Verifique se o arquivo .env existe na pasta raiz e tem a chave correta.

**ChromaDB demora na primeira vez**
Normal — ele baixa o modelo de embeddings (~90MB) na primeira execução.
Da segunda vez em diante é instantâneo.

---

## Prompt para continuar com outra IA

Se precisar continuar o desenvolvimento com outra IA, use este contexto:

```
Estou desenvolvendo um assistente cidadão via WhatsApp para o Distrito Federal (DF)
como projeto de hackathon. O backend está em Python com FastAPI.

STACK:
- FastAPI (backend)
- Groq com Llama 3.3 70B (LLM principal, gratuito)
- Groq Whisper (transcrição de áudio, gratuito)
- ChromaDB local (RAG com normas do TCU)
- Supabase (PostgreSQL - banco de dados)
- Redis/Upstash (cache de contexto de conversa)
- Evolution API via Docker (WhatsApp - protocolo Baileys)
- ngrok (expõe o servidor local)

AGENTES IMPLEMENTADOS:
1. Orquestrador - roteamento e menu principal
2. Agente de Saúde - triagem leve (Manchester), filas IGES-DF, unidades CNES
3. Agente de Ouvidoria - coleta denúncia, RAG TCU, salva no Supabase
4. Agente Educativo - guia em sistemas digitais, lê prints com visão

ESTRUTURA DE ARQUIVOS:
cidadao-df/
├── main.py
├── app/agents/ (orchestrator, health, complaint, educational)
├── app/core/ (config, context, groq_client, whatsapp)
├── app/routers/webhook.py
├── app/services/ (health_data, rag, database)
├── data/tcu_docs/normas_tcu_df.txt
└── scripts/ (setup_whatsapp.py, supabase_schema.sql)

REGRAS DE NEGÓCIO:
- Sistema NÃO faz diagnóstico médico
- Triagem baseada em discriminadores do Protocolo de Manchester
- Denúncias NÃO são anônimas (precisa de contato para retorno)
- RAG usa ChromaDB com documentos do TCU para classificar denúncias
- IGES-DF não tem API pública — usa scraping + dados estáticos como fallback
- CNES tem API pública: apidadosabertos.saude.gov.br/v1/cnes/estabelecimentos

O que preciso agora: [DESCREVA O QUE PRECISA CONTINUAR]
```

---

## Painel público de denúncias

Depois de ter denúncias salvas, você pode ver os dados em:
```
http://localhost:8000/complaints
```

Para uma demo visual, acesse o Supabase → Table Editor → complaints
e veja os dados salvos em tempo real.

---

## Limites gratuitos — o que você tem

| Serviço | Limite gratuito | Suficiente para hackathon? |
|---------|----------------|---------------------------|
| Groq | 1.000 req/dia, 30 req/min | ✅ Sim |
| Groq Whisper | incluso no free tier | ✅ Sim |
| Supabase | 500MB, 50K req/mês | ✅ Sim |
| Redis/Upstash | 10K req/dia | ✅ Sim |
| Evolution API | gratuito (open source) | ✅ Sim |
| ChromaDB | local, ilimitado | ✅ Sim |
| ngrok | 1 túnel simultâneo, grátis | ✅ Sim |

---

Feito para o Hackathon DF 2025.
