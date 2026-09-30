# ContaView — estado de continuidade

Este arquivo é o ponto de retomada do projeto. Atualize-o ao encerrar qualquer etapa de `etapas.md`.

## Estado atual

**Etapa concluída:** Etapa 2 — esqueleto Django e execução pelo navegador.

**Situação da aplicação nova:** o esqueleto Django abre no navegador, possui layout responsivo, dark mode, rotas diretas, páginas de erro, diagnóstico e arquivos estáticos locais. Os módulos operacionais ainda são páginas de espera até suas etapas específicas.

**Situação do código legado:** a aplicação Reflex continua publicada como referência temporária e permanece congelada.

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

**Etapa 3 — Autenticação e contexto de trabalho.**

### Evidências da Etapa 1 concluída

- Inventário somente leitura do PostgreSQL em `docs/inventario_etapa1.md`.
- Catálogo dos módulos reutilizáveis em `docs/catalogo_logic_etapa1.md`.
- Base de aceitação e resultados CAP em `docs/aceitacao_etapa1.md`.
- Dump nativo local `temp/etapa1/backup_public.dump`, SHA-256 `1690190f89517154ea032757cde2f170344d465218d09871ca7770299fd96b0c`.
- Restauração e comparação aprovadas em `docs/verificacao_backup_etapa1.md`.
- Três fixtures anonimizadas e versionadas em `tests/fixtures/aceitacao/`.
- Três testes de aceitação executados com sucesso usando `unittest`.
- Dark mode disponível no mockup em `mockups/interface_nova.html`.

### Evidências da Etapa 2 concluída

- Aplicação Django criada em `web/`, sem remover o Reflex legado.
- Configurações separadas para desenvolvimento, produção, testes e coleta de estáticos.
- Tailwind 4.3.0 compilado e HTMX 2.0.11 servido localmente.
- Layout responsivo com sidebar, cabeçalho, conteúdo, mensagens, dark mode e páginas de erro.
- `/saude/aplicacao/` e `/saude/` testados; o segundo diferencia banco disponível de indisponível.
- Logs JSON correlacionados por `X-Request-ID`.
- Dockerfile com Gunicorn e WhiteNoise criado; construção local pendente porque este computador não possui Docker.
- 10 testes Django e 30 testes legados aprovados.
- Teste HTTP aprovou página inicial, rota interna, erro 404, CSS, HTMX, JavaScript e conexão PostgreSQL.
- Evidência detalhada em `docs/aceitacao_etapa2.md`.
- Nenhuma migração, DDL ou escrita foi feita no banco de produção.

### Ações da próxima etapa

1. Criar usuário administrativo inicial por comando seguro.
2. Implementar login, logout e expiração de sessão.
3. Aplicar proteção CSRF e cookies seguros ao fluxo autenticado.
4. Criar limitação de tentativas de login.
5. Implementar seleção persistente de empresa e competência.
6. Garantir que toda consulta receba o contexto selecionado no servidor.

### Condição para iniciar

A Etapa 3 aguarda autorização do usuário, conforme a regra de aprovação entre etapas.

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
| 2 | Concluída | Django, interface, diagnósticos, logs, ativos e contêiner documentados |
| 3 | Próxima | Aguarda autorização para iniciar |
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
