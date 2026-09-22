import logging
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher

import pandas as pd

from contaview.logic.database import inserir_conciliacao

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
                "Tipo": f"Sem par ({row['tipo'] or 'Nao classificado'})",
                "Seq. C": row["sequencial_lote"] if row["tipo"] == "C" else "",
                "Seq. D": row["sequencial_lote"] if row["tipo"] == "D" else "",
                "Data": row["data"],
                "Conta": row.get("conta_contabil", ""),
                "Valor": row["valor"],
                "Status": "Sem par",
            })

    return pd.DataFrame(linhas)


def _descricao_normalizada(valor: str | None) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", texto.upper())).strip()


def _data_conciliacao(valor) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor))


def conciliar_fontes(
    extrato: list[dict], referencia: list[dict], janela_dias: int = 3,
) -> dict:
    """Cruza fontes sem confirmar automaticamente pares ambíguos."""
    if janela_dias < 0 or janela_dias > 31:
        raise ValueError("A janela de datas deve estar entre 0 e 31 dias.")
    for conjunto in (extrato, referencia):
        if any(item.get("status") != "validado" for item in conjunto):
            raise ValueError("Resolva as pendências antes de conciliar os lotes.")
        if any(item.get("data") is None or item.get("valor") is None for item in conjunto):
            raise ValueError("Data e valor são obrigatórios para conciliação.")

    def chave(item: dict) -> tuple:
        return (
            _data_conciliacao(item["data"]),
            Decimal(str(item["valor"])).quantize(Decimal("0.01")),
            _descricao_normalizada(item.get("descricao")),
        )

    grupos_extrato: dict[tuple, list[dict]] = defaultdict(list)
    grupos_referencia: dict[tuple, list[dict]] = defaultdict(list)
    for item in extrato:
        grupos_extrato[chave(item)].append(item)
    for item in referencia:
        grupos_referencia[chave(item)].append(item)

    pares: list[dict] = []
    ids_extrato: set[int] = set()
    ids_referencia: set[int] = set()
    for chave_exata, entradas in grupos_extrato.items():
        saidas = grupos_referencia.get(chave_exata, [])
        if chave_exata[2] and len(entradas) == len(saidas) == 1:
            a, b = entradas[0], saidas[0]
            ids_extrato.add(int(a["id"]))
            ids_referencia.add(int(b["id"]))
            pares.append({
                "extrato_id": int(a["id"]),
                "referencia_id": int(b["id"]),
                "linha_extrato": int(a.get("numero_linha", a["id"])),
                "linha_referencia": int(b.get("numero_linha", b["id"])),
                "data": chave_exata[0].strftime("%d/%m/%Y"),
                "valor": str(chave_exata[1]),
                "descricao": a.get("descricao") or "",
            })

    sem_extrato = [item for item in extrato if int(item["id"]) not in ids_extrato]
    sem_referencia = [item for item in referencia if int(item["id"]) not in ids_referencia]
    referencia_por_data: dict[date, list[dict]] = defaultdict(list)
    for item in sem_referencia:
        referencia_por_data[_data_conciliacao(item["data"])].append(item)
    candidatos: list[dict] = []
    divergencias_valor: list[dict] = []
    for origem in sem_extrato:
        data_origem, valor_origem, descricao_origem = chave(origem)
        for deslocamento in range(-janela_dias, janela_dias + 1):
            data_candidata = data_origem + timedelta(days=deslocamento)
            for destino in referencia_por_data.get(data_candidata, []):
                _, valor_destino, descricao_destino = chave(destino)
                if valor_origem != valor_destino and not descricao_origem:
                    continue
                similaridade = SequenceMatcher(
                    None, descricao_origem, descricao_destino
                ).ratio() if descricao_origem and descricao_destino else 0.0
                registro = {
                    "extrato_id": int(origem["id"]),
                    "referencia_id": int(destino["id"]),
                    "linha_extrato": int(origem.get("numero_linha", origem["id"])),
                    "linha_referencia": int(destino.get("numero_linha", destino["id"])),
                    "dias_diferenca": abs(deslocamento),
                    "similaridade_descricao": round(similaridade, 2),
                    "valor_extrato": str(valor_origem),
                    "valor_referencia": str(valor_destino),
                }
                if valor_origem == valor_destino:
                    candidatos.append(registro)
                elif similaridade >= 0.75:
                    divergencias_valor.append(registro)
                if len(candidatos) + len(divergencias_valor) > 100000:
                    raise ValueError(
                        "Há candidatos demais para revisão; reduza o período ou filtre os lotes."
                    )

    ids_com_candidato_extrato = {
        item["extrato_id"] for item in candidatos + divergencias_valor
    }
    ids_com_candidato_referencia = {
        item["referencia_id"] for item in candidatos + divergencias_valor
    }
    faltantes_extrato = [
        item for item in sem_extrato
        if int(item["id"]) not in ids_com_candidato_extrato
    ]
    faltantes_referencia = [
        item for item in sem_referencia
        if int(item["id"]) not in ids_com_candidato_referencia
    ]

    return {
        "pares_confirmados": pares,
        "candidatos": candidatos,
        "divergencias_valor": divergencias_valor,
        "sem_correspondencia_extrato": sem_extrato,
        "sem_correspondencia_referencia": sem_referencia,
        "faltantes_extrato": faltantes_extrato,
        "faltantes_referencia": faltantes_referencia,
        "total_extrato": len(extrato),
        "total_referencia": len(referencia),
    }
