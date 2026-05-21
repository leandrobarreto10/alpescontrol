# Primeiro Deploy Online de Teste

Roteiro pratico para publicar o primeiro ambiente online de TESTE do sistema ALPES Gestao e Facilities.

Este documento nao substitui os guias completos. Use-o como sequencia objetiva para executar o deploy real.

## Etapa 1 - Supabase TESTE

1. Acesse o Supabase.
2. Crie um novo projeto para TESTE.
3. Nome sugerido: `alpes-teste`.
4. Regiao recomendada: escolha a regiao mais proxima dos usuarios no Brasil. Se houver Sao Paulo disponivel, use Sao Paulo.
5. Aguarde o projeto ficar pronto.
6. Abra **SQL Editor**.
7. Abra o arquivo `supabase_schema.sql` neste repositorio.
8. Copie todo o conteudo.
9. Cole no SQL Editor.
10. Execute o script.
11. Execute o script uma segunda vez para confirmar que ele e idempotente.

Validar no Supabase:

- [ ] Tabelas criadas.
- [ ] Indices criados.
- [ ] Triggers criadas.
- [ ] Buckets criados.
- [ ] Politicas de Storage criadas.

Buckets esperados:

- [ ] `alpes-system`
- [ ] `imagens-produtos`
- [ ] `anexos-frotas`
- [ ] `documentos`
- [ ] `uploads`
- [ ] `imagens-sistema`

Localizar chaves:

1. Abra **Project Settings**.
2. Abra **API**.
3. Copie:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`

Use a `SUPABASE_SERVICE_ROLE_KEY` somente nos Secrets do Streamlit Cloud.

## Etapa 2 - Streamlit Cloud

1. Acesse o Streamlit Cloud.
2. Crie conta ou entre na conta existente.
3. Conecte o GitHub.
4. Clique em **New app**.
5. Selecione o repositorio:

```text
leandrobarreto10/alpescontrol
```

6. Selecione:

```text
Branch: main
Main file: app.py
```

7. Abra **Secrets**.
8. Configure:

```toml
ENVIRONMENT = "production"
SUPABASE_URL = "https://SEU-PROJETO-TESTE.supabase.co"
SUPABASE_ANON_KEY = "SUA_ANON_KEY_TESTE"
SUPABASE_SERVICE_ROLE_KEY = "SUA_SERVICE_ROLE_KEY_TESTE"
SUPABASE_BUCKET = "alpes-system"
ALPES_ADMIN_USER = "admin_teste"
ALPES_ADMIN_PASSWORD = "USE_UMA_SENHA_FORTE"
```

Opcional:

```toml
ALPES_ADMIN_EMAIL = "admin.teste@sistemaalpes.com.br"
```

9. Salve os Secrets.
10. Inicie o deploy.
11. Abra os logs.
12. Confirme que o app iniciou sem erro de importacao.
13. Para reiniciar o app, use **Manage app > Reboot app**.

## Etapa 3 - Testes Online

Execute no ambiente publicado:

- [ ] Login funcionando.
- [ ] Logout funcionando.
- [ ] Cadastro de produto.
- [ ] Movimentacao de estoque.
- [ ] Clientes.
- [ ] Fornecedores.
- [ ] Frotas.
- [ ] Uploads.
- [ ] Imagens.
- [ ] Storage funcionando.
- [ ] Persistencia apos restart.
- [ ] Persistencia apos novo deploy.
- [ ] Multiusuario funcionando.
- [ ] Producao bloqueando fallback local.

Teste minimo recomendado:

1. Cadastrar um produto de teste.
2. Cadastrar um cliente de teste.
3. Cadastrar um veiculo de teste.
4. Fazer uma movimentacao de estoque.
5. Enviar uma imagem ou anexo.
6. Reiniciar o app.
7. Confirmar que tudo permaneceu salvo.
8. Fazer novo deploy.
9. Confirmar novamente que tudo permaneceu salvo.

## Etapa 4 - Seguranca

Regras obrigatorias:

- Nunca subir `.env`.
- Nunca subir `.streamlit/secrets.toml`.
- Nunca compartilhar `SUPABASE_SERVICE_ROLE_KEY`.
- Validar Secrets antes do deploy.
- Manter ambiente TESTE separado da PRODUCAO.
- Nao usar senha `123` online.
- Usar senha forte em `ALPES_ADMIN_PASSWORD`.

Mensagem obrigatoria quando production estiver sem Supabase:

```text
Erro crítico: Supabase não configurado. O sistema não pode operar em produção sem banco de dados.
```

## Etapa 5 - Producao Futura

Planejamento resumido:

- Teste: `teste.sistemaalpes.com.br`
- Producao: `app.sistemaalpes.com.br`
- Configurar DNS/CNAME no provedor do dominio.
- Ativar HTTPS.
- Manter Supabase TESTE separado do Supabase PRODUCAO.
- Railway pode ser usado futuramente conectando o GitHub e configurando as mesmas Variables.
- VPS pode ser usado futuramente com Dockerfile, HTTPS e variaveis de ambiente seguras.

## Etapa 6 - Validacao Final Local

Antes de iniciar o deploy, rode:

```powershell
python -m py_compile app.py
python -m py_compile scripts\validate_deploy.py
```

Validar variaveis de production:

```powershell
$env:ENVIRONMENT="production"
$env:SUPABASE_URL="https://SEU-PROJETO-TESTE.supabase.co"
$env:SUPABASE_ANON_KEY="SUA_ANON_KEY_TESTE"
$env:SUPABASE_SERVICE_ROLE_KEY="SUA_SERVICE_ROLE_KEY_TESTE"
$env:SUPABASE_BUCKET="alpes-system"
$env:ALPES_ADMIN_USER="admin_teste"
$env:ALPES_ADMIN_PASSWORD="USE_UMA_SENHA_FORTE"
python scripts\validate_deploy.py
```

Confirmar:

- [ ] Imports validos.
- [ ] Conexao Supabase preparada.
- [ ] Storage preparado.
- [ ] Secrets definidos.
- [ ] Deploy pronto.
- [ ] Ambiente `production` definido.

## Status

Depois de concluir estas etapas, o sistema esta pronto para o primeiro deploy online de TESTE.
