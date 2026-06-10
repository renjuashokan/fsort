# face-sort Architecture Roadmap (v2)

## Goal

Build `face-sort` as a persistent, offline face management engine that supports:

* Stable person identities
* Incremental processing
* Local HTTP API
* Future web UI
* Raspberry Pi deployment
* Large photo libraries (100k+ media)

The design should minimize future breaking changes.

---

# Priority 1 (Must Do)

## 1. Replace JSON + PKL with SQLite

Current:

```
embeddings.pkl
people.json
file_index.json
clusters.json
```

Replace with:

```
cache/
    faces.db
```

SQLite is embedded, cross-platform, atomic, supports indexes, transactions, and future REST APIs.

---

## Proposed Database Schema

### persons

```
id              TEXT PRIMARY KEY
display_name    TEXT UNIQUE
created_at      TEXT
updated_at      TEXT
embedding_count INTEGER
```

Example:

```
9c6dba74

Mom

42 embeddings
```

---

### media

One row per original image/video.

```
id              INTEGER PRIMARY KEY
path            TEXT UNIQUE
sha256          TEXT UNIQUE
mtime           INTEGER
media_type      TEXT
processed       INTEGER
```

Example:

```
1

/photos/img1.jpg

image

processed=1
```

---

### faces

One row per detected face.

```
id              INTEGER PRIMARY KEY
media_id        INTEGER
person_id       TEXT NULL
embedding       BLOB
bbox_x          INTEGER
bbox_y          INTEGER
bbox_w          INTEGER
bbox_h          INTEGER
confidence      REAL
quality_score   REAL
```

Each image can contain multiple face rows.

---

### settings

```
key
value
```

Example:

```
model_name

buffalo_l

------------------

schema_version

1

------------------

embedding_dimension

512
```

---

### operations (future)

Background task queue.

```
id

operation

payload

status

created_at
```

Example:

```
rename

{"person":"Mom","new":"Mother"}

pending
```

Future HTTP server and worker can share this.

---

# Priority 2 (Must Do)

## 2. Separate Extraction and Organization

Current pipeline:

```
scan

↓

extract

↓

cluster

↓

copy
```

Instead split responsibilities.

---

## Extract phase

```
face-sort extract INPUT
```

Responsibilities:

* scan filesystem
* hash files
* detect faces
* generate embeddings
* write SQLite

Never moves or copies files.

Can be resumed.

Can be parallelized.

Can be watched continuously.

---

## Organize phase

```
face-sort organize
```

Responsibilities:

* assign people
* cluster unknown faces
* rename
* merge
* split
* generate folders
* create hardlinks/copies

Uses only SQLite.

No ML work required.

Runs quickly.

---

Benefits:

* rename is instant
* merge is instant
* split is instant
* web UI becomes easy
* future REST API is simple

---

# Priority 3 (Must Do)

## 3. Embedded HTTP Server

Add:

```
face-sort serve \
    --host 127.0.0.1 \
    --port 9876
```

Runs a lightweight FastAPI server.

Endpoints:

```
GET /people

GET /stats

GET /verify

POST /rename

POST /merge

POST /split

POST /organize

POST /extract

POST /watch/start

POST /watch/stop
```

CLI should call the same service layer as HTTP.

No duplicated business logic.

Future Rust frontend can consume these APIs directly.

---

# Priority 4 (Should Do)

## 4. Watch Mode

```
face-sort watch INPUT
```

Uses filesystem notifications.

Workflow:

```
new file

↓

extract embedding

↓

match existing person

↓

unknown?

↓

buffer

↓

periodic DBSCAN

↓

new person

↓

organize
```

Only new media is processed.

Suitable for Raspberry Pi or NAS.

---

# Priority 5 (Future)

## 5. Replace Single Centroid

Current:

```
Person

↓

centroid
```

Future:

```
Person

↓

30 representative embeddings
```

Examples:

```
front face

left profile

right profile

smile

glasses

beard

old

young

low light

high light
```

Matching compares against multiple prototypes.

This greatly improves robustness.

Implementation can wait.

---

# Important Recommendation

Never rerun DBSCAN over existing people.

Instead:

```
new embedding

↓

nearest person

↓

distance < threshold

↓

assign

otherwise

↓

unknown buffer

↓

DBSCAN only unknowns

↓

create new person
```

Stable identities are preserved forever.

---

# Service Layer

Every interface should call the same service functions.

```
CLI

↓

service.py

↓

registry.py

↓

organizer.py

↓

SQLite
```

HTTP:

```
REST

↓

service.py

↓

registry.py

↓

organizer.py

↓

SQLite
```

Future GUI:

```
React

↓

REST

↓

service.py

↓

SQLite
```

Business logic exists only once.

---

# Commands

```
face-sort extract

face-sort organize

face-sort watch

face-sort serve

face-sort rename

face-sort merge

face-sort split

face-sort list

face-sort stats

face-sort verify
```

Each command should have a single responsibility.

---

# Things NOT Worth Doing Now

* FAISS vector database
* PostgreSQL backend
* Docker-specific changes
* Multi-user support
* Authentication
* Distributed processing
* Cloud sync
* Pet recognition
* Face quality ranking
* Interactive review UI

These can be added later without affecting the core architecture.

---

# Final Recommendation

Implement only these changes now:

1. Migrate all persistent state to a single SQLite database.
2. Split the engine into `extract` and `organize` phases.
3. Introduce a shared service layer used by both CLI and HTTP.
4. Add an embedded HTTP server (`face-sort serve`).
5. Add filesystem watch mode.
6. Keep centroid-based matching for now, but design the schema so multiple embeddings per person can be supported later.

With these changes, `face-sort` will have a stable architecture that can evolve into a complete self-hosted face management engine while remaining lightweight and fully offline.
