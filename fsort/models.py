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
    prototypes: list[list[float]] = field(default_factory=list)

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
            prototypes=list(value.get("prototypes", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "created": self.created,
            "embedding_count": self.embedding_count,
            "centroid": self.centroid,
            "prototypes": self.prototypes,
        }


@dataclass(slots=True)
class FaceRecord:
    embedding: list[float]
    person_id: str | None = None
    frame: int | None = None
    bbox_x: int | None = None
    bbox_y: int | None = None
    bbox_w: int | None = None
    bbox_h: int | None = None
    confidence: float | None = None
    quality_score: float | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FaceRecord":
        return cls(
            embedding=list(value["embedding"]),
            person_id=value.get("person_id"),
            frame=value.get("frame"),
            bbox_x=value.get("bbox_x"),
            bbox_y=value.get("bbox_y"),
            bbox_w=value.get("bbox_w"),
            bbox_h=value.get("bbox_h"),
            confidence=value.get("confidence"),
            quality_score=value.get("quality_score"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "embedding": self.embedding,
            "person_id": self.person_id,
        }
        if self.frame is not None:
            result["frame"] = self.frame
        if self.bbox_x is not None:
            result["bbox_x"] = self.bbox_x
        if self.bbox_y is not None:
            result["bbox_y"] = self.bbox_y
        if self.bbox_w is not None:
            result["bbox_w"] = self.bbox_w
        if self.bbox_h is not None:
            result["bbox_h"] = self.bbox_h
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.quality_score is not None:
            result["quality_score"] = self.quality_score
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
