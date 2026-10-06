# ContaView — estado de continuidade

Este arquivo é o ponto de retomada do projeto. Atualize-o ao encerrar qualquer etapa de `etapas.md`.

## Estado atual

**Etapa concluída:** Etapa 12 — Assistente com consultas agregadas e rastreáveis.

**Etapa em andamento:** Etapa 13 — produção e corte.

**Situação da aplicação nova:** todas as etapas de produto foram concluídas e validadas localmente: acesso, contexto, Trabalho, Entradas, Conferência, Conciliação, Auditoria, Entregas, Automações e Assistente. O corte do Django está em execução na Railway e ainda exige validação pública e aceite do ciclo CAP.

**Situação do código legado:** a aplicação Reflex continua publicada como referência temporária e permanece congelada.

**Último deploy conhecido do legado:** aplicação Reflex em execução, mas com falhas de conexão de estado no navegador e acesso direto a rotas internas incompleto.

**Banco:** PostgreSQL do Supabase continua sendo a base de produção. Não trocar por SQLite.

**Dados:** antes do corte foi criado um dump nativo do schema `public` em `temp/corte/` e validado por `pg_restore`. O arquivo temporário não é versionado. As nove migrações Django do núcleo foram aplicadas e as 14 tabelas novas protegidas por RLS foram confirmadas por consulta somente leitura.

**Produção:** o projeto Railway `ContaView`, serviço `contaview-web` e domínio HTTPS `https://contaview-web-production.up.railway.app` foram criados. As variáveis de produção foram configuradas sem expor valores. A conexão direta IPv6 não era roteável pela Railway e foi substituída pelo pool de sessão IPv4 do Supabase. O deploy `b4586a13-1c63-4264-803f-3f587e022c80` está `SUCCESS`; saúde, banco, login, rota protegida e logout foram validados no domínio público.

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

**Etapa 13 — Produção e corte.**

### Pendências para encerrar a Etapa 13

1. Configurar no GitHub o segredo `RAILWAY_TOKEN` e a variável `RAILWAY_DEPLOY_ENABLED=true`; validar o workflow de testes e deploy automático.
2. Executar, com aceite humano, o ciclo CAP completo: entrada, conferência, aprovação, conciliação, auditoria, relatório e exportação.
3. Manter o Reflex como fallback até o aceite do ciclo real. A desativação do legado só ocorre depois desse aceite.

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

### Evidências da Etapa 5 concluída

- Upload múltiplo de XLSX, XLS e CSV implementado em `/entradas/`.
- Validação de 20 MB, 30.000 linhas por aba, assinatura do conteúdo e expansão de XLSX.
- Hash SHA-256 consultado antes da criação do lote e também protegido no fluxo final.
- Seleção de aba, cabeçalho e tipo com prévia das linhas originais.
- Mapeamento manual e sugestão local; IA disponível somente quando data e valor não forem encontrados.
- Modelos de mapeamento confirmados persistidos por empresa, estrutura e tipo.
- A CAP anonimizada gera 42 linhas e preserva todas as colunas em `dados_brutos`.
- Migração das tabelas temporárias e de modelos preparada com constraints, índices, RLS e revogação de `anon` e `authenticated`.
- 46 testes Django e 30 testes legados aprovados.
- Consulta somente leitura confirmou as tabelas de preparação existentes e RLS ativa no PostgreSQL real.
- Evidência detalhada em `docs/aceitacao_etapa5.md`.
- Nenhuma migração, DDL ou escrita foi feita no banco de produção.

### Ações da próxima etapa

1. Exibir linhas prontas, pendentes e ignoradas do lote.
2. Permitir correção de data, valor, tipo, conta e filial.
3. Implementar edição em lote e colagem controlada.
4. Mostrar totais de débito e crédito.
5. Exigir a resolução de pendências antes da aprovação.
6. Validar empresa e competência dentro da transação.
7. Exigir confirmação explícita para substituir uma competência existente.
8. Gravar `sequencial_lote`, histórico e estado final de forma atômica.
9. Permitir reabrir ou cancelar uma preparação ainda não aprovada.

### Condição para iniciar

A Etapa 6 ainda não foi autorizada. Não iniciá-la antes da autorização do usuário.

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
| 5 | Concluída | Upload, inspeção, prévia, mapeamento, hash e 46 testes Django aprovados |
| 6 | Concluída | Conferência, correção e aprovação atômica do lote validadas localmente |
| 7 | Concluída | Assistente controlado com conversa, saneamento e limites de contexto |
| 8 | Concluída | Conciliação determinística e revisões humanas validadas localmente |
| 9 | Concluída | Auditoria operacional, trilha e resolução de ocorrências validadas localmente |
| 10 | Concluída | Entregas, relatórios, perfis e registro de geração validados localmente |
| 11 | Concluída | Automações recorrentes, lembretes, perfis de origem e fila local validados |
| 12 | Concluída | Assistente com agregados, fontes e rastreabilidade local validados |
| 13 | Em andamento | Backup, Railway, variáveis e deploy inicial concluídos; validação pública pendente |

