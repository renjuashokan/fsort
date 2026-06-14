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
        files = sorted(iter_media(input_root, excluded=[self.output_root, self.cache_root]))
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

        self.generate_thumbnails()

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
        self._delete_person_thumbnail(old_name)
        person.display_name = name

        recompute_centroids(people, records)
        from .cli import _input_root
        in_root = _input_root(input_root, records)
        index = build_index(records, people, in_root, self.output_root)

        sync_output(old_index, index, self.output_root, self.config.copy_mode)
        self.store.save(people, records, index)

        self.generate_thumbnails()

        return f"Renamed {person.id} ({old_name}) to {name}."

    def merge(
        self, target_val: str, source_val: str, input_root: Path | None = None
    ) -> str:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        old_index = self.store.load_index()

        from .registry import merge_people, resolve_person
        source_person = resolve_person(people, source_val)
        self._delete_person_thumbnail(source_person.display_name)

        person = merge_people(people, records, target_val, source_val)

        from .cli import _input_root
        in_root = _input_root(input_root, records)
        index = build_index(records, people, in_root, self.output_root)

        sync_output(old_index, index, self.output_root, self.config.copy_mode)
        self.store.save(people, records, index)

        self.generate_thumbnails()

        return f"Merged into {person.id} ({person.display_name})."

    def split(self, person_val: str, input_root: Path | None = None) -> str:
        people = self.store.load_people()
        records = self.store.load_embeddings()
        old_index = self.store.load_index()

        from .registry import split_person, resolve_person
        person = resolve_person(people, person_val)
        self._delete_person_thumbnail(person.display_name)

        released = split_person(people, records, person_val)

        from .cli import _input_root
        in_root = _input_root(input_root, records)
        index = build_index(records, people, in_root, self.output_root)

        sync_output(old_index, index, self.output_root, self.config.copy_mode)
        self.store.save(people, records, index)

        self.generate_thumbnails()

        return f"Released {released} faces for reclustering."

    def _delete_person_thumbnail(self, display_name: str) -> None:
        try:
            from .registry import validate_display_name
            folder_name = validate_display_name(display_name)
            thumb_path = self.output_root / folder_name / "thumbnail_fsort.jpg"
            if thumb_path.is_file():
                thumb_path.unlink()
        except Exception:
            pass

    def generate_thumbnails(self) -> int:
        from collections import defaultdict
        import cv2
        import numpy as np
        from .registry import validate_display_name

        people = self.store.load_people()
        records = self.store.load_embeddings()

        # Group all faces by person_id
        person_faces = defaultdict(list)
        for path_str, record in records.items():
            for face in record.faces:
                if face.person_id is not None:
                    person_faces[face.person_id].append((path_str, face))

        count = 0
        for person in people:
            faces = person_faces.get(person.id, [])
            if not faces:
                continue

            # Sort faces by similarity to centroid if centroid exists
            if person.centroid and len(person.centroid) > 0:
                centroid = np.asarray(person.centroid, dtype=np.float32)
                # Normalize centroid
                c_norm = np.linalg.norm(centroid)
                if c_norm > 0:
                    centroid = centroid / c_norm

                def similarity_key(item: tuple[str, Any]) -> float:
                    _, face = item
                    emb = np.asarray(face.embedding, dtype=np.float32)
                    emb_norm = np.linalg.norm(emb)
                    if emb_norm > 0:
                        emb = emb / emb_norm
                    return float(1.0 - np.dot(emb, centroid))

                try:
                    faces = sorted(faces, key=similarity_key)
                except Exception:
                    pass

            # Find the first face that we can successfully load and crop
            success = False
            for path_str, face in faces:
                path = Path(path_str)
                if not path.is_file():
                    continue

                try:
                    if face.frame is not None:
                        # Video frame extraction
                        cap = cv2.VideoCapture(str(path))
                        if not cap.isOpened():
                            continue
                        cap.set(cv2.CAP_PROP_POS_FRAMES, face.frame)
                        ok, frame = cap.read()
                        cap.release()
                        if not ok or frame is None:
                            continue
                        img = frame
                    else:
                        # Photo
                        img = cv2.imread(str(path))
                        if img is None:
                            continue
                except Exception:
                    continue

                h_img, w_img = img.shape[:2]

                # Crop bounding box if coordinates are valid
                x = face.bbox_x if face.bbox_x is not None else 0
                y = face.bbox_y if face.bbox_y is not None else 0
                w = face.bbox_w if face.bbox_w is not None else w_img
                h = face.bbox_h if face.bbox_h is not None else h_img

                # Add a 15% margin padding
                pad_x = int(w * 0.15)
                pad_y = int(h * 0.15)

                crop_x = max(0, x - pad_x)
                crop_y = max(0, y - pad_y)
                crop_w = min(w_img - crop_x, w + 2 * pad_x)
                crop_h = min(h_img - crop_y, h + 2 * pad_y)

                crop = img[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
                if crop.size == 0:
                    continue

                try:
                    thumbnail = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA)
                    # Create target directory
                    try:
                        folder_name = validate_display_name(person.display_name)
                    except ValueError:
                        folder_name = person.id
                    
                    person_folder = self.output_root / folder_name
                    person_folder.mkdir(parents=True, exist_ok=True)
                    thumbnail_path = person_folder / "thumbnail_fsort.jpg"
                    
                    cv2.imwrite(str(thumbnail_path), thumbnail)
                    success = True
                    break
                except Exception:
                    continue

            if success:
                count += 1

        return count

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

    def create_person(self, name: str) -> Person:
        from .registry import validate_display_name
        people = self.store.load_people()
        name = validate_display_name(name)
        if any(p.display_name.casefold() == name.casefold() for p in people):
            raise ValueError(f"Person already exists: {name}")
        person = Person.create(name)
        people.append(person)
        records = self.store.load_embeddings()
        index = self.store.load_index()
        self.store.save(people, records, index)
        return person

    def list_people_paginated(
        self,
        skip: int,
        limit: int,
        sort_by: str,
        order: str,
        search: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        self.store._init_db()
        search_pattern = f"%{search}%" if search else "%"
        
        # Mapping sort fields to SQL order columns
        sort_mapping = {
            "name": "display_name",
            "media_count": "media_count",
            "image_count": "image_count",
            "video_count": "video_count",
            "created": "created_at",
            "updated": "updated_at",
        }
        sql_sort_col = sort_mapping.get(sort_by, "display_name")
        sql_order = "ASC" if order.lower() == "asc" else "DESC"

        total_query = """
            WITH combined AS (
                SELECT display_name FROM persons
                UNION ALL
                SELECT 'Unknown' as display_name
                UNION ALL
                SELECT 'Multiple Faces' as display_name
            )
            SELECT COUNT(*) FROM combined WHERE display_name LIKE ?
        """

        query = f"""
            WITH combined AS (
                SELECT p.id, p.display_name, p.created_at, p.updated_at, p.embedding_count,
                       (SELECT COUNT(DISTINCT f.media_id) FROM faces f WHERE f.person_id = p.id) as media_count,
                       (SELECT COUNT(DISTINCT f.media_id) FROM faces f JOIN media m ON f.media_id = m.id WHERE f.person_id = p.id AND m.media_type = 'image') as image_count,
                       (SELECT COUNT(DISTINCT f.media_id) FROM faces f JOIN media m ON f.media_id = m.id WHERE f.person_id = p.id AND m.media_type = 'video') as video_count
                FROM persons p
                UNION ALL
                SELECT '_unknown' as id, 'Unknown' as display_name, '' as created_at, '' as updated_at, 0 as embedding_count,
                       (SELECT COUNT(*) FROM media WHERE destination LIKE '%/Unknown/%' OR destination LIKE 'Unknown/%' OR destination = 'Unknown') as media_count,
                       (SELECT COUNT(*) FROM media WHERE (destination LIKE '%/Unknown/%' OR destination LIKE 'Unknown/%' OR destination = 'Unknown') AND media_type = 'image') as image_count,
                       (SELECT COUNT(*) FROM media WHERE (destination LIKE '%/Unknown/%' OR destination LIKE 'Unknown/%' OR destination = 'Unknown') AND media_type = 'video') as video_count
                UNION ALL
                SELECT '_multiple' as id, 'Multiple Faces' as display_name, '' as created_at, '' as updated_at, 0 as embedding_count,
                       (SELECT COUNT(*) FROM media WHERE destination LIKE '%/MultipleFaces/%' OR destination LIKE 'MultipleFaces/%' OR destination = 'MultipleFaces') as media_count,
                       (SELECT COUNT(*) FROM media WHERE (destination LIKE '%/MultipleFaces/%' OR destination LIKE 'MultipleFaces/%' OR destination = 'MultipleFaces') AND media_type = 'image') as image_count,
                       (SELECT COUNT(*) FROM media WHERE (destination LIKE '%/MultipleFaces/%' OR destination LIKE 'MultipleFaces/%' OR destination = 'MultipleFaces') AND media_type = 'video') as video_count
            )
            SELECT * FROM combined
            WHERE display_name LIKE ?
            ORDER BY {sql_sort_col} {sql_order}
            LIMIT ? OFFSET ?
        """

        with self.store._get_connection() as conn:
            total = conn.execute(total_query, (search_pattern,)).fetchone()[0]
            cursor = conn.execute(query, (search_pattern, limit, skip))
            items = []
            for row in cursor:
                items.append({
                    "id": row["id"],
                    "display_name": row["display_name"],
                    "thumbnail_url": f"/api/person/{row['id']}/thumbnail",
                    "image_count": row["image_count"],
                    "video_count": row["video_count"],
                    "media_count": row["media_count"],
                })
        return total, items

    def list_person_media_paginated(
        self,
        person_id: str,
        skip: int,
        limit: int,
        sort_by: str,
        order: str,
    ) -> tuple[int, list[dict[str, Any]]]:
        self.store._init_db()
        sort_mapping = {
            "filename": "path",
            "created": "mtime",
            "modified": "mtime",
            "type": "media_type",
            "filesize": "size",
        }
        sql_sort_col = sort_mapping.get(sort_by, "path")
        sql_order = "ASC" if order.lower() == "asc" else "DESC"

        if person_id == "_unknown":
            total_query = "SELECT COUNT(*) FROM media WHERE destination LIKE '%/Unknown/%' OR destination LIKE 'Unknown/%' OR destination = 'Unknown'"
            query = f"""
                SELECT id, path, sha256, mtime, size, media_type, destination
                FROM media
                WHERE destination LIKE '%/Unknown/%' OR destination LIKE 'Unknown/%' OR destination = 'Unknown'
                ORDER BY {sql_sort_col} {sql_order}
                LIMIT ? OFFSET ?
            """
            params = (limit, skip)
            total_params = ()
        elif person_id == "_multiple":
            total_query = "SELECT COUNT(*) FROM media WHERE destination LIKE '%/MultipleFaces/%' OR destination LIKE 'MultipleFaces/%' OR destination = 'MultipleFaces'"
            query = f"""
                SELECT id, path, sha256, mtime, size, media_type, destination
                FROM media
                WHERE destination LIKE '%/MultipleFaces/%' OR destination LIKE 'MultipleFaces/%' OR destination = 'MultipleFaces'
                ORDER BY {sql_sort_col} {sql_order}
                LIMIT ? OFFSET ?
            """
            params = (limit, skip)
            total_params = ()
        else:
            total_query = "SELECT COUNT(DISTINCT media_id) FROM faces WHERE person_id = ?"
            query = f"""
                SELECT DISTINCT m.id, m.path, m.sha256, m.mtime, m.size, m.media_type, m.destination
                FROM media m
                JOIN faces f ON f.media_id = m.id
                WHERE f.person_id = ?
                ORDER BY m.{sql_sort_col} {sql_order}
                LIMIT ? OFFSET ?
            """
            params = (person_id, limit, skip)
            total_params = (person_id,)

        with self.store._get_connection() as conn:
            total = conn.execute(total_query, total_params).fetchone()[0]
            cursor = conn.execute(query, params)
            items = []
            for row in cursor:
                import datetime
                try:
                    mtime_sec = row["mtime"] / 1_000_000_000.0
                    dt = datetime.datetime.fromtimestamp(mtime_sec, tz=datetime.timezone.utc)
                    created_str = dt.strftime("%Y-%m-%d")
                except Exception:
                    created_str = ""
                items.append({
                    "id": row["id"],
                    "thumbnail_url": f"/api/media/{row['id']}/thumbnail",
                    "media_url": f"/api/media/{row['id']}",
                    "type": row["media_type"],
                    "filename": Path(row["path"]).name,
                    "created": created_str,
                })
        return total, items

    def reassign_media(self, media_id: int, person_id: str | None, input_root: Path | None = None) -> None:
        self.store._init_db()
        if person_id == "":
            person_id = None

        with self.store._get_connection() as conn:
            if person_id is not None:
                row = conn.execute("SELECT id FROM persons WHERE id = ?", (person_id,)).fetchone()
                if not row:
                    raise ValueError(f"Person {person_id} does not exist")

            cursor = conn.execute("SELECT COUNT(*) FROM faces WHERE media_id = ?", (media_id,))
            count = cursor.fetchone()[0]
            if count > 0:
                conn.execute("UPDATE faces SET person_id = ? WHERE media_id = ?", (person_id, media_id))
            elif person_id is not None:
                from .storage import serialize_embedding
                conn.execute(
                    "INSERT INTO faces (media_id, person_id, embedding) VALUES (?, ?, ?)",
                    (media_id, person_id, serialize_embedding([]))
                )

        people = self.store.load_people()
        records = self.store.load_embeddings()
        old_index = self.store.load_index()
        clusters = self.store.load_clusters()

        recompute_centroids(people, records)
        from .cli import _input_root
        in_root = _input_root(input_root, records)
        index = build_index(records, people, in_root, self.output_root)

        sync_output(old_index, index, self.output_root, self.config.copy_mode)
        self.store.save(people, records, index, clusters)
        self.generate_thumbnails()

    def search(self, query: str) -> dict[str, list[dict[str, Any]]]:
        self.store._init_db()
        people_results = []
        media_results = []
        with self.store._get_connection() as conn:
            people_cursor = conn.execute(
                "SELECT id, display_name FROM persons WHERE display_name LIKE ?",
                (f"%{query}%",)
            )
            for row in people_cursor:
                people_results.append({
                    "id": row["id"],
                    "display_name": row["display_name"],
                    "thumbnail_url": f"/api/person/{row['id']}/thumbnail",
                })

            media_cursor = conn.execute(
                "SELECT id, path, media_type FROM media WHERE path LIKE ? OR destination LIKE ? LIMIT 100",
                (f"%{query}%", f"%{query}%")
            )
            for row in media_cursor:
                filename = Path(row["path"]).name
                media_results.append({
                    "id": row["id"],
                    "filename": filename,
                    "type": row["media_type"],
                    "thumbnail_url": f"/api/media/{row['id']}/thumbnail",
                    "media_url": f"/api/media/{row['id']}",
                })
        return {"people": people_results, "media": media_results}
