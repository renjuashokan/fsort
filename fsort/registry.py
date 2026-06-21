from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.cluster import DBSCAN

from .config import Config
from .models import FaceRecord, MediaRecord, Person, normalized


def validate_display_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Display name cannot be empty")
    if value in {".", ".."} or any(character in value for character in '<>:"/\\|?*'):
        raise ValueError("Display name contains characters that are unsafe in folder names")
    if value.endswith((" ", ".")):
        raise ValueError("Display name cannot end with a space or period")
    reserved = {"CON", "PRN", "AUX", "NUL", "Unknown", "MultipleFaces"}
    reserved.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10))
    if value.split(".", 1)[0].upper() in {name.upper() for name in reserved}:
        raise ValueError("Display name is reserved for system or organizer use")
    return value


def resolve_person(people: list[Person], value: str) -> Person:
    by_id = [person for person in people if person.id == value]
    if by_id:
        return by_id[0]
    by_name = [
        person for person in people if person.display_name.casefold() == value.casefold()
    ]
    if len(by_name) == 1:
        return by_name[0]
    if len(by_name) > 1:
        raise ValueError(f"Ambiguous person name: {value}")
    raise ValueError(f"Unknown person: {value}")


def next_person_name(people: list[Person]) -> str:
    used = {person.display_name.casefold() for person in people}
    number = 1
    while f"person_{number:03d}".casefold() in used:
        number += 1
    return f"Person_{number:03d}"


def assign_to_existing(
    faces: list[FaceRecord], people: list[Person], threshold: float
) -> int:
    prototypes_list = []
    for person in people:
        vectors = person.prototypes if person.prototypes else ([person.centroid] if person.centroid else [])
        for vec in vectors:
            prototypes_list.append((person.id, normalized(vec)))

    if not prototypes_list:
        return 0

    person_ids = [item[0] for item in prototypes_list]
    prototypes_matrix = np.vstack([item[1] for item in prototypes_list])

    assigned = 0
    for face in faces:
        if face.person_id is not None:
            continue
        embedding = normalized(face.embedding)
        distances = 1.0 - prototypes_matrix @ embedding
        nearest = int(np.argmin(distances))
        if float(distances[nearest]) < threshold:
            face.person_id = person_ids[nearest]
            assigned += 1
    return assigned


def cluster_unknowns(
    records: dict[str, MediaRecord],
    people: list[Person],
    config: Config,
) -> tuple[int, dict[str, list[dict[str, int | str]]]]:
    unknown: list[tuple[str, int, FaceRecord]] = []
    for path, record in records.items():
        for index, face in enumerate(record.faces):
            if face.person_id is None:
                unknown.append((path, index, face))
    if len(unknown) < config.min_samples:
        return 0, {}

    matrix = np.vstack([normalized(item[2].embedding) for item in unknown])
    labels = DBSCAN(
        eps=config.dbscan_eps,
        min_samples=config.min_samples,
        metric="cosine",
    ).fit_predict(matrix)

    created = 0
    clusters: dict[str, list[dict[str, int | str]]] = {}
    for label in sorted(set(labels) - {-1}):
        members = [item for item, assigned_label in zip(unknown, labels) if assigned_label == label]
        person = Person.create(next_person_name(people))
        people.append(person)
        created += 1
        clusters[person.id] = []
        for path, index, face in members:
            face.person_id = person.id
            clusters[person.id].append({"path": path, "face_index": index})
    return created, clusters


def recompute_centroids(
    people: list[Person], records: dict[str, MediaRecord]
) -> None:
    grouped: dict[str, list[np.ndarray]] = defaultdict(list)
    for record in records.values():
        for face in record.faces:
            if face.person_id and face.embedding:
                grouped[face.person_id].append(normalized(face.embedding))

    valid_ids = {person.id for person in people}
    for record in records.values():
        for face in record.faces:
            if face.person_id not in valid_ids:
                face.person_id = None

    for person in people:
        embeddings = grouped.get(person.id, [])
        person.embedding_count = len(embeddings)
        if embeddings:
            person.centroid = normalized(np.mean(embeddings, axis=0)).tolist()
            if len(embeddings) <= 30:
                person.prototypes = [emb.tolist() for emb in embeddings]
            else:
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=30, n_init="auto", random_state=42)
                kmeans.fit(embeddings)
                person.prototypes = kmeans.cluster_centers_.tolist()
        else:
            person.centroid = []
            person.prototypes = []


def merge_people(
    people: list[Person],
    records: dict[str, MediaRecord],
    target_value: str,
    source_value: str,
) -> Person:
    target = resolve_person(people, target_value)
    source = resolve_person(people, source_value)
    if target.id == source.id:
        raise ValueError("Cannot merge a person into itself")
    for record in records.values():
        for face in record.faces:
            if face.person_id == source.id:
                face.person_id = target.id
    people.remove(source)
    recompute_centroids(people, records)
    return target


def split_person(
    people: list[Person], records: dict[str, MediaRecord], value: str
) -> int:
    person = resolve_person(people, value)
    released = 0
    for record in records.values():
        for face in record.faces:
            if face.person_id == person.id:
                face.person_id = None
                released += 1
    people.remove(person)
    recompute_centroids(people, records)
    return released
