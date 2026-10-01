# Aceitação da Etapa 6 — Conferência

## Entregue

- A rota `/conferencia/` seleciona lotes somente pela empresa e competência do contexto.
- Linhas preparadas podem ser corrigidas com validação de data, valor, tipo, conta e filial.
- Edição em lote é explícita: a contadora seleciona as linhas e o campo a alterar.
- Totais de débitos, créditos, linhas válidas e pendências ficam visíveis antes da aprovação.
- A aprovação reaproveita a transação contábil existente, exige lote em revisão sem pendências e mantém `sequencial_lote`.
- Quando a competência já possui lançamentos, a tela oferece Substituir e Cancelar.
- Lotes em revisão podem ser cancelados e lotes cancelados podem ser reabertos.

## Verificações

- `web/manage.py test nucleo --settings=configuracao.settings.teste`: 46 testes aprovados.
- `python -m unittest discover -s tests -q`: 30 testes aprovados.
- `python -m py_compile ...`: aprovado.
- `npm run build:css`: aprovado.
- Nenhuma escrita ou migração foi executada no Supabase de produção.

## Limite conhecido

A aprovação continua exigindo uma única competência por lote. Arquivos com vários meses devem ser separados ou revisados antes da aprovação, como exige a regra contábil.
