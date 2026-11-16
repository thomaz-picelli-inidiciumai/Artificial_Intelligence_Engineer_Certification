"""Constrói o banco DuckDB a partir dos CSVs em data/raw/: python -m srag_agent.data"""

import sys
from pathlib import Path

from srag_agent.data.store import DEFAULT_DB, build_database

RAW_DIR = Path("data/raw")


def main() -> int:
    csvs = sorted(RAW_DIR.glob("*.csv"))
    if not csvs:
        print(f"Nenhum CSV encontrado em {RAW_DIR}/. Baixe os arquivos do Open DATASUS.", file=sys.stderr)
        return 1
    rows = build_database(csvs, DEFAULT_DB)
    print(f"{rows} linhas gravadas em {DEFAULT_DB} a partir de {len(csvs)} arquivo(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
