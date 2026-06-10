from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import numpy as np


def normalized(values: list[float] | np.ndarray) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float32)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


@dataclass(slots=True)
class Person:
    id: str
    display_name: str
    created: str
    embedding_count: int = 0
    centroid: list[float] = field(default_factory=list)

    @classmethod
    def create(cls, display_name: str) -> "Person":
        return cls(
            id=uuid4().hex[:8],
            display_name=display_name,
            created=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Person":
        return cls(
            id=value["id"],
            display_name=value["display_name"],
            created=value.get("created", ""),
            embedding_count=int(value.get("embedding_count", 0)),
            centroid=list(value.get("centroid", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "created": self.created,
            "embedding_count": self.embedding_count,
            "centroid": self.centroid,
        }


@dataclass(slots=True)
class FaceRecord:
    embedding: list[float]
    person_id: str | None = None
    frame: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FaceRecord":
        return cls(
            embedding=list(value["embedding"]),
            person_id=value.get("person_id"),
            frame=value.get("frame"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "embedding": self.embedding,
            "person_id": self.person_id,
        }
        if self.frame is not None:
            result["frame"] = self.frame
        return result


@dataclass(slots=True)
class MediaRecord:
    hash: str
    mtime_ns: int
    size: int
    faces: list[FaceRecord]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MediaRecord":
        return cls(
            hash=value["hash"],
            mtime_ns=int(value["mtime_ns"]),
            size=int(value["size"]),
            faces=[FaceRecord.from_dict(face) for face in value.get("faces", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.hash,
            "mtime_ns": self.mtime_ns,
            "size": self.size,
            "face_count": len(self.faces),
            "faces": [face.to_dict() for face in self.faces],
        }
