from __future__ import annotations

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


def iter_media(root: Path, excluded: list[Path] | None = None) -> Iterator[Path]:
    excluded_resolved = [path.resolve() for path in excluded or []]
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        resolved = path.resolve()
        if any(resolved == item or item in resolved.parents for item in excluded_resolved):
            continue
        yield resolved
