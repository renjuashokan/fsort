from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config
from .organizer import build_index, sync_output
from .pipeline import run_sort
from .registry import (
    merge_people,
    recompute_centroids,
    resolve_person,
    split_person,
    validate_display_name,
)
from .storage import RegistryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="face-sort",
        description="Incrementally organize local media by recognized people.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sort_parser = subparsers.add_parser("sort", help="scan and organize media")
    sort_parser.add_argument("input", type=Path)
    _add_paths(sort_parser, include_input=False)
    sort_parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    sort_parser.add_argument("--checkpoint-interval", type=int)
    sort_parser.add_argument("--no-progress", action="store_true")

    for name, help_text in (
        ("list", "list registered people"),
        ("stats", "show registry statistics"),
        ("verify", "check registry consistency"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        _add_paths(command)

    rename = subparsers.add_parser("rename", help="rename a person")
    rename.add_argument("person")
    rename.add_argument("name")
    _add_paths(rename)

    merge = subparsers.add_parser("merge", help="merge source into target")
    merge.add_argument("target")
    merge.add_argument("source")
    _add_paths(merge)

    split = subparsers.add_parser(
        "split",
        help="release a person's faces for reclustering on the next sort",
    )
    split.add_argument("person")
    _add_paths(split)
    return parser


def _add_paths(parser: argparse.ArgumentParser, include_input: bool = True) -> None:
    if include_input:
        parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--cache", type=Path, default=Path("cache"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "sort":
            return _sort(args)
        if args.command == "list":
            return _list(args)
        if args.command == "stats":
            return _stats(args)
        if args.command == "verify":
            return _verify(args)
        return _maintain(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _sort(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    if args.checkpoint_interval is not None:
        config.checkpoint_interval = args.checkpoint_interval
        config.validate()
    result = run_sort(
        input_root=args.input,
        output_root=args.output,
        cache_root=args.cache,
        config=config,
        show_progress=not args.no_progress,
    )
    print(
        f"scanned={result.scanned} processed={result.processed} "
        f"skipped={result.skipped} failed={result.failed} deleted={result.deleted}"
    )
    print(
        f"assigned={result.assigned} people_created={result.people_created} "
        f"written={result.files_written} removed={result.files_removed}"
    )
    return 0


def _list(args: argparse.Namespace) -> int:
    people = RegistryStore(args.cache.resolve()).load_people()
    if not people:
        print("No registered people.")
        return 0
    for person in sorted(people, key=lambda item: item.display_name.casefold()):
        print(f"{person.id}  {person.display_name}  ({person.embedding_count} embeddings)")
    return 0


def _stats(args: argparse.Namespace) -> int:
    store = RegistryStore(args.cache.resolve())
    people = store.load_people()
    records = store.load_embeddings()
    faces = [face for record in records.values() for face in record.faces]
    print(f"people: {len(people)}")
    print(f"media files: {len(records)}")
    print(f"faces: {len(faces)}")
    print(f"assigned faces: {sum(face.person_id is not None for face in faces)}")
    print(f"unknown faces: {sum(face.person_id is None for face in faces)}")
    return 0


def _verify(args: argparse.Namespace) -> int:
    store = RegistryStore(args.cache.resolve())
    people = store.load_people()
    records = store.load_embeddings()
    index = store.load_index()
    errors: list[str] = []
    ids = [person.id for person in people]
    if len(ids) != len(set(ids)):
        errors.append("duplicate person IDs")
    names = [person.display_name.casefold() for person in people]
    if len(names) != len(set(names)):
        errors.append("duplicate display names")
    valid_ids = set(ids)
    counts = {person_id: 0 for person_id in ids}
    for path, record in records.items():
        for face in record.faces:
            if face.person_id and face.person_id not in valid_ids:
                errors.append(f"{path}: dangling person ID {face.person_id}")
            elif face.person_id:
                counts[face.person_id] += 1
    for person in people:
        if person.embedding_count != counts[person.id]:
            errors.append(
                f"{person.id}: count is {person.embedding_count}, expected {counts[person.id]}"
            )
        try:
            validate_display_name(person.display_name)
        except ValueError as error:
            errors.append(f"{person.id}: {error}")
    missing_index = set(records) - set(index)
    if missing_index:
        errors.append(f"{len(missing_index)} cached files missing from file index")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        f"Registry OK: {len(people)} people, {len(records)} media files, "
        f"{sum(counts.values())} assigned faces."
    )
    return 0


def _maintain(args: argparse.Namespace) -> int:
    store = RegistryStore(args.cache.resolve())
    people = store.load_people()
    records = store.load_embeddings()
    old_index = store.load_index()

    if args.command == "rename":
        person = resolve_person(people, args.person)
        name = validate_display_name(args.name)
        if any(
            other.id != person.id
            and other.display_name.casefold() == name.casefold()
            for other in people
        ):
            raise ValueError(f"Display name already exists: {name}")
        person.display_name = name
        message = f"Renamed {person.id} to {name}."
    elif args.command == "merge":
        person = merge_people(people, records, args.target, args.source)
        message = f"Merged into {person.id} ({person.display_name})."
    else:
        released = split_person(people, records, args.person)
        message = f"Released {released} faces for reclustering."

    recompute_centroids(people, records)
    index = build_index(
        records,
        people,
        _input_root(args.input, records),
        args.output.resolve(),
    )
    sync_output(old_index, index, args.output.resolve(), copy_mode=True)
    store.save(people, records, index)
    print(message)
    return 0


def _input_root(
    configured: Path | None, records: dict[str, object]
) -> Path:
    if configured is not None:
        return configured.resolve()
    paths = [Path(path).resolve() for path in records]
    if not paths:
        return Path.cwd()
    if len(paths) == 1:
        return paths[0].parent
    common = Path(*paths[0].parts)
    for path in paths[1:]:
        while common != common.parent and common not in path.parents:
            common = common.parent
    return common


if __name__ == "__main__":
    raise SystemExit(main())
