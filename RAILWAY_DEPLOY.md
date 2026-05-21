# Deploy no Railway

## 1. Criar projeto

1. Acesse https://railway.app.
2. Crie um novo projeto.
3. Escolha **Deploy from GitHub repo**.
4. Selecione `leandrobarreto10/alpescontrol`.

O Railway usa o `Procfile`:

```text
web: streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.fileWatcherType=poll
```

## 2. Variáveis obrigatórias

Em **Variables**, adicione:

```text
ENVIRONMENT=production
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_ANON_KEY=SUA_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=SUA_SERVICE_ROLE_KEY
SUPABASE_BUCKET=alpes-system
ALPES_EXIGIR_ARMAZENAMENTO_ONLINE=true
ALPES_ADMIN_USER=admin_alpes
ALPES_ADMIN_EMAIL=admin@sistemaalpes.com.br
ALPES_ADMIN_PASSWORD=USE_UMA_SENHA_FORTE
```

Não configure `ALPES_DATA_DIR` em produção. O banco oficial é o Supabase.

## 3. Supabase

Antes do primeiro acesso:

1. Execute `supabase_schema.sql` no SQL Editor.
2. Confirme os buckets `alpes-system`, `imagens-produtos`, `anexos-frotas`, `documentos`, `uploads` e `imagens-sistema`.

## 4. Domínio próprio

No Railway:

1. Abra **Settings > Networking**.
2. Clique em **Custom Domain**.
3. Adicione:
   - `app.sistemaalpes.com.br` para produção
   - `teste.sistemaalpes.com.br` para homologação
4. Configure o DNS conforme o Railway informar.

## 5. Teste final

Depois do deploy:

1. Abra o domínio.
2. Faça login com o admin inicial.
3. Cadastre um registro simples.
4. Reinicie o serviço no Railway.
5. Confirme que o registro permaneceu salvo.

Se o Supabase não estiver configurado, o sistema deve bloquear a operação com erro crítico.
