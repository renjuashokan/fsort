from __future__ import annotations

import os
import sys
import ctypes
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from .config import Config
from .models import FaceRecord, normalized

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


class FaceExtractor:
    def __init__(self, config: Config):
        self.config = config
        self._app = None
        self._dll_directories: list[object] = []
        self._dll_libraries: list[object] = []

    def extract(self, path: Path) -> list[FaceRecord]:
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            return self._extract_video(path)
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError("OpenCV could not decode the image")
        return self._faces_from_frame(image)

    def _extract_video(self, path: Path) -> list[FaceRecord]:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise ValueError("OpenCV could not open the video")
        fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        step = max(1, round(fps * self.config.video_interval))
        records: list[FaceRecord] = []
        frame_number = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_number % step == 0:
                    for face in self._faces_from_frame(frame):
                        face.frame = frame_number
                        records.append(face)
                frame_number += 1
        finally:
            capture.release()
        return records

    def _faces_from_frame(self, frame: np.ndarray) -> list[FaceRecord]:
        records = []
        for face in self._model().get(frame):
            box = np.asarray(face.bbox, dtype=np.float32)
            width, height = box[2] - box[0], box[3] - box[1]
            if min(width, height) < self.config.min_face_size:
                continue
            embedding = getattr(face, "normed_embedding", None)
            if embedding is None:
                embedding = normalized(face.embedding)
            records.append(FaceRecord(embedding=np.asarray(embedding).tolist()))
        return records

    def _model(self):
        if self._app is None:
            import onnxruntime as ort
            from insightface.app import FaceAnalysis

            if self.config.gpu and hasattr(ort, "preload_dlls"):
                self._add_nvidia_dll_directories()
                # Load CUDA and cuDNN installed in Python site-packages.
                ort.preload_dlls(directory="")
                self._preload_cudnn_sublibraries()
            available = ort.get_available_providers()
            if self.config.gpu:
                if "CUDAExecutionProvider" not in available:
                    raise RuntimeError(
                        "GPU mode requires ONNX Runtime's CUDAExecutionProvider, "
                        f"but available providers are: {', '.join(available)}. "
                        "Check the NVIDIA driver, CUDA/cuDNN runtime, and "
                        "onnxruntime-gpu installation."
                    )
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                providers = ["CPUExecutionProvider"]
            self._app = FaceAnalysis(
                name=self.config.model_name,
                providers=providers,
            )
            ctx_id = 0 if self.config.gpu else -1
            self._app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        return self._app

    def _add_nvidia_dll_directories(self) -> None:
        if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
            return
        for entry in map(Path, sys.path):
            nvidia_root = entry / "nvidia"
            if not nvidia_root.is_dir():
                continue
            for bin_dir in nvidia_root.glob("*/bin"):
                if bin_dir.is_dir():
                    self._dll_directories.append(
                        os.add_dll_directory(str(bin_dir.resolve()))
                    )

    def _preload_cudnn_sublibraries(self) -> None:
        if sys.platform != "win32":
            return
        load_order = (
            "cudnn64_9.dll",
            "cudnn_ops64_9.dll",
            "cudnn_cnn64_9.dll",
            "cudnn_adv64_9.dll",
            "cudnn_graph64_9.dll",
            "cudnn_heuristic64_9.dll",
            "cudnn_engines_precompiled64_9.dll",
            "cudnn_engines_runtime_compiled64_9.dll",
            "cudnn_engines_tensor_ir64_9.dll",
            "cudnn_ext64_9.dll",
        )
        for entry in map(Path, sys.path):
            cudnn_bin = entry / "nvidia" / "cudnn" / "bin"
            if not cudnn_bin.is_dir():
                continue
            for name in load_order:
                path = cudnn_bin / name
                if path.is_file():
                    self._dll_libraries.append(ctypes.CDLL(str(path)))
            return


def iter_media(root: Path, excluded: list[Path] | None = None) -> Iterator[Path]:
    excluded_resolved = [path.resolve() for path in excluded or []]
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        resolved = path.resolve()
        if any(resolved == item or item in resolved.parents for item in excluded_resolved):
            continue
        yield resolved
