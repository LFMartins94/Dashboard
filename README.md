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

## Importação de planilhas

O importador não é específico da planilha CAP. A primeira versão aceita:

- XLSX, incluindo múltiplas abas.
- XLS binário e XML Spreadsheet legado quando o leitor conseguir processá-los.
- CSV com separadores `;`, `,`, tabulação ou `|`.
- Arquivos de até 20 MB e 30.000 linhas por aba na configuração inicial.

O sistema identifica possíveis campos como data, valor, descrição, tipo, conta contábil e filial. Nomes diferentes podem representar o mesmo campo. O sistema sugere o mapeamento, mostra uma prévia e exige confirmação antes da gravação.

Quando a estrutura é nova ou ambígua, a contadora corrige o mapeamento manualmente. O modelo aprovado fica salvo para reutilização futura. Arquivos protegidos por senha, PDFs, imagens, OFX e XML contábil exigem leitores próprios e entram em etapas posteriores.

A IA pode sugerir a relação entre nomes de colunas. Ela nunca escolhe sozinha a empresa, o tipo de documento, a competência ou o destino dos dados.

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

## Execução local durante a transição

O projeto Reflex legado ainda pode ser executado para manutenção:

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\reflex.exe compile --dry
```

O novo backend Django será adicionado em uma etapa própria, com ambiente e comando de execução documentados em `etapas.md` antes de qualquer migração de dados.

## Documentos de continuidade

- [`etapas.md`](etapas.md): plano completo da migração e construção, etapa por etapa.
- [`faltando.md`](faltando.md): estado atual, próxima etapa autorizável e pendências concretas.
- [`AGENTS.md`](AGENTS.md): regras para agentes e limites da transição.
- [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md): tokens e regras visuais que serão reaproveitados na interface HTML.
- [`docs/PROMPTS_ETAPAS.md`](docs/PROMPTS_ETAPAS.md): documento histórico do Reflex; não é o plano vigente.
- [`docs/inventario_etapa1.md`](docs/inventario_etapa1.md): fotografia somente leitura do banco para a Etapa 1.
- [`docs/catalogo_logic_etapa1.md`](docs/catalogo_logic_etapa1.md): catálogo dos módulos Python reutilizáveis.
- [`docs/aceitacao_etapa1.md`](docs/aceitacao_etapa1.md): arquivos e critérios do primeiro ciclo de aceite.

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
