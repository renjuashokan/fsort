"""CLIP semantic encoder for face-sort.

Adapted from Immich's machine-learning CLIP implementation.
Downloads the ONNX model from HuggingFace (immich-app/<model>) on first use
and caches it alongside the InsightFace models.

Supported model names (from Immich's constants):
  ViT-B-32__openai       (87 MB visual + 64 MB text) — recommended default
  ViT-B-16__openai       (343 MB)
  ViT-L-14__openai       (890 MB)
  XLM-Roberta-Large-ViT-B-32  (multilingual)
"""
from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Text helpers (verbatim from Immich transforms.py / textual.py)
# ---------------------------------------------------------------------------

_PUNCTUATION_TRANS = str.maketrans("", "", string.punctuation)


def _clean_text(text: str, canonicalize: bool = False) -> str:
    text = " ".join(text.split())
    if canonicalize:
        text = text.translate(_PUNCTUATION_TRANS).lower()
    return text


def _serialize(arr: NDArray[np.float32]) -> list[float]:
    return arr.tolist()


# ---------------------------------------------------------------------------
# Image preprocessing helpers (verbatim from Immich transforms.py / visual.py)
# ---------------------------------------------------------------------------

def _resize_pil(img: Any, size: int) -> Any:
    from PIL import Image as PILImage
    if img.width < img.height:
        return img.resize((size, int((img.height / img.width) * size)), resample=PILImage.Resampling.BICUBIC)
    else:
        return img.resize((int((img.width / img.height) * size), size), resample=PILImage.Resampling.BICUBIC)


def _crop_pil(img: Any, size: int) -> Any:
    left = int((img.size[0] / 2) - (size / 2))
    upper = int((img.size[1] / 2) - (size / 2))
    right = left + size
    lower = upper + size
    return img.crop((left, upper, right, lower))


def _get_pil_resampling(resample: str) -> Any:
    from PIL import Image as PILImage
    methods = {r.name.lower(): r for r in PILImage.Resampling}
    return methods[resample.lower()]


def _decode_pil(source: bytes | Path) -> Any:
    from PIL import Image as PILImage
    from io import BytesIO
    if isinstance(source, Path):
        img = PILImage.open(source)
    else:
        img = PILImage.open(BytesIO(source))
    img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _normalize(img: NDArray[np.float32], mean: NDArray[np.float32], std: NDArray[np.float32]) -> NDArray[np.float32]:
    return (img - mean) / std


def _to_numpy(img: Any) -> NDArray[np.float32]:
    return np.asarray(img, dtype=np.float32) / 255.0


# ---------------------------------------------------------------------------
# Model download
# ---------------------------------------------------------------------------

_HF_REPO_PREFIX = "immich-app"


def _model_dir(cache_root: Path, model_name: str) -> Path:
    """Return the local directory where a model is cached."""
    # Immich stores models like:  cache/<task>/<model_name>/
    # We'll use:                  cache/clip/<model_name>/
    return cache_root / "clip" / model_name


def _clean_model_name(name: str) -> str:
    return name.replace("/", "__")


def _download_model(model_name: str, cache_root: Path) -> Path:
    """Download the CLIP model from HuggingFace if not already cached."""
    from huggingface_hub import snapshot_download

    dest = _model_dir(cache_root, model_name)
    dest.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded (has at least the visual model file)
    visual_onnx = dest / "visual" / "model.onnx"
    if visual_onnx.is_file():
        return dest

    clean = _clean_model_name(model_name)
    repo_id = f"{_HF_REPO_PREFIX}/{clean}"
    print(f"[clip] Downloading CLIP model '{model_name}' from HuggingFace ({repo_id})...")
    print("[clip] This only happens once. Please wait...")
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest),
        ignore_patterns=["*.armnn", "*.rknn"],
    )
    return dest


# ---------------------------------------------------------------------------
# CLIP Visual Encoder
# ---------------------------------------------------------------------------

