# face-sort

`face-sort` is a local, offline face organizer with persistent person IDs. It
only extracts faces from new or modified media, matches them against saved
person centroids, and clusters remaining unknown faces with DBSCAN.

## Install

The project uses Python 3.14 and `uv`. Install it as a command-line tool:

```powershell
uv tool install --editable .
```

On Windows with an NVIDIA GPU, InsightFace's CPU ONNX Runtime dependency can
overwrite the GPU package during tool installation. Reinstall the GPU wheel
and its CUDA/cuDNN runtime DLLs last:

```powershell
uv pip install --python "$env:APPDATA\uv\tools\fsort\Scripts\python.exe" --reinstall "onnxruntime-gpu[cuda,cudnn]"
```

After installation, `face-sort` can be run from any directory without
activating a virtual environment:

```powershell
face-sort sort D:\Photos --output D:\Sorted --cache D:\face-sort-cache
```

Run `uv tool upgrade fsort` after dependency or packaging changes, followed by
the GPU reinstall command above when using NVIDIA. Because the project itself
is installed editable, Python source changes are used immediately. To remove
the command, run `uv tool uninstall fsort`.

For project development, create the local environment with:

```powershell
uv sync
```

InsightFace downloads its configured model the first time sorting runs. After
that, processing remains local. On Windows and Linux x64, the project installs
the NVIDIA GPU build of ONNX Runtime. Other platforms use its CPU build.

## Usage

```powershell
uv run face-sort sort D:\Photos --output output --cache cache
uv run face-sort sort D:\Photos --output output --cache cache --checkpoint-interval 100
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
checkpoint_interval: 250
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

During sorting, extraction state and provisional output are checkpointed after
`checkpoint_interval` newly processed media files. Files without a final
person assignment are temporarily written under `Unknown`; the final
clustering pass moves them to their completed destinations. Restarting the
same command resumes from the latest checkpoint.

Person IDs are immutable. Display names and their output folders can be
changed without affecting future recognition.
