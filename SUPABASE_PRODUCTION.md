# Supabase em produção

## Banco

Execute `supabase_schema.sql` no SQL Editor do Supabase.

O script cria:

- tabelas operacionais;
- tabela `logs_sistema`;
- tabela `migracoes_sistema`;
- índices operacionais;
- buckets de Storage;
- trigger de `updated_at`.

## Storage

Buckets esperados:

- `alpes-system`: privado, usado para anexos, documentos, comprovantes e arquivos internos.
- `anexos-frotas`: privado, usado para anexos operacionais da frota.
- `documentos`: privado, usado para documentos administrativos.
- `uploads`: privado, usado para arquivos enviados pelo usuario.
- `imagens-sistema`: privado, usado para imagens internas do sistema.
- `imagens-produtos`: público, usado para imagens de produtos.

## Chaves

Use:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

A `SERVICE_ROLE_KEY` deve ficar apenas em Secrets/Variables do provedor.

## Backup

O backup operacional real deve ser feito pelo Supabase:

1. Ative backups/snapshots no painel do Supabase.
2. Para exportação manual, use **Table Editor > Export data**.
3. Para restauração, use ambiente controlado e valide antes de aplicar em produção.

## Ambientes

Use projetos separados:

- Produção: `app.sistemaalpes.com.br`
- Teste: `teste.sistemaalpes.com.br`

Não misture dados de teste no projeto de produção.
