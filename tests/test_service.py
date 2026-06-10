from pathlib import Path

import pytest

from fsort.config import Config
from fsort.models import FaceRecord
from fsort.service import FsortService


class FakeExtractor:
    def __init__(self, embeddings: dict[str, list[list[float]]]):
        self.embeddings = embeddings
        self.calls: list[str] = []

    def extract(self, path: Path) -> list[FaceRecord]:
        self.calls.append(path.name)
        return [
            FaceRecord(embedding=embedding)
            for embedding in self.embeddings[path.name]
        ]


def test_service_extract_and_organize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "photos"
    output = tmp_path / "output"
    cache = tmp_path / "cache"
    source.mkdir()
    (source / "a.jpg").write_bytes(b"a")
    (source / "b.jpg").write_bytes(b"b")

    config = Config(min_samples=2, dbscan_eps=0.1, match_threshold=0.1)
    service = FsortService(cache, output, config)

    # Monkeypatch FaceExtractor inside service/extractor to use our FakeExtractor
    fake_embeddings = {
        "a.jpg": [[1.0, 0.0]],
        "b.jpg": [[0.99, 0.01]],
        "c.jpg": [[0.98, 0.02]],
    }
    fake_extractor = FakeExtractor(fake_embeddings)

    monkeypatch.setattr(
        "fsort.extractor.FaceExtractor",
        lambda *args, **kwargs: fake_extractor,
    )

    # 1. Run Extract
    res_extract = service.extract(source, show_progress=False)
    assert res_extract["scanned"] == 2
    assert res_extract["processed"] == 2
    assert res_extract["skipped"] == 0

    # 2. Run Organize
    res_organize = service.organize(source)
    assert res_organize["assigned"] == 0
    assert res_organize["people_created"] == 1
    assert res_organize["files_written"] == 2

    # Verify folders created
    assert (output / "Person_001" / "a.jpg").exists()
    assert (output / "Person_001" / "b.jpg").exists()

    # Add a new file and process incrementally
    (source / "c.jpg").write_bytes(b"c")

    # Run Extract again
    res_extract_2 = service.extract(source, show_progress=False)
    assert res_extract_2["scanned"] == 3
    assert res_extract_2["processed"] == 1
    assert res_extract_2["skipped"] == 2

    # Run Organize again
    res_organize_2 = service.organize(source)
    assert res_organize_2["assigned"] == 1
    assert res_organize_2["people_created"] == 0
    assert res_organize_2["files_written"] == 1

    # Verify new file organized into same person folder
    assert (output / "Person_001" / "c.jpg").exists()


def test_config_server_port_and_host(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("server_port: 12345\nserver_host: 0.0.0.0\n", encoding="utf-8")

    config = Config.load(config_file)
    assert config.server_port == 12345
    assert config.server_host == "0.0.0.0"
