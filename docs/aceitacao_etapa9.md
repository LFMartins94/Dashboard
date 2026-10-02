# Aceitação da Etapa 9 — Auditoria operacional

## Entregue

- A rota `/auditoria/` exige autenticação, empresa e competência do contexto.
- A auditoria executa regras determinísticas para duplicidade, falta de par, histórico vazio, valor anômalo e conta fora do padrão.
- Novas ocorrências trazem `lancamento_id` quando o lançamento existe; registros antigos sem vínculo permanecem explícitos para revisão, sem associação presumida.
- A inserção de ocorrências é idempotente e usa bloqueio de tabela no PostgreSQL para reduzir risco de duplicação concorrente.
- Ocorrências podem ser resolvidas ou reabertas com usuário, data e justificativa preservados em `django_estados_ocorrencias_auditoria`.
- A tela exibe o histórico recente de inserções, edições e exclusões de linhas preparadas e lançamentos.
- A exportação CSV contém somente severidade, tipo, descrição, valores de negócio e estado, sem identificadores técnicos.
- A migração `0006_auditoria_operacional.py` prepara histórico, triggers, RLS e bloqueio de acesso pelos papéis públicos.

## Verificações

- 55 testes Django e 31 testes legados aprovados.
- Testes específicos cobrem vínculo de ocorrência ao lançamento e resolução com usuário e data.
- `makemigrations --check`, verificação Django, compilação Python, template e Tailwind aprovados.
- Nenhuma migração, DDL ou escrita foi executada no Supabase de produção.

## Limite conhecido

Ocorrências anteriores sem `lancamento_id` não são vinculadas automaticamente porque isso poderia atribuí-las ao lançamento errado. Elas ficam visíveis como casos sem vínculo para revisão humana.