## Atualização da Etapa 6

Etapa 6 concluída. A tela de Conferência agora carrega o lote da empresa e competência selecionadas, permite editar linhas individualmente ou em lote, apresenta totais, bloqueia aprovação com pendências, solicita confirmação para substituir competência existente e permite cancelar ou reabrir preparação. Foram aprovados 48 testes Django, 30 testes legados, verificação de sintaxe e compilação Tailwind. A próxima etapa é a Etapa 7, Assistente controlado, aguardando autorização.

## Atualização da Etapa 7

Etapa 7 concluída. O Assistente agora possui conversas persistidas, exclusão limitada à sessão autenticada, histórico controlado, bloqueio de consultas fora da empresa e competência atuais, remoção de identificadores e registros nominais antes do envio à IA e tratamento de indisponibilidade. Foram adicionados 2 testes específicos. A próxima etapa é a Etapa 8, Conciliação, aguardando autorização.

## Atualização da Etapa 8

Etapa 8 concluída. A Conciliação compara um extrato aos lançamentos aprovados ou a outro lote da empresa e competência atuais com regras determinísticas, mostra pares exatos, candidatos, divergências e linhas sem correspondência, e registra decisões humanas com justificativa. O resumo da competência é substituído ao reexecutar, sem duplicação. A migração `0005_revisoes_conciliacao.py` está pronta, com RLS e revogação de acesso público, mas não foi aplicada em produção. Foram aprovados 53 testes Django e 31 testes legados. A próxima etapa é a Etapa 9, Auditoria operacional, aguardando autorização.

## Atualização da Etapa 9

Etapa 9 concluída. A Auditoria executa regras determinísticas, preserva vínculos aos lançamentos novos, mostra registros antigos sem vínculo para revisão humana, permite resolver ou reabrir com usuário, data e justificativa, exibe a trilha de alterações e exporta exceções sem colunas técnicas. A migração `0006_auditoria_operacional.py` prepara triggers, RLS e estados de resolução, mas não foi aplicada em produção. Foram aprovados 55 testes Django e 31 testes legados. A próxima etapa é a Etapa 10, Entregas e relatórios, aguardando autorização.

## Atualização da Etapa 10

Etapa 10 concluída em ambiente local. A rota `/entregas/` gera balancete com saldo anterior, débitos, créditos e saldo final, DRE baseada em classificações de prefixo confirmadas pela contadora e exportações de lançamentos por perfil genérico ou personalizado. PDF e Excel excluem colunas técnicas; cada geração preserva empresa, competência, parâmetros, versão de cálculo, usuária e horário. A migração `0007_entregas_relatorios.py` cria as tabelas locais, ativa RLS no PostgreSQL e revoga acesso dos papéis públicos, mas não foi aplicada em produção. Os resultados finais dos testes e verificações desta etapa ficam registrados em `docs/aceitacao_etapa10.md`. A próxima etapa é a Etapa 11, Automações recorrentes, aguardando autorização.

## Atualização da Etapa 11

Etapa 11 concluída em ambiente local. A rota `/automacoes/` configura documentos esperados, prazos e perfis de origem por empresa; a abertura de uma competência copia os documentos ativos para o checklist sem duplicar itens. Os lembretes internos e a fila de processamento exibem pendências, estado e tentativas. Cada arquivo aceito cria uma tarefa concluída de inspeção; uma falha pode ser reexecutada no mesmo contexto, até três vezes. Pastas e e-mail externos permanecem intencionalmente desconectados até que existam credenciais, permissões e autorização específica. A migração `0008_automacoes_recorrentes.py` prepara tabelas, RLS e bloqueio de papéis públicos, mas não foi aplicada em produção. Os resultados finais das verificações desta etapa ficam em `docs/aceitacao_etapa11.md`. A próxima etapa é a Etapa 12, Assistente, aguardando autorização.

## Atualização da Etapa 12

Etapa 12 concluída em ambiente local. O Assistente passou a receber somente um resumo agregado, calculado no servidor, de lançamentos aprovados, conciliação, auditoria, checklist e automações da empresa e competência validadas. Nenhuma ferramenta de banco é exposta ao modelo. A tela mostra as fontes que sustentam cada resposta; pergunta saneada, filtros, resposta e fontes ficam registrados em `django_registros_consultas_assistente`. CPFs, CNPJs, e-mails e referências nominais de terceiros são ocultados antes de persistir ou enviar conteúdo à IA. Perguntas de valor sem dados retornam ausência de informação sem chamar o modelo ou estimar números. A migração `0009_registros_consultas_assistente.py` prepara tabela, constraints, índice, RLS e revogação de papéis públicos, mas não foi aplicada em produção. Foram aprovados 70 testes Django e 31 testes legados; a evidência detalhada está em `docs/aceitacao_etapa12.md`. A próxima etapa é a Etapa 13, Corte e implantação, aguardando autorização.

