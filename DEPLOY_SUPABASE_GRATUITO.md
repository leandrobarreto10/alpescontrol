# Deploy com Streamlit Cloud + Supabase

Este sistema usa Supabase como armazenamento persistente profissional para o ambiente online.

No Streamlit Cloud, o disco local e temporario. Por isso, cadastros feitos online so ficam seguros quando o Supabase esta configurado.

## 1. Criar projeto no Supabase

1. Acesse https://supabase.com.
2. Crie um projeto.
3. Aguarde o provisionamento finalizar.

## 2. Criar tabelas e buckets

1. No Supabase, abra **SQL Editor**.
2. Copie todo o conteudo de `supabase_schema.sql`.
3. Execute o script.

O script cria as tabelas operacionais, gatilhos de `updated_at` e os buckets:

- `imagens-produtos`
- `alpes-system`

## 3. Configurar Streamlit Secrets

No Supabase, abra **Project Settings > API** e copie:

- `Project URL`
- `service_role key`

No Streamlit Cloud, abra **Settings > Secrets** e adicione:

```toml
SUPABASE_URL = "COLE_AQUI_PROJECT_URL"
SUPABASE_SERVICE_ROLE_KEY = "COLE_AQUI_SERVICE_ROLE_KEY"
SUPABASE_BUCKET = "alpes-system"
ALPES_EXIGIR_ARMAZENAMENTO_ONLINE = "true"
```

Depois clique em **Save changes** e **Reboot app**.

## 4. Migração automática

Na primeira inicializacao com Supabase configurado, o sistema verifica os arquivos antigos:

- `.xlsx`
- `.json`
- imagens
- anexos

Se uma tabela estiver vazia, o sistema migra os dados locais existentes para o PostgreSQL.

Se a tabela ja tiver dados, o sistema nao duplica registros.

Os arquivos antigos continuam na pasta como copia historica. Eles nao sao apagados.

## 5. Fonte principal dos dados

Com Supabase configurado:

- leituras de tabelas usam PostgreSQL primeiro;
- salvamentos gravam no PostgreSQL;
- imagens e anexos sobem para o Supabase Storage;
- logs de auditoria tambem sao enviados ao banco;
- o app bloqueia gravacoes online se nao houver armazenamento persistente configurado.

## 6. Backup

O backup principal passa a ser o banco PostgreSQL do Supabase.

Para exportar dados manualmente:

1. No Supabase, abra **Table Editor**.
2. Escolha a tabela.
3. Use **Export data** para CSV.

Para uma rotina profissional, configure tambem backups/snapshots no painel do Supabase conforme o plano contratado.

## 7. Observacao importante

Nunca coloque `SUPABASE_SERVICE_ROLE_KEY` no GitHub.

Essa chave deve ficar apenas nos Secrets do Streamlit Cloud ou em variaveis de ambiente do servidor.
