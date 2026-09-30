# Base de aceitação — Etapa 1

Os arquivos abaixo são referências de entrada. O sistema deverá preservar o original, identificar a estrutura e exigir confirmação do mapeamento antes de gravar dados.

| Arquivo | Formato | Uso no aceite | Estado | SHA-256 |
|---|---|---|---|---|
| `CAP_ILHAS_DO_LAGO_CONCILIADO (1).xlsx` | XLSX com linhas delimitadas por `;` | Caso principal contábil | disponível | `1f7156b4638a4924bfc226f281624b8f7ea6b3116cbc4a103a029540ca3ea21e` |
| `JUNHO 2026.xlsx` | XLSX com três abas e layouts diferentes | Caso de estrutura desconhecida/múltiplas abas | disponível | `683118dbb1b676b61dbb53e6ebae62adeec36a4288a5c21c9ea4c0390ec776d6` |
| `caju-300-ml-0.csv` | CSV sem campos contábeis | Caso negativo: rejeição explicada | disponível | `não registrado no repositório` |

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

## Pendências para encerrar a etapa

- Restaurar um dump nativo em PostgreSQL de teste; o ambiente atual não possui Docker/Podman, `pg_dump` ou `psql`.
- Confirmar com a contadora que `JUNHO 2026.xlsx` é uma entrada desejada para o fluxo contábil.
- Obter mais um arquivo contábil real em CSV ou XLS e anonimizá-lo antes de versionar qualquer fixture.
