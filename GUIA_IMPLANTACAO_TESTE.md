# Guia de Implantacao do Ambiente de Teste

Este guia e o passo a passo pratico para publicar o primeiro ambiente de TESTE do sistema ALPES Gestao e Facilities.

Use este ambiente antes da producao real. Nao coloque chaves reais em arquivos do GitHub.

## Etapa 1 - Supabase

1. Acesse o Supabase e crie um novo projeto.
2. Use um nome claro, por exemplo: `alpes-teste`.
3. Regiao recomendada: escolha a regiao mais proxima dos usuarios no Brasil. Se houver opcao em Sao Paulo, use ela. Caso nao haja, use a regiao com menor latencia disponivel.
4. Aguarde o projeto terminar de provisionar.
5. Abra o menu **SQL Editor**.
6. Abra o arquivo `supabase_schema.sql` do projeto.
7. Copie todo o conteudo do arquivo.
8. Cole no SQL Editor do Supabase.
9. Execute o script.

O `supabase_schema.sql` foi preparado para ser idempotente. Ele pode ser executado novamente para validar ou recriar partes seguras sem duplicar buckets ou quebrar tabelas existentes.

Depois da execucao, valide no Supabase:

- Tabelas criadas.
- Indices criados.
- Triggers de `updated_at` criadas.
- Politicas de Storage criadas.
- Buckets criados.

Buckets esperados:

- `alpes-system`
- `imagens-produtos`
- `anexos-frotas`
- `documentos`
- `uploads`
- `imagens-sistema`

Para localizar as chaves:

