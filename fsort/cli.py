from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config
from .service import FsortService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="face-sort",
        description="Incrementally organize local media by recognized people.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Legacy / convenience subcommand
    sort_parser = subparsers.add_parser("sort", help="scan and organize media")
    sort_parser.add_argument("input", type=Path)
    _add_paths(sort_parser, include_input=False)
    sort_parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    sort_parser.add_argument("--checkpoint-interval", type=int)
    sort_parser.add_argument("--no-progress", action="store_true")

    # Priority 2: Extract subcommand
    extract_parser = subparsers.add_parser("extract", help="scan and extract face embeddings")
    extract_parser.add_argument("input", type=Path)
    _add_paths(extract_parser, include_input=False)
    extract_parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    extract_parser.add_argument("--checkpoint-interval", type=int)
    extract_parser.add_argument("--no-progress", action="store_true")

    # Priority 2: Organize subcommand
    organize_parser = subparsers.add_parser("organize", help="cluster faces and synchronize output folders")
    _add_paths(organize_parser)
    organize_parser.add_argument("--config", type=Path, default=Path("config.yaml"))

    # Priority 3: Serve subcommand
    serve_parser = subparsers.add_parser("serve", help="start the embedded HTTP API server")
    serve_parser.add_argument("--host", help="host address to bind")
    serve_parser.add_argument("--port", type=int, help="port to listen on")
    _add_paths(serve_parser, include_input=False)
    serve_parser.add_argument("--config", type=Path, default=Path("config.yaml"))

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

    thumbnails = subparsers.add_parser(
        "thumbnails",
        help="generate/regenerate thumbnails for registered people",
    )
    _add_paths(thumbnails)

    remap = subparsers.add_parser(
        "remap-paths",
        help="migrate existing DB paths from one HDD mount point to another (one-time fix for Windows→Linux moves)",
    )
    remap.add_argument(
        "--from-root",
        required=True,
        help="old HDD mount point (e.g. 'D:\\' on Windows or '/old/mount')",
    )
    remap.add_argument(
        "--to-root",
        required=True,
        help="new HDD mount point on this machine (e.g. '/mnt/sda1')",
    )
    remap.add_argument("--cache", type=Path, default=Path("cache"))
    remap.add_argument("--dry-run", action="store_true", help="show what would change without modifying the DB")
    return parser


