# ContaView

Ferramenta web para reduzir o trabalho manual de uma contadora que administra várias empresas. A contadora acessa tudo pelo navegador; não há aplicativo para instalar no computador.

O ContaView recebe arquivos contábeis de origens diferentes, preserva os dados originais, prepara lançamentos, apresenta exceções para revisão humana, executa conciliação determinística e gera arquivos e relatórios para o sistema contábil utilizado pela empresa.

O projeto não substitui o sistema contábil oficial. Ele funciona como uma camada de preparação, conferência, automação e entrega, independente de Domínio, Alterdata ou qualquer outro fornecedor.

## Direção arquitetural

O Reflex continua disponível apenas como legado durante a transição. A aplicação principal será reconstruída como uma aplicação web HTTP tradicional:

- Backend: Django 5.2 LTS.
- Interface: Django Templates, HTML semântico, Tailwind CSS e HTMX.
- JavaScript: módulos pequenos para upload, seleção em lote, atalhos e interações locais.
- Banco: PostgreSQL gerenciado pelo Supabase.
- Arquivos: armazenamento privado, preferencialmente Supabase Storage.
- Relatórios: ReportLab e XlsxWriter.
- Processamento: Python, Pandas e os parsers já existentes.
- IA: OpenAI apenas para sugestão de mapeamento e Assistente de consulta.
- Hospedagem: contêiner Linux com processo persistente e deploy automático pelo GitHub.

O navegador nunca acessa diretamente o banco. O servidor autentica a contadora, executa as regras e retorna páginas completas ou fragmentos HTML.

## Fluxo de trabalho

1. **Trabalho:** mostra empresas, competências, arquivos pendentes, divergências e entregas próximas.
2. **Entradas:** recebe um ou vários arquivos pelo navegador, identifica abas e cabeçalhos e reutiliza mapeamentos confirmados.
3. **Conferência:** exibe linhas preparadas, erros, duplicidades, lançamentos e exceções de conciliação em uma única área operacional.
4. **Aprovação:** grava o lote final em uma transação, com validação de empresa, competência e duplicidade.
5. **Entregas:** gera arquivos de saída, balancete, DRE e relatórios de divergência.
6. **Assistente:** responde perguntas usando consultas controladas e dados agregados, sem receber dados brutos sensíveis.

Auditoria é uma camada transversal. Triggers e serviços registram alterações; o histórico aparece junto do lote ou lançamento correspondente.

### Tela Trabalho

A tela inicial da nova aplicação funciona como fila operacional da empresa e competência selecionadas. Ela apresenta:

- arquivos recebidos e lotes que ainda precisam de revisão;
- documentos aguardados;
- divergências abertas;
- entregas prontas e concluídas;
- a próxima ação recomendada por regras determinísticas;
- checklist recorrente com os estados aguardando, recebido, em conferência, com divergência, revisado e entregue;
- alternância rápida entre competências abertas.

O início de uma competência e cada mudança de estado usam requisições `POST` com CSRF. A página não cria registros durante um simples carregamento. As consultas de lotes, linhas, conciliações e ocorrências sempre recebem a empresa e a competência validadas da sessão.

## Importação de planilhas

O importador não é específico da planilha CAP. A primeira versão aceita:

- XLSX, incluindo múltiplas abas.
- XLS binário e XML Spreadsheet legado quando o leitor conseguir processá-los.
- CSV com separadores `;`, `,`, tabulação ou `|`.
- Arquivos de até 20 MB e 30.000 linhas por aba na configuração inicial.

O sistema identifica possíveis campos como data, valor, descrição, tipo, conta contábil e filial. Nomes diferentes podem representar o mesmo campo. O sistema sugere o mapeamento, mostra uma prévia e exige confirmação antes da gravação.

Quando a estrutura é nova ou ambígua, a contadora corrige o mapeamento manualmente. O modelo aprovado fica salvo para reutilização futura. Arquivos protegidos por senha, PDFs, imagens, OFX e XML contábil exigem leitores próprios e entram em etapas posteriores.

A IA pode sugerir a relação entre nomes de colunas. Ela nunca escolhe sozinha a empresa, o tipo de documento, a competência ou o destino dos dados.

### Entrada genérica implementada