1. Abra **Project Settings**.
2. Abra **API**.
3. Copie:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`

Use a `SUPABASE_SERVICE_ROLE_KEY` somente nos Secrets do Streamlit Cloud. Nunca publique essa chave no GitHub.

## Etapa 2 - Storage

No Supabase, abra **Storage** e confirme os buckets listados acima.

Teste rapido recomendado:

1. Abra o bucket `uploads`.
2. Envie um arquivo pequeno de teste.
3. Confirme que o arquivo aparece na lista.
4. Apague o arquivo de teste.
5. Abra o bucket `imagens-produtos`.
6. Confirme que ele esta como publico.
7. Abra os buckets privados e confirme que nao estao publicos.

Validacao esperada:

- Upload funciona.
- Leitura funciona.
- Exclusao funciona.
- Bucket publico gera URL publica quando aplicavel.
- Buckets privados usam URL assinada pelo sistema.
- Nenhuma permissao deve expor `SERVICE_ROLE_KEY`.

## Etapa 3 - Streamlit Cloud

1. Acesse o Streamlit Cloud.
2. Crie ou entre na sua conta.
3. Conecte sua conta GitHub.
4. Clique em **New app**.
5. Selecione o repositorio:

```text
leandrobarreto10/alpescontrol
```

6. Selecione a branch:

```text
main
```

7. Selecione o arquivo principal:

```text
app.py
```

8. Abra **Advanced settings** ou **Secrets**.
9. Configure os Secrets:

```toml
ENVIRONMENT = "production"
SUPABASE_URL = "https://SEU-PROJETO-TESTE.supabase.co"
SUPABASE_ANON_KEY = "SUA_ANON_KEY_TESTE"
SUPABASE_SERVICE_ROLE_KEY = "SUA_SERVICE_ROLE_KEY_TESTE"
SUPABASE_BUCKET = "alpes-system"
ALPES_EXIGIR_ARMAZENAMENTO_ONLINE = "true"
ALPES_ADMIN_USER = "admin_teste"
ALPES_ADMIN_PASSWORD = "USE_UMA_SENHA_FORTE"
```

Opcional, se quiser informar email do admin inicial:

```toml
ALPES_ADMIN_EMAIL = "admin.teste@sistemaalpes.com.br"
```

10. Salve os Secrets.
11. Inicie o deploy.
12. Abra os logs do Streamlit Cloud.
13. Confirme que nao houve erro de importacao.
14. Para reiniciar, use **Manage app > Reboot app** ou faca um novo deploy.

## Etapa 4 - Testes Praticos

Depois do primeiro deploy, execute este checklist no ambiente de TESTE:

- [ ] Login funcionando.
- [ ] Logout funcionando.
- [ ] Admin inicial acessando.
- [ ] Cadastro de produto funcionando.
- [ ] Imagem de produto enviando para Storage.
- [ ] Movimentacao de estoque salvando.
- [ ] Clientes salvando.
- [ ] Fornecedores salvando.
- [ ] Veiculos/frotas salvando.
- [ ] Anexos de frota enviando para Storage.
- [ ] Imagens aparecendo corretamente.
- [ ] Logs registrando acoes principais.
- [ ] Reiniciar app sem perder dados.
- [ ] Fazer novo deploy sem perder dados.
- [ ] Abrir com dois usuarios/sessoes e validar cadastros simples.
- [ ] Production bloqueia fallback local se Supabase estiver sem Secrets.

Teste de persistencia recomendado:

1. Cadastre um produto de teste.
2. Cadastre um veiculo de teste.
3. Envie um anexo pequeno.
4. Reinicie o app.
5. Confirme que os dados continuam.
6. Faca um novo deploy.
7. Confirme novamente que os dados continuam.

## Etapa 5 - Producao Futura

Quando o teste estiver aprovado, crie ambiente separado para producao.

Subdominios sugeridos:

- Teste: `teste.sistemaalpes.com.br`
- Producao: `app.sistemaalpes.com.br`

Regras importantes:

- Use projeto Supabase separado para TESTE.
- Use projeto Supabase separado para PRODUCAO.
- Use Secrets separados.
- Nao misture dados de teste com dados reais.
- Ative HTTPS no provedor usado.

DNS resumido:

1. No provedor do dominio, crie um CNAME para o endereco informado pelo Streamlit Cloud.
2. Aguarde propagacao.
3. Valide acesso externo.
4. Confirme HTTPS ativo.

## Etapa 6 - Railway Futuro

Se optar por Railway depois:

1. Acesse Railway.
2. Crie um projeto.
3. Conecte o GitHub.
4. Selecione `leandrobarreto10/alpescontrol`.
5. Configure as Variables com os mesmos nomes usados no Streamlit Cloud.
6. Confirme que o Railway reconheceu o `Procfile`.
7. O comando esperado e:

```text
web: streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.fileWatcherType=poll
```

8. O Dockerfile tambem esta pronto para uso.
9. O Railway injeta a variavel `PORT` automaticamente.
10. Valide logs, login, uploads e persistencia apos restart.

## Etapa 7 - Seguranca

Regras obrigatorias:

- Nunca subir `.env` para o GitHub.
- Nunca subir `.streamlit/secrets.toml` para o GitHub.
- Nunca compartilhar `SUPABASE_SERVICE_ROLE_KEY`.
- Nunca usar senha `123` em ambiente online.
- Manter TESTE e PRODUCAO separados.
- Conferir Secrets antes do deploy.
- Usar senha forte para `ALPES_ADMIN_PASSWORD`.
- Revogar chaves caso alguma seja exposta por engano.

Arquivos sensiveis ja protegidos no projeto:

- `.env`
- `.env.*`
- `.streamlit/secrets.toml`
- arquivos com `credential`, `credentials` ou `credenciais` no nome.

## Etapa 8 - Validacao Final Local

Antes de publicar, rode:

```powershell
python -m py_compile app.py
python -m py_compile scripts\validate_deploy.py
```

Para validar variaveis de production localmente:

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

Validacoes finais:

- [ ] Imports compilando.
- [ ] Secrets preenchidos no Streamlit Cloud.
- [ ] Supabase conectado.
- [ ] Storage conectado.
- [ ] Deploy concluido.
- [ ] Logs sem erro critico.
- [ ] Fallback local bloqueado em production.
- [ ] Persistencia validada apos restart.
- [ ] Persistencia validada apos novo deploy.

## Status Esperado

Ao concluir este guia, o ambiente de TESTE online estara pronto para validacao operacional antes da publicacao em producao.
