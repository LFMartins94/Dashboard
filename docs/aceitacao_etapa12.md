# Aceitação da Etapa 12 — Assistente

## Escopo concluído

- A rota `/assistente/` preserva conversas na sessão autenticada e mantém o histórico após atualização do navegador.
- Cada pergunta usa somente o contexto de empresa e competência validado no servidor.
- O serviço calcula agregados de lançamentos, conciliação, auditoria, checklist e automações; históricos, identificadores, CNPJ, CPF, e-mails e nomes de terceiros não entram no contexto enviado ao modelo.
- A tela mostra as fontes e os números que sustentam cada resposta persistida.
- A tabela `django_registros_consultas_assistente` registra usuária, pergunta saneada, filtros, resposta e fontes.
- Perguntas sobre valores sem lançamentos, conciliações ou ocorrências retornam ausência de dados sem chamar o modelo nem estimar totais.
- O modelo não recebe ferramentas nem acesso ao banco e não altera lançamentos, lotes, conciliações ou ocorrências.

## Segurança e migração

- A migração `0009_registros_consultas_assistente.py` cria a trilha de consulta, índice de contexto, constraints, RLS e revogação de acesso de `anon` e `authenticated`.
- A migração foi executada somente no banco SQLite isolado dos testes. Nenhuma escrita, DDL ou migração foi feita no PostgreSQL de produção.

## Verificações locais

- 70 testes Django aprovados, incluindo sete testes específicos do Assistente.
- 31 testes legados aprovados.
- `makemigrations --check --dry-run`, `manage.py check`, compilação Python, carregamento do template, `git diff --check` e compilação do Tailwind aprovados.
