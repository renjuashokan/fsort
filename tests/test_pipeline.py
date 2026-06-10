from pathlib import Path

import pytest

from fsort.config import Config
from fsort.models import FaceRecord
from fsort.pipeline import run_sort
from fsort.storage import RegistryStore


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


class InterruptingExtractor(FakeExtractor):
    def __init__(
        self, embeddings: dict[str, list[list[float]]], interrupt_on: str
    ) -> None:
        super().__init__(embeddings)
        self.interrupt_on = interrupt_on

    def extract(self, path: Path) -> list[FaceRecord]:
        if path.name == self.interrupt_on:
            raise KeyboardInterrupt
        return super().extract(path)


def test_incremental_sort_keeps_stable_person(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    output = tmp_path / "output"
    cache = tmp_path / "cache"
    source.mkdir()
    (source / "a.jpg").write_bytes(b"a")
    (source / "b.jpg").write_bytes(b"b")
    config = Config(min_samples=2, dbscan_eps=0.1, match_threshold=0.1)
    extractor = FakeExtractor(
        {
            "a.jpg": [[1.0, 0.0]],
            "b.jpg": [[0.99, 0.01]],
            "c.jpg": [[0.98, 0.02]],
        }
    )

    first = run_sort(
        source, output, cache, config, extractor=extractor, show_progress=False
    )
    people = RegistryStore(cache).load_people()
    person_id = people[0].id

    assert first.processed == 2
    assert first.people_created == 1
    assert (output / "Person_001" / "a.jpg").exists()

    (source / "c.jpg").write_bytes(b"c")
    second = run_sort(
        source, output, cache, config, extractor=extractor, show_progress=False
    )
    people = RegistryStore(cache).load_people()

    assert second.skipped == 2
    assert second.processed == 1
    assert second.assigned == 1
    assert people[0].id == person_id
    assert people[0].embedding_count == 3
    assert extractor.calls == ["a.jpg", "b.jpg", "c.jpg"]
    assert (output / "Person_001" / "c.jpg").exists()


def test_interrupted_sort_checkpoints_and_resumes(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    output = tmp_path / "output"
    cache = tmp_path / "cache"
    source.mkdir()
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        (source / name).write_bytes(name.encode())
    embeddings = {
        "a.jpg": [[1.0, 0.0]],
        "b.jpg": [[0.99, 0.01]],
        "c.jpg": [[0.98, 0.02]],
    }
    config = Config(
        checkpoint_interval=2,
        min_samples=2,
        dbscan_eps=0.1,
        match_threshold=0.1,
    )
    interrupted = InterruptingExtractor(embeddings, interrupt_on="c.jpg")

    with pytest.raises(KeyboardInterrupt):
        run_sort(
            source,
            output,
            cache,
            config,
            extractor=interrupted,
            show_progress=False,
        )

    records = RegistryStore(cache).load_embeddings()
    assert set(Path(path).name for path in records) == {"a.jpg", "b.jpg"}
    assert (output / "Unknown" / "a.jpg").exists()
    assert (output / "Unknown" / "b.jpg").exists()

    resumed = FakeExtractor(embeddings)
    result = run_sort(
        source, output, cache, config, extractor=resumed, show_progress=False
    )

    assert result.skipped == 2
    assert result.processed == 1
    assert resumed.calls == ["c.jpg"]
    assert (output / "Person_001" / "a.jpg").exists()
    assert (output / "Person_001" / "b.jpg").exists()
    assert (output / "Person_001" / "c.jpg").exists()
    assert not (output / "Unknown").exists()
