from __future__ import annotations

import os
import sys
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

        if self.config.video_single_frame:
            # Single-frame mode: seek to video_interval seconds and read one frame.
            target_frame = max(0, round(fps * self.config.video_interval))
            capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ok, frame = capture.read()
            capture.release()
            if not ok or frame is None:
                # Seek failed — fall back to frame 0
                capture2 = cv2.VideoCapture(str(path))
                ok, frame = capture2.read()
                capture2.release()
                target_frame = 0
            if not ok or frame is None:
                return []
            records = []
            for face in self._faces_from_frame(frame):
                face.frame = target_frame
                records.append(face)
            return records

        # Default: sample every video_interval seconds throughout the video
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
        try:
            return self._detect_faces(frame)
        except Exception as exc:
            # cuDNN kernel compatibility errors (e.g. SM 6.1 not supported by
            # cuDNN 9 in onnxruntime-gpu 1.24+) surface here as a RuntimeError
            # or onnxruntime Fail error during the first inference call.
            # If we were using GPU, tear it down and retry on CPU.
            if self._app is not None and self.config.gpu:
                msg = str(exc)
                if any(
                    kw in msg
                    for kw in (
                        "no kernel image",
                        "CUDNN_BACKEND_API_FAILED",
                        "cudaErrorNoKernelImageForDevice",
                        "CUDNN_FE failure",
                    )
                ):
                    import warnings

                    warnings.warn(
                        f"cuDNN kernel error — GPU (SM {self._gpu_sm()}) is not "
                        "supported by the installed cuDNN version. "
                        "Falling back to CPU for all remaining frames. "
                        "Set gpu: false in config.yaml to suppress this warning.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    self._app = None  # force re-init on next call
                    import dataclasses

                    self.config = dataclasses.replace(self.config, gpu=False)
                    return self._detect_faces(frame)  # retry with CPU
            raise

    @staticmethod
    def _gpu_sm() -> str:
        try:
            import subprocess

            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
                text=True,
                timeout=3,
            )
            return out.strip().split("\n")[0].strip()
        except Exception:
            return "unknown"

    def _detect_faces(self, frame: np.ndarray) -> list[FaceRecord]:
        records = []
        for face in self._model().get(frame):
            box = np.asarray(face.bbox, dtype=np.float32)
            width, height = box[2] - box[0], box[3] - box[1]
            if min(width, height) < self.config.min_face_size:
                continue
            embedding = getattr(face, "normed_embedding", None)
            if embedding is None:
                embedding = normalized(face.embedding)
            records.append(
                FaceRecord(
                    embedding=np.asarray(embedding).tolist(),
                    bbox_x=int(box[0]),
                    bbox_y=int(box[1]),
                    bbox_w=int(width),
                    bbox_h=int(height),
                    confidence=(
                        float(face.det_score) if hasattr(face, "det_score") else None
                    ),
                )
            )
        return records

    def _model(self):
        if self._app is None:
            import onnxruntime as ort
            from insightface.app import FaceAnalysis

            if self.config.gpu:
                if hasattr(ort, "preload_dlls"):
                    # Windows: load CUDA/cuDNN DLLs from nvidia site-package wheels.
                    self._add_nvidia_dll_directories()
                    ort.preload_dlls(directory="")
                    self._preload_cudnn_sublibraries()
                else:
                    # Linux: nvidia-* wheels ship .so files under
                    # site-packages/nvidia/<pkg>/lib/.  These aren't on
                    # LD_LIBRARY_PATH by default, so we pre-load them via
                    # ctypes so the dynamic linker can resolve them when
                    # onnxruntime opens its CUDA plugin.
                    self._preload_nvidia_linux_libs()

            available = ort.get_available_providers()
            if self.config.gpu:
                if "CUDAExecutionProvider" not in available:
                    import warnings

                    warnings.warn(
                        "GPU mode requested but CUDAExecutionProvider is not available "
                        f"(providers: {', '.join(available)}). "
                        "Falling back to CPU. Check NVIDIA driver, CUDA runtime, and "
                        "onnxruntime-gpu installation.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    providers = ["CPUExecutionProvider"]
                    ctx_id = -1
                else:
                    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                    ctx_id = 0
            else:
                providers = ["CPUExecutionProvider"]
                ctx_id = -1
            self._app = FaceAnalysis(
                name=self.config.model_name,
                providers=providers,
            )
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

    def _preload_nvidia_linux_libs(self) -> None:
        """Pre-load CUDA/cuDNN shared libraries from nvidia-* pip wheels on Linux.

        onnxruntime-gpu ships CUDA runtime, cuBLAS, cuDNN, etc. as separate
        nvidia-* wheels.  Their .so files live under:
            <site-packages>/nvidia/<package>/lib/*.so.*

        These directories are not on LD_LIBRARY_PATH by default, so
        CUDAExecutionProvider won't register unless we load the libraries
        first via ctypes.
        """
        if sys.platform == "win32":
            return
        import ctypes

        for entry in map(Path, sys.path):
            nvidia_root = entry / "nvidia"
            if not nvidia_root.is_dir():
                continue
            for lib_dir in sorted(nvidia_root.glob("*/lib")):
                if not lib_dir.is_dir():
                    continue
                for so_file in sorted(lib_dir.glob("*.so*")):
                    if so_file.is_file() and not so_file.is_symlink():
                        try:
                            self._dll_libraries.append(
                                ctypes.CDLL(str(so_file), mode=ctypes.RTLD_GLOBAL)
                            )
                        except OSError:
                            pass  # skip libs that fail to load (wrong arch, etc.)

    def _preload_cudnn_sublibraries(self) -> None:
        if sys.platform != "win32":
            return
        import ctypes

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
        if any(
            resolved == item or item in resolved.parents for item in excluded_resolved
        ):
            continue
        yield resolved
