# Auditoria de persistencia

## Regra de producao

Com `ENVIRONMENT=production`, o sistema exige Supabase configurado.

Sem Supabase, o app interrompe a operacao com:

```text
Erro crítico: Supabase não configurado. O sistema não pode operar em produção sem banco de dados.
```

## Uso permitido de arquivos

Arquivos `.xlsx`, `.json`, `.csv` e `.zip` ficam permitidos apenas para:

- migracao inicial;
- importacao controlada;
- exportacao manual;
- relatorios administrativos;
- desenvolvimento local.

## Uso proibido em producao

Em producao, arquivos locais nao sao fonte oficial para:

- usuarios;
- produtos;
- movimentacoes;
- clientes;
- fornecedores;
- categorias;
- bases;
- frotas;
- abastecimentos;
- manutencoes;
- documentos;
- controle de faltas;
- configuracoes;
- logs.

## Fonte oficial

Dados operacionais: Supabase/PostgreSQL.

Arquivos, anexos e imagens: Supabase Storage.

## Pontos revisados

- `pd.read_excel`: permitido apenas como fallback de desenvolvimento ou migracao inicial.
- `to_excel`: interceptado pela camada central; em producao grava no Supabase e nao cria Excel operacional.
- `json.load` e `json.dump`: permitidos em desenvolvimento; em producao, dados operacionais usam Supabase.
- uploads: em producao usam Supabase Storage.
- backups locais: bloqueados para restauracao em producao; snapshots oficiais devem ser feitos pelo Supabase.
- logs: gravados em `logs_sistema`.
- migracao: registrada em `migracoes_sistema`.
