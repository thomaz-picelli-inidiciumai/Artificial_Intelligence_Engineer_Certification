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


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica os tratamentos de qualidade sobre um DataFrame bruto."""
    df = raw.copy()

    for col in DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")

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


def load_srag_csv(path: str | Path) -> pd.DataFrame:
    """Lê o CSV do DATASUS (separador ';') carregando apenas as colunas úteis."""
    raw = pd.read_csv(
        path,
        sep=";",
        usecols=COLUMNS,
        dtype=str,
        encoding="latin-1",
        low_memory=False,
    )
    return clean(raw)
