# Design Enhancement: Persistent Person Registry

## Motivation

A pure DBSCAN clustering approach produces cluster IDs (`Person_001`, `Person_002`, etc.) that may change between runs as new photos are added.

To support incremental execution, the application should maintain a persistent registry of discovered people.

This allows:

* Stable person folders
* Fast rescanning
* Processing only new files
* Manual renaming of people
* Future web UI support
* Future face search capability

---

# Architecture

```
                 Input Directory
                        │
                        ▼
                 Recursive Scanner
                        │
            New / Modified Files Only
                        │
                        ▼
                 Face Detection
                        │
                        ▼
              Face Embedding Generator
                        │
                        ▼
         ┌────────────────────────────┐
         │ Persistent Person Registry │
         └────────────────────────────┘
                │              │
      Existing Person      Unknown Face
                │              │
                ▼              ▼
      Assign to Person     Buffer Embeddings
                                   │
                                   ▼
                        Cluster Remaining Faces
                                   │
                                   ▼
                     Create New Persistent Person
                                   │
                                   ▼
                        Organize Output Files
```

---

# Persistent Storage

```
project/

cache/

    embeddings.pkl

    people.json

    file_index.json

    clusters.json

output/
```

---

# people.json

Stores the canonical list of people.

```
[
    {
        "id": "9c6dba74",
        "display_name": "Person_001",
        "created": "2026-06-10T10:00:00Z",
        "embedding_count": 42,
        "centroid": [512 floats]
    },

    {
        "id": "d71f4432",
        "display_name": "Mom",
        "embedding_count": 388,
        "centroid": [512 floats]
    }
]
```

The centroid is the average embedding representing that person.

---

# file_index.json

Maps processed files to people.

```
{
    "/photos/img1.jpg": {
        "hash": "...",
        "persons": [
            "9c6dba74"
        ]
    },

    "/photos/family.jpg": {
        "persons": [
            "9c6dba74",
            "d71f4432"
        ]
    }
}
```

This prevents rescanning unchanged files.

---

# embeddings.pkl

Stores every extracted embedding.

```
hash

embedding

person_id

face_count

mtime
```

Used to avoid recomputation and to update person centroids.

---

# Person Matching Algorithm

When a new face is detected:

```
Generate embedding

↓

Compare against all person centroids

↓

Find nearest centroid

↓

Distance < threshold?

        YES

Assign to existing person

        NO

Store as unknown candidate
```

This avoids rerunning DBSCAN on the entire collection.

---

# Unknown Face Buffer

Unknown faces are accumulated.

```
Unknown embeddings

↓

DBSCAN

↓

Cluster size >= min_samples

↓

Create new person

↓

Update registry
```

Only new unknown faces are clustered.

Existing people remain stable.

---

# Updating Person Centroid

When assigning a new embedding:

```
Old centroid

+

New embedding

↓

Weighted average

↓

Updated centroid
```

This improves recognition as more images are processed.

---

# Stable Folder Structure

```
output/

    Mom/

    Dad/

    Renju/

    Daughter/

    Unknown/

    MultipleFaces/
```

Initially:

```
Person_001

Person_002
```

Users can rename folders:

```
Person_001

↓

Mom
```

Future scans continue placing matching photos into the renamed folder because matching is based on the immutable person ID, not the folder name.

---

# Multi-face Images

Instead of duplicating images:

```
family.jpg
```

is stored once:

```
MultipleFaces/family.jpg
```

The registry records:

```
family.jpg

↓

Mom

Dad

Daughter
```

Future enhancement:

Optional `--duplicate-multiface` mode to copy the image into every person's folder.

---

# Incremental Execution

```
Run 1

10000 photos

↓

Discover 45 people

↓

Save registry

------------------------

Run 2

+300 new photos

↓

Skip unchanged files

↓

Extract embeddings

↓

Compare to existing people

↓

298 assigned

↓

2 unknown

↓

DBSCAN unknowns

↓

Create Person_046

↓

Update registry
```

Execution time becomes proportional to newly added content.

---

# Folder Naming

Each person has an immutable UUID.

```
9c6dba74
```

and a mutable display name.

```
Person_001

↓

Grandma

↓

Amma

↓

Jane
```

Changing the display name never changes the underlying identity.

---

# Manual Commands

```
face-sort rename 9c6dba74 Grandma
```

```
face-sort merge Person_003 Person_009
```

```
face-sort split Person_005
```

```
face-sort list
```

```
face-sort stats
```

```
face-sort verify
```

These commands enable long-term maintenance without editing JSON manually.

---

# Configuration

```
config.yaml

video_interval: 2

match_threshold: 0.42

dbscan_eps: 0.45

min_samples: 2

min_face_size: 80

copy_mode: true

cache_enabled: true

gpu: false
```

---

# Future Roadmap

* Interactive review of uncertain matches
* Best face thumbnail for each person
* Automatic duplicate detection
* Similar face search
* Face quality scoring
* Age progression handling
* Pet face clustering
* SQLite backend replacing JSON
* FAISS vector index for millions of embeddings
* Lightweight local web UI
* Docker image for NAS deployment
* REST API for external integrations

---

# Final Design Philosophy

The application should be treated as a **local, offline face knowledge base**, not just a clustering script.

Its primary responsibilities are:

1. Maintain a persistent registry of people.
2. Process only new or modified media.
3. Preserve stable person identities across runs.
4. Allow human-friendly renaming and maintenance.
5. Remain fully self-hosted with no cloud dependencies.
6. Scale efficiently from a few hundred to hundreds of thousands of photos while maintaining consistent organization and fast incremental updates.
