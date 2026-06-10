from pathlib import Path

import numpy as np
import pytest

from fsort.config import Config
from fsort.models import FaceRecord, MediaRecord, Person
from fsort.registry import (
    assign_to_existing,
    cluster_unknowns,
    merge_people,
    recompute_centroids,
    split_person,
    validate_display_name,
)
from fsort.storage import RegistryStore


def record(*embeddings: list[float]) -> MediaRecord:
    return MediaRecord(
        hash="hash",
        mtime_ns=1,
        size=1,
        faces=[FaceRecord(embedding=value) for value in embeddings],
    )


def test_cluster_match_merge_split_and_persist(tmp_path: Path) -> None:
    records = {
        "a.jpg": record([1.0, 0.0], [0.99, 0.01]),
        "b.jpg": record([0.0, 1.0], [0.01, 0.99]),
    }
    people: list[Person] = []
    config = Config(min_samples=2, dbscan_eps=0.1)

    created, _ = cluster_unknowns(records, people, config)
    recompute_centroids(people, records)

    assert created == 2
    assert len(people) == 2
    assert sorted(person.embedding_count for person in people) == [2, 2]

    first = min(people, key=lambda person: person.centroid[1])
    face = FaceRecord(embedding=[0.98, 0.02])
    assert assign_to_existing([face], people, threshold=0.1) == 1
    assert face.person_id == first.id

    target, source = people
    merge_people(people, records, target.id, source.id)
    assert len(people) == 1
    assert people[0].embedding_count == 4

    released = split_person(people, records, target.id)
    assert released == 4
    assert people == []

    store = RegistryStore(tmp_path / "cache")
    store.save(people, records, {"a.jpg": {"persons": []}})
    loaded = store.load_embeddings()
    assert set(loaded) == set(records)
    assert all(face.person_id is None for item in loaded.values() for face in item.faces)


def test_weighted_centroid_is_normalized() -> None:
    person = Person.create("Person_001")
    records = {
        "a": record([1.0, 0.0]),
        "b": record([1.0, 1.0]),
    }
    for item in records.values():
        item.faces[0].person_id = person.id

    recompute_centroids([person], records)

    assert person.embedding_count == 2
    assert np.linalg.norm(person.centroid) == pytest.approx(1.0)


@pytest.mark.parametrize("name", ["../Mom", "CON", "Unknown", "name."])
def test_unsafe_display_names_are_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        validate_display_name(name)
