"""Banco DuckDB com os dados já limpos (evita reprocessar os CSVs a cada execução)."""

from pathlib import Path

import duckdb
import pandas as pd

from srag_agent.data.cleaning import load_srag_csv

TABLE = "srag"
DEFAULT_DB = Path("data/processed/srag.duckdb")


def build_database(csv_paths: list[Path], db_path: Path = DEFAULT_DB) -> int:
    """Limpa os CSVs e grava a tabela `srag`. Retorna o número de linhas gravadas."""
    df = load_srag_csv(*csv_paths)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        con.execute(f"CREATE OR REPLACE TABLE {TABLE} AS SELECT * FROM df")
    return len(df)


def read_cases(db_path: Path = DEFAULT_DB) -> pd.DataFrame:
    """Lê a tabela limpa em modo somente leitura."""
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(f"SELECT * FROM {TABLE}").df()