def _add_paths(parser: argparse.ArgumentParser, include_input: bool = True) -> None:
    if include_input:
        parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--cache", type=Path, default=Path("cache"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "serve":
            return _serve(args)
        if args.command == "remap-paths":
            return _remap_paths(args)

        config_path = getattr(args, "config", Path("config.yaml"))
        config = Config.load(config_path)
        if hasattr(args, "checkpoint_interval") and args.checkpoint_interval is not None:
            config.checkpoint_interval = args.checkpoint_interval
            config.validate()

        service = FsortService(
            cache_root=args.cache,
            output_root=args.output,
            config=config,
        )

        if args.command == "extract":
            res = service.extract(args.input, show_progress=not args.no_progress)
            print(
                f"scanned={res['scanned']} processed={res['processed']} "
                f"skipped={res['skipped']} failed={res['failed']} deleted={res['deleted']}"
            )
            return 0
        elif args.command == "organize":
            in_root = args.input if hasattr(args, "input") else None
            res = service.organize(in_root)
            print(
                f"assigned={res['assigned']} people_created={res['people_created']} "
                f"written={res['files_written']} removed={res['files_removed']}"
            )
            return 0
        elif args.command == "sort":
            res_e = service.extract(args.input, show_progress=not args.no_progress)
            print(
                f"extract: scanned={res_e['scanned']} processed={res_e['processed']} "
                f"skipped={res_e['skipped']} failed={res_e['failed']} deleted={res_e['deleted']}"
            )
            res_o = service.organize(args.input)
            print(
                f"organize: assigned={res_o['assigned']} people_created={res_o['people_created']} "
                f"written={res_o['files_written']} removed={res_o['files_removed']}"
            )
            return 0
        elif args.command == "list":
            people = service.list_people()
            if not people:
                print("No registered people.")
                return 0
            for person in sorted(people, key=lambda item: item.display_name.casefold()):
                print(f"{person.id}  {person.display_name}  ({person.embedding_count} embeddings)")
            return 0
        elif args.command == "stats":
            stats = service.stats()
            print(f"people: {stats['people']}")
            print(f"media files: {stats['media_files']}")
            print(f"faces: {stats['faces']}")
            print(f"assigned faces: {stats['assigned_faces']}")
            print(f"unknown faces: {stats['unknown_faces']}")
            return 0
        elif args.command == "verify":
            errors = service.verify()
            if errors:
                for error in errors:
                    print(f"ERROR: {error}")
                return 1
            stats = service.stats()
            print(
                f"Registry OK: {stats['people']} people, {stats['media_files']} media files, "
                f"{stats['assigned_faces']} assigned faces."
            )
            return 0
        elif args.command == "rename":
            in_root = args.input if hasattr(args, "input") else None
            msg = service.rename(args.person, args.name, in_root)
            print(msg)
            return 0
        elif args.command == "merge":
            in_root = args.input if hasattr(args, "input") else None
            msg = service.merge(args.target, args.source, in_root)
            print(msg)
            return 0
        elif args.command == "split":
            in_root = args.input if hasattr(args, "input") else None
            msg = service.split(args.person, in_root)
            print(msg)
            return 0
        elif args.command == "thumbnails":
            count = service.generate_thumbnails()
            print(f"Generated/updated thumbnails for {count} people.")
            return 0
        elif args.command == "remap-paths":
            return _remap_paths(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import app

    config = Config.load(args.config)
    host = args.host if args.host is not None else config.server_host
    port = args.port if args.port is not None else config.server_port

    app.state.cache_root = args.cache.resolve()
    app.state.output_root = args.output.resolve()
    app.state.config_path = args.config
    uvicorn.run(app, host=host, port=port)
    return 0


def _remap_paths(args: argparse.Namespace) -> int:
    """Rewrite all stored paths in the DB from one HDD root to another.

    Useful when moving the HDD between Windows and Linux (or changing mount
    points) so you don't need to re-run extraction.

    Example:
        face-sort remap-paths \\
            --from-root "D:\\" \\
            --to-root "/mnt/sda1" \\
            --cache /mnt/sda1/cache
    """
    import sqlite3

    cache_dir = args.cache.resolve()
    db_path = cache_dir / "faces.db"
    if not db_path.exists():
        print(f"error: database not found at {db_path}", file=sys.stderr)
        return 2

    from_root = args.from_root.replace("\\", "/").rstrip("/")
    to_root = args.to_root.replace("\\", "/").rstrip("/")
    dry_run = args.dry_run

    def _remap(value: str | None) -> str | None:
        if not value:
            return value
        normalized = value.replace("\\", "/")
        if normalized.lower().startswith(from_root.lower() + "/") or normalized.lower() == from_root.lower():
            remainder = normalized[len(from_root):].lstrip("/")
            return to_root + "/" + remainder
        return value  # not under from_root, leave unchanged

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT id, path, destination FROM media").fetchall()
        updated = 0
        for row in rows:
            new_path = _remap(row["path"])
            new_dest = _remap(row["destination"])
            if new_path != row["path"] or new_dest != row["destination"]:
                updated += 1
                if dry_run:
                    print(f"  path: {row['path']!r}")
                    print(f"     -> {new_path!r}")
                    if new_dest != row["destination"]:
                        print(f"  dest: {row['destination']!r}")
                        print(f"     -> {new_dest!r}")
                else:
                    conn.execute(
                        "UPDATE media SET path = ?, destination = ? WHERE id = ?",
                        (new_path, new_dest, row["id"]),
                    )
        if dry_run:
            print(f"\nDry run: {updated} of {len(rows)} rows would be updated.")
        else:
            conn.commit()
            print(f"Remapped {updated} of {len(rows)} media rows.")
            print(f"  {from_root!r}  →  {to_root!r}")
    finally:
        conn.close()
    return 0


def _input_root(configured: Path | None, records: dict[str, object]) -> Path:
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
