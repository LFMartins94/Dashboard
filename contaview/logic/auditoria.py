import logging

import pandas as pd

from contaview.logic.conciliacao import conciliar_partidas
from contaview.logic.database import inserir_ocorrencias

logger = logging.getLogger(__name__)


def auditar_lancamentos(df: pd.DataFrame) -> list[dict]:
    ocorrencias: list[dict] = []

    # a. DUPLICIDADE (alta)
    dup_mask = df.duplicated(subset=["data", "conta_contabil", "valor", "tipo"], keep=False)
    duplicados = df[dup_mask]
    indices_dup = set(duplicados.index)
    ocorrencias_por_grupo: set[tuple] = set()
    for _, row in duplicados.iterrows():
        chave = (row["data"], row["conta_contabil"], row["valor"], row["tipo"])
        if chave not in ocorrencias_por_grupo:
            ocorrencias_por_grupo.add(chave)
            ocorrencias.append({
                "lancamento_id": None,
                "tipo_ocorrencia": "DUPLICIDADE",
                "descricao": (
                    f"Lancamento duplicado: {row['conta_contabil']} "
                    f"R$ {row['valor']:.2f} em {row['data']}"
                ),
                "severidade": "alta",
            })

    # b. SEM_PAR (alta) — roda conciliacao internamente
    try:
        conc_result = conciliar_partidas(df)
    except Exception as exc:
        logger.warning("Conciliacao para auditoria falhou: %s", exc)
        conc_result = {"df_sem_par": pd.DataFrame()}

    for _, row in conc_result["df_sem_par"].iterrows():
        ocorrencias.append({
            "lancamento_id": None,
            "tipo_ocorrencia": "SEM_PAR",
            "descricao": (
                f"Lancamento sem par: {row['tipo'] or 'Nao classificado'} "
                f"R$ {row['valor']:.2f} em {row['data']}"
            ),
            "severidade": "alta",
        })

    # c. HISTORICO_VAZIO (media)
    df_hist = df.copy()
    df_hist["_hist_len"] = df_hist["historico"].fillna("").astype(str).str.len()
    vazios = df_hist[df_hist["_hist_len"] < 3]
    for _, row in vazios.iterrows():
        ocorrencias.append({
            "lancamento_id": None,
            "tipo_ocorrencia": "HISTORICO_VAZIO",
            "descricao": (
                f"Historico nao preenchido na conta "
                f"{row['conta_contabil']} em {row['data']}"
            ),
            "severidade": "media",
        })

    # d. VALOR_ANOMALO (media)
    if not df.empty and df["valor"].notna().any():
        media = df["valor"].mean()
        std = df["valor"].std()
        if std > 0:
            anomalos = df[abs(df["valor"] - media) > 3 * std]
            for _, row in anomalos.iterrows():
                ocorrencias.append({
                    "lancamento_id": None,
                    "tipo_ocorrencia": "VALOR_ANOMALO",
                    "descricao": (
                        f"Valor atipico: R$ {row['valor']:.2f} na conta "
                        f"{row['conta_contabil']} (media do periodo: R$ {media:.2f})"
                    ),
                    "severidade": "media",
                })

    # e. CONTA_FORMATO_INVALIDO (baixa)
    invalidas = df[
        df["conta_contabil"].fillna("").astype(str).str.len() < 3
    ]
    for _, row in invalidas.iterrows():
        ocorrencias.append({
            "lancamento_id": None,
            "tipo_ocorrencia": "CONTA_FORMATO_INVALIDO",
            "descricao": f"Codigo de conta fora do padrao: {row['conta_contabil']}",
            "severidade": "baixa",
        })

    logger.info(
        "Auditoria: %d ocorrencias encontradas "
        "(alta=%d, media=%d, baixa=%d).",
        len(ocorrencias),
        sum(1 for o in ocorrencias if o["severidade"] == "alta"),
        sum(1 for o in ocorrencias if o["severidade"] == "media"),
        sum(1 for o in ocorrencias if o["severidade"] == "baixa"),
    )

    return ocorrencias


def salvar_ocorrencias(ocorrencias: list[dict], empresa_id: int) -> int:
    if not ocorrencias:
        return 0
    for o in ocorrencias:
        o["empresa_id"] = empresa_id
    return inserir_ocorrencias(ocorrencias)


def resumo_auditoria(ocorrencias: list[dict]) -> dict:
    total = len(ocorrencias)
    alta = sum(1 for o in ocorrencias if o["severidade"] == "alta")
    media = sum(1 for o in ocorrencias if o["severidade"] == "media")
    baixa = sum(1 for o in ocorrencias if o["severidade"] == "baixa")
    return {"alta": alta, "media": media, "baixa": baixa, "total": total}
