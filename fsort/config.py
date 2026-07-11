from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class Config:
    video_interval: float = 2.0
    # When True, extract only a single frame from each video (at video_interval
    # seconds) instead of sampling every video_interval seconds throughout.
    # Use this to speed up extraction when full-video scanning is not needed.
    video_single_frame: bool = False
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
    # Mount point of the HDD on the current machine.
    # Paths in the DB are stored relative to this root so the
    # same database works on Windows and Linux.
    # Leave empty to use absolute paths (default / single-machine setup).
    hdd_root: str = ""
    # CLIP semantic search settings.
    # Set clip_enabled=true to index whole-image CLIP embeddings during extraction
    # and enable keyword search (e.g. 'sunglass', 'beach') in the web UI.
    clip_enabled: bool = False
    clip_model: str = "ViT-B-32__openai"

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        # If the specified config file doesn't exist (covers both the bare
        # "config.yaml" default and explicit paths like /opt/fsort/config.yaml
        # that haven't been created yet), fall back to ~/.fsort/config.yaml.
        if path is not None and not path.exists():
            home_config = Path.home() / ".fsort" / "config.yaml"
            if home_config.exists():
                path = home_config
            else:
                try:
                    home_config.parent.mkdir(parents=True, exist_ok=True)
                    default_data = asdict(cls())
                    with home_config.open("w", encoding="utf-8") as handle:
                        yaml.safe_dump(default_data, handle, default_flow_style=False)
                    path = home_config
                except Exception:
                    return cls()

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
        # Environment variable overrides config file (useful for systemd service)
        env_hdd_root = os.environ.get("FSORT_HDD_ROOT", "").strip()
        if env_hdd_root:
            config.hdd_root = env_hdd_root
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
            raise ValueError(
                f"Configuration values must be positive: {', '.join(invalid)}"
            )