## Atualização da Etapa 13

Etapa 13 iniciada em 03/10/2026. Foi criado o projeto Railway `ContaView`, com o serviço `contaview-web` e domínio HTTPS público. O serviço usa Dockerfile, Gunicorn e variáveis Django configuradas sem registrar segredos no repositório ou terminal. Foi produzido um dump nativo do schema `public` antes do corte e ele foi validado por `pg_restore`.

A Railway não alcançava a conexão direta IPv6 do Supabase. A variável `DATABASE_URL` do serviço foi alterada para o pool de sessão IPv4 e validada por consulta de leitura. As migrações foram aplicadas uma única vez depois do backup; a verificação `scripts/verificar_corte_producao.py` confirmou as 9 migrações do núcleo e 14 tabelas com RLS. A conta administrativa inicial foi criada sem expor credenciais. O deploy `b4586a13-1c63-4264-803f-3f587e022c80` terminou com `SUCCESS`. Os smoke tests públicos confirmaram `/saude/` com banco disponível, formulário de acesso, login, rota protegida, redirecionamento de contexto, logout e bloqueio pós-saída. Os logs Railway registraram os IDs de requisição, por exemplo `d0150bf2-aa98-42cd-ac4c-b041ebea570d` para o login e `6291313f-b293-41ac-b1b5-c16b5ac11574` para a saída bem-sucedida.

O arquivo `railway.json`, o workflow `.github/workflows/validar_e_implantar.yml`, o procedimento `docs/corte_producao.md` e os scripts de backup, configuração e smoke test foram preparados, commitados e enviados ao GitHub no commit `47c3eae`. O workflow aplica migrações de forma explícita antes do deploy e aponta para o projeto e serviço Railway corretos. Ainda falta cadastrar a credencial de deploy no GitHub, executar o ciclo CAP completo com aceite humano e somente depois decidir a retirada do Reflex como fallback.

### Correção do Assistente em produção

Em 06/10/2026 a abertura de `/assistente/` falhava no contêiner, embora `/saude/` confirmasse o banco pelo Django. Os logs identificaram que a camada legada de SQLAlchemy tentava carregar o driver padrão ausente no ambiente publicado. A conexão foi padronizada explicitamente em `psycopg` 3, declarado em `requirements.txt`; para o pool do Supabase, cada worker usa `NullPool`, evitando a criação de um segundo pool de conexões ociosas.

A view do Assistente também passou a tratar falhas transitórias da camada legada sem retornar HTTP 500. O teste `web/nucleo/tests_resiliencia_assistente.py` valida essa resposta controlada. O script `scripts/smoke_assistente_publico.py` executa login temporário, seleciona contexto, envia uma pergunta genérica sem dados contábeis e remove a conversa ao final.

Evidências: 31 testes Django e 31 testes legados aprovados; conexão legada local com `psycopg` aprovada; deploy Railway `e75a909f-738a-4401-86d8-23c20f65c743` com status `SUCCESS`; smoke público do Assistente aprovado e `/saude/` confirmou aplicação e banco disponíveis. As alterações estão nos commits `31b0e27` e `95f3c22`.

### Refinamento visual durante a Etapa 13

Em 06/10/2026, as telas operacionais receberam ajustes de hierarquia e leitura sem alterar regras contábeis, dados ou migrações. O Assistente passou a exibir o campo de pergunta logo após o aviso de privacidade, com rótulo, foco visível e altura adequada. A tela de Entregas ganhou grades responsivas que preservam os campos e os botões de salvamento, contraste maior nas ações e textos auxiliares mais legíveis.

Na Auditoria, as ações agora têm estilos primário e secundário consistentes; os indicadores são cards de prioridade; ocorrências são delimitadas; severidade e tipos são apresentados em linguagem natural, incluindo `VALOR_ANOMALO` como “Valor anômalo”; o campo de justificativa ganhou rótulo e foco; os plurais são tratados corretamente; e o histórico vazio deixou de mostrar mensagem de migração. Os códigos internos continuam preservados para regras e exportação. A Conciliação passou a separar a escolha de fontes da ação principal, exibir uma área inicial que explica onde os resultados aparecerão e organizar os indicadores após a execução. Os `selects` recebem estilo consistente no estado fechado; a lista aberta continua nativa por acessibilidade e compatibilidade entre navegadores. Na tela de Conciliação, o contexto repetido no cabeçalho fica oculto apenas em desktop, pois já está acessível na barra lateral; em tela móvel ele permanece visível.

Evidências: `manage.py test --settings=configuracao.settings.teste` com 31 testes aprovados; `unittest discover -s tests -p "test_*.py"` com 31 testes aprovados; `manage.py check` sem problemas; Tailwind recompilado; e `git diff --check` aprovado. Ainda falta publicar este conjunto de refinamentos, executar o smoke público após o deploy, cadastrar a credencial de deploy no GitHub, executar o ciclo CAP completo com aceite humano e decidir sobre a retirada do Reflex como fallback.
