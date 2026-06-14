from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

from .models import FaceRecord, MediaRecord, Person


def serialize_embedding(embedding: list[float] | np.ndarray | None) -> bytes | None:
    if embedding is None or len(embedding) == 0:
        return None
    return np.asarray(embedding, dtype=np.float32).tobytes()


def deserialize_embedding(blob: bytes | None) -> list[float]:
    if not blob:
        return []
    return np.frombuffer(blob, dtype=np.float32).tolist()


def serialize_prototypes(prototypes: list[list[float]] | np.ndarray | None) -> bytes | None:
    if prototypes is None or len(prototypes) == 0:
        return None
    return np.asarray(prototypes, dtype=np.float32).tobytes()


def deserialize_prototypes(blob: bytes | None) -> list[list[float]]:
    if not blob:
        return []
    arr = np.frombuffer(blob, dtype=np.float32)
    if len(arr) % 512 != 0:
        return []
    num_embeddings = len(arr) // 512
    return arr.reshape((num_embeddings, 512)).tolist()


class RegistryStore:
    def __init__(self, cache_dir: Path, hdd_root: str = ""):
        self.cache_dir = cache_dir.resolve()
        self.db_path = self.cache_dir / "faces.db"
        # Normalize hdd_root: always use forward slashes for comparison
        self._hdd_root = hdd_root.replace("\\", "/").rstrip("/") if hdd_root else ""

    # ------------------------------------------------------------------
    # Path helpers: convert between absolute (runtime) ↔ stored (relative)
    # ------------------------------------------------------------------

    def _to_stored(self, abs_path: str) -> str:
        """Strip hdd_root and normalize to POSIX for storage.

        On Windows, D:\\Docs\\photo.jpg  → Docs/photo.jpg
        On Linux,   /mnt/hdd/Docs/photo.jpg → Docs/photo.jpg
        If hdd_root is empty, the path is stored as-is.
        """
        if not self._hdd_root:
            return abs_path
        from pathlib import PurePosixPath, PureWindowsPath
        # Normalize source path to forward slashes for comparison
        normalized = abs_path.replace("\\", "/")
        root = self._hdd_root  # already normalized in __init__
        if normalized.lower().startswith(root.lower() + "/") or normalized.lower() == root.lower():
            rel = normalized[len(root):].lstrip("/")
            return rel  # already POSIX (forward slashes)
        # Can't relativize (different drive/root) — store as-is
        return abs_path

    def _to_abs(self, stored_path: str) -> str:
        """Reconstruct absolute path from a stored path.

        Detects whether stored_path is already absolute (old format)
        and returns it unchanged for backward compatibility.
        """
        if not stored_path:
            return stored_path
        # Already absolute: Linux (/...) or Windows (X:\...) — backward compat
        if stored_path.startswith("/") or (len(stored_path) > 1 and stored_path[1] == ":"):
            return stored_path
        # Relative path — prepend hdd_root
        if self._hdd_root:
            return self._hdd_root.replace("\\", "/").rstrip("/") + "/" + stored_path
        return stored_path

    def _get_connection(self) -> sqlite3.Connection:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        db_existed = self.db_path.exists()
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    id TEXT PRIMARY KEY,
                    display_name TEXT UNIQUE,
                    created_at TEXT,
                    updated_at TEXT,
                    embedding_count INTEGER,
                    centroid BLOB,
                    prototypes BLOB
                )
            """)

            # Ensure prototypes column exists (migration for existing SQLite database)
            cursor = conn.execute("PRAGMA table_info(persons)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "prototypes" not in columns:
                conn.execute("ALTER TABLE persons ADD COLUMN prototypes BLOB")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    sha256 TEXT,
                    mtime INTEGER,
                    size INTEGER,
                    media_type TEXT,
                    processed INTEGER DEFAULT 0,
                    destination TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_id INTEGER,
                    person_id TEXT,
                    embedding BLOB,
                    bbox_x INTEGER,
                    bbox_y INTEGER,
                    bbox_w INTEGER,
                    bbox_h INTEGER,
                    confidence REAL,
                    quality_score REAL,
                    frame INTEGER,
                    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE,
                    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_path ON media(path);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_faces_media_id ON faces(media_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_faces_person_id ON faces(person_id);")

        if not db_existed:
            self._migrate_if_needed()

    def _migrate_if_needed(self) -> None:
        people_json = self.cache_dir / "people.json"
        embeddings_pkl = self.cache_dir / "embeddings.pkl"
        file_index_json = self.cache_dir / "file_index.json"
        clusters_json = self.cache_dir / "clusters.json"

        if not (people_json.exists() or embeddings_pkl.exists()):
            return

        import pickle

        print("Migrating existing JSON/Pickle cache to SQLite database...")

        people: list[Person] = []
        if people_json.exists():
            try:
                with people_json.open("r", encoding="utf-8") as f:
                    values = json.load(f)
                people = [Person.from_dict(val) for val in values]
            except Exception as e:
                print(f"Warning: Failed to load old people.json during migration: {e}")

        records: dict[str, MediaRecord] = {}
        if embeddings_pkl.exists():
            try:
                with embeddings_pkl.open("rb") as f:
                    values = pickle.load(f)
                records = {path: MediaRecord.from_dict(val) for path, val in values.items()}
            except Exception as e:
                print(f"Warning: Failed to load old embeddings.pkl during migration: {e}")

        index: dict[str, dict[str, Any]] = {}
        if file_index_json.exists():
            try:
                with file_index_json.open("r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load old file_index.json during migration: {e}")

        clusters: dict[str, Any] = {}
        if clusters_json.exists():
            try:
                with clusters_json.open("r", encoding="utf-8") as f:
                    clusters = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load old clusters.json during migration: {e}")

        self.save(people, records, index, clusters)

        for path in (people_json, embeddings_pkl, file_index_json, clusters_json):
            if path.exists():
                try:
                    path.rename(path.with_suffix(path.suffix + ".bak"))
                except Exception as e:
                    print(f"Warning: Failed to rename {path.name} to backup: {e}")
                    try:
                        path.unlink()
                    except Exception:
                        pass
        print("Migration to SQLite completed successfully.")

    def load_people(self) -> list[Person]:
        self._init_db()
        people = []
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, display_name, created_at, embedding_count, centroid, prototypes FROM persons"
            )
            for row in cursor:
                centroid_list = deserialize_embedding(row["centroid"])
                prototypes_list = deserialize_prototypes(row["prototypes"])
                people.append(
                    Person(
                        id=row["id"],
                        display_name=row["display_name"],
                        created=row["created_at"] or "",
                        embedding_count=row["embedding_count"] or 0,
                        centroid=centroid_list,
                        prototypes=prototypes_list,
                    )
                )
        return people

    def load_embeddings(self) -> dict[str, MediaRecord]:
        self._init_db()
        records: dict[str, MediaRecord] = {}
        with self._get_connection() as conn:
            media_cursor = conn.execute("SELECT id, path, sha256, mtime, size FROM media")
            media_rows = media_cursor.fetchall()
            if not media_rows:
                return {}

            faces_cursor = conn.execute(
                "SELECT media_id, person_id, embedding, bbox_x, bbox_y, bbox_w, bbox_h, confidence, quality_score, frame FROM faces"
            )
            faces_by_media: dict[int, list[FaceRecord]] = {}
            for row in faces_cursor:
                media_id = row["media_id"]
                face = FaceRecord(
                    embedding=deserialize_embedding(row["embedding"]),
                    person_id=row["person_id"],
                    frame=row["frame"],
                    bbox_x=row["bbox_x"],
                    bbox_y=row["bbox_y"],
                    bbox_w=row["bbox_w"],
                    bbox_h=row["bbox_h"],
                    confidence=row["confidence"],
                    quality_score=row["quality_score"],
                )
                if media_id not in faces_by_media:
                    faces_by_media[media_id] = []
                faces_by_media[media_id].append(face)

            for row in media_rows:
                m_id = row["id"]
                # Reconstruct absolute path for the current platform
                path = self._to_abs(row["path"])
                records[path] = MediaRecord(
                    hash=row["sha256"] or "",
                    mtime_ns=row["mtime"] or 0,
                    size=row["size"] or 0,
                    faces=faces_by_media.get(m_id, []),
                )
        return records

    def load_index(self) -> dict[str, dict[str, Any]]:
        self._init_db()
        index: dict[str, dict[str, Any]] = {}
        with self._get_connection() as conn:
            media_cursor = conn.execute("SELECT id, path, sha256, destination FROM media")
            media_rows = media_cursor.fetchall()

            faces_cursor = conn.execute("SELECT media_id, person_id FROM faces WHERE person_id IS NOT NULL")
            persons_by_media: dict[int, set[str]] = {}
            for row in faces_cursor:
                media_id = row["media_id"]
                p_id = row["person_id"]
                if media_id not in persons_by_media:
                    persons_by_media[media_id] = set()
                persons_by_media[media_id].add(p_id)

            for row in media_rows:
                m_id = row["id"]
                # Reconstruct absolute path for the current platform
                path = self._to_abs(row["path"])
                destination = self._to_abs(row["destination"]) if row["destination"] else ""
                person_ids = sorted(list(persons_by_media.get(m_id, set())))
                index[path] = {
                    "hash": row["sha256"] or "",
                    "persons": person_ids,
                    "destination": destination,
                }
        return index

    def load_clusters(self) -> dict[str, Any]:
        self._init_db()
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'clusters'").fetchone()
            if row and row["value"]:
                try:
                    return json.loads(row["value"])
                except Exception:
                    pass
        return {}

    def save(
        self,
        people: list[Person],
        records: dict[str, MediaRecord],
        index: dict[str, dict[str, Any]],
        clusters: dict[str, Any] | None = None,
    ) -> None:
        self._init_db()
        with self._get_connection() as conn:
            active_person_ids = {person.id for person in people}
            if active_person_ids:
                placeholders = ",".join("?" for _ in active_person_ids)
                conn.execute(
                    f"DELETE FROM persons WHERE id NOT IN ({placeholders})",
                    list(active_person_ids)
                )
            else:
                conn.execute("DELETE FROM persons")

            for person in people:
                centroid_blob = serialize_embedding(person.centroid)
                prototypes_blob = serialize_prototypes(person.prototypes)
                now_str = person.created or ""
                conn.execute(
                    """
                    INSERT INTO persons (id, display_name, created_at, updated_at, embedding_count, centroid, prototypes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        display_name = excluded.display_name,
                        updated_at = ?,
                        embedding_count = excluded.embedding_count,
                        centroid = excluded.centroid,
                        prototypes = excluded.prototypes
                    """,
                    (
                        person.id,
                        person.display_name,
                        person.created,
                        now_str,
                        person.embedding_count,
                        centroid_blob,
                        prototypes_blob,
                        now_str,
                    )
                )

            # Build stored (relative) path set for the DELETE query
            active_stored_paths = {self._to_stored(p) for p in records.keys()}
            if active_stored_paths:
                conn.execute("CREATE TEMP TABLE IF NOT EXISTS active_media_paths (path TEXT UNIQUE)")
                conn.execute("DELETE FROM active_media_paths")
                conn.executemany("INSERT INTO active_media_paths (path) VALUES (?)", [(p,) for p in active_stored_paths])
                conn.execute("DELETE FROM media WHERE path NOT IN (SELECT path FROM active_media_paths)")
            else:
                conn.execute("DELETE FROM media")

            for path, record in records.items():
                stored_path = self._to_stored(path)
                suffix = Path(path).suffix.lower()
                from .extractor import VIDEO_EXTENSIONS
                media_type = "video" if suffix in VIDEO_EXTENSIONS else "image"

                destination = None
                if path in index:
                    dest_val = index[path].get("destination")
                    if dest_val:
                        destination = self._to_stored(str(dest_val))

                conn.execute(
                    """
                    INSERT INTO media (path, sha256, mtime, size, media_type, processed, destination)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        sha256 = excluded.sha256,
                        mtime = excluded.mtime,
                        size = excluded.size,
                        media_type = excluded.media_type,
                        processed = 1,
                        destination = excluded.destination
                    """,
                    (stored_path, record.hash, record.mtime_ns, record.size, media_type, destination)
                )

                media_row = conn.execute("SELECT id FROM media WHERE path = ?", (stored_path,)).fetchone()
                media_id = media_row["id"]

                conn.execute("DELETE FROM faces WHERE media_id = ?", (media_id,))

                for face in record.faces:
                    embedding_blob = serialize_embedding(face.embedding)
                    conn.execute(
                        """
                        INSERT INTO faces (
                            media_id, person_id, embedding, bbox_x, bbox_y, bbox_w, bbox_h,
                            confidence, quality_score, frame
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            media_id,
                            face.person_id,
                            embedding_blob,
                            face.bbox_x,
                            face.bbox_y,
                            face.bbox_w,
                            face.bbox_h,
                            face.confidence,
                            face.quality_score,
                            face.frame,
                        )
                    )

            clusters_str = json.dumps(clusters or {})
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES ('clusters', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (clusters_str,)
            )
