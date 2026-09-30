# ContaView — estado de continuidade

Este arquivo é o ponto de retomada do projeto. Atualize-o ao encerrar qualquer etapa de `etapas.md`.

## Estado atual

**Etapa concluída:** Etapa 0 — decisão e documentação.

**Situação do código legado:** a aplicação Reflex continua publicada como referência temporária. O fluxo novo ainda não foi implementado.

**Último deploy conhecido do legado:** aplicação Reflex em execução, mas com falhas de conexão de estado no navegador e acesso direto a rotas internas incompleto.

**Banco:** PostgreSQL do Supabase continua sendo a base de produção. Não trocar por SQLite.

**Dados:** não executar migração, limpeza ou substituição de dados reais antes do backup e do inventário da Etapa 1.

## O que já está documentado

- Acesso exclusivamente pelo navegador.
- Django + HTML + Tailwind + HTMX como arquitetura alvo.
- Supabase PostgreSQL mantido.
- Reflex congelado como legado durante a transição.
- Fluxos Trabalho, Entradas, Conferência, Entregas e Assistente.
- Importador genérico para XLSX, XLS e CSV.
- Mapeamento confirmado reaproveitável por origem.
- Automação separada entre ações automáticas, sugestões e decisões manuais.
- Critérios de aceite e regra de aprovação entre etapas.

## Artefato visual adicional

- Mockup navegável criado em `mockups/interface_nova.html`.
- O mockup representa a interface alvo para navegador: Trabalho, Entradas, Conferência, Entregas e Assistente.
- A página é somente visual e não está ligada ao banco, à autenticação ou aos fluxos Django/HTMX.
- A paleta usa fundo mineral, grafite e cobre, com foco em tarefas pendentes e no fluxo da competência.

## Próxima etapa

**Etapa 1 — Inventário, backup e base de aceitação.**

### Ações obrigatórias

1. Catalogar tabelas, colunas, índices, triggers e privilégios do Supabase.
2. Criar e verificar um backup antes de qualquer DDL ou limpeza.
3. Catalogar os módulos reutilizáveis de `contaview/logic/`.
4. Separar pelo menos três arquivos reais anonimizados para aceitação.
5. Registrar os resultados esperados da planilha CAP.
6. Definir o teste completo do primeiro ciclo.

### Condição para encerrar a etapa

- Backup restaurado em ambiente de teste.
- Inventário registrado.
- Arquivos de aceitação disponíveis.
- Teste CAP documentado.
- `faltando.md` atualizado com evidências.

## Regra para continuar em outro local

O próximo agente deve ler, nesta ordem:

1. `AGENTS.md`
2. `README.md`
3. `etapas.md`
4. `faltando.md`
5. `docs/DESIGN_SYSTEM.md`

Depois deve executar somente a próxima etapa indicada aqui. Ao concluir, atualizar este arquivo antes de pedir autorização para avançar.

## Registro de etapas

| Etapa | Estado | Evidência |
|---:|---|---|
| 0 | Concluída | Documentação e decisão arquitetural atualizadas |
| 1 | Próxima | Ainda não iniciada |
| 2 | Pendente | Depende da Etapa 1 |
| 3 | Pendente | Depende da Etapa 2 |
| 4 | Pendente | Depende da Etapa 3 |
| 5 | Pendente | Depende da Etapa 4 |
| 6 | Pendente | Depende da Etapa 5 |
| 7 | Pendente | Depende da Etapa 6 |
| 8 | Pendente | Depende da Etapa 7 |
| 9 | Pendente | Depende da Etapa 8 |
| 10 | Pendente | Depende da Etapa 9 |
| 11 | Pendente | Depende da Etapa 10 |
| 12 | Pendente | Depende da Etapa 11 |
| 13 | Pendente | Depende da Etapa 12 |
