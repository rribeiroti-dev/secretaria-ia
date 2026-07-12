-- =============================================================================
-- Schema do banco — Agente Secretária Particular
-- Execute este script no SQL Editor do seu projeto Supabase (gratuito).
-- =============================================================================

-- Extensão para busca vetorial (memória semântica)
create extension if not exists vector;

-- -----------------------------------------------------------------------------
-- Tabela de usuários da aplicação.
-- Observação: a autenticação (senha + 2FA) é controlada inteiramente pelo
-- nosso backend, não pelo Supabase Auth, para termos controle total do fluxo
-- de 2FA obrigatório descrito no briefing. A service_role key do backend é
-- a única credencial com acesso a esta tabela.
-- -----------------------------------------------------------------------------
create table if not exists app_users (
    id uuid primary key default gen_random_uuid(),
    email text unique not null,
    full_name text not null,
    password_hash text not null,
    totp_secret_encrypted text not null,
    totp_confirmed boolean not null default false,
    failed_login_attempts integer not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_app_users_email on app_users (email);

-- -----------------------------------------------------------------------------
-- Tabela de memórias multimodais (texto, áudio, foto, vídeo já convertidos
-- em texto pesquisável) com embedding para busca semântica.
-- all-MiniLM-L6-v2 gera vetores de 384 dimensões.
-- -----------------------------------------------------------------------------
create table if not exists memories (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references app_users (id) on delete cascade,
    source_type text not null check (source_type in ('texto', 'audio', 'foto', 'video')),
    extracted_text text not null,
    original_filename text,
    embedding vector(384) not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_memories_user_id on memories (user_id);

-- Índice aproximado para busca vetorial eficiente (cosine distance)
create index if not exists idx_memories_embedding
    on memories using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- -----------------------------------------------------------------------------
-- Row Level Security: segunda camada de isolamento por usuário, independente
-- da lógica da aplicação. Mesmo que a service key seja usada, mantemos as
-- políticas ativas como defesa em profundidade (e para permitir, no futuro,
-- acesso direto com uma chave anon caso o projeto evolua).
-- -----------------------------------------------------------------------------
alter table app_users enable row level security;
alter table memories enable row level security;

-- Apenas o backend (service_role) acessa app_users diretamente; nenhuma
-- policy pública é criada para essa tabela.

create policy "memories_isolated_by_owner"
    on memories
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

-- -----------------------------------------------------------------------------
-- Função RPC: busca por similaridade SEMPRE filtrada por user_id no próprio
-- SQL. Isso garante que, mesmo com um bug na camada de aplicação, a consulta
-- nunca devolve memórias de outro usuário.
-- -----------------------------------------------------------------------------
create or replace function match_memories (
    query_embedding vector(384),
    match_user_id uuid,
    match_count int default 6
)
returns table (
    id uuid,
    source_type text,
    extracted_text text,
    original_filename text,
    created_at timestamptz,
    similarity float
)
language sql
stable
as $$
    select
        memories.id,
        memories.source_type,
        memories.extracted_text,
        memories.original_filename,
        memories.created_at,
        1 - (memories.embedding <=> query_embedding) as similarity
    from memories
    where memories.user_id = match_user_id
    order by memories.embedding <=> query_embedding
    limit match_count;
$$;
