# Configuração Do Supabase

## 1. Criar As Tabelas

No painel do Supabase, abra:

`SQL Editor > New query`

Cole e execute o conteúdo do arquivo:

`supabase_schema.sql`

Esse script cria:

- `produtos`
- `movimentacoes`
- `usuarios`
- `fornecedores`
- `clientes`
- `categorias`
- `configuracoes`
- bucket `imagens-produtos`

## 2. Criar/Validar O Bucket De Imagens

No Supabase, abra:

`Storage > Buckets`

Confirme se existe:

`imagens-produtos`

Configuração recomendada:

- Nome: `imagens-produtos`
- Público: `Sim`

## 3. Configurar As Chaves No Streamlit

No Streamlit Cloud, abra:

`App > Settings > Secrets`

Adicione:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_ANON_KEY = "SUA_ANON_KEY"
SUPABASE_KEY = "SUA_CHAVE_DO_SUPABASE"
```

Também funciona usando variáveis de ambiente com os mesmos nomes:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_KEY`

## 4. Como Testar

1. Inicie o sistema.
2. Cadastre um produto com imagem.
3. Confira no Supabase:
   - tabela `produtos`
   - bucket `imagens-produtos`
4. Reinicie o Streamlit.
5. Entre novamente no sistema.
6. O produto e a imagem devem continuar aparecendo.

## 5. Exportação Manual

Na aba:

`Configurações > Backup`

Use:

- `Exportar Produtos Para Excel`
- `Exportar Movimentações Para Excel`

Esses botões geram arquivos `.xlsx` para backup manual.
