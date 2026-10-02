# Plano de atualização do ContaView

Este é o plano vigente para transformar o ContaView em uma ferramenta web confiável para o trabalho diário da contadora.

O plano substitui a construção em largura dos módulos Reflex. A aplicação será reconstruída por fluxos verticais, sempre fechando um ciclo real antes de abrir o próximo.

## Regras de execução

1. A contadora acessa tudo pelo navegador. Nenhum software é instalado no computador dela.
2. O PostgreSQL do Supabase continua sendo o banco de produção.
3. Os dados e tabelas existentes são preservados.
4. A lógica determinística continua em Python e não recebe decisões probabilísticas da IA.
5. Cada etapa precisa de uma checklist de aceite executada antes de ser encerrada.
6. Ao concluir uma etapa, atualizar `faltando.md` com o que foi feito, o que foi testado e a próxima etapa.
7. Antes de iniciar a etapa seguinte, apresentar o resultado da etapa concluída e pedir autorização para avançar.
8. Não iniciar duas etapas de produto ao mesmo tempo.
9. Um erro visível para a contadora precisa ter mensagem acionável e referência para o log do servidor.
10. Nenhuma alteração destrutiva no banco ocorre sem backup, conferência do alvo e registro no histórico.

## Arquitetura alvo

```text
Navegador
  -> Django + HTML + Tailwind + HTMX
  -> serviços de negócio Python
  -> PostgreSQL/Supabase

Arquivos originais -> armazenamento privado
IA -> sugestão de mapeamento e consultas controladas do Assistente
Auditoria -> triggers PostgreSQL + histórico exibido junto ao registro
```

### Tecnologias

- Django 5.2 LTS.
- Django Templates para renderização HTML.
- Tailwind CSS compilado para arquivo estático.
- HTMX para atualizações parciais sem uma aplicação SPA.
- JavaScript puro apenas para interações locais.
- PostgreSQL do Supabase para produção.
- Gunicorn em contêiner Linux.
- GitHub Actions para testes e deploy.
- Pandas, SQLAlchemy, ReportLab, XlsxWriter e parsers já existentes.

## Etapa 0 — Decisão e documentação

**Status:** concluída.

### Entregas

- Arquitetura Django + HTML + Tailwind + HTMX definida.
- Reflex classificado como legado durante a transição.
- PostgreSQL/Supabase mantido como banco de produção.
- Fluxo de trabalho reorganizado em Trabalho, Entradas, Conferência, Entregas e Assistente.
- Política de automação por nível de risco definida.
- `README.md`, `etapas.md`, `faltando.md` e `AGENTS.md` atualizados.

### Aceite

- É possível continuar a execução em outro computador lendo apenas `README.md`, `etapas.md` e `faltando.md`.
- O próximo passo está identificado sem depender do histórico da conversa.

## Etapa 1 — Inventário, backup e base de aceitação

**Status:** concluída.

### Objetivo

Criar uma fotografia segura do estado atual antes da migração e definir os arquivos reais que provarão a funcionalidade.

### Tarefas

1. Catalogar tabelas, colunas, índices, triggers e privilégios do Supabase.
2. Fazer backup verificável do banco.
3. Separar dados de produção, dados de teste e dados antigos.
4. Catalogar os fluxos existentes em `contaview/logic/`.
5. Selecionar pelo menos três planilhas reais anonimizadas de formatos diferentes.
6. Registrar os resultados esperados da planilha CAP, incluindo os 42 lançamentos e os 21 pares conhecidos.
7. Definir os critérios de aceite do primeiro ciclo.

### Aceite

- Backup restaurado em um banco de teste.
- Inventário registrado.
- Pelo menos três arquivos de teste disponíveis.
- Teste de aceitação documentado para importar, aprovar, conciliar e exportar.

### Saída

Um relatório de inventário e uma suíte de arquivos de aceitação. Nenhuma tabela de produção é removida.

## Etapa 2 — Esqueleto Django e execução pelo navegador

**Status:** concluída em 30/09/2026.

### Objetivo

Criar a nova aplicação web sem alterar o banco de produção.

### Tarefas

1. Criar o projeto Django e separar configurações de desenvolvimento e produção.
2. Configurar variáveis de ambiente e segredo de sessão.
3. Configurar conexão PostgreSQL com SSL e pool adequado ao servidor persistente.
4. Configurar arquivos estáticos, Tailwind e templates base.
5. Criar layout com sidebar, cabeçalho, área de conteúdo e mensagens de erro.
6. Configurar health check que verifique aplicação e banco.
7. Criar logs estruturados com identificador de requisição.
8. Criar Dockerfile e comando de execução local.

### Aceite

- A tela inicial abre em navegador comum.
- Uma rota inexistente mostra página de erro do sistema, não erro genérico.
- O health check diferencia aplicação disponível de banco indisponível.
- Nenhum segredo aparece no HTML, JavaScript ou repositório.

## Etapa 3 — Autenticação e contexto de trabalho

**Status:** concluída em 01/10/2026.

### Objetivo

