# Deploy no Streamlit Cloud

## 1. Preparar Supabase

1. Crie um projeto no Supabase.
2. Abra **SQL Editor**.
3. Execute todo o arquivo `supabase_schema.sql`.
4. Confirme os buckets:
   - `alpes-system`
   - `imagens-produtos`
   - `anexos-frotas`
   - `documentos`
   - `uploads`
   - `imagens-sistema`

## 2. Configurar Secrets

No Streamlit Cloud, abra o app em **Settings > Secrets** e adicione:

```toml
ENVIRONMENT = "production"
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_ANON_KEY = "SUA_ANON_KEY"
SUPABASE_SERVICE_ROLE_KEY = "SUA_SERVICE_ROLE_KEY"
SUPABASE_BUCKET = "alpes-system"
ALPES_EXIGIR_ARMAZENAMENTO_ONLINE = "true"
ALPES_ADMIN_USER = "admin_alpes"
ALPES_ADMIN_EMAIL = "admin@sistemaalpes.com.br"
ALPES_ADMIN_PASSWORD = "USE_UMA_SENHA_FORTE"
```

Nunca coloque `SUPABASE_SERVICE_ROLE_KEY` no GitHub.

## 3. Configurar app

No Streamlit Cloud:

1. Conecte o repositório `leandrobarreto10/alpescontrol`.
2. Branch: `main`.
3. Main file: `app.py`.
4. Python: 3.12.
5. Salve e aguarde o deploy.

## 4. Comportamento esperado

Em produção, o sistema para se o Supabase não estiver configurado:

```text
Erro crítico: Supabase não configurado. O sistema não pode operar em produção sem banco de dados.
```

Isso evita perda de dados no filesystem temporário do Streamlit Cloud.

## 5. Domínio próprio

No Streamlit Cloud, use **Settings > Custom domain**.

Sugestão:

- Produção: `app.sistemaalpes.com.br`
- Teste: `teste.sistemaalpes.com.br`

No provedor de DNS, crie o registro indicado pelo Streamlit Cloud.
