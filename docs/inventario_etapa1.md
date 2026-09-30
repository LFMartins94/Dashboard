# Inventário técnico — Etapa 1

Gerado em `2026-09-30T17:58:43+00:00` a partir de uma conexão somente leitura com o PostgreSQL.

## Escopo

- PostgreSQL: `PostgreSQL 17.6 on aarch64-unknown-linux-gnu`.
- Tabelas públicas da aplicação catalogadas: **10**.
- Tabelas nos schemas não sistêmicos encontrados na conexão: **53**; os schemas gerenciados pelo Supabase não foram incluídos no snapshot de dados.
- Nenhum DDL, insert, update ou delete foi executado.
- O snapshot local inclui a lista completa de colunas, tipos e linhas de cada tabela pública.

## Tabelas, volume e RLS

| Tabela | Linhas | RLS | Forçar RLS | Políticas |
|---|---:|:---:|:---:|---:|
| `conciliacoes` | 3 | sim | não | 0 |
| `conversas` | 6 | sim | não | 0 |
| `empresas` | 3 | sim | não | 0 |
| `gastos` | 42 | sim | não | 0 |
| `historico_alteracoes` | 0 | sim | não | 0 |
| `lancamentos` | 100 | sim | não | 0 |
| `linhas_preparadas` | 0 | sim | não | 0 |
| `lotes_importacao` | 0 | sim | não | 0 |
| `mensagens` | 2 | sim | não | 0 |
| `ocorrencias_auditoria` | 4 | sim | não | 0 |

> Atenção: o RLS está habilitado nas tabelas públicas, mas o catálogo retornou zero políticas. Nenhuma política foi criada nesta etapa porque isso exige decisão explícita do modelo de autenticação da nova aplicação.

## Índices

