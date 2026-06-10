# face-sort

`face-sort` is a local, offline face organizer with persistent person IDs. It
only extracts faces from new or modified media, matches them against saved
person centroids, and clusters remaining unknown faces with DBSCAN.

## Install

The project uses Python 3.14 and `uv`:

```powershell
uv sync
```

InsightFace downloads its configured model the first time sorting runs. After
that, processing remains local. On Windows and Linux x64, the project installs
the NVIDIA GPU build of ONNX Runtime. Other platforms use its CPU build.

## Usage

```powershell
uv run face-sort sort D:\Photos --output output --cache cache
uv run face-sort list
uv run face-sort rename 9c6dba74 Grandma
uv run face-sort merge Person_003 Person_009
uv run face-sort split Person_005
uv run face-sort stats
uv run face-sort verify
```

`merge TARGET SOURCE` preserves the target identity. `split PERSON` removes
that identity and returns all of its faces to the unknown pool; the next
`sort` run reclusters them.

Maintenance commands default to `cache/` and `output/`. Pass `--input`,
`--cache`, or `--output` when those locations differ. Multi-face media is
stored once under `MultipleFaces/`; unmatched or faceless media goes under
`Unknown/`.

When `copy_mode` is false, the organizer creates hard links where possible and
falls back to copying. It never removes source media.

## Configuration

Create `config.yaml` as needed:

```yaml
video_interval: 2
match_threshold: 0.42
dbscan_eps: 0.45
min_samples: 2
min_face_size: 80
copy_mode: true
cache_enabled: true
gpu: true
model_name: buffalo_l
```

GPU mode requires an NVIDIA GPU and a compatible NVIDIA driver plus CUDA/cuDNN
runtime. The command exits with the available ONNX Runtime providers instead
of silently using the CPU when CUDA is unavailable. Set `gpu: false` to force
CPU execution.

State is written atomically to:

```text
cache/
  embeddings.pkl
  people.json
  file_index.json
  clusters.json
```

Person IDs are immutable. Display names and their output folders can be
changed without affecting future recognition.
