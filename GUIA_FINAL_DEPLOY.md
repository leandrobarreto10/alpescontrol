# Guia Final de Deploy

Este guia operacional publica o sistema ALPES Gestão e Facilities em ambiente online com Supabase, Supabase Storage, Streamlit Cloud ou Railway e domínio próprio.

Não coloque chaves reais no GitHub. Use somente Secrets/Variables do provedor.

## ETAPA 1 - Supabase

1. Acesse o Supabase e crie um projeto para TESTE.
2. Crie outro projeto separado para PRODUÇÃO.
3. Abra o projeto desejado.
4. Vá em **SQL Editor**.
5. Copie e execute todo o arquivo `supabase_schema.sql`.
6. Confirme no **Table Editor** se as tabelas foram criadas, incluindo:
   - `usuarios`
   - `produtos`
   - `movimentacoes`
   - `clientes`
   - `fornecedores`
   - `frotas_veiculos`
   - `frotas_abastecimentos`
   - `controle_faltas`
   - `logs_sistema`
   - `migracoes_sistema`
7. Vá em **Storage** e confirme os buckets:
   - `alpes-system`
   - `imagens-produtos`
   - `anexos-frotas`
   - `documentos`
   - `uploads`
   - `imagens-sistema`
8. Vá em **Project Settings > API**.
9. Copie:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`

Use a `SERVICE_ROLE_KEY` somente em Secrets/Variables. Nunca envie essa chave para o GitHub.

## ETAPA 2 - Ambiente De Teste

1. Use o projeto Supabase de TESTE.
2. Configure as variáveis do ambiente de teste:

```text
ENVIRONMENT=production
SUPABASE_URL=https://SEU-PROJETO-TESTE.supabase.co
SUPABASE_ANON_KEY=SUA_ANON_KEY_TESTE
SUPABASE_SERVICE_ROLE_KEY=SUA_SERVICE_ROLE_KEY_TESTE
SUPABASE_BUCKET=alpes-system
ALPES_EXIGIR_ARMAZENAMENTO_ONLINE=true
ALPES_ADMIN_USER=admin_teste
ALPES_ADMIN_EMAIL=admin.teste@sistemaalpes.com.br
ALPES_ADMIN_PASSWORD=USE_UMA_SENHA_FORTE
```

3. Suba primeiro o ambiente de teste.
4. Acesse o sistema.
5. Valide login.
6. Cadastre um produto.
7. Registre uma movimentação.
8. Cadastre um veículo.
9. Faça um upload de imagem/anexo.
10. Reinicie o app.
11. Confirme que os registros continuam no sistema.
12. Faça um novo deploy.
13. Confirme novamente que os dados continuam salvos.

## ETAPA 3 - Streamlit Cloud

1. Acesse o Streamlit Cloud.
2. Clique em **New app**.
3. Conecte o GitHub.
4. Selecione o repositório `leandrobarreto10/alpescontrol`.
5. Selecione a branch `main`.
6. Defina o arquivo principal como `app.py`.
7. Abra **Settings > Secrets**.
8. Configure:

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

9. Salve os Secrets.
10. Faça o deploy.
11. Abra os logs do Streamlit Cloud.
12. Confirme que não há erro de importação.
13. Confirme que o erro crítico aparece se os Secrets do Supabase forem removidos.
14. Com Secrets corretos, valide login, cadastros, frotas e uploads.

## ETAPA 4 - Railway

1. Acesse o Railway.
2. Crie um novo projeto.
3. Escolha **Deploy from GitHub repo**.
4. Selecione `leandrobarreto10/alpescontrol`.
5. Confirme que o Railway detectou o `Procfile`.
6. O comando esperado é:

```text
web: streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.fileWatcherType=poll
```

7. Em **Variables**, configure:

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

8. Não configure `ALPES_DATA_DIR` em produção.
9. O Railway injeta a variável `PORT` automaticamente.
10. Faça o deploy.
11. Abra os logs.
12. Valide login, cadastros, frotas, uploads e persistência após restart.

## ETAPA 5 - Domínio Próprio

Use dois subdomínios:

- Teste: `teste.sistemaalpes.com.br`
- Produção: `app.sistemaalpes.com.br`

### Streamlit Cloud

1. Abra **Settings > Custom domain**.
2. Informe o subdomínio.
3. Copie o registro DNS indicado pelo Streamlit.
4. No provedor do domínio, crie o CNAME solicitado.
5. Aguarde a propagação.
6. Confirme HTTPS ativo.
7. Acesse o sistema externamente pelo domínio.

### Railway

1. Abra **Settings > Networking**.
2. Clique em **Custom Domain**.
3. Informe o subdomínio.
4. Copie o CNAME ou registro indicado.
5. Configure no DNS do domínio.
6. Aguarde a propagação.
7. Confirme HTTPS ativo.
8. Acesse o sistema externamente pelo domínio.

## ETAPA 6 - Checklist Final

Antes de liberar para uso real, marque todos os itens:

- [ ] Projeto Supabase de TESTE criado.
- [ ] Projeto Supabase de PRODUÇÃO criado.
- [ ] `supabase_schema.sql` executado no ambiente correto.
- [ ] Bucket `alpes-system` criado.
- [ ] Bucket `imagens-produtos` criado.
- [ ] Buckets privados `anexos-frotas`, `documentos`, `uploads` e `imagens-sistema` criados.
- [ ] `SUPABASE_URL` configurada.
- [ ] `SUPABASE_ANON_KEY` configurada.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` configurada em Secrets/Variables.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` não está no GitHub.
- [ ] `ENVIRONMENT=production` configurado.
- [ ] `ALPES_ADMIN_USER` configurado.
- [ ] `ALPES_ADMIN_PASSWORD` forte configurado.
- [ ] Produção bloqueia fallback local sem Supabase.
- [ ] Login funcionando.
- [ ] Produtos salvando.
- [ ] Movimentações salvando.
- [ ] Frotas salvando.
- [ ] Controle de faltas salvando.
- [ ] Uploads funcionando no Supabase Storage.
- [ ] Logs aparecendo em `logs_sistema`.
- [ ] Restart sem perda de dados.
- [ ] Novo deploy sem perda de dados.
- [ ] Domínio de teste acessando corretamente.
- [ ] Domínio de produção acessando corretamente.
- [ ] HTTPS ativo.

## Validação Local De Variáveis

Para validar variáveis antes de subir:

```powershell
$env:ENVIRONMENT="production"
$env:SUPABASE_URL="https://SEU-PROJETO.supabase.co"
$env:SUPABASE_ANON_KEY="SUA_ANON_KEY"
$env:SUPABASE_SERVICE_ROLE_KEY="SUA_SERVICE_ROLE_KEY"
$env:SUPABASE_BUCKET="alpes-system"
$env:ALPES_ADMIN_USER="admin_alpes"
$env:ALPES_ADMIN_PASSWORD="USE_UMA_SENHA_FORTE"
python scripts\validate_deploy.py
```

Resultado esperado:

```text
Variaveis de production validadas.
```

## Regra De Segurança

O arquivo `.env` real nunca deve ser versionado.

Arquivos protegidos no Git:

- `.env`
- `.env.*`
- `.streamlit/secrets.toml`
- logs
- backups
- credenciais locais
