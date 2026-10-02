# Aceitação da Etapa 11 — Automações recorrentes

## Entregue

- A rota autenticada `/automacoes/` usa exclusivamente empresa e competência do contexto validado na sessão.
- Documentos esperados são configurados por empresa com tipo, prazo e obrigatoriedade. Eles são copiados para o checklist quando uma competência é iniciada, sem duplicar itens existentes.
- Lembretes internos mostram os documentos ainda pendentes e destacam os prazos vencidos.
- Perfis de origem associam prefixos de nomes de arquivo a uma empresa e sugerem a origem durante o recebimento. Eles não escolhem empresa, competência, destino ou aprovação.
- Cada arquivo aceito para mapeamento ganha uma tarefa persistida de processamento. O hash existente continua bloqueando reenvio do mesmo conteúdo.
- A fila mantém estado, tentativas, horário e mensagem de falha. Tarefas em falha podem ser reexecutadas até três vezes, somente no mesmo contexto.
- A migração `0008_automacoes_recorrentes.py` cria as tabelas de modelos, perfis e tarefas, ativa RLS no PostgreSQL e revoga acesso dos papéis `anon` e `authenticated`.

## Verificações

- 65 testes Django aprovados em SQLite isolado, incluindo checklist automático, perfil de origem, registro de processamento, reexecução de falha, isolamento entre empresas e a tela de automações.
- 31 testes legados aprovados.
- `makemigrations --check`, `manage.py check`, compilação Python, carregamento do template de Automações e compilação Tailwind aprovados.
- Nenhuma migração, DDL ou escrita foi executada no Supabase de produção.

## Limite conhecido

Nenhuma pasta compartilhada ou caixa de e-mail é acessada nesta versão. Esses perfis servem de referência para o recebimento manual pelo navegador e não armazenam credenciais externas.
