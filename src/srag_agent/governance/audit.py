"""Log de auditoria append-only em JSONL, com encadeamento por hash.

Cada registro guarda o hash do anterior; alterar ou remover uma linha quebra a cadeia,
e `verify()` detecta isso. Registra decisões do agente, chamadas de tools e bloqueios.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DIR = Path("audit_logs")
GENESIS = "0" * 64


def _digest(prev_hash: str, record: dict) -> str:
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256((prev_hash + payload).encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, directory: Path = DEFAULT_DIR, run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex[:12]
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"run-{self.run_id}.jsonl"
        self._last_hash = GENESIS

    def log(self, event: str, **data) -> dict:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "event": event,
            "data": data,
            "prev_hash": self._last_hash,
        }
        record["hash"] = _digest(self._last_hash, {k: v for k, v in record.items() if k != "hash"})
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._last_hash = record["hash"]
        return record

    @staticmethod
    def verify(path: Path) -> bool:
        """True se a cadeia de hashes do arquivo está íntegra."""
        prev = GENESIS
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            stored = record.pop("hash")
            if record["prev_hash"] != prev or _digest(prev, record) != stored:
                return False
            prev = stored
        return True
