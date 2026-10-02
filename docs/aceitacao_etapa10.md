# Aceitação da Etapa 10 — Entregas e relatórios

## Entregue

- A rota autenticada `/entregas/` usa exclusivamente empresa e competência do contexto validado na sessão.
- O balancete calcula saldo anterior, débitos, créditos e saldo final por conta. O saldo é assinado de forma explícita: débito positivo e crédito negativo, pois a natureza de cada conta pertence ao plano da empresa.
- A DRE usa regras de prefixo confirmadas pela contadora, prioriza o prefixo mais específico e mantém contas não classificadas visíveis.
- A tela permite salvar perfis de exportação por empresa e classificar contas da DRE por grupo, categoria e ordem.
- As exportações em Excel e PDF removem colunas técnicas. O PDF usa A4 horizontal e repete o cabeçalho da tabela em novas páginas.
- Cada arquivo gerado registra empresa, competência, tipo, formato, parâmetros, versão de cálculo, usuária e data em `django_geracoes_relatorios`.
- A migração `0007_entregas_relatorios.py` cria as tabelas de classificação, perfis e histórico de geração. No PostgreSQL, ela ativa RLS e revoga acesso dos papéis `anon` e `authenticated`.

## Verificações

- 60 testes Django aprovados em SQLite isolado, incluindo saldo anterior, classificação da DRE, contas sem classificação, PDF, Excel, perfil e registro de geração.
- 31 testes legados aprovados.
- `makemigrations --check`, `manage.py check`, compilação Python, carregamento do template de Entregas e compilação Tailwind aprovados.
- Nenhuma migração, DDL ou escrita foi executada no Supabase de produção.

## Limite conhecido

O plano de classificação da DRE começa vazio para cada empresa. Enquanto a contadora não confirmar os prefixos, as contas são mantidas no grupo “Não classificado” e não entram silenciosamente em receitas, custos ou despesas.
