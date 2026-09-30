# Verificação do backup — Etapa 1

Executada em `2026-09-30T20:23:56+00:00`.

## Procedimento

1. O `pg_dump` 17.11 gerou um arquivo custom a partir do schema `public` do PostgreSQL remoto 17.6.
2. Um PostgreSQL 17.11 portátil foi inicializado localmente em `127.0.0.1:55432`.
3. O dump foi restaurado no banco isolado `contaview_restore`, dentro de uma única transação e com parada no primeiro erro.
4. `ANALYZE` foi executado no banco restaurado.
5. Estrutura e totais foram comparados com o banco remoto por consultas somente leitura.

## Resultado

**Aprovado**

| Verificação | Resultado |
|---|:---:|
| Tabelas | OK |
| Totais de linhas | OK |
| Colunas e tipos | OK |
| Índices | OK |
| Triggers | OK |
| Constraints | OK |
| Configuração RLS | OK |
| Quantidade de políticas RLS | OK |

## Totais conferidos

| Tabela | Remoto | Restaurado |
|---|---:|---:|
| `conciliacoes` | 3 | 3 |
| `conversas` | 6 | 6 |
| `empresas` | 3 | 3 |
| `gastos` | 42 | 42 |
| `historico_alteracoes` | 0 | 0 |
| `lancamentos` | 100 | 100 |
| `linhas_preparadas` | 0 | 0 |
| `lotes_importacao` | 0 | 0 |
| `mensagens` | 2 | 2 |
| `ocorrencias_auditoria` | 4 | 4 |

## Artefato

- Arquivo local ignorado pelo Git: `temp\etapa1\backup_public.dump`.
- Tamanho: `42468` bytes.
- SHA-256: `1690190f89517154ea032757cde2f170344d465218d09871ca7770299fd96b0c`.
- O dump contém dados reais e deve permanecer fora do repositório.
