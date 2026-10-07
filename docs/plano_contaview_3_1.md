# Plano ContaView 3.1

## Objetivo

O ContaView é uma ferramenta web de apoio à contadora. Ele fica ao lado do sistema oficial da empresa: recebe arquivos de diversas origens, prepara, confere, classifica mediante revisão humana e produz o arquivo de importação já aceito pelo sistema contábil.

Ele não grava no sistema oficial, não substitui a escrituração formal e não assume obrigações fiscais, ECD ou ECF.

## Princípios de produto

- A contadora confirma decisões relevantes. IA apenas sugere ou explica.
- Cada valor é rastreável ao arquivo, aba, linha, lote, versão e aprovação.
- Reenvios, correções e reprocessamentos são registrados; não há exclusão silenciosa.
- Empresa e competência são validadas no servidor antes de toda consulta ou alteração.
- Erro silencioso é pior que pendência explícita. Toda validação bloqueante aparece antes da exportação.
- Dados ficam privados; o uso de dados reais exige autorização, definição de retenção e backup.

## Perfis de origem

Cada origem terá um perfil por empresa, com mapeamento confirmado independente e uma regra de competência.

| Modo | Uso | Resultado da entrada |
|---|---|---|
| Transacional | OFX, extrato ou relatório operacional | Movimentos preservados para classificação assistida e revisão posterior. |
| Contábil estruturado | Arquivo que já possui partidas D/C | Validação, rastreabilidade e exportação, sem reclassificação. |

As regras de competência são `restrita`, `ampliada` ou `livre`. Data futura, incoerente ou fora da regra configurada é uma pendência bloqueante. A hipótese de inversão de dia e mês pode ser mostrada como sugestão, mas nunca aplicada automaticamente.

## Fases de execução

### Fase 0 — Descoberta e autorização

Executar em paralelo à construção técnica com dados sintéticos.

1. Obter autorização da empresa para dados reais e definir retenção, acesso, armazenamento e recuperação.
2. Reunir duas ou três competências anonimizadas de cada fluxo e o razão histórico já classificado.
3. Confirmar produto e versão do Senior, formato aceito para importação, plano de contas, razão bancário e fonte da conciliação.
4. Investigar a origem do arquivo de exemplo e confirmar datas, histórico, homologação e procedimento de reversão de uma importação.
5. Cronometrar o processo manual para criar a linha de base das métricas.

Nenhum teste em produção será feito sem homologação ou procedimento de reversão conhecido.

### Fase 1 — Entrada confiável

Prioridade de formatos: OFX, CSV, XLSX e PDF estruturado somente quando não houver alternativa. A entrada deve tratar planilhas com cabeçalho fora da primeira linha, totais, linhas vazias, células mescladas, CSV em coluna única, codificação variável e valores ou datas em texto.

- Hash do arquivo para bloquear reenvio.
- Identificador OFX preservado para detectar repetição de transações.
- Arquivo, aba, linha, perfil de origem e lote preservados.
- Mapeamento salvo por empresa, perfil e estrutura; alteração estrutural pede nova confirmação.
- OFX só confere saldo inicial mais movimentos contra saldo final quando a fonte disponibilizar saldo inicial confiável. O OFX bancário usual normalmente traz apenas saldo final; nesse caso o sistema registra que a conferência não é possível e não inventa um saldo.
- Conferência por modo: OFX com saldo quando disponível; fonte transacional por entradas e saídas da conta gerada; fonte D/C por débitos iguais a créditos.

Aceite: a conferência aplicável fecha, o reenvio não cria duplicidade e o arquivo de exemplo é lido sem ajuste manual.

### Fase 2 — Classificação contábil assistida

- Regras reutilizáveis por descrição, favorecido, documento, valor, operação e padrão bancário.
- Regras iniciais podem ser extraídas do razão histórico classificado.
- Cada regra tem empresa, conta bancária, critérios, prioridade, vigência, escopo, responsável, histórico, último uso, taxa de erro e situação.
- Conflitos viram exceção. Regra ampla, como apenas `PIX`, não define contrapartida sem critério adicional.
- A sugestão informa se veio de regra confirmada, sugestão nova ou decisão manual. Criar regra exige confirmação.
- Transferências entre contas próprias, tarifas, IOF, juros e estornos recebem tratamento explícito.

Aceite: medir percentual classificado por regra reutilizada e tempo de revisão.

### Fase 3 — Revisão por exceção e aprovação

Exceções incluem ausência de conta, regra desconhecida ou conflitante, valor fora de faixa, duplicidade, data suspeita, total divergente e descrição insuficiente.

A tela permite filtro, correção individual e em lote. Uma amostra aleatória das classificações automáticas é revisada a cada lote. Aprovação registra responsável, data e justificativa; a correção posterior cria nova versão.

### Fase 4 — Exportação para o sistema oficial

O primeiro perfil replica o arquivo de exemplo: duas linhas por lançamento, D/C, data `DD/MM/AAAA`, valor decimal com vírgula e ordem exata das colunas.

Antes de gerar, validar pares, débitos e créditos, competência, conta, histórico e campos exigidos. Exportação passa por `Exportado`, `Importação confirmada` ou `Importação rejeitada`; confirmação inicial é manual e registra lote externo, responsável, data e motivo. Reexportar exige bloqueio ou confirmação forte.

Aceite: arquivo importado sem ajuste no ambiente de homologação ou em procedimento reversível conhecido.

### Fase 5 — Conciliação

Comparar extrato com fonte independente: razão bancário do sistema oficial, contas a pagar e receber ou lote validado. Par automático só existe com identificador OFX ou candidato único. Ambiguidades e reversões são revisadas e justificadas. O MVP cobre 1:1; 1:N e N:1 ficam para expansão.

### Fase 6 — Auditoria e comparação mensal

Detectar duplicidade, histórico vazio, conta inválida, ausência de classificação, divergência de total, data suspeita, variação relevante contra meses anteriores e recorrência ausente. Cada alerta expõe regra, fonte, linha e resolução.

### Fase 7 — Expansão controlada

Contas a pagar e receber, XML de NF-e/NFS-e, checklist por empresa e competência, folha, conciliação 1:N e N:1, Assistente somente leitura e relatórios adicionais só entram depois de validar o fluxo prioritário.

## Validação e métricas

Executar uma competência em paralelo ao processo manual, comparar resultado, divergências e duração.

| Métrica | Meta inicial |
|---|---|
| Diferença entre arquivo e dados preparados | R$ 0,00 |
| Arquivos duplicados aceitos | 0 |
| Exportações sem ajuste no fluxo escolhido | 100% |
| Conciliações ambíguas auto-confirmadas | 0 |
| Linhas por regra reutilizada | Definir após a linha de base |
| Redução de tempo | Definir após a linha de base |
| Erros encontrados na amostra | Medir e reduzir por competência |

## Situação desta implementação

A fundação técnica da Fase 1 iniciou em 07/10/2026: perfis de origem possuem os dois modos e a regra de competência; OFX, CSV, XLS e XLSX são aceitos; FITID, conta bancária, totais e saldo final do OFX são preservados; e os mapeamentos confirmados são isolados por perfil de origem. A classificação, a revisão por exceção e a exportação específica do Senior continuam pendentes das descobertas da Fase 0.
