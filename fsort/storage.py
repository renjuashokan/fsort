from __future__ import annotations

import json
import os
import pickle
import tempfile
from pathlib import Path
from typing import Any

from .models import MediaRecord, Person


class RegistryStore:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.people_path = cache_dir / "people.json"
        self.index_path = cache_dir / "file_index.json"
        self.embeddings_path = cache_dir / "embeddings.pkl"
        self.clusters_path = cache_dir / "clusters.json"

    def load_people(self) -> list[Person]:
        values = self._load_json(self.people_path, [])
        return [Person.from_dict(value) for value in values]

    def load_embeddings(self) -> dict[str, MediaRecord]:
        if not self.embeddings_path.exists():
            return {}
        with self.embeddings_path.open("rb") as handle:
            values = pickle.load(handle)
        if not isinstance(values, dict):
            raise ValueError(f"Invalid embeddings cache: {self.embeddings_path}")
        return {path: MediaRecord.from_dict(value) for path, value in values.items()}

    def load_index(self) -> dict[str, dict[str, Any]]:
        value = self._load_json(self.index_path, {})
        if not isinstance(value, dict):
            raise ValueError(f"Invalid file index: {self.index_path}")
        return value

    def save(
        self,
        people: list[Person],
        records: dict[str, MediaRecord],
        index: dict[str, dict[str, Any]],
        clusters: dict[str, Any] | None = None,
    ) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_json(self.people_path, [person.to_dict() for person in people])
        self._atomic_pickle(
            self.embeddings_path,
            {path: record.to_dict() for path, record in records.items()},
        )
        self._atomic_json(self.index_path, index)
        self._atomic_json(self.clusters_path, clusters or {})

    @staticmethod
    def _load_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _atomic_json(path: Path, value: Any) -> None:
        payload = json.dumps(value, indent=2, ensure_ascii=True) + "\n"
        RegistryStore._atomic_bytes(path, payload.encode("utf-8"))

    @staticmethod
    def _atomic_pickle(path: Path, value: Any) -> None:
        RegistryStore._atomic_bytes(
            path, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        )

    @staticmethod
    def _atomic_bytes(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
