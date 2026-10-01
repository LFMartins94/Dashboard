# Aceitação da Etapa 8 — Conciliação e exceções

## Entregue

- A rota `/conciliacao/` exige autenticação, empresa e competência na sessão.
- A primeira fonte deve ser um lote de extrato; a referência pode ser outro lote ou os lançamentos aprovados da competência atual.
- O cruzamento é determinístico e exige valor, data, descrição, conta e cardinalidade única para confirmar pares automaticamente.
- Candidatos e divergências de valor ficam separados para confirmação, rejeição ou ajuste manual com justificativa.
- Decisões ficam em `django_revisoes_conciliacao`, com empresa, competência, lotes, linhas, usuário e data.
- O resumo em `conciliacoes` é substituído por competência em uma transação, evitando duplicação ao reexecutar.
- A migração preparada habilita RLS e remove acesso dos papéis `anon` e `authenticated` quando for aplicada no PostgreSQL da Etapa 13.

## Verificações

- 53 testes Django aprovados.
- 31 testes legados aprovados.
- Testes específicos cobrem par exato, revisão humana e substituição idempotente do resumo.
- `makemigrations --check`, verificação Django e compilação Tailwind aprovados.
- Nenhuma migração, DDL ou escrita foi executada no Supabase de produção.

## Limite conhecido

O detalhamento das revisões será persistido após o corte de banco da Etapa 13. Até a aplicação da migração em produção, a tela exige que as tabelas preparadas já existam no ambiente usado pela aplicação.
