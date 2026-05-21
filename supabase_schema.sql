-- Execute este script no SQL Editor do Supabase.
-- O script cria/valida as tabelas e os buckets "imagens-produtos" e "alpes-system".

create table if not exists produtos (
    id text primary key,
    codigo text,
    produto text,
    categoria text,
    estoque_minimo numeric default 0,
    localizacao text,
    imagem text,
    unidade text,
    valor_unitario numeric default 0,
    fornecedor text,
    status text default 'Ativo',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists movimentacoes (
    id text primary key,
    produto text,
    tipo text,
    quantidade numeric default 0,
    data timestamptz,
    cliente text,
    observacao text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists usuarios (
    id text primary key,
    nome text,
    email text,
    senha text,
    nivel text,
    status text default 'Ativo',
    criado_em text,
    veiculo_frota text,
    veiculos_frota jsonb default '[]'::jsonb,
    bases_permitidas jsonb default '[]'::jsonb,
    pode_lancar_despesa_frota boolean default false,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists fornecedores (
    id text primary key,
    codigo text,
    nome_fornecedor text,
    telefone text,
    cidade text,
    estado text,
    tipo_contrato text,
    data_inicial text,
    data_final text,
    status text default 'Ativo',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists clientes (
    id text primary key,
    codigo text,
    nome_cliente text,
    telefone text,
    cidade text,
    estado text,
    tipo_contrato text,
    data_inicial text,
    data_final text,
    status text default 'Ativo',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists categorias (
    id text primary key,
    nome text,
    cor text,
    status text default 'Ativo',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists unidades (
    id text primary key,
    nome text,
    cor text,
    status text default 'Ativo',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists controle_faltas (
    id text primary key,
    data text,
    colaborador text,
    funcao text,
    presenca text,
    motivo_falta text,
    almocou_base text,
    observacoes text,
    tipo_escala text,
    data_base_escala text,
    trabalha_data_base text,
    status_colaborador text default 'Ativo',
    base_frequencia text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists frotas_veiculos (
    id text primary key,
    placa text,
    modelo text,
    marca text,
    ano text,
    tipo text,
    responsavel text,
    cidade_local text,
    status text default 'Ativo',
    km_atual text,
    periodicidade_vistoria text,
    ultima_vistoria text,
    proxima_vistoria text,
    status_responsabilidade text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists frotas_abastecimentos (
    id text primary key,
    data text,
    placa text,
    km numeric default 0,
    combustivel text,
    litros numeric default 0,
    valor_litro numeric default 0,
    valor_total numeric default 0,
    posto text,
    responsavel_lancamento text,
    registrado_em text,
    nota_anexo text,
    status_conferencia text default 'Pendente',
    observacao_administrativo text,
    observacoes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists frotas_manutencoes (
    id text primary key,
    data text,
    placa text,
    tipo_manutencao text,
    km numeric default 0,
    servico_executado text,
    fornecedor text,
    valor numeric default 0,
    manutencao_agendada text,
    proxima_revisao text,
    status_manutencao text,
    responsavel_lancamento text,
    registrado_em text,
    nota_anexo text,
    status_conferencia text default 'Pendente',
    observacao_administrativo text,
    observacoes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists frotas_documentos (
    id text primary key,
    placa text,
    documento text,
    vencimento text,
    valor numeric default 0,
    status text,
    observacoes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists frotas_entregas (
    id text primary key,
    data text,
    placa text,
    responsavel text,
    km numeric default 0,
    periodicidade text,
    proxima_vistoria text,
    pneus text,
    lataria text,
    vidros text,
    farois_lanternas text,
    documentacao text,
    itens_obrigatorios text,
    fotos text,
    observacoes text,
    registrado_em text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists frotas_vistorias (
    id text primary key,
    data text,
    placa text,
    tipo_vistoria text,
    responsavel text,
    km numeric default 0,
    periodicidade text,
    proxima_vistoria text,
    pneus text,
    lataria text,
    vidros text,
    farois_lanternas text,
    documentacao text,
    itens_obrigatorios text,
    fotos text,
    observacoes text,
    registrado_em text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists bases_movimentacoes (
    id text primary key,
    data text,
    base text,
    produto text,
    tipo text,
    quantidade numeric default 0,
    responsavel text,
    origem_destino text,
    observacoes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists bases_transferencias (
    id text primary key,
    data text,
    produto text,
    quantidade numeric default 0,
    origem text,
    destino text,
    responsavel_envio text,
    responsavel_recebimento text,
    status text,
    observacoes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists configuracoes (
    chave text primary key,
    valor jsonb,
    updated_at timestamptz default now()
);

create table if not exists logs_sistema (
    id text primary key,
    data_hora text,
    usuario text,
    nivel text,
    acao text,
    modulo text,
    registro text,
    detalhe text,
    antes text,
    depois text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists migracoes_sistema (
    id text primary key,
    nome_migracao text unique,
    status text,
    data_execucao timestamptz,
    registros_importados integer default 0,
    registros_ignorados integer default 0,
    erros text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists permissoes (
    id text primary key,
    perfil text,
    modulo text,
    acao text,
    permitido boolean default true,
    ativo boolean default true,
    usuario_criacao text,
    usuario_alteracao text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists bases (
    id text primary key,
    nome text unique,
    status text default 'Ativo',
    ativo boolean default true,
    usuario_criacao text,
    usuario_alteracao text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists base_tmg_sorriso (
    id text primary key,
    tipo_registro text,
    dados jsonb default '{}'::jsonb,
    ativo boolean default true,
    usuario_criacao text,
    usuario_alteracao text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists base_tmg_rondonopolis (
    id text primary key,
    tipo_registro text,
    dados jsonb default '{}'::jsonb,
    ativo boolean default true,
    usuario_criacao text,
    usuario_alteracao text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists compras (
    id text primary key,
    data text,
    fornecedor text,
    produto text,
    quantidade numeric default 0,
    valor_unitario numeric default 0,
    valor_total numeric default 0,
    status text,
    observacoes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists relatorios (
    id text primary key,
    tipo text,
    periodo text,
    usuario text,
    parametros jsonb default '{}'::jsonb,
    arquivo text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists historicos (
    id text primary key,
    entidade text,
    entidade_id text,
    acao text,
    usuario text,
    dados jsonb default '{}'::jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

do $$
declare
    tabela text;
begin
    foreach tabela in array array[
        'produtos',
        'usuarios',
        'fornecedores',
        'clientes',
        'categorias',
        'frotas_veiculos'
    ]
    loop
        execute format('alter table %I add column if not exists ativo boolean default true', tabela);
        execute format('alter table %I add column if not exists usuario_criacao text', tabela);
        execute format('alter table %I add column if not exists usuario_alteracao text', tabela);
    end loop;
end $$;

create or replace function alpes_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

do $$
declare
    tabela text;
begin
    foreach tabela in array array[
        'produtos',
        'movimentacoes',
        'usuarios',
        'fornecedores',
        'clientes',
        'categorias',
        'unidades',
        'controle_faltas',
        'frotas_veiculos',
        'frotas_abastecimentos',
        'frotas_manutencoes',
        'frotas_documentos',
        'frotas_entregas',
        'frotas_vistorias',
        'bases_movimentacoes',
        'bases_transferencias',
        'configuracoes',
        'logs_sistema',
        'migracoes_sistema',
        'permissoes',
        'bases',
        'base_tmg_sorriso',
        'base_tmg_rondonopolis',
        'compras',
        'relatorios',
        'historicos'
    ]
    loop
        execute format('drop trigger if exists set_updated_at on %I', tabela);
        execute format(
            'create trigger set_updated_at before update on %I for each row execute function alpes_set_updated_at()',
            tabela
        );
    end loop;
end $$;

insert into storage.buckets (id, name, public)
values ('imagens-produtos', 'imagens-produtos', true)
on conflict (id) do update set public = true;

insert into storage.buckets (id, name, public)
values ('alpes-system', 'alpes-system', false)
on conflict (id) do update set public = false;

drop policy if exists "Leitura publica imagens produtos" on storage.objects;
create policy "Leitura publica imagens produtos"
on storage.objects for select
using (bucket_id = 'imagens-produtos');

drop policy if exists "Upload imagens produtos autenticado" on storage.objects;
create policy "Upload imagens produtos autenticado"
on storage.objects for insert
with check (bucket_id = 'imagens-produtos');

drop policy if exists "Atualizar imagens produtos autenticado" on storage.objects;
create policy "Atualizar imagens produtos autenticado"
on storage.objects for update
using (bucket_id = 'imagens-produtos')
with check (bucket_id = 'imagens-produtos');
