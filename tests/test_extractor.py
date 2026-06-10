import sys
from types import ModuleType, SimpleNamespace

import pytest

from fsort.config import Config
from fsort.extractor import FaceExtractor


def test_gpu_mode_rejects_missing_cuda_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ModuleType("onnxruntime")
    runtime.get_available_providers = lambda: ["CPUExecutionProvider"]  # type: ignore[attr-defined]
    insightface = ModuleType("insightface")
    insightface_app = ModuleType("insightface.app")
    insightface_app.FaceAnalysis = object  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "onnxruntime", runtime)
    monkeypatch.setitem(sys.modules, "insightface", insightface)
    monkeypatch.setitem(sys.modules, "insightface.app", insightface_app)

    with pytest.raises(RuntimeError, match="CUDAExecutionProvider"):
        FaceExtractor(Config(gpu=True))._model()


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

    FaceExtractor(Config(gpu=True))._model()

    assert captured["providers"] == [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    assert captured["ctx_id"] == 0