Substituir a autenticação por variáveis soltas por sessão segura do Django.

### Tarefas

1. Criar usuário administrativo inicial por comando seguro.
2. Implementar login, logout e expiração de sessão.
3. Adicionar proteção CSRF e cookies seguros.
4. Criar limitação de tentativas de login.
5. Implementar seleção persistente de empresa e competência.
6. Garantir que toda consulta receba o contexto selecionado no servidor.

### Aceite

- Acesso sem login redireciona para a tela de login.
- Uma sessão não acessa dados de outra sessão.
- Logout invalida a sessão e limpa o contexto.
- Credenciais incorretas não revelam se o usuário existe.

## Etapa 4 — Tela Trabalho

**Status:** concluída em 01/10/2026.

### Objetivo

Dar à contadora uma fila de tarefas, em vez de um painel de indicadores sem ação.

### Tarefas

1. Exibir empresas e competências abertas.
2. Mostrar documentos aguardados, lotes pendentes, divergências e entregas.
3. Criar estados operacionais: aguardando, recebido, em conferência, com divergência, revisado e entregue.
4. Permitir abrir diretamente a próxima ação.
5. Criar checklist recorrente por empresa e competência.

### Aceite

- A contadora identifica o próximo trabalho sem navegar por vários módulos.
- Cada alerta possui link para a tela e registro responsável.
- O estado exibido vem do banco e não de variáveis de sessão perdidas.

## Etapa 5 — Entrada genérica de arquivos

**Status:** concluída.

### Objetivo

Aceitar diferentes planilhas sem criar uma página específica para cada fornecedor.

### Tarefas

1. Upload de XLSX, XLS e CSV.
2. Leitura de abas, cabeçalho e prévia.
3. Mapeamento para data, valor, descrição, tipo, conta e filial.
4. Preservação de colunas originais não mapeadas.
5. Detecção de datas, valores e sinais em formatos brasileiros.
6. Validação de tamanho, extensão e linhas.
7. Hash de arquivo e bloqueio de reenvio acidental.
8. Sugestão de mapeamento por regras locais.
9. Sugestão de IA somente quando a regra local não for suficiente.
10. Salvamento de modelos de mapeamento confirmados.

### Aceite

- Os três arquivos selecionados na Etapa 1 entram pelo navegador.
- A planilha CAP gera 42 linhas preparadas.
- Um formato desconhecido abre o mapeamento manual sem perder o arquivo original.
- Arquivo repetido é identificado antes de criar novo lote.
- Arquivo inválido gera erro explicando campo, aba e linha.

## Etapa 6 — Conferência e aprovação do lote

**Status:** concluída.

### Objetivo

Fechar a ponte entre preparação e lançamentos finais.

### Tarefas

1. Exibir linhas prontas, pendentes e ignoradas.
2. Editar datas, valores, tipos, contas e filiais.
3. Permitir edição em lote e colagem controlada.
4. Mostrar totais de débito e crédito.
5. Exigir resolução das pendências antes da aprovação.
6. Verificar empresa e competência dentro da transação.
7. Exigir confirmação para substituir competência existente.
8. Gravar `sequencial_lote` e histórico.
9. Permitir reabrir ou cancelar uma preparação ainda não aprovada.

### Aceite

- As 42 linhas CAP podem ser conferidas e aprovadas.
- Após atualizar a página, os lançamentos continuam disponíveis.
- Uma falha durante a aprovação não deixa dados parcialmente gravados.
- Substituição de competência exige confirmação explícita.

Implementação concluída em `docs/aceitacao_etapa6.md`. A aprovação mantém a regra de um único período por lote; arquivos com vários meses precisam ser separados.

## Etapa 7 — Assistente controlado

**Status:** concluída.

### Objetivo

Permitir consultas em linguagem natural sem expor dados nominais nem permitir alterações contábeis.

### Tarefas

1. Persistir conversas e mensagens por sessão autenticada.
2. Restringir consultas à empresa e competência do contexto atual.
3. Remover CPFs, CNPJs e registros nominais antes do envio à IA.
4. Permitir perguntas gerais e consultas determinísticas de saldo, conciliação e auditoria.
5. Tratar chave ausente, indisponibilidade e mensagens inválidas sem quebrar a rotina.

### Aceite

- Uma conversa pode ser criada, retomada e excluída na mesma sessão.
- Uma pergunta fora do contexto selecionado é bloqueada.
- O assistente não grava lançamentos nem recebe registros nominais brutos.

Os lançamentos manuais e o histórico permanecem planejados para uma etapa posterior específica.

## Etapa 8 — Conciliação e exceções

**Status:** concluída.

### Objetivo

Automatizar correspondências seguras e enviar ambiguidades para decisão humana.

### Tarefas

1. Cruzar fontes por data, valor, histórico e filial.
2. Respeitar cardinalidade única.
3. Separar pares confirmados, candidatos, diferenças e sem correspondência.
4. Exibir a origem de cada linha.
5. Permitir confirmar, rejeitar ou resolver manualmente um candidato.
6. Gravar resumo e resultado da execução.
7. Impedir duplicação ao reexecutar.

