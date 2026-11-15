"""Leitura e limpeza do CSV de SRAG (SIVEP-Gripe / Open DATASUS).

Só as colunas necessárias às métricas são carregadas. Colunas de identificação
pessoal (nome, CPF, endereço etc.) nunca são lidas, o que já cumpre a
minimização de dados sensíveis na origem.
"""

from pathlib import Path

import pandas as pd

# Colunas usadas pelo projeto. Dicionário de dados: Open DATASUS (SIVEP-Gripe).
COLUMNS = [
    "DT_NOTIFIC",  # data da notificação
    "DT_SIN_PRI",  # data dos primeiros sintomas
    "SG_UF_NOT",  # UF de notificação
    "HOSPITAL",  # internado? 1=sim 2=não 9=ignorado
    "UTI",  # internado em UTI? 1=sim 2=não 9=ignorado
    "EVOLUCAO",  # 1=cura 2=óbito 3=óbito por outras causas 9=ignorado
    "DT_EVOLUCA",  # data do desfecho
    "VACINA_COV",  # recebeu vacina COVID-19? 1=sim 2=não 9=ignorado
]

DATE_COLUMNS = ["DT_NOTIFIC", "DT_SIN_PRI", "DT_EVOLUCA"]
CATEGORY_COLUMNS = ["HOSPITAL", "UTI", "EVOLUCAO", "VACINA_COV"]
VALID_CODES = {1, 2, 3, 9}


def _parse_dates(series: pd.Series) -> pd.Series:
    """O CSV atual traz datas ISO (2025-07-23T00:00:00.000Z); aceita também dd/mm/aaaa."""
    iso = pd.to_datetime(series, format="ISO8601", errors="coerce", utc=True).dt.tz_localize(None)
    br = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(br)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica os tratamentos de qualidade sobre um DataFrame bruto."""
    df = raw.copy()

    for col in DATE_COLUMNS:
        df[col] = _parse_dates(df[col])

    # Sem data de notificação o caso não entra em nenhuma série temporal.
    df = df.dropna(subset=["DT_NOTIFIC"])

    # Datas no futuro são erro de preenchimento.
    df = df[df["DT_NOTIFIC"] <= pd.Timestamp.today().normalize()]

    # Códigos fora do domínio (ou ausentes) viram 9 = ignorado.
    for col in CATEGORY_COLUMNS:
        codes = pd.to_numeric(df[col], errors="coerce")
        df[col] = codes.where(codes.isin(VALID_CODES), 9).astype("int8")

    # Desfecho antes da notificação é inconsistente: descarta a data, mantém o caso.
    inconsistent = df["DT_EVOLUCA"] < df["DT_NOTIFIC"]
    df.loc[inconsistent, "DT_EVOLUCA"] = pd.NaT

    return df.reset_index(drop=True)


def load_srag_csv(*paths: str | Path) -> pd.DataFrame:
    """Lê um ou mais CSVs do DATASUS (separador ';'), só com as colunas úteis."""
    frames = [
        pd.read_csv(p, sep=";", usecols=COLUMNS, dtype=str, encoding="latin-1", low_memory=False)
        for p in paths
    ]
    return clean(pd.concat(frames, ignore_index=True))
