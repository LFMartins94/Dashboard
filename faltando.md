# ContaView — estado de continuidade

Este arquivo é o ponto de retomada do projeto. Atualize-o ao encerrar qualquer etapa de `etapas.md`.

## Estado atual

**Etapa concluída:** Etapa 1 — inventário, backup e base de aceitação.

**Situação do código legado:** a aplicação Reflex continua publicada como referência temporária. O fluxo novo ainda não foi implementado.

**Último deploy conhecido do legado:** aplicação Reflex em execução, mas com falhas de conexão de estado no navegador e acesso direto a rotas internas incompleto.

**Banco:** PostgreSQL do Supabase continua sendo a base de produção. Não trocar por SQLite.

**Dados:** o backup nativo foi restaurado e verificado em PostgreSQL local. Nenhuma alteração foi feita nos dados de produção.

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

**Etapa 2 — Esqueleto Django e execução pelo navegador.**

### Evidências da Etapa 1 concluída

- Inventário somente leitura do PostgreSQL em `docs/inventario_etapa1.md`.
- Catálogo dos módulos reutilizáveis em `docs/catalogo_logic_etapa1.md`.
- Base de aceitação e resultados CAP em `docs/aceitacao_etapa1.md`.
- Dump nativo local `temp/etapa1/backup_public.dump`, SHA-256 `1690190f89517154ea032757cde2f170344d465218d09871ca7770299fd96b0c`.
- Restauração e comparação aprovadas em `docs/verificacao_backup_etapa1.md`.
- Três fixtures anonimizadas e versionadas em `tests/fixtures/aceitacao/`.
- Três testes de aceitação executados com sucesso usando `unittest`.
- Dark mode disponível no mockup em `mockups/interface_nova.html`.

### Ações da próxima etapa

1. Criar o projeto Django sem alterar o banco de produção.
2. Separar configurações de desenvolvimento e produção.
3. Configurar variáveis de ambiente, conexão PostgreSQL e health check.
4. Criar templates base, arquivos estáticos, Tailwind e HTMX.
5. Reproduzir o layout aprovado do mockup, incluindo dark mode.
6. Criar Dockerfile e comando documentado de execução local.

### Condição para iniciar

A Etapa 2 aguarda autorização do usuário, conforme a regra de aprovação entre etapas.

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
| 1 | Concluída | Inventário, dump restaurado, comparação aprovada e três fixtures anonimizadas |
| 2 | Próxima | Aguarda autorização para iniciar |
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
