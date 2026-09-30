# Base de aceitação — Etapa 1

Os arquivos abaixo são referências de entrada. O sistema deverá preservar o original, identificar a estrutura e exigir confirmação do mapeamento antes de gravar dados.

| Arquivo | Formato | Uso no aceite | Estado | SHA-256 |
|---|---|---|---|---|
| `CAP_ILHAS_DO_LAGO_CONCILIADO (1).xlsx` | XLSX com linhas delimitadas por `;` | Caso principal contábil | disponível | `1f7156b4638a4924bfc226f281624b8f7ea6b3116cbc4a103a029540ca3ea21e` |
| `cap_anonimizada_delimitada.xlsx` | XLSX com linhas delimitadas por `;` | Importação automática do formato original | versionada | `441a1ac3c3295fedf40ee99421cebd4cf34756589f2e0388d63d3553d2553463` |
| `cap_anonimizada_colunas.csv` | CSV em colunas | Importação automática em formato aberto | versionada | `0c89c850337d1ca0e447412801a583d7cef984d215d221a9d1f4c45237f9d767` |
| `cap_anonimizada_multiplas_abas.xlsx` | XLSX com resumo e movimentos | Escolha manual de aba e cabeçalho | versionada | `8edebe57f01091db324c5be5a766d1f6d4e3502fdd2c770a8778311374285f67` |

## Caso CAP confirmado

- 42 linhas de dados, em 21 datas.
- 21 créditos (`C`) e 21 débitos (`D`).
- Soma dos créditos: `R$ 11.243,72`.
- Soma dos débitos: `R$ 11.243,72`.
- Filial observada: `1`.
- Resultado esperado da conciliação: 21 pares conhecidos, sem confirmação automática de ambiguidades.

## Primeiro ciclo de aceite

1. Entrar pelo navegador e selecionar empresa e competência.
2. Enviar o arquivo CAP e mostrar a prévia das 42 linhas.
3. Confirmar o mapeamento de data, conta contábil, valor, tipo, histórico e filial.
4. Exigir revisão das pendências e aprovação manual do lote.
5. Verificar que os 42 lançamentos aprovados permanecem após atualizar a página.
6. Executar conciliação e conferir os 21 pares conhecidos.
7. Exportar a saída sem colunas técnicas.

## Evidências de conclusão

- O dump nativo foi restaurado e comparado com o banco remoto em `docs/verificacao_backup_etapa1.md`.
- As três fixtures anonimizadas estão em `tests/fixtures/aceitacao/` e preservam 42 linhas, 21 débitos, 21 créditos e os totais conhecidos.
- Os três testes de aceitação das fixtures passam com `unittest`.
