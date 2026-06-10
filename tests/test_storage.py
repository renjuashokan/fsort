import json
import pickle
from pathlib import Path

import numpy as np

from fsort.models import FaceRecord, MediaRecord, Person
from fsort.storage import RegistryStore


def test_sqlite_initialization_and_crud(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    store = RegistryStore(cache_dir)
    
    # Check that cache_dir doesn't have the db yet
    db_path = cache_dir / "faces.db"
    assert not db_path.exists()
    
    # Initialize/load people (triggers schema creation)
    people = store.load_people()
    assert people == []
    assert db_path.exists()
    
    # Add a person and media record
    person = Person(
        id="p1234567",
        display_name="Test Person",
        created="2026-06-10T12:00:00Z",
        embedding_count=1,
        centroid=[0.5] * 512,
    )
    
    face = FaceRecord(
        embedding=[0.5] * 512,
        person_id="p1234567",
        frame=42,
        bbox_x=10,
        bbox_y=20,
        bbox_w=100,
        bbox_h=120,
        confidence=0.95,
        quality_score=0.88,
    )
    
    record = MediaRecord(
        hash="abcde12345",
        mtime_ns=123456789,
        size=1024,
        faces=[face],
    )
    
    records = {"/photos/img.jpg": record}
    index = {
        "/photos/img.jpg": {
            "hash": "abcde12345",
            "persons": ["p1234567"],
            "destination": "/sorted/Test Person/img.jpg",
        }
    }
    clusters = {"p1234567": [{"path": "/photos/img.jpg", "face_index": 0}]}
    
    # Save to SQLite
    store.save([person], records, index, clusters)
    
    # Load and verify
    loaded_people = store.load_people()
    assert len(loaded_people) == 1
    assert loaded_people[0].id == person.id
    assert loaded_people[0].display_name == person.display_name
    assert loaded_people[0].created == person.created
    assert loaded_people[0].embedding_count == 1
    assert np.allclose(loaded_people[0].centroid, [0.5] * 512)
    
    loaded_records = store.load_embeddings()
    assert "/photos/img.jpg" in loaded_records
    loaded_rec = loaded_records["/photos/img.jpg"]
    assert loaded_rec.hash == "abcde12345"
    assert loaded_rec.mtime_ns == 123456789
    assert loaded_rec.size == 1024
    assert len(loaded_rec.faces) == 1
    
    loaded_face = loaded_rec.faces[0]
    assert loaded_face.person_id == "p1234567"
    assert loaded_face.frame == 42
    assert loaded_face.bbox_x == 10
    assert loaded_face.bbox_y == 20
    assert loaded_face.bbox_w == 100
    assert loaded_face.bbox_h == 120
    assert loaded_face.confidence == 0.95
    assert loaded_face.quality_score == 0.88
    assert np.allclose(loaded_face.embedding, [0.5] * 512)

    loaded_index = store.load_index()
    assert "/photos/img.jpg" in loaded_index
    assert loaded_index["/photos/img.jpg"]["hash"] == "abcde12345"
    assert loaded_index["/photos/img.jpg"]["persons"] == ["p1234567"]
    assert loaded_index["/photos/img.jpg"]["destination"] == "/sorted/Test Person/img.jpg"

    loaded_clusters = store.load_clusters()
    assert loaded_clusters == clusters


def test_sqlite_migration(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)
    
    # Create old files
    people_json = cache_dir / "people.json"
    embeddings_pkl = cache_dir / "embeddings.pkl"
    file_index_json = cache_dir / "file_index.json"
    clusters_json = cache_dir / "clusters.json"
    
    old_people = [
        {
            "id": "p9999999",
            "display_name": "Old Person",
            "created": "2026-06-10T10:00:00Z",
            "embedding_count": 1,
            "centroid": [0.1] * 512,
        }
    ]
    with people_json.open("w", encoding="utf-8") as f:
        json.dump(old_people, f)
        
    old_embeddings = {
        "/old/path.jpg": {
            "hash": "oldhash",
            "mtime_ns": 987654321,
            "size": 5000,
            "faces": [
                {
                    "embedding": [0.1] * 512,
                    "person_id": "p9999999",
                    "frame": None,
                }
            ],
        }
    }
    with embeddings_pkl.open("wb") as f:
        pickle.dump(old_embeddings, f)
        
    old_index = {
        "/old/path.jpg": {
            "hash": "oldhash",
            "persons": ["p9999999"],
            "destination": "/old/destination.jpg",
        }
    }
    with file_index_json.open("w", encoding="utf-8") as f:
        json.dump(old_index, f)
        
    old_clusters = {"p9999999": [{"path": "/old/path.jpg", "face_index": 0}]}
    with clusters_json.open("w", encoding="utf-8") as f:
        json.dump(old_clusters, f)
        
    # Instantiate store and load people to trigger migration
    store = RegistryStore(cache_dir)
    people = store.load_people()
    
    # Verify migration loaded correctly
    assert len(people) == 1
    assert people[0].id == "p9999999"
    assert people[0].display_name == "Old Person"
    assert np.allclose(people[0].centroid, [0.1] * 512)
    
    embeddings = store.load_embeddings()
    assert "/old/path.jpg" in embeddings
    assert embeddings["/old/path.jpg"].hash == "oldhash"
    assert len(embeddings["/old/path.jpg"].faces) == 1
    assert embeddings["/old/path.jpg"].faces[0].person_id == "p9999999"
    
    # Verify old files are renamed to .bak
    assert not people_json.exists()
    assert not embeddings_pkl.exists()
    assert not file_index_json.exists()
    assert not clusters_json.exists()
    
    assert (cache_dir / "people.json.bak").exists()
    assert (cache_dir / "embeddings.pkl.bak").exists()
    assert (cache_dir / "file_index.json.bak").exists()
    assert (cache_dir / "clusters.json.bak").exists()
