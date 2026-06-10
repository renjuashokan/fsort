from __future__ import annotations

import os
import shutil
from pathlib import Path

from .models import MediaRecord, Person
from .registry import validate_display_name


def build_index(
    records: dict[str, MediaRecord],
    people: list[Person],
    input_root: Path,
    output_root: Path,
) -> dict[str, dict[str, object]]:
    names = {
        person.id: validate_display_name(person.display_name) for person in people
    }
    index: dict[str, dict[str, object]] = {}
    for source_value, record in records.items():
        source = Path(source_value)
        person_ids = sorted(
            {
                face.person_id
                for face in record.faces
                if face.person_id is not None and face.person_id in names
            }
        )
        has_unknown = any(face.person_id is None for face in record.faces)
        if len(person_ids) == 1 and not has_unknown:
            folder = names[person_ids[0]]
        elif len(record.faces) > 1:
            folder = "MultipleFaces"
        else:
            folder = "Unknown"
        try:
            relative = source.relative_to(input_root)
        except ValueError:
            relative = Path(source.name)
        destination = output_root / folder / relative
        index[source_value] = {
            "hash": record.hash,
            "persons": person_ids,
            "destination": str(destination),
        }
    return index


def sync_output(
    old_index: dict[str, dict[str, object]],
    new_index: dict[str, dict[str, object]],
    output_root: Path,
    copy_mode: bool,
) -> tuple[int, int]:
    output_root = output_root.resolve()
    desired = {str(value["destination"]) for value in new_index.values()}
    removed = 0
    for value in old_index.values():
        destination_value = value.get("destination")
        if not destination_value or destination_value in desired:
            continue
        destination = Path(str(destination_value))
        if _inside(destination, output_root) and destination.is_file():
            destination.unlink()
            removed += 1

    written = 0
    for source_value, value in new_index.items():
        source = Path(source_value)
        destination = Path(str(value["destination"]))
        if not source.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            source_stat = source.stat()
            destination_stat = destination.stat()
            if (
                source_stat.st_size == destination_stat.st_size
                and source_stat.st_mtime_ns == destination_stat.st_mtime_ns
            ):
                continue
            destination.unlink()
        if copy_mode:
            shutil.copy2(source, destination)
        else:
            try:
                os.link(source, destination)
            except OSError:
                shutil.copy2(source, destination)
        written += 1
    _remove_empty_directories(output_root)
    return written, removed


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _remove_empty_directories(root: Path) -> None:
    if not root.exists():
        return
    directories = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass
