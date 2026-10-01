# ContaView — estado de continuidade

Este arquivo é o ponto de retomada do projeto. Atualize-o ao encerrar qualquer etapa de `etapas.md`.

## Estado atual

**Etapa concluída:** Etapa 4 — tela Trabalho e fila operacional.

**Etapa em andamento:** nenhuma. A Etapa 5 aguarda autorização do usuário.

**Situação da aplicação nova:** o Django possui login protegido, contexto persistente e uma tela Trabalho funcional. A fila reúne checklist, documentos aguardados, lotes pendentes, divergências, entregas, próxima ação e competências abertas. Entradas, Conferência, Entregas e Assistente ainda são páginas de espera até suas etapas específicas.

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

**Etapa 5 — Entrada genérica de arquivos.**

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

### Evidências da Etapa 3 concluída

- Login e logout implementados com autenticação e sessão nativas do Django.
- Rotas operacionais protegidas por padrão; login e diagnósticos são exceções explícitas.
- Cookies, expiração de sessão, CSRF e destinos de redirecionamento protegidos.
- Limite de tentativas persistente com chave HMAC, sem endereço ou usuário brutos no banco.
- Comando `criar_usuario_inicial` recebe a senha por prompt seguro ou variável temporária.
- Empresa ativa e competência são validadas no servidor e armazenadas na sessão.
- Duas sessões simultâneas mantêm contextos independentes.
- Migrações para autenticação, sessão, limitador e proteção RLS foram preparadas, mas não aplicadas em produção.
- 24 testes Django aprovados no banco SQLite isolado.
- Evidência detalhada em `docs/aceitacao_etapa3.md`.
- Nenhuma migração, DDL, criação de usuário ou escrita foi feita no banco de produção.

### Evidências da Etapa 4 concluída

- Tela Trabalho reconstruída como fila operacional da empresa e competência selecionadas.
- Início explícito e idempotente de competência por `POST` com CSRF.
- Checklist recorrente para documentos, conferência, divergências e entrega.
- Seis estados persistidos: aguardando, recebido, em conferência, com divergência, revisado e entregue.
- Próxima ação definida por regras determinísticas.
- Métricas alimentadas por lotes, linhas preparadas, conciliações, ocorrências e checklist.
- Alertas apontam para a área e o identificador do registro responsável.
- Alternância rápida entre competências abertas com revalidação no servidor.
- Constraints, índices e proteção RLS preparados para as duas tabelas novas.
- 35 testes Django, 30 testes legados e consulta somente leitura no PostgreSQL real aprovados.
- Evidência detalhada em `docs/aceitacao_etapa4.md`.
- Nenhuma migração, DDL ou escrita foi feita no banco de produção.

### Ações da próxima etapa

1. Implementar upload de XLSX, XLS e CSV.
2. Ler abas, detectar cabeçalho e apresentar prévia.
3. Mapear data, valor, descrição, tipo, conta e filial.
4. Preservar colunas originais não mapeadas.
5. Validar tamanho, extensão, quantidade de linhas e formatos brasileiros.
6. Detectar reenvio pelo hash antes de criar lote.
7. Aplicar sugestão local e usar IA somente quando as regras não forem suficientes.
8. Salvar modelos de mapeamento confirmados.

### Condição para iniciar

A Etapa 5 ainda não foi autorizada. Não iniciá-la antes da autorização do usuário.

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
| 3 | Concluída | Login, sessão, CSRF, limitação de tentativas e contexto validados em 24 testes isolados |
| 4 | Concluída | Fila operacional, checklist recorrente, próxima ação e 35 testes Django aprovados |
| 5 | Aguardando autorização | Entrada genérica de XLSX, XLS e CSV |
| 6 | Pendente | Depende da Etapa 5 |
| 7 | Pendente | Depende da Etapa 6 |
| 8 | Pendente | Depende da Etapa 7 |
| 9 | Pendente | Depende da Etapa 8 |
| 10 | Pendente | Depende da Etapa 9 |
| 11 | Pendente | Depende da Etapa 10 |
| 12 | Pendente | Depende da Etapa 11 |
| 13 | Pendente | Depende da Etapa 12 |
