# Checklist Final de Implantacao Online

Use este checklist antes do primeiro deploy online de TESTE do sistema ALPES Gestao e Facilities.

Objetivo: confirmar que Supabase, Storage, Streamlit Cloud e ambiente `production` estao prontos para validar persistencia real, uploads e multiplos usuarios.

## Etapa 1 - Supabase

- [ ] Criar projeto TESTE no Supabase.
- [ ] Nome sugerido: `alpes-teste`.
- [ ] Escolher a regiao mais proxima dos usuarios no Brasil.
- [ ] Aguardar o provisionamento completo do projeto.
- [ ] Abrir **SQL Editor**.
- [ ] Executar o arquivo `supabase_schema.sql` completo.
- [ ] Reexecutar o `supabase_schema.sql` uma vez para confirmar idempotencia.
- [ ] Validar tabelas no **Table Editor**.
- [ ] Validar indices criados.
- [ ] Validar triggers de `updated_at`.
- [ ] Validar politicas de Storage.
- [ ] Validar buckets criados.

Buckets esperados:

- [ ] `alpes-system`
- [ ] `imagens-produtos`
- [ ] `anexos-frotas`
- [ ] `documentos`
- [ ] `uploads`
- [ ] `imagens-sistema`

Chaves do projeto:

- [ ] Copiar `SUPABASE_URL`.
- [ ] Copiar `SUPABASE_ANON_KEY`.
- [ ] Copiar `SUPABASE_SERVICE_ROLE_KEY`.
- [ ] Guardar `SUPABASE_SERVICE_ROLE_KEY` apenas em Secrets/Variables.
- [ ] Confirmar que nenhuma chave foi colocada em arquivo do GitHub.

## Etapa 2 - Storage

- [ ] Abrir o menu **Storage** no Supabase.
- [ ] Confirmar bucket publico `imagens-produtos`.
- [ ] Confirmar buckets privados `alpes-system`, `anexos-frotas`, `documentos`, `uploads` e `imagens-sistema`.
- [ ] Testar upload manual de arquivo pequeno no bucket `uploads`.
- [ ] Testar leitura/listagem do arquivo enviado.
- [ ] Testar exclusao do arquivo enviado.
- [ ] Testar URL publica em `imagens-produtos`.
- [ ] Testar URL assinada em bucket privado pelo sistema apos deploy.
- [ ] Validar permissoes de Storage.
- [ ] Confirmar que nenhuma permissao expoe a `SERVICE_ROLE_KEY`.

## Etapa 3 - Streamlit Cloud

- [ ] Criar conta ou acessar o Streamlit Cloud.
- [ ] Conectar a conta GitHub.
- [ ] Selecionar repositorio:

```text
leandrobarreto10/alpescontrol
```

- [ ] Selecionar branch `main`.
- [ ] Selecionar arquivo principal `app.py`.
- [ ] Abrir configuracao de **Secrets**.

Secrets obrigatorios:

```toml
ENVIRONMENT = "production"
SUPABASE_URL = "https://SEU-PROJETO-TESTE.supabase.co"
SUPABASE_ANON_KEY = "SUA_ANON_KEY_TESTE"
SUPABASE_SERVICE_ROLE_KEY = "SUA_SERVICE_ROLE_KEY_TESTE"
SUPABASE_BUCKET = "alpes-system"
ALPES_ADMIN_USER = "admin_teste"
ALPES_ADMIN_PASSWORD = "USE_UMA_SENHA_FORTE"
```

Secret opcional:

```toml
ALPES_ADMIN_EMAIL = "admin.teste@sistemaalpes.com.br"
```

- [ ] Salvar Secrets.
- [ ] Iniciar deploy.
- [ ] Abrir logs do deploy.
- [ ] Validar inicializacao sem erro de importacao.
- [ ] Validar que o app abre no navegador.
- [ ] Saber onde reiniciar o app: **Manage app > Reboot app**.

## Etapa 4 - Testes Operacionais

- [ ] Login funcionando.
- [ ] Logout funcionando.
- [ ] Usuario admin inicial funcionando.
- [ ] Cadastro de produto funcionando.
- [ ] Edicao de produto funcionando.
- [ ] Upload de imagem de produto funcionando.
- [ ] Movimentacao de estoque funcionando.
- [ ] Cadastro de clientes funcionando.
- [ ] Cadastro de fornecedores funcionando.
- [ ] Cadastro de veiculos funcionando.
- [ ] Abastecimentos funcionando.
- [ ] Manutencoes funcionando.
- [ ] Uploads de anexos funcionando.
- [ ] Imagens carregando corretamente.
- [ ] Storage funcionando.
- [ ] Logs registrando acoes principais.
- [ ] Persistencia apos restart do app.
- [ ] Persistencia apos novo deploy.
- [ ] Multiusuario funcionando em duas sessoes diferentes.
- [ ] Producao bloqueando fallback local.

Teste minimo de persistencia:

- [ ] Cadastrar um produto de teste.
- [ ] Cadastrar um veiculo de teste.
- [ ] Enviar uma imagem ou anexo.
- [ ] Reiniciar o app.
- [ ] Confirmar que produto, veiculo e arquivo continuam disponiveis.
- [ ] Fazer novo deploy.
- [ ] Confirmar novamente que os dados continuam disponiveis.

## Etapa 5 - Seguranca

- [ ] `.env` protegido no `.gitignore`.
- [ ] `.streamlit/secrets.toml` protegido no `.gitignore`.
- [ ] `.env` protegido no `.dockerignore`.
- [ ] `.streamlit/secrets.toml` protegido no `.dockerignore`.
- [ ] Nenhuma chave hardcoded no codigo.
- [ ] Nenhuma chave real em arquivos Markdown.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` mantida privada.
- [ ] `ALPES_ADMIN_PASSWORD` forte.
- [ ] Senha `123` nao usada em ambiente online.
- [ ] Logs funcionando.
- [ ] Producao bloqueia operacao sem Supabase.

Mensagem obrigatoria quando production estiver sem Supabase:

```text
Erro crítico: Supabase não configurado. O sistema não pode operar em produção sem banco de dados.
```

## Etapa 6 - Producao Futura

- [ ] Planejar subdominio `teste.sistemaalpes.com.br`.
- [ ] Planejar subdominio `app.sistemaalpes.com.br`.
- [ ] Manter banco Supabase de TESTE separado do banco de PRODUCAO.
- [ ] Manter Storage de TESTE separado do Storage de PRODUCAO.
- [ ] Configurar DNS/CNAME no provedor do dominio.
- [ ] Ativar HTTPS.
- [ ] Validar acesso externo.
- [ ] Ativar backup/snapshot do Supabase no ambiente de producao.
- [ ] Definir rotina de monitoramento.
- [ ] Definir rotina de restauracao em caso de incidente.

## Etapa 7 - Validacao Final Local

Executar antes do deploy:

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

Resultado esperado:

```text
Variaveis de production validadas.
```

Checklist final:

- [ ] Imports validados.
- [ ] Deploy preparado.
- [ ] Conexao Supabase preparada.
- [ ] Storage preparado.
- [ ] Secrets definidos.
- [ ] Ambiente `production` definido.
- [ ] Bloqueio de fallback local validado.
- [ ] Documentacao revisada.
- [ ] Nenhuma credencial exposta.

## Status Final

Quando todos os itens essenciais estiverem marcados, o sistema esta pronto para iniciar o deploy online de TESTE.
