# Secretária Particular IA

Agente pessoal multimodal com memória: registre texto, áudio, fotos e vídeos,
e pergunte depois — a secretária só responde com base no que você já contou
a ela. Interface mobile-first (PWA), pensada para funcionar bem no celular e
também no navegador desktop.

> Projeto acadêmico, construído inteiramente com ferramentas de camada
> gratuita (free tier). Veja `SECURITY.md` para o detalhamento das medidas
> de segurança.

## Arquitetura

```
frontend/   PWA em HTML/CSS/JS puro (mobile-first) → deploy no Netlify
backend/    API em Python/FastAPI                   → deploy no Render
database/   Schema SQL (Postgres + pgvector)         → Supabase (free tier)
```

- **Frontend**: HTML/CSS/JS vanilla, sem build step, instalável como app
  (PWA) via `manifest.json` + `service-worker.js`. Usa `MediaDevices`/
  `MediaRecorder` para capturar foto/áudio/vídeo direto da câmera e do
  microfone do navegador.
- **Backend**: FastAPI, com autenticação por senha + 2FA (TOTP), ingestão
  multimodal (transcrição de áudio via Groq Whisper, descrição de imagem via
  modelo de visão gratuito no OpenRouter) e um pipeline de memória (RAG) que
  restringe as respostas do agente ao que o próprio usuário já registrou.
- **Banco**: Supabase (Postgres + extensão `pgvector` para busca semântica +
  Row Level Security).

## Pré-requisitos

- Python 3.11+
- `ffmpeg` instalado localmente (necessário para processar vídeo) —
  `sudo apt install ffmpeg` (Linux) ou `brew install ffmpeg` (macOS)
- Uma conta gratuita em:
  - [Supabase](https://supabase.com) (banco de dados)
  - [Groq Console](https://console.groq.com) (transcrição de áudio)
  - [OpenRouter](https://openrouter.ai) (chat e descrição de imagem — use
    modelos com sufixo `:free`)
- Um navegador com suporte a `getUserMedia`/`MediaRecorder` (todos os
  navegadores modernos) e, para captura de câmera/microfone, **HTTPS ou
  `localhost`** (o navegador bloqueia essas APIs em HTTP puro fora do
  localhost).

## 1. Configurar o banco (Supabase)

1. Crie um projeto gratuito em supabase.com.
2. Abra **SQL Editor** e execute o conteúdo de `database/schema.sql`.
3. Em **Project Settings → API**, copie a `Project URL` e a
   `service_role key` — vão para `SUPABASE_URL` e `SUPABASE_SERVICE_KEY`.

## 2. Rodar o backend localmente

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edite o .env e preencha os valores (veja os comandos abaixo para gerar as chaves)
```

Gerar as chaves de segurança:

```bash
# JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"

# TOTP_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Rodar a API:

```bash
uvicorn app.main:app --reload --port 8000
```

A documentação interativa fica em `http://localhost:8000/docs` (apenas em
`ENVIRONMENT=development`; em produção o Swagger é desativado por segurança).

Rodar os testes:

```bash
pytest
```

## 3. Rodar o frontend localmente

O frontend não tem build step — é só servir os arquivos estáticos. Abra
`frontend/config.js` e confirme que `API_BASE_URL` aponta para
`http://localhost:8000`.

Com o VS Code, a extensão **Live Server** funciona bem (clique com o botão
direito em `index.html` → "Open with Live Server"). Ou, via terminal:

```bash
cd frontend
python -m http.server 5500
```

Acesse `http://localhost:5500`. Para testar captura de câmera/microfone no
celular durante o desenvolvimento, use um túnel HTTPS (ex.: `ngrok http 5500`),
já que o navegador exige contexto seguro para essas APIs fora do localhost.

## 4. Deploy gratuito

### Backend → Render

1. Suba o repositório no GitHub.
2. No [Render](https://render.com), crie um **New Web Service** apontando
   para a pasta `backend/` do repositório.
   - Se usar o `render.yaml` (Blueprint): Render detecta automaticamente
     build/start commands e instala o `ffmpeg` via `apt-get`.
   - Alternativa mais confiável para o `ffmpeg`: escolha **Docker** como
     ambiente e aponte para `backend/Dockerfile`.
3. Configure as variáveis de ambiente (as mesmas do `.env`) no painel do
   Render — nunca as coloque no `render.yaml` nem no código.
4. Plano **Free**: o serviço "dorme" após um período sem requisições e o
   primeiro request após esse período pode demorar ~30-60s para responder
   (cold start) — comportamento esperado do free tier.

### Frontend → Netlify

1. Em `frontend/config.js`, troque `API_BASE_URL` pela URL pública do seu
   serviço no Render (ex.: `https://secretaria-particular-api.onrender.com`).
2. No [Netlify](https://app.netlify.com), **Add new site → Import an
   existing project**, selecione o repositório e configure:
   - **Base directory**: `frontend`
   - **Publish directory**: `frontend` (não há build step)
3. Depois do primeiro deploy, copie a URL pública do Netlify e adicione-a em
   `ALLOWED_ORIGINS` nas variáveis de ambiente do backend no Render (assim o
   CORS passa a aceitar o domínio publicado). Redeploy o backend.

### Checklist pós-deploy

- [ ] `ALLOWED_ORIGINS` no backend contém a URL exata do Netlify (sem barra final)
- [ ] `API_BASE_URL` no `frontend/config.js` aponta para a URL do Render
- [ ] Variáveis de ambiente sensíveis configuradas no painel do Render (não no código)
- [ ] `GROQ_API_KEY` e `OPENROUTER_API_KEY` válidas e com modelos `:free` configurados
- [ ] Testar cadastro → configurar 2FA → login → registrar texto/áudio/foto → perguntar no chat

## Estrutura de pastas

```
backend/
  app/
    core/            configuração, segurança (JWT/senha/2FA), dependências
    routes/           endpoints HTTP (auth, memory, chat)
    services/         regras de negócio (auth, ingestão de mídia, LLM, RAG)
    repositories/      acesso a dados (Supabase)
    models/           schemas Pydantic de entrada/saída
    middleware/        rate limiting, cabeçalhos de segurança
  tests/               testes automatizados (pytest)
  requirements.txt
  render.yaml / Dockerfile

frontend/
  index.html           login / cadastro / configuração do 2FA
  app.html              chat + histórico (autenticado)
  manifest.json / service-worker.js   PWA
  src/css/              tokens de design, componentes, layout
  src/js/                lógica de auth, captura de mídia, chat, histórico
  public/icons/          ícones do PWA

database/
  schema.sql            tabelas, pgvector, RLS, função de busca semântica
```

## Sobre os modelos de IA gratuitos

A oferta de modelos `:free` no OpenRouter muda com frequência. Se o modelo
configurado em `LLM_CHAT_MODEL` ou `LLM_VISION_MODEL` parar de responder,
verifique a lista atual em https://openrouter.ai/models?order=pricing-low-to-high
e atualize a variável de ambiente correspondente — não é necessário alterar
código.
