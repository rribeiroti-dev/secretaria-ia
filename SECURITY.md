# Segurança — Agente Secretária Particular

Este documento resume as medidas de segurança implementadas e as decisões de
arquitetura tomadas para reduzir a superfície de ataque, já que a aplicação
lida com dados pessoais sensíveis (memórias multimodais do usuário).

## Autenticação e sessão

- **Senha + 2FA obrigatórios**: nenhuma conta acessa a API sem confirmar um
  código TOTP (Google Authenticator, Authy etc.) além da senha. O login
  acontece em duas etapas (`/auth/login` → `/auth/verify-2fa`); o primeiro
  passo nunca emite um token de acesso real.
- **Senhas**: hash com Argon2 (via `passlib`), nunca armazenadas em texto
  plano. Política mínima exigida: 10+ caracteres, maiúscula, minúscula,
  número e símbolo (validada no backend, não só no frontend).
- **Segredo do 2FA cifrado em repouso**: o segredo TOTP de cada usuário é
  cifrado com Fernet (AES) antes de ir para o banco — mesmo um vazamento do
  banco não expõe o segredo em texto plano.
- **Bloqueio por força bruta**: após 5 tentativas de senha incorretas, a
  conta é temporariamente bloqueada (`423 Locked`).
- **Tokens JWT de vida curta**: access token expira em 30 minutos; refresh
  token em 7 dias. Ambos assinados com `JWT_SECRET_KEY` (nunca hardcoded).
- **Tokens apenas em memória no frontend**: o app nunca grava tokens em
  `localStorage`/`sessionStorage`, reduzindo o impacto de um eventual XSS.

## Isolamento de dados entre usuários

- Toda consulta à memória (`memories`) é filtrada por `user_id` **dentro do
  próprio SQL** (função `match_memories`), não apenas na camada de
  aplicação — mesmo um bug de lógica no backend não vazaria dados de outro
  usuário.
- Row Level Security (RLS) habilitada nas tabelas do Supabase como defesa em
  profundidade adicional.

## Validação e sanitização de entrada

- Todo payload de texto é validado com Pydantic (tamanho, formato, força de
  senha, formato do código 2FA).
- Todo upload de mídia é validado por **tipo MIME permitido** e **tamanho
  máximo** (`MAX_UPLOAD_SIZE_MB`) antes de ser processado — protege tanto
  contra abuso quanto contra estouro de memória/disco no free tier.
- Vídeo é processado em diretório temporário isolado (`tempfile.TemporaryDirectory`),
  removido automaticamente ao final do processamento.

## Prevenção de XSS

- O frontend nunca insere texto vindo do usuário/API via `innerHTML`. Todo
  conteúdo dinâmico (mensagens, histórico, transcrições) é inserido via
  `textContent`, que não interpreta HTML/JS.
- Cabeçalho `X-Content-Type-Options: nosniff` em toda resposta da API.

## Prevenção de SQL/NoSQL injection

- Todo acesso a dado usa o client oficial do Supabase (queries parametrizadas
  internamente) ou a função RPC `match_memories` com parâmetros tipados —
  nunca há concatenação manual de SQL com entrada do usuário.

## Rede e transporte

- **CORS restrito**: apenas as origens listadas em `ALLOWED_ORIGINS` (o
  domínio do frontend no Netlify) podem chamar a API — nunca `*`.
- **HTTPS obrigatório em produção**: Render e Netlify fornecem HTTPS por
  padrão; `Strict-Transport-Security` é adicionado às respostas em produção.
- **Rate limiting** por IP em todas as rotas sensíveis (`/auth/*`,
  `/chat/ask`, `/memory/*`), protegendo contra força bruta e contra abuso das
  cotas gratuitas de API (Groq/OpenRouter).

## Gestão de segredos

- Nenhuma chave de API, credencial de banco ou segredo JWT é hardcoded.
  Tudo vem de variáveis de ambiente (`.env` local, painel do Render em
  produção). O `.env.example` documenta as variáveis sem conter valores
  reais, e `.env` está no `.gitignore`.
- A `service_role key` do Supabase (privilégio administrativo) só existe no
  backend; o frontend nunca a recebe nem fala diretamente com o Supabase.

## Tratamento de erros

- Exceções não tratadas nunca vazam stack trace ao cliente: o
  `unhandled_exception_handler` global loga o erro completo no servidor e
  devolve apenas uma mensagem genérica.
- Mensagens de erro de login não diferenciam "e-mail não existe" de "senha
  errada", dificultando enumeração de contas.

## Cabeçalhos de segurança HTTP

Aplicados em toda resposta via `SecurityHeadersMiddleware`:
`X-Content-Type-Options`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`,
`Permissions-Policy` restringindo geolocalização e liberando câmera/microfone
apenas para o próprio site (`self`).

## Limitações conhecidas (escopo acadêmico)

- Não há verificação de e-mail (envio de confirmação) nem fluxo de
  "esqueci minha senha" — fora do escopo do briefing original. Se o projeto
  evoluir para uso real, isso deve ser adicionado.
- O refresh token, por ser uma API pura (sem cookies de sessão), fica em
  memória no frontend em vez de um cookie `HttpOnly` — trade-off aceito
  para o escopo acadêmico; documentado em `frontend/src/js/api.js`.
- Não há revogação individual de tokens (blacklist de `jti`) — cada JWT é
  válido até expirar. Para produção real, considerar uma tabela de tokens
  revogados.
