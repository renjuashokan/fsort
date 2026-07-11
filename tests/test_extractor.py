import ctypes
import sys
from pathlib import Path
from types import ModuleType

import pytest

from fsort.config import Config
from fsort.extractor import FaceExtractor


def test_gpu_mode_falls_back_when_cuda_provider_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ModuleType("onnxruntime")
    runtime.get_available_providers = lambda: ["CPUExecutionProvider"]  # type: ignore[attr-defined]
    insightface = ModuleType("insightface")
    insightface_app = ModuleType("insightface.app")
    captured: dict[str, object] = {}

    class FakeFaceAnalysis:
        def __init__(self, **kwargs: object):
            captured.update(kwargs)

        def prepare(self, **kwargs: object) -> None:
            captured.update(kwargs)

    insightface_app.FaceAnalysis = FakeFaceAnalysis  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "onnxruntime", runtime)
    monkeypatch.setitem(sys.modules, "insightface", insightface)
    monkeypatch.setitem(sys.modules, "insightface.app", insightface_app)

    with pytest.warns(RuntimeWarning, match="Falling back to CPU"):
        FaceExtractor(Config(gpu=True))._model()

    assert captured["providers"] == ["CPUExecutionProvider"]
    assert captured["ctx_id"] == -1


def test_gpu_mode_requests_cuda_first(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = ModuleType("onnxruntime")
    runtime.get_available_providers = lambda: [  # type: ignore[attr-defined]
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    captured: dict[str, object] = {}

    class FakeFaceAnalysis:
        def __init__(self, **kwargs: object):
            captured.update(kwargs)

        def prepare(self, **kwargs: object) -> None:
            captured.update(kwargs)

    insightface = ModuleType("insightface")
    insightface_app = ModuleType("insightface.app")
    insightface_app.FaceAnalysis = FakeFaceAnalysis  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "onnxruntime", runtime)
    monkeypatch.setitem(sys.modules, "insightface", insightface)
    monkeypatch.setitem(sys.modules, "insightface.app", insightface_app)

    extractor = FaceExtractor(Config(gpu=True))
    monkeypatch.setattr(extractor, "_add_nvidia_dll_directories", lambda: None)
    monkeypatch.setattr(extractor, "_preload_cudnn_sublibraries", lambda: None)
    extractor._model()

    assert captured["providers"] == [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    assert captured["ctx_id"] == 0


def test_gpu_mode_retains_nvidia_dll_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cudnn_bin = tmp_path / "nvidia" / "cudnn" / "bin"
    cublas_bin = tmp_path / "nvidia" / "cublas" / "bin"
    cudnn_bin.mkdir(parents=True)
    cublas_bin.mkdir(parents=True)
    handles: list[object] = []

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    def add_dll_directory(path: str) -> object:
        handles.append(path)
        return object()

    monkeypatch.setattr(
        "fsort.extractor.os.add_dll_directory", add_dll_directory, raising=False
    )
    extractor = FaceExtractor(Config(gpu=True))

    extractor._add_nvidia_dll_directories()

    assert set(handles) == {str(cudnn_bin.resolve()), str(cublas_bin.resolve())}
    assert len(extractor._dll_directories) == 2


def test_gpu_mode_preloads_cudnn_sublibraries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cudnn_bin = tmp_path / "nvidia" / "cudnn" / "bin"
    cudnn_bin.mkdir(parents=True)
    for name in ("cudnn64_9.dll", "cudnn_engines_tensor_ir64_9.dll"):
        (cudnn_bin / name).touch()
    loaded: list[str] = []

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    def load_library(path: str) -> object:
        loaded.append(path)
        return object()

    monkeypatch.setattr(ctypes, "CDLL", load_library)
    extractor = FaceExtractor(Config(gpu=True))

    extractor._preload_cudnn_sublibraries()

    assert loaded == [
        str(cudnn_bin / "cudnn64_9.dll"),
        str(cudnn_bin / "cudnn_engines_tensor_ir64_9.dll"),
    ]
    assert len(extractor._dll_libraries) == 2