A rota `/entradas/` da nova aplicação já executa o fluxo de recebimento e preparação:

- recebe vários arquivos pelo mesmo formulário;
- valida nome, extensão, assinatura do conteúdo, tamanho e quantidade de linhas;
- limita a expansão interna de XLSX para evitar arquivos compactados abusivos;
- calcula SHA-256 e recusa reenvio da mesma empresa antes de criar outro lote;
- permite escolher aba, linha do cabeçalho e tipo de documento;
- exibe doze linhas de prévia sem gravar lançamentos;
- sugere data, valor, descrição, tipo, conta e filial com regras locais;
- oferece sugestão por IA somente quando data e valor não foram identificados localmente, enviando apenas os nomes das colunas;
- preserva todas as colunas originais em `dados_brutos`;
- salva o mapeamento confirmado para estruturas futuras;
- grava o arquivo final em `lotes_importacao` e as linhas em `linhas_preparadas`.

O arquivo fica em armazenamento temporário privado durante o mapeamento. Depois da confirmação, a cópia temporária é apagada porque o original já está preservado no lote. A correção e a aprovação dessas linhas são feitas na tela de Conferência. A evidência está em `docs/aceitacao_etapa6.md`.

O Assistente está disponível em `/assistente/` para consultas controladas. Ele respeita a empresa e competência selecionadas, remove identificadores antes da chamada à IA e não executa alterações contábeis. A evidência está em `docs/aceitacao_etapa7.md`.

A Conciliação está disponível em `/conciliacao/`: ela compara um extrato com uma referência do mesmo contexto, confirma apenas pares inequívocos e mantém candidatos e divergências para decisão humana. A evidência está em `docs/aceitacao_etapa8.md`.

A Auditoria está disponível em `/auditoria/`, com regras reproduzíveis, resolução atribuída à usuária, exportação de exceções e histórico de alterações. A evidência está em `docs/aceitacao_etapa9.md`.

## Automação por nível de risco

### Automático

- Hash e detecção de arquivos repetidos.
- Normalização de datas e valores.
- Validação de campos obrigatórios.
- Identificação de linhas vazias ou inválidas.
- Reutilização de mapeamentos aprovados.
- Cálculo de totais.
- Detecção de duplicidades.
- Criação de checklist mensal.
- Geração de arquivos de saída.

### Sugestão para confirmação

- Cabeçalho e aba.
- Mapeamento de colunas.
- Empresa e competência.
- Conta contábil.
- Correspondências de conciliação.
- Classificação para relatório.

### Sempre manual

- Aprovação do lote.
- Substituição de uma competência.
- Resolução de pares ambíguos.
- Alteração de lançamento aprovado.
- Fechamento e entrega da competência.

## Dados e segurança

As tabelas existentes são preservadas. A preparação utiliza `lotes_importacao`, `linhas_preparadas` e `historico_alteracoes`. O arquivo original e os dados brutos permanecem vinculados ao lote.

O PostgreSQL continua sendo usado em produção porque oferece transações, concorrência, triggers, constraints, backup gerenciado e RLS. SQLite pode ser usado em testes locais isolados, mas não será a base de produção: o arquivo seria dependente de armazenamento persistente e exigiria uma estratégia própria de backup e recuperação.

O servidor usa `DATABASE_URL`. A chave anon do Supabase não é necessária no navegador. Nenhum segredo fica no código-fonte.

## Execução local

### Nova aplicação Django

No PowerShell, a partir da raiz do repositório:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
npm run build
Copy-Item .env.example .env
# Preencha DATABASE_URL e DJANGO_SECRET_KEY no .env.
.venv\Scripts\python.exe web\manage.py check
.venv\Scripts\python.exe web\manage.py runserver
```

A interface fica disponível em `http://127.0.0.1:8000/`. O diagnóstico completo fica em `/saude/`; `/saude/aplicacao/` verifica somente o processo web. O primeiro retorna HTTP 503 com `banco: indisponivel` quando a aplicação está ativa, mas não consegue consultar o PostgreSQL.

Para acompanhar alterações visuais durante o desenvolvimento, execute `npm run dev:css` em outro terminal. HTMX e o CSS compilado são servidos localmente, sem dependência de CDN no navegador.

Os testes da aplicação Django usam SQLite em memória, isolado do banco de produção:

