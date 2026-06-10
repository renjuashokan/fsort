from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class Config:
    video_interval: float = 2.0
    match_threshold: float = 0.42
    dbscan_eps: float = 0.45
    min_samples: int = 2
    min_face_size: int = 80
    copy_mode: bool = True
    cache_enabled: bool = True
    checkpoint_interval: int = 250
    gpu: bool = False
    model_name: str = "buffalo_l"
    server_port: int = 9876
    server_host: str = "127.0.0.1"

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        if path is None or not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as handle:
            values = yaml.safe_load(handle) or {}
        if not isinstance(values, dict):
            raise ValueError(f"{path} must contain a YAML mapping")
        known = set(asdict(cls()))
        unknown = sorted(set(values) - known)
        if unknown:
            raise ValueError(f"Unknown configuration keys: {', '.join(unknown)}")
        config = cls(**values)
        config.validate()
        return config

    def validate(self) -> None:
        positive: dict[str, Any] = {
            "video_interval": self.video_interval,
            "match_threshold": self.match_threshold,
            "dbscan_eps": self.dbscan_eps,
            "min_samples": self.min_samples,
            "min_face_size": self.min_face_size,
            "checkpoint_interval": self.checkpoint_interval,
            "server_port": self.server_port,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ValueError(f"Configuration values must be positive: {', '.join(invalid)}")
