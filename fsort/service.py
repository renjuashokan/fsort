from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Config
from .models import MediaRecord, Person
from .organizer import build_index, sync_output
from .registry import assign_to_existing, cluster_unknowns, recompute_centroids
from .storage import RegistryStore


class FsortService:
    def __init__(self, cache_root: Path, output_root: Path, config: Config):
        self.cache_root = cache_root.resolve()
        self.output_root = output_root.resolve()
        self.config = config
        self.store = RegistryStore(self.cache_root)

    def extract(
        self,
        input_root: Path,
        show_progress: bool = True,
        progress_callback: Any = None,
    ) -> dict[str, int]:
        input_root = input_root.resolve()
        if not input_root.is_dir():
            raise ValueError(f"Input directory does not exist: {input_root}")

        people = self.store.load_people()
        records = self.store.load_embeddings()
        index = self.store.load_index()
        clusters = self.store.load_clusters()

        from .extractor import iter_media
        files = list(iter_media(input_root, excluded=[self.output_root, self.cache_root]))
        scanned = len(files)

        current = {str(path) for path in files}
        stale = set(records) - current
        for path in stale:
            del records[path]
        deleted = len(stale)
        if stale:
            recompute_centroids(people, records)
            self.store.save(people, records, index, clusters)

        from .extractor import FaceExtractor
        from tqdm import tqdm

        extractor = FaceExtractor(self.config)

        processed = 0
        skipped = 0
        failed = 0

        total_files = len(files)
        if progress_callback:
            progress_callback(0, total_files)

        iterator = tqdm(files, desc="Extracting faces", disable=not show_progress)

        pending_checkpoint = bool(stale)

        for idx, path in enumerate(iterator):
            key = str(path)
            stat = path.stat()
            cached = records.get(key)

            if (
                self.config.cache_enabled
                and cached
                and cached.mtime_ns == stat.st_mtime_ns
                and cached.size == stat.st_size
            ):
                skipped += 1
                if progress_callback:
                    progress_callback(idx + 1, total_files)
                continue

            try:
                from .pipeline import _sha256
                digest = _sha256(path)
                if self.config.cache_enabled and cached and cached.hash == digest:
                    cached.mtime_ns = stat.st_mtime_ns
                    cached.size = stat.st_size
                    pending_checkpoint = True
                    skipped += 1
                    if progress_callback:
                        progress_callback(idx + 1, total_files)
                    continue
                faces = extractor.extract(path)
            except (OSError, ValueError) as error:
                if show_progress:
                    tqdm.write(f"warning: skipped {path}: {error}")
                failed += 1
                if progress_callback:
                    progress_callback(idx + 1, total_files)
                continue

            record = MediaRecord(
                hash=digest,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
                faces=faces,
            )
            records[key] = record
            pending_checkpoint = True
            processed += 1

            if progress_callback:
                progress_callback(idx + 1, total_files)

            if processed % self.config.checkpoint_interval == 0:
                if pending_checkpoint:
                    self.store.save(people, records, index, clusters)
                    pending_checkpoint = False

        if pending_checkpoint:
            self.store.save(people, records, index, clusters)

        return {
            "scanned": scanned,
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
            "deleted": deleted,
        }

    def organize(self, input_root: Path | None = None) -> dict[str, int]:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        old_index = self.store.load_index()

        recompute_centroids(people, records)

        new_faces = []
        for record in records.values():
            for face in record.faces:
                if face.person_id is None:
                    new_faces.append(face)

        assigned = assign_to_existing(
            new_faces, people, threshold=self.config.match_threshold
        )

        people_created, clusters = cluster_unknowns(records, people, self.config)

        recompute_centroids(people, records)

        from .cli import _input_root
        in_root = _input_root(input_root, records)

        index = build_index(records, people, in_root, self.output_root)

        written, removed = sync_output(
            old_index, index, self.output_root, self.config.copy_mode
        )

        self.store.save(people, records, index, clusters)

        return {
            "assigned": assigned,
            "people_created": people_created,
            "files_written": written,
            "files_removed": removed,
        }

    def rename(
        self, person_val: str, new_name: str, input_root: Path | None = None
    ) -> str:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        old_index = self.store.load_index()

        from .registry import resolve_person, validate_display_name
        person = resolve_person(people, person_val)
        name = validate_display_name(new_name)

        if any(
            other.id != person.id
            and other.display_name.casefold() == name.casefold()
            for other in people
        ):
            raise ValueError(f"Display name already exists: {name}")

        old_name = person.display_name
        person.display_name = name

        recompute_centroids(people, records)
        from .cli import _input_root
        in_root = _input_root(input_root, records)
        index = build_index(records, people, in_root, self.output_root)

        sync_output(old_index, index, self.output_root, self.config.copy_mode)
        self.store.save(people, records, index)

        return f"Renamed {person.id} ({old_name}) to {name}."

    def merge(
        self, target_val: str, source_val: str, input_root: Path | None = None
    ) -> str:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        old_index = self.store.load_index()

        from .registry import merge_people
        person = merge_people(people, records, target_val, source_val)

        from .cli import _input_root
        in_root = _input_root(input_root, records)
        index = build_index(records, people, in_root, self.output_root)

        sync_output(old_index, index, self.output_root, self.config.copy_mode)
        self.store.save(people, records, index)

        return f"Merged into {person.id} ({person.display_name})."

    def split(self, person_val: str, input_root: Path | None = None) -> str:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        old_index = self.store.load_index()

        from .registry import split_person
        released = split_person(people, records, person_val)

        from .cli import _input_root
        in_root = _input_root(input_root, records)
        index = build_index(records, people, in_root, self.output_root)

        sync_output(old_index, index, self.output_root, self.config.copy_mode)
        self.store.save(people, records, index)

        return f"Released {released} faces for reclustering."

    def list_people(self) -> list[Person]:
        return self.store.load_people()

    def stats(self) -> dict[str, int]:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        faces = [face for record in records.values() for face in record.faces]
        return {
            "people": len(people),
            "media_files": len(records),
            "faces": len(faces),
            "assigned_faces": sum(face.person_id is not None for face in faces),
            "unknown_faces": sum(face.person_id is None for face in faces),
        }

    def verify(self) -> list[str]:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        index = self.store.load_index()
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
            from .registry import validate_display_name
            try:
                validate_display_name(person.display_name)
            except ValueError as error:
                errors.append(f"{person.id}: {error}")
        missing_index = set(records) - set(index)
        if missing_index:
            errors.append(f"{len(missing_index)} cached files missing from file index")
        return errors