| Tabela | Índice | Definição |
|---|---|---|
| `conciliacoes` | `conciliacoes_pkey` | `CREATE UNIQUE INDEX conciliacoes_pkey ON public.conciliacoes USING btree (id)` |
| `conciliacoes` | `idx_conciliacoes_empresa` | `CREATE INDEX idx_conciliacoes_empresa ON public.conciliacoes USING btree (empresa_id)` |
| `conversas` | `conversas_pkey` | `CREATE UNIQUE INDEX conversas_pkey ON public.conversas USING btree (id)` |
| `empresas` | `empresas_nome_key` | `CREATE UNIQUE INDEX empresas_nome_key ON public.empresas USING btree (nome)` |
| `empresas` | `empresas_pkey` | `CREATE UNIQUE INDEX empresas_pkey ON public.empresas USING btree (id)` |
| `gastos` | `gastos_pkey` | `CREATE UNIQUE INDEX gastos_pkey ON public.gastos USING btree (id)` |
| `gastos` | `idx_gastos_categoria` | `CREATE INDEX idx_gastos_categoria ON public.gastos USING btree (categoria)` |
| `gastos` | `idx_gastos_data` | `CREATE INDEX idx_gastos_data ON public.gastos USING btree (data)` |
| `historico_alteracoes` | `historico_alteracoes_pkey` | `CREATE UNIQUE INDEX historico_alteracoes_pkey ON public.historico_alteracoes USING btree (id)` |
| `historico_alteracoes` | `idx_historico_alteracoes_empresa` | `CREATE INDEX idx_historico_alteracoes_empresa ON public.historico_alteracoes USING btree (empresa_id, alterado_em DESC)` |
| `historico_alteracoes` | `idx_historico_alteracoes_registro` | `CREATE INDEX idx_historico_alteracoes_registro ON public.historico_alteracoes USING btree (tabela, registro_id, alterado_em DESC)` |
| `lancamentos` | `idx_lancamentos_conta` | `CREATE INDEX idx_lancamentos_conta ON public.lancamentos USING btree (conta_contabil)` |
| `lancamentos` | `idx_lancamentos_data` | `CREATE INDEX idx_lancamentos_data ON public.lancamentos USING btree (data)` |
| `lancamentos` | `idx_lancamentos_empresa` | `CREATE INDEX idx_lancamentos_empresa ON public.lancamentos USING btree (empresa_id)` |
| `lancamentos` | `idx_lancamentos_periodo` | `CREATE INDEX idx_lancamentos_periodo ON public.lancamentos USING btree (periodo)` |
| `lancamentos` | `idx_lancamentos_tipo` | `CREATE INDEX idx_lancamentos_tipo ON public.lancamentos USING btree (tipo)` |
| `lancamentos` | `lancamentos_pkey` | `CREATE UNIQUE INDEX lancamentos_pkey ON public.lancamentos USING btree (id)` |
| `linhas_preparadas` | `idx_linhas_preparadas_empresa` | `CREATE INDEX idx_linhas_preparadas_empresa ON public.linhas_preparadas USING btree (empresa_id, lote_id, status)` |
| `linhas_preparadas` | `linhas_preparadas_lote_id_numero_linha_key` | `CREATE UNIQUE INDEX linhas_preparadas_lote_id_numero_linha_key ON public.linhas_preparadas USING btree (lote_id, numero_linha)` |
| `linhas_preparadas` | `linhas_preparadas_pkey` | `CREATE UNIQUE INDEX linhas_preparadas_pkey ON public.linhas_preparadas USING btree (id)` |
| `lotes_importacao` | `idx_lotes_importacao_empresa` | `CREATE INDEX idx_lotes_importacao_empresa ON public.lotes_importacao USING btree (empresa_id, criado_em DESC)` |
| `lotes_importacao` | `lotes_importacao_id_empresa_id_key` | `CREATE UNIQUE INDEX lotes_importacao_id_empresa_id_key ON public.lotes_importacao USING btree (id, empresa_id)` |
| `lotes_importacao` | `lotes_importacao_pkey` | `CREATE UNIQUE INDEX lotes_importacao_pkey ON public.lotes_importacao USING btree (id)` |
| `mensagens` | `idx_mensagens_conversa` | `CREATE INDEX idx_mensagens_conversa ON public.mensagens USING btree (conversa_id)` |
| `mensagens` | `mensagens_pkey` | `CREATE UNIQUE INDEX mensagens_pkey ON public.mensagens USING btree (id)` |
| `ocorrencias_auditoria` | `idx_ocorrencias_auditoria_empresa` | `CREATE INDEX idx_ocorrencias_auditoria_empresa ON public.ocorrencias_auditoria USING btree (empresa_id)` |
| `ocorrencias_auditoria` | `idx_ocorrencias_auditoria_lancamento` | `CREATE INDEX idx_ocorrencias_auditoria_lancamento ON public.ocorrencias_auditoria USING btree (lancamento_id)` |
| `ocorrencias_auditoria` | `ocorrencias_auditoria_pkey` | `CREATE UNIQUE INDEX ocorrencias_auditoria_pkey ON public.ocorrencias_auditoria USING btree (id)` |

## Triggers

| Tabela | Trigger | Evento | Momento | Ação |
|---|---|---|---|---|
| `lancamentos` | `historico_lancamentos` | INSERT | AFTER | `EXECUTE FUNCTION registrar_historico_alteracoes()` |
| `lancamentos` | `historico_lancamentos` | DELETE | AFTER | `EXECUTE FUNCTION registrar_historico_alteracoes()` |
| `lancamentos` | `historico_lancamentos` | UPDATE | AFTER | `EXECUTE FUNCTION registrar_historico_alteracoes()` |
| `linhas_preparadas` | `historico_linhas_preparadas` | INSERT | AFTER | `EXECUTE FUNCTION registrar_historico_alteracoes()` |
| `linhas_preparadas` | `historico_linhas_preparadas` | DELETE | AFTER | `EXECUTE FUNCTION registrar_historico_alteracoes()` |
| `linhas_preparadas` | `historico_linhas_preparadas` | UPDATE | AFTER | `EXECUTE FUNCTION registrar_historico_alteracoes()` |

## Constraints