### Aceite

- A planilha CAP produz os 21 pares esperados.
- Uma diferença de valor não vira par confirmado.
- Dois candidatos iguais ficam para revisão.
- A segunda execução não duplica ocorrências.

Implementação concluída em `docs/aceitacao_etapa8.md`. A migração de revisões permanece preparada localmente e será aplicada no Supabase apenas na Etapa 13.

## Etapa 9 — Auditoria operacional

**Status:** concluída.

### Objetivo

Transformar auditoria em uma trilha de exceções e histórico, sem julgamento de modelo.

### Tarefas

1. Manter triggers PostgreSQL para inserção, edição e exclusão.
2. Corrigir registros antigos sem `lancamento_id` após backup.
3. Detectar duplicidade, histórico vazio, conta inválida e valor anômalo.
4. Exibir histórico junto do lote ou lançamento.
5. Permitir marcar ocorrência como resolvida com usuário e data.
6. Exportar exceções sem colunas técnicas desnecessárias.

### Aceite

- Toda ocorrência nova aponta para o lançamento quando existir.
- Auditoria repetida é idempotente.
- A contadora consegue entender e resolver cada ocorrência.

Implementação concluída em `docs/aceitacao_etapa9.md`. A migração de histórico, triggers e estados de resolução permanece preparada localmente e será aplicada no Supabase somente na Etapa 13.

## Etapa 10 — Entregas e relatórios

**Status:** concluída em ambiente local; migração pendente para o corte da Etapa 13.

### Objetivo

Gerar saídas úteis e verificáveis, independentes do sistema oficial.

### Tarefas

1. Criar perfis de exportação genéricos e personalizados.
2. Calcular balancete com saldo anterior, movimento e saldo final.
3. Definir plano de classificação da DRE com a contadora.
4. Calcular DRE por grupos e subtotais.
5. Gerar Excel e PDF com layout legível.
6. Excluir colunas internas das exportações.
7. Registrar parâmetros e versão do relatório gerado.

### Aceite

- Os valores batem com uma conferência manual da contadora.
- O PDF não corta colunas nem esconde totais.
- Um relatório gerado pode ser reproduzido com a mesma competência.

## Etapa 11 — Automações recorrentes

**Status:** concluída em ambiente local; migração pendente para o corte da Etapa 13.

### Objetivo

Reduzir atividades repetitivas depois que o ciclo básico estiver estável.

### Tarefas

1. Checklist mensal automático por empresa.
2. Modelos de documentos esperados.
3. Lembretes internos de pendências.
4. Processamento de múltiplos arquivos em lote.
5. Perfis de nomes e pastas de origem.
6. Integração opcional com pasta de entrada ou e-mail, somente depois de validar segurança e autorização.
7. Fila de processamento com retry e estado visível quando arquivos demorarem.

### Aceite

- Uma nova competência cria as tarefas esperadas sem cadastro manual repetido.
- Falhas de automação ficam visíveis e podem ser reexecutadas.
- Nenhum arquivo é processado duas vezes sem confirmação.

## Etapa 12 — Assistente

**Status:** concluída em ambiente local; migração pendente para o corte da Etapa 13.

### Objetivo

Permitir consultas em linguagem natural sem delegar decisões contábeis à IA.

### Tarefas

1. Criar funções de consulta autorizadas.
2. Enviar somente agregados e dados necessários.
3. Remover CPF, CNPJ individual e nomes de terceiros do contexto quando não forem indispensáveis.
4. Registrar pergunta, filtros e resposta.
5. Mostrar a origem dos números consultados.
6. Impedir qualquer escrita feita pelo Assistente.

### Aceite

- O Assistente responde sobre dados existentes.
- Não inventa totais quando não há dados.
- Não altera lançamentos, lotes ou ocorrências.
- As conversas persistem depois de atualizar o navegador.

## Etapa 13 — Produção e corte

**Status:** aguardando.

### Objetivo

Colocar o Django em produção com operação observável e reversível.

### Tarefas

1. Criar contêiner Linux e health check.
2. Configurar variáveis de ambiente e secrets.
3. Configurar deploy automático após testes.
4. Executar migrações Django com backup confirmado.
5. Rodar smoke tests no endereço público.
6. Executar o ciclo CAP completo em ambiente de aceitação.
7. Manter o Reflex somente como fallback temporário.
8. Desativar o Reflex depois da aprovação do ciclo real.

### Aceite

- Login, rotas internas e atualização de página funcionam.
- O ciclo inteiro é executado sem abrir o código.
- Erros aparecem nos logs com referência de atendimento.
- O rollback está documentado.

## Critério de conclusão do plano

O plano estará concluído quando a contadora puder, pelo navegador:

```text
receber arquivos
-> preparar e corrigir
-> aprovar lotes
-> lançar manualmente
-> conciliar
-> resolver exceções
-> gerar relatórios
-> exportar a entrega
```

O Assistente será considerado complementar. O ciclo contábil determinístico precisa continuar funcionando mesmo sem a chave da OpenAI.
