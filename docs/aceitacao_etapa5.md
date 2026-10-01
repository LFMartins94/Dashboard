# Aceitação da Etapa 5 — entrada genérica de arquivos

Data da verificação: 01/10/2026.

## Entrega

A página Entradas deixou de ser uma tela de espera. Ela recebe XLSX, XLS e CSV pelo navegador, preserva o original durante a decisão, apresenta abas e prévia, permite confirmar o significado das colunas e cria um lote em `lotes_importacao` com suas linhas em `linhas_preparadas`.

Esse fluxo prepara dados para revisão. Ele não aprova lançamentos contábeis; essa responsabilidade permanece na Etapa 6.

## Fluxo implementado

1. A empresa e a competência vêm exclusivamente do contexto autenticado da sessão.
2. O formulário aceita um ou vários arquivos.
3. Cada arquivo passa por validação de nome, extensão, conteúdo, tamanho e quantidade de linhas.
4. XLSX também possui limite de quantidade e tamanho dos membros internos compactados.
5. O SHA-256 é comparado com lotes da mesma empresa antes de criar o temporário.
6. O parser apresenta abas, cabeçalho detectado, total de linhas e doze linhas de prévia.
7. A contadora escolhe aba, linha do cabeçalho e tipo do documento.
8. Regras locais sugerem data, valor, descrição, tipo, conta contábil e filial.
9. A IA fica disponível somente quando as regras não encontram data e valor. Apenas nomes de colunas higienizados são enviados.
10. A confirmação chama `contaview.logic.importacao.salvar_preparacao_confirmada`, que volta a inspecionar o arquivo e delega a gravação ao serviço legado de banco.
11. Todas as colunas originais permanecem em `dados_brutos`, inclusive as não mapeadas.
12. O mapeamento confirmado é salvo por empresa, assinatura da estrutura e tipo do documento.
13. Depois da gravação final, a segunda cópia binária do armazenamento temporário é apagada.

## Validações e limites

- Extensões permitidas: `.xlsx`, `.xls` e `.csv`.
- Tamanho máximo: 20 MB por arquivo.
- Quantidade máxima: 30.000 linhas por aba.
- XLSX descompactado: até 100 MB e 1.000 membros internos.
- XLS: binário OLE ou SpreadsheetML reconhecido.
- CSV: rejeição de conteúdo binário e detecção de `;`, `,`, tabulação ou `|`.
- Valores brasileiros: milhar, vírgula decimal, `R$` e negativos entre parênteses.
- Datas ambíguas: nunca são inventadas; a competência orienta a validação.
- Colunas repetidas no mapeamento: recusadas no servidor.
- Arquivo, usuário, empresa e competência: revalidados em toda ação.

## Persistência e proteção

As tabelas Django preparadas nesta etapa são:

- `django_arquivos_entrada_temporarios`;
- `django_modelos_mapeamento_entrada`.

A migração `0004_entrada_generica` adiciona chaves estrangeiras para `empresas`, constraints de empresa, competência, extensão, estado e tipo, além de índices por contexto e hash. No PostgreSQL, ela habilita RLS e revoga todos os privilégios das roles `anon` e `authenticated`. O navegador não recebe credenciais do Supabase.

Essa migração foi testada no banco isolado e permanece pendente para o corte controlado da Etapa 13. Nenhum DDL foi executado no Supabase de produção.

## Critérios de aceite

| Critério | Resultado |
|---|---|
| Três fixtures da Etapa 1 entrarem pelo navegador | Aprovado |
| CAP produzir 42 linhas preparadas | Aprovado |
| Preservar todas as colunas originais | Aprovado |
| Formato desconhecido abrir mapeamento manual | Aprovado |
| Original continuar intacto antes da confirmação | Aprovado |
| Reenvio ser identificado antes de criar lote | Aprovado |
| Erros identificarem arquivo, aba ou linha responsável | Aprovado |
| XLS legado XML e formatos brasileiros entrarem pelo navegador | Aprovado |
| IA não ser chamada quando a regra local for suficiente | Aprovado |
| Mapeamento confirmado poder ser reutilizado | Aprovado |

## Resultado da fixture CAP

A fixture `cap_anonimizada_delimitada.xlsx` possui 42 movimentos e cobre janeiro a maio de 2026. No teste com a competência `2026-01`, as 42 linhas entram na preparação e as 40 linhas de outros meses recebem pendência explícita. Nenhuma linha é descartada silenciosamente.

## Verificações executadas

| Verificação | Resultado |
|---|---|
| Testes Django do app `nucleo` | 46 aprovados |
| Testes específicos da entrada | 11 aprovados |
| Testes legados com `unittest` | 30 aprovados |
| `makemigrations --check --dry-run` | Nenhuma mudança pendente |
| Compilação Python | Aprovada |
| Build do Tailwind | Aprovado |
| `collectstatic` com manifesto | Aprovado |
| `pip check` | Nenhuma dependência quebrada |
| `npm audit --omit=dev` | 0 vulnerabilidades |
| Configuração de produção | Aprovada; preload de HSTS continua reservado ao domínio final |
| Consulta no PostgreSQL real | Somente leitura; tabelas e RLS confirmadas |

## Pendência de produção

As tabelas temporárias e de modelos ainda não existem no Supabase de produção. A aplicação Django não deve ser publicada antes da Etapa 13, quando todas as migrações serão aplicadas após novo backup, com smoke test e procedimento de reversão.
