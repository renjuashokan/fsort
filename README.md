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

The examples below use the globally installed `face-sort` command. When
running from a development checkout, prefix the same commands with `uv run`,
for example `uv run face-sort list`.

### Sort photos

```powershell
face-sort sort D:\Photos --output D:\Sorted --cache D:\face-sort-cache
```

The input directory contains the original media. The output directory contains
the organized copies or hard links, and the cache stores the face embeddings,
person registry, and output index. Keep the cache if you want names and person
identities to remain stable across later runs.

To checkpoint more frequently during a large scan:

```powershell
face-sort sort D:\Photos --output D:\Sorted --cache D:\face-sort-cache --checkpoint-interval 100
```

### List registered people

Use `list` to see each person's immutable ID, current display name, and number
of saved face embeddings:

```powershell
face-sort list --cache D:\face-sort-cache
```

Example output:

```text
9c6dba74  Person_001  (42 embeddings)
```

Maintenance commands accept either the immutable ID or the current display
name. Using the ID is useful after a person has already been renamed.

### Rename a person

Use `rename PERSON NEW_NAME` to change a person's display name and output
folder. Do not rename the folder manually because that would not update the
person registry or output index.

For example, after sorting with:

```powershell
face-sort sort D:\Docs\pgrms\df-scrape\output --output D:\Docs\pgrms\to-del\output --cache D:\Docs\pgrms\to-del\cache
```

rename `Person_001` to `PersonX` with:

```powershell
face-sort rename Person_001 PersonX --input D:\Docs\pgrms\df-scrape\output --output D:\Docs\pgrms\to-del\output --cache D:\Docs\pgrms\to-del\cache
```

This updates the registry, moves or recreates the organized files under
`PersonX`, and removes the old `Person_001` directory when it becomes empty.
The immutable person ID and learned face identity do not change, so future
matching photos continue to go into `PersonX`.

Names containing spaces must be quoted:

```powershell
face-sort rename Person_001 "Jane Smith" --input D:\Photos --output D:\Sorted --cache D:\face-sort-cache
```

Display names must be unique and valid as Windows folder names. Reserved
organizer names such as `Unknown` and `MultipleFaces` cannot be used.

### Merge duplicate people

If the same person was assigned to two identities, merge them with
`merge TARGET SOURCE`:

```powershell
face-sort merge Person_003 Person_009 --input D:\Photos --output D:\Sorted --cache D:\face-sort-cache
```

All faces assigned to `Person_009` are reassigned to `Person_003`.
`Person_003` is the target, so its immutable ID and display name are preserved;
the source identity is removed. The registry, centroids, and output folders
are synchronized immediately.

### Split an incorrect person

If one registered identity contains faces that should be reclustered, release
that identity with:

```powershell
face-sort split Person_005 --input D:\Photos --output D:\Sorted --cache D:\face-sort-cache
```

This removes the person from the registry and marks all of its faces as
unknown. Run the original sort command again to recluster them:

```powershell
face-sort sort D:\Photos --output D:\Sorted --cache D:\face-sort-cache
```

`split` operates on the entire identity. It does not select individual photos
or faces from that identity.

### Show statistics

```powershell
face-sort stats --cache D:\face-sort-cache
```

This reports the number of registered people, cached media files, detected
faces, assigned faces, and unknown faces.

### Verify the registry

```powershell
face-sort verify --cache D:\face-sort-cache
```

This checks for duplicate IDs or names, invalid display names, dangling person
references, incorrect embedding counts, and cached files missing from the
file index. It prints `Registry OK` and exits successfully when no problems
are found.

### Maintenance paths

The `rename`, `merge`, and `split` commands rewrite the registry and synchronize
the organized output. Pass the same `--input`, `--output`, and `--cache` paths
used by the corresponding `sort` command:

```powershell
face-sort rename PERSON NEW_NAME --input INPUT --output OUTPUT --cache CACHE
face-sort merge TARGET SOURCE --input INPUT --output OUTPUT --cache CACHE
face-sort split PERSON --input INPUT --output OUTPUT --cache CACHE
```

`--input` is optional because face-sort can infer a common input directory
from cached file paths, but specifying the original input root preserves the
intended relative directory layout. Maintenance commands otherwise default
to `output/` and `cache/` under the current directory.

Multi-face media is stored once under `MultipleFaces/`; unmatched or faceless
media goes under `Unknown/`.

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