class ClipVisualEncoder:
    """Encodes images into CLIP embedding vectors.

    Mirrors Immich's OpenClipVisualEncoder.
    """

    def __init__(self, model_name: str, cache_root: Path, providers: list[str] | None = None):
        self.model_name = model_name
        self.model_dir = _download_model(model_name, cache_root)
        self._providers = providers or ["CPUExecutionProvider"]
        self._session = None
        self._size: int = 224
        self._mean: NDArray[np.float32] = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
        self._std: NDArray[np.float32] = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

    def _load(self) -> None:
        import onnxruntime as ort

        visual_onnx = self.model_dir / "visual" / "model.onnx"
        if not visual_onnx.is_file():
            raise FileNotFoundError(f"CLIP visual model not found: {visual_onnx}")

        self._session = ort.InferenceSession(str(visual_onnx), providers=self._providers)

        # Load preprocessing config
        preprocess_cfg_path = self.model_dir / "visual" / "preprocess_cfg.json"
        if preprocess_cfg_path.is_file():
            cfg: dict[str, Any] = json.loads(preprocess_cfg_path.read_text())
            size = cfg.get("size", 224)
            self._size = size[0] if isinstance(size, list) else int(size)
            if "mean" in cfg:
                self._mean = np.array(cfg["mean"], dtype=np.float32)
            if "std" in cfg:
                self._std = np.array(cfg["std"], dtype=np.float32)

    @property
    def session(self) -> Any:
        if self._session is None:
            self._load()
        return self._session

    def encode(self, image_path: Path) -> NDArray[np.float32]:
        """Return a unit-norm float32 embedding vector for the given image path."""
        img = _decode_pil(image_path)
        img = _resize_pil(img, self._size)
        img = _crop_pil(img, self._size)
        img_np = _to_numpy(img)
        img_np = _normalize(img_np, self._mean, self._std)
        # HWC → CHW → add batch dim
        img_input = np.expand_dims(img_np.transpose(2, 0, 1), 0)
        result: NDArray[np.float32] = self.session.run(None, {"image": img_input})[0][0]
        return result

    def encode_bytes(self, image_bytes: bytes) -> NDArray[np.float32]:
        """Return a float32 embedding for raw image bytes."""
        img = _decode_pil(image_bytes)
        img = _resize_pil(img, self._size)
        img = _crop_pil(img, self._size)
        img_np = _to_numpy(img)
        img_np = _normalize(img_np, self._mean, self._std)
        img_input = np.expand_dims(img_np.transpose(2, 0, 1), 0)
        result: NDArray[np.float32] = self.session.run(None, {"image": img_input})[0][0]
        return result


# ---------------------------------------------------------------------------
# CLIP Textual Encoder
# ---------------------------------------------------------------------------

class ClipTextualEncoder:
    """Encodes text queries into CLIP embedding vectors.

    Mirrors Immich's OpenClipTextualEncoder.
    """

    def __init__(self, model_name: str, cache_root: Path, providers: list[str] | None = None):
        self.model_name = model_name
        self.model_dir = _download_model(model_name, cache_root)
        self._providers = providers or ["CPUExecutionProvider"]
        self._session = None
        self._tokenizer = None
        self._canonicalize = False

    def _load(self) -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        textual_onnx = self.model_dir / "textual" / "model.onnx"
        if not textual_onnx.is_file():
            raise FileNotFoundError(f"CLIP textual model not found: {textual_onnx}")

        self._session = ort.InferenceSession(str(textual_onnx), providers=self._providers)

        # Load tokenizer
        tokenizer_path = self.model_dir / "textual" / "tokenizer.json"
        tokenizer_cfg_path = self.model_dir / "textual" / "tokenizer_config.json"
        model_cfg_path = self.model_dir / "config.json"

        context_length = 77  # default for most CLIP models
        if model_cfg_path.is_file():
            cfg: dict[str, Any] = json.loads(model_cfg_path.read_text())
            text_cfg = cfg.get("text_cfg", {})
            context_length = text_cfg.get("context_length", 77)

            # Check for canonicalize flag
            tokenizer_kwargs = text_cfg.get("tokenizer_kwargs")
            if tokenizer_kwargs and tokenizer_kwargs.get("clean") == "canonicalize":
                self._canonicalize = True

        pad_token = "<|endoftext|>"  # default for openai CLIP
        if tokenizer_cfg_path.is_file():
            tok_cfg: dict[str, Any] = json.loads(tokenizer_cfg_path.read_text())
            pad_token = tok_cfg.get("pad_token", pad_token)

        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        pad_id = self._tokenizer.token_to_id(pad_token)
        if pad_id is None:
            # Fallback: use 0
            pad_id = 0
        self._tokenizer.enable_padding(length=context_length, pad_token=pad_token, pad_id=pad_id)
        self._tokenizer.enable_truncation(max_length=context_length)

    @property
    def session(self) -> Any:
        if self._session is None:
            self._load()
        return self._session

    @property
    def tokenizer(self) -> Any:
        if self._tokenizer is None:
            self._load()
        return self._tokenizer

    def encode(self, text: str) -> NDArray[np.float32]:
        """Return a unit-norm float32 embedding vector for the given text."""
        text = _clean_text(text, canonicalize=self._canonicalize)
        tokens = self.tokenizer.encode(text)
        token_ids = np.array([tokens.ids], dtype=np.int32)

        # Determine input name: OpenCLIP uses "text", mCLIP uses "input_ids"
        inputs_info = self.session.get_inputs()
        input_name = inputs_info[0].name if inputs_info else "text"

        result: NDArray[np.float32] = self.session.run(None, {input_name: token_ids})[0][0]
        return result


# ---------------------------------------------------------------------------
# Convenience: cosine similarity
# ---------------------------------------------------------------------------

def cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
    """Return the cosine similarity between two 1-D vectors."""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def serialize_clip_embedding(arr: NDArray[np.float32] | list[float]) -> bytes:
    return np.asarray(arr, dtype=np.float32).tobytes()


def deserialize_clip_embedding(blob: bytes | None) -> NDArray[np.float32] | None:
    if not blob:
        return None
    return np.frombuffer(blob, dtype=np.float32).copy()
