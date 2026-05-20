# Deploy profissional ALPES

## Variaveis obrigatorias em producao

Configure no Streamlit Cloud, Railway, Render ou servidor:

```toml
ENVIRONMENT = "production"
SUPABASE_URL = "..."
SUPABASE_SERVICE_ROLE_KEY = "..."
SUPABASE_BUCKET = "alpes-system"
ALPES_EXIGIR_ARMAZENAMENTO_ONLINE = "true"
ALPES_ADMIN_USER = "..."
ALPES_ADMIN_EMAIL = "..."
ALPES_ADMIN_PASSWORD = "..."
```

Em producao, o sistema nao opera sem Supabase.

## Banco de dados

Execute `supabase_schema.sql` no SQL Editor do Supabase antes de iniciar o app em producao.

O Supabase/PostgreSQL e a fonte oficial dos dados operacionais. Arquivos locais sao permitidos apenas para:

- migracao inicial;
- exportacao administrativa;
- backup manual;
- relatorio gerado pelo usuario;
- desenvolvimento local controlado.

## Storage

O bucket `alpes-system` guarda anexos, documentos, comprovantes e imagens internas.

O bucket `imagens-produtos` guarda imagens publicas de produtos.

## Backups

Ative os backups/snapshots no painel do Supabase conforme o plano contratado.

Para exportacao manual, use o Table Editor do Supabase ou as telas administrativas do sistema.

## Ambientes

Use ambientes separados:

- TESTE: banco e storage proprios.
- PRODUCAO: banco e storage proprios.

Nunca use a mesma chave `service_role` nos dois ambientes.
