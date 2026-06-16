import logging

import pandas as pd

from database import inserir_conciliacao

logger = logging.getLogger(__name__)


def conciliar_partidas(df: pd.DataFrame) -> dict:
    df_ordenado = df.sort_values(["data", "sequencial_lote"]).reset_index(drop=True)

    pares: list[tuple[int, int]] = []
    indices_sem_par = set(df_ordenado.index)

    for (_data, _valor), grupo in df_ordenado.groupby(["data", "valor"]):
        cs = grupo[grupo["tipo"] == "C"].index.tolist()
        ds = grupo[grupo["tipo"] == "D"].index.tolist()

        n = min(len(cs), len(ds))
        for i in range(n):
            pares.append((cs[i], ds[i]))

        for idx in cs[:n] + ds[:n]:
            indices_sem_par.discard(idx)

    registros_pares = []
    for c_idx, d_idx in pares:
        row_c = df_ordenado.loc[c_idx]
        registros_pares.append({
            "seq_c": int(row_c["sequencial_lote"]),
            "seq_d": int(df_ordenado.loc[d_idx, "sequencial_lote"]),
            "data": row_c["data"],
            "conta_contabil": row_c["conta_contabil"],
            "valor": row_c["valor"],
            "status": "conciliado",
        })

    df_pares = pd.DataFrame(registros_pares)
    df_sem_par = df_ordenado.loc[sorted(indices_sem_par)].reset_index(drop=True)

    pares_ok = len(pares)
    sem_par = len(indices_sem_par)

    logger.info("Conciliacao: %d pares ok, %d sem par.", pares_ok, sem_par)

    return {
        "pares_ok": pares_ok,
        "sem_par": sem_par,
        "df_pares": df_pares,
        "df_sem_par": df_sem_par,
    }


def salvar_resultado_conciliacao(empresa_id: int, periodo: str, resultado: dict) -> None:
    total_pares = resultado["pares_ok"] + resultado["sem_par"]
    inserir_conciliacao(empresa_id, periodo, total_pares, resultado["pares_ok"], resultado["sem_par"])


def gerar_relatorio_conciliacao(resultado: dict) -> pd.DataFrame:
    linhas = []

    if not resultado["df_pares"].empty:
        for _, row in resultado["df_pares"].iterrows():
            linhas.append({
                "Tipo": "Par conciliado",
                "Seq. C": row["seq_c"],
                "Seq. D": row["seq_d"],
                "Data": row["data"],
                "Conta": row.get("conta_contabil", ""),
                "Valor": row["valor"],
                "Status": "OK",
            })

    if not resultado["df_sem_par"].empty:
        for _, row in resultado["df_sem_par"].iterrows():
            linhas.append({
                "Tipo": f"Sem par ({row['tipo']})",
                "Seq. C": row["sequencial_lote"] if row["tipo"] == "C" else "",
                "Seq. D": row["sequencial_lote"] if row["tipo"] == "D" else "",
                "Data": row["data"],
                "Conta": row.get("conta_contabil", ""),
                "Valor": row["valor"],
                "Status": "Sem par",
            })

    return pd.DataFrame(linhas)