| Tabela | Nome | Tipo | Definição |
|---|---|---|---|
| `gastos` | `gastos_pkey` | p | `PRIMARY KEY (id)` |
| `empresas` | `empresas_nome_key` | u | `UNIQUE (nome)` |
| `empresas` | `empresas_pkey` | p | `PRIMARY KEY (id)` |
| `lancamentos` | `lancamentos_empresa_id_fkey` | f | `FOREIGN KEY (empresa_id) REFERENCES empresas(id)` |
| `lancamentos` | `lancamentos_pkey` | p | `PRIMARY KEY (id)` |
| `lancamentos` | `lancamentos_tipo_check` | c | `CHECK ((tipo = ANY (ARRAY['C'::bpchar, 'D'::bpchar])))` |
| `conciliacoes` | `conciliacoes_empresa_id_fkey` | f | `FOREIGN KEY (empresa_id) REFERENCES empresas(id)` |
| `conciliacoes` | `conciliacoes_pkey` | p | `PRIMARY KEY (id)` |
| `ocorrencias_auditoria` | `ocorrencias_auditoria_empresa_id_fkey` | f | `FOREIGN KEY (empresa_id) REFERENCES empresas(id)` |
| `ocorrencias_auditoria` | `ocorrencias_auditoria_lancamento_id_fkey` | f | `FOREIGN KEY (lancamento_id) REFERENCES lancamentos(id)` |
| `ocorrencias_auditoria` | `ocorrencias_auditoria_pkey` | p | `PRIMARY KEY (id)` |
| `conversas` | `conversas_pkey` | p | `PRIMARY KEY (id)` |
| `mensagens` | `mensagens_conversa_id_fkey` | f | `FOREIGN KEY (conversa_id) REFERENCES conversas(id) ON DELETE CASCADE` |
| `mensagens` | `mensagens_pkey` | p | `PRIMARY KEY (id)` |
| `mensagens` | `mensagens_role_check` | c | `CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying])::text[])))` |
| `lotes_importacao` | `lotes_importacao_empresa_id_fkey` | f | `FOREIGN KEY (empresa_id) REFERENCES empresas(id)` |
| `lotes_importacao` | `lotes_importacao_id_empresa_id_key` | u | `UNIQUE (id, empresa_id)` |
| `lotes_importacao` | `lotes_importacao_periodo_check` | c | `CHECK (((periodo IS NULL) OR ((periodo)::text ~ '^[0-9]{4}-(0[1-9]\|1[0-2])$'::text)))` |
| `lotes_importacao` | `lotes_importacao_pkey` | p | `PRIMARY KEY (id)` |
| `lotes_importacao` | `lotes_importacao_status_check` | c | `CHECK (((status)::text = ANY ((ARRAY['em_revisao'::character varying, 'concluido'::character varying, 'cancelado'::character varying])::text[])))` |
| `lotes_importacao` | `lotes_importacao_total_linhas_check` | c | `CHECK ((total_linhas > 0))` |
| `linhas_preparadas` | `linhas_preparadas_empresa_id_fkey` | f | `FOREIGN KEY (empresa_id) REFERENCES empresas(id)` |
| `linhas_preparadas` | `linhas_preparadas_lote_id_empresa_id_fkey` | f | `FOREIGN KEY (lote_id, empresa_id) REFERENCES lotes_importacao(id, empresa_id)` |
| `linhas_preparadas` | `linhas_preparadas_lote_id_numero_linha_key` | u | `UNIQUE (lote_id, numero_linha)` |
| `linhas_preparadas` | `linhas_preparadas_numero_linha_check` | c | `CHECK ((numero_linha > 0))` |
| `linhas_preparadas` | `linhas_preparadas_pkey` | p | `PRIMARY KEY (id)` |
| `linhas_preparadas` | `linhas_preparadas_status_check` | c | `CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'validado'::character varying])::text[])))` |
| `linhas_preparadas` | `linhas_preparadas_tipo_check` | c | `CHECK (((tipo IS NULL) OR (tipo = ANY (ARRAY['C'::bpchar, 'D'::bpchar]))))` |
| `historico_alteracoes` | `historico_alteracoes_pkey` | p | `PRIMARY KEY (id)` |

## Políticas RLS

Nenhuma política cadastrada no schema `public`.

## Privilégios encontrados

