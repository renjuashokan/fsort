from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from .config import Config
from .extractor import FaceExtractor, iter_media
from .models import MediaRecord
from .organizer import build_index, sync_output
from .registry import assign_to_existing, cluster_unknowns, recompute_centroids
from .storage import RegistryStore


@dataclass(slots=True)
class SortResult:
    scanned: int = 0
    skipped: int = 0
    processed: int = 0
    failed: int = 0
    deleted: int = 0
    assigned: int = 0
    people_created: int = 0
    files_written: int = 0
    files_removed: int = 0


def run_sort(
    input_root: Path,
    output_root: Path,
    cache_root: Path,
    config: Config,
    extractor: FaceExtractor | None = None,
    show_progress: bool = True,
) -> SortResult:
    input_root = input_root.resolve()
    output_root = output_root.resolve()
    cache_root = cache_root.resolve()
    if not input_root.is_dir():
        raise ValueError(f"Input directory does not exist: {input_root}")
    if input_root == output_root or input_root == cache_root:
        raise ValueError("Input, output, and cache directories must be distinct")

    store = RegistryStore(cache_root)
    people = store.load_people()
    records = store.load_embeddings()
    old_index = store.load_index()
    saved_clusters = store.load_clusters()
    result = SortResult()

    files = list(iter_media(input_root, excluded=[output_root, cache_root]))
    result.scanned = len(files)
    current = {str(path) for path in files}
    stale = set(records) - current
    for path in stale:
        del records[path]
    result.deleted = len(stale)
    if stale:
        recompute_centroids(people, records)

    extractor = extractor or FaceExtractor(config)
    iterator = tqdm(files, desc="Processing media", disable=not show_progress)
    new_faces = []
    checkpoint_index = old_index
    pending_checkpoint = bool(stale)

    def checkpoint() -> None:
        nonlocal checkpoint_index, pending_checkpoint
        if not pending_checkpoint:
            return
        index = build_index(records, people, input_root, output_root)
        # Save extraction work first so an interruption during copying can resume.
        store.save(people, records, index, saved_clusters)
        written, removed = sync_output(
            checkpoint_index, index, output_root, config.copy_mode
        )
        result.files_written += written
        result.files_removed += removed
        checkpoint_index = index
        pending_checkpoint = False
        tqdm.write(f"checkpoint: saved {len(records)} media records")

    try:
        for path in iterator:
            key = str(path)
            stat = path.stat()
            cached = records.get(key)
            if (
                config.cache_enabled
                and cached
                and cached.mtime_ns == stat.st_mtime_ns
                and cached.size == stat.st_size
            ):
                result.skipped += 1
                continue
            try:
                digest = _sha256(path)
                if config.cache_enabled and cached and cached.hash == digest:
                    cached.mtime_ns = stat.st_mtime_ns
                    cached.size = stat.st_size
                    pending_checkpoint = True
                    result.skipped += 1
                    continue
                faces = extractor.extract(path)
            except (OSError, ValueError) as error:
                tqdm.write(f"warning: skipped {path}: {error}")
                result.failed += 1
                continue
            record = MediaRecord(
                hash=digest,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
                faces=faces,
            )
            records[key] = record
            new_faces.extend(faces)
            pending_checkpoint = True
            result.processed += 1
            if result.processed % config.checkpoint_interval == 0:
                checkpoint()
    except KeyboardInterrupt:
        checkpoint()
        tqdm.write("Interrupted; completed extraction work was checkpointed.")
        raise

    checkpoint()

    # Modified records have replaced their previously assigned embeddings.
    recompute_centroids(people, records)
    result.assigned = assign_to_existing(
        new_faces, people, threshold=config.match_threshold
    )
    result.people_created, clusters = cluster_unknowns(records, people, config)
    recompute_centroids(people, records)
    index = build_index(records, people, input_root, output_root)
    written, removed = sync_output(
        checkpoint_index, index, output_root, config.copy_mode
    )
    result.files_written += written
    result.files_removed += removed
    store.save(people, records, index, clusters)
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