```powershell
$env:DJANGO_SETTINGS_MODULE="configuracao.settings.teste"
.venv\Scripts\python.exe web\manage.py test nucleo
```

### Autenticação da nova aplicação

As rotas de trabalho exigem uma sessão Django válida e um contexto de empresa e competência selecionado no servidor. A rota `/acesso/` e os diagnósticos são as únicas páginas públicas. O logout aceita somente `POST` e encerra a sessão completa.

Depois que as migrações forem executadas no ambiente de destino, crie o primeiro usuário pelo prompt seguro:

```powershell
.venv\Scripts\python.exe web\manage.py criar_usuario_inicial --usuario contadora --nome "Nome da contadora"
```

A senha é solicitada sem aparecer no comando nem no histórico do terminal. Em automação, use `DJANGO_ADMIN_PASSWORD` apenas como variável temporária e remova-a ao terminar.

As migrações Django ainda não devem ser executadas no PostgreSQL de produção. Elas serão aplicadas na Etapa 13, depois de novo backup e da confirmação do ambiente de corte. Até lá, o fluxo completo de autenticação é verificado pela suíte isolada:

```powershell
$env:DJANGO_SETTINGS_MODULE="configuracao.settings.teste"
.venv\Scripts\python.exe web\manage.py test nucleo
Remove-Item Env:DJANGO_SETTINGS_MODULE
```

### Contêiner

```powershell
docker build -t contaview .
docker run --rm -p 8000:8000 --env-file .env contaview
```

O contêiner executa Gunicorn. As configurações de produção exigem `DATABASE_URL`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS`.

### Aplicação Reflex legada

O projeto Reflex ainda pode ser executado para manutenção:

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\reflex.exe compile --dry
```

A nova implementação fica em `web/`. O legado permanece congelado durante a transição e nenhuma tabela foi migrada na Etapa 2.

## Documentos de continuidade

- [`etapas.md`](etapas.md): plano completo da migração e construção, etapa por etapa.
- [`faltando.md`](faltando.md): estado atual, próxima etapa autorizável e pendências concretas.
- [`AGENTS.md`](AGENTS.md): regras para agentes e limites da transição.
- [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md): tokens e regras visuais que serão reaproveitados na interface HTML.
- [`docs/PROMPTS_ETAPAS.md`](docs/PROMPTS_ETAPAS.md): documento histórico do Reflex; não é o plano vigente.
- [`docs/inventario_etapa1.md`](docs/inventario_etapa1.md): fotografia somente leitura do banco para a Etapa 1.
- [`docs/catalogo_logic_etapa1.md`](docs/catalogo_logic_etapa1.md): catálogo dos módulos Python reutilizáveis.
- [`docs/aceitacao_etapa1.md`](docs/aceitacao_etapa1.md): arquivos e critérios do primeiro ciclo de aceite.
- [`docs/verificacao_backup_etapa1.md`](docs/verificacao_backup_etapa1.md): evidência da restauração e comparação do backup.
- [`docs/aceitacao_etapa2.md`](docs/aceitacao_etapa2.md): evidências do esqueleto Django, interface, diagnóstico e testes HTTP.
- [`docs/aceitacao_etapa3.md`](docs/aceitacao_etapa3.md): controles de autenticação, sessão, contexto e evidências de segurança.
- [`docs/aceitacao_etapa4.md`](docs/aceitacao_etapa4.md): fila operacional, checklist recorrente, consultas agregadas e aceite da tela Trabalho.
- [`docs/aceitacao_etapa5.md`](docs/aceitacao_etapa5.md): upload genérico, prévia, mapeamento, hash, modelos reutilizáveis e aceite da preparação.

## Critério de conclusão do primeiro ciclo

A primeira entrega será considerada funcional quando a contadora puder:

1. Entrar pelo navegador.
2. Selecionar uma empresa e competência.
3. Enviar a planilha real.
4. Corrigir somente as pendências necessárias.
5. Aprovar o lote.
6. Atualizar o navegador e encontrar os lançamentos aprovados.
7. Executar a conciliação.
8. Resolver divergências.
9. Gerar uma exportação e um relatório.

Esse ciclo deve funcionar sem abrir o código e sem depender de uma sessão WebSocket persistente para exibir a aplicação.