| Tabela | Concedido a | Privilégio |
|---|---|---|
| `conciliacoes` | `postgres` | DELETE |
| `conciliacoes` | `postgres` | INSERT |
| `conciliacoes` | `postgres` | REFERENCES |
| `conciliacoes` | `postgres` | SELECT |
| `conciliacoes` | `postgres` | TRIGGER |
| `conciliacoes` | `postgres` | TRUNCATE |
| `conciliacoes` | `postgres` | UPDATE |
| `conversas` | `postgres` | DELETE |
| `conversas` | `postgres` | INSERT |
| `conversas` | `postgres` | REFERENCES |
| `conversas` | `postgres` | SELECT |
| `conversas` | `postgres` | TRIGGER |
| `conversas` | `postgres` | TRUNCATE |
| `conversas` | `postgres` | UPDATE |
| `empresas` | `postgres` | DELETE |
| `empresas` | `postgres` | INSERT |
| `empresas` | `postgres` | REFERENCES |
| `empresas` | `postgres` | SELECT |
| `empresas` | `postgres` | TRIGGER |
| `empresas` | `postgres` | TRUNCATE |
| `empresas` | `postgres` | UPDATE |
| `gastos` | `postgres` | DELETE |
| `gastos` | `postgres` | INSERT |
| `gastos` | `postgres` | REFERENCES |
| `gastos` | `postgres` | SELECT |
| `gastos` | `postgres` | TRIGGER |
| `gastos` | `postgres` | TRUNCATE |
| `gastos` | `postgres` | UPDATE |
| `historico_alteracoes` | `postgres` | DELETE |
| `historico_alteracoes` | `postgres` | INSERT |
| `historico_alteracoes` | `postgres` | REFERENCES |
| `historico_alteracoes` | `postgres` | SELECT |
| `historico_alteracoes` | `postgres` | TRIGGER |
| `historico_alteracoes` | `postgres` | TRUNCATE |
| `historico_alteracoes` | `postgres` | UPDATE |
| `lancamentos` | `postgres` | DELETE |
| `lancamentos` | `postgres` | INSERT |
| `lancamentos` | `postgres` | REFERENCES |
| `lancamentos` | `postgres` | SELECT |
| `lancamentos` | `postgres` | TRIGGER |
| `lancamentos` | `postgres` | TRUNCATE |
| `lancamentos` | `postgres` | UPDATE |
| `linhas_preparadas` | `postgres` | DELETE |
| `linhas_preparadas` | `postgres` | INSERT |
| `linhas_preparadas` | `postgres` | REFERENCES |
| `linhas_preparadas` | `postgres` | SELECT |
| `linhas_preparadas` | `postgres` | TRIGGER |
| `linhas_preparadas` | `postgres` | TRUNCATE |
| `linhas_preparadas` | `postgres` | UPDATE |
| `lotes_importacao` | `postgres` | DELETE |
| `lotes_importacao` | `postgres` | INSERT |
| `lotes_importacao` | `postgres` | REFERENCES |
| `lotes_importacao` | `postgres` | SELECT |
| `lotes_importacao` | `postgres` | TRIGGER |
| `lotes_importacao` | `postgres` | TRUNCATE |
| `lotes_importacao` | `postgres` | UPDATE |
| `mensagens` | `postgres` | DELETE |
| `mensagens` | `postgres` | INSERT |
| `mensagens` | `postgres` | REFERENCES |
| `mensagens` | `postgres` | SELECT |
| `mensagens` | `postgres` | TRIGGER |
| `mensagens` | `postgres` | TRUNCATE |
| `mensagens` | `postgres` | UPDATE |
| `ocorrencias_auditoria` | `postgres` | DELETE |
| `ocorrencias_auditoria` | `postgres` | INSERT |
| `ocorrencias_auditoria` | `postgres` | REFERENCES |
| `ocorrencias_auditoria` | `postgres` | SELECT |
| `ocorrencias_auditoria` | `postgres` | TRIGGER |
| `ocorrencias_auditoria` | `postgres` | TRUNCATE |
| `ocorrencias_auditoria` | `postgres` | UPDATE |

## Backup local

- Snapshot lógico: `temp\etapa1\backup_public_logico.json`.
- SHA-256: `cf7ff5d31f29efa8c0386722ec5776f623c02b68767fdac6397b4df2542140b7`; manifesto em `temp/etapa1/backup_manifesto.json`.
- Verificação realizada: o arquivo foi lido novamente como JSON e os totais por tabela foram comparados com a fotografia gerada.
- Limitação: `pg_dump` não pôde ser executado porque o CLI do Supabase exige Docker/Podman neste ambiente. Ainda falta restaurar o dump nativo em um PostgreSQL de teste.
