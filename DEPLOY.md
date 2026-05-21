# Deploy do Sistema Alpes

O sistema está preparado para produção online usando Supabase/PostgreSQL e Supabase Storage.

## Fonte oficial de dados

Em produção:

- dados operacionais ficam no Supabase/PostgreSQL;
- imagens e anexos ficam no Supabase Storage;
- arquivos locais não são banco de dados;
- se o Supabase não estiver configurado, o app bloqueia a operação.

Mensagem esperada:

```text
Erro crítico: Supabase não configurado. O sistema não pode operar em produção sem banco de dados.
```

## Documentos de deploy

- `STREAMLIT_DEPLOY.md`: deploy no Streamlit Cloud.
- `RAILWAY_DEPLOY.md`: deploy no Railway.
- `SUPABASE_PRODUCTION.md`: configuração de banco, Storage e backups.
- `README_DEPLOY.md`: visão geral de produção.

## Variáveis obrigatórias

Consulte `.env.example`.

Principais variáveis:

```text
ENVIRONMENT=production
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_BUCKET=alpes-system
ALPES_EXIGIR_ARMAZENAMENTO_ONLINE=true
ALPES_ADMIN_USER=
ALPES_ADMIN_EMAIL=
ALPES_ADMIN_PASSWORD=
```

## Domínios sugeridos

- Produção: `app.sistemaalpes.com.br`
- Teste: `teste.sistemaalpes.com.br`

Use ambientes Supabase separados para teste e produção.
