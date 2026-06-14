from pathlib import Path
import pytest
import numpy as np
import cv2

from fsort.config import Config
from fsort.models import FaceRecord
from fsort.service import FsortService


class FakeExtractor:
    def __init__(self, face_records: dict[str, list[FaceRecord]]):
        self.face_records = face_records
        self.calls: list[str] = []

    def extract(self, path: Path) -> list[FaceRecord]:
        self.calls.append(path.name)
        return self.face_records[path.name]


def test_thumbnail_generation_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "photos"
    output = tmp_path / "output"
    cache = tmp_path / "cache"
    source.mkdir()

    # Create dummy images (a is pure red, b is pure blue)
    img_a = np.zeros((100, 100, 3), dtype=np.uint8)
    img_a[:, :, 2] = 255  # Red in BGR (OpenCV uses BGR, so index 2 is red)
    cv2.imwrite(str(source / "a.jpg"), img_a)

    img_b = np.zeros((100, 100, 3), dtype=np.uint8)
    img_b[:, :, 0] = 255  # Blue in BGR (index 0 is blue)
    cv2.imwrite(str(source / "b.jpg"), img_b)

    config = Config(min_samples=2, dbscan_eps=0.1, match_threshold=0.1)
    service = FsortService(cache, output, config)

    # Face embeddings:
    # a.jpg: embedding closer to the centroid [1.0, 0.0]
    # b.jpg: embedding further away, but within dbscan_eps (0.1)
    face_a = FaceRecord(
        embedding=[1.0, 0.0],
        bbox_x=10,
        bbox_y=10,
        bbox_w=80,
        bbox_h=80,
    )
    face_b = FaceRecord(
        embedding=[0.99, 0.01],
        bbox_x=20,
        bbox_y=20,
        bbox_w=60,
        bbox_h=60,
    )

    fake_extractor = FakeExtractor({"a.jpg": [face_a], "b.jpg": [face_b]})
    monkeypatch.setattr(
        "fsort.extractor.FaceExtractor",
        lambda *args, **kwargs: fake_extractor,
    )

    # 1. Run Extract & Organize
    service.extract(source, show_progress=False)
    service.organize(source)

    # Verify output directory and thumbnail exist
    person_folder = output / "Person_001"
    assert person_folder.exists()
    assert (person_folder / "a.jpg").exists()
    assert (person_folder / "b.jpg").exists()
    
    thumb_path = person_folder / "thumbnail_fsort.jpg"
    assert thumb_path.exists()

    # Read generated thumbnail and verify shape
    thumb = cv2.imread(str(thumb_path))
    assert thumb.shape == (256, 256, 3)

    # Verify that red image (a.jpg) was chosen because its embedding [1.0, 0.0]
    # is closer to the centroid (mean of [1.0, 0.0] and [0.5, 0.866] is [0.75, 0.433],
    # and [1.0, 0.0] is closer than [0.5, 0.866]).
    # We check the average color to make sure it's red (high red value, low blue value).
    # Since in BGR, index 2 is Red and index 0 is Blue.
    avg_blue = thumb[:, :, 0].mean()
    avg_red = thumb[:, :, 2].mean()
    assert avg_red > 200
    assert avg_blue < 50

    # 2. Test Standalone Thumbnail Regeneration
    # Delete thumbnail file
    thumb_path.unlink()
    assert not thumb_path.exists()

    # Generate via service method
    count = service.generate_thumbnails()
    assert count == 1
    assert thumb_path.exists()

    # 3. Test Rename Cleanup
    # Rename person to "Jane Doe"
    service.rename("Person_001", "Jane Doe", source)
    
    # Verify old folder is removed (meaning thumbnail inside it was cleaned up first)
    assert not person_folder.exists()
    
    # Verify new folder has the thumbnail
    new_folder = output / "Jane Doe"
    assert new_folder.exists()
    assert (new_folder / "thumbnail_fsort.jpg").exists()

    # 4. Test Split Cleanup
    # Split Jane Doe
    service.split("Jane Doe", source)
    
    # Verify the thumbnail is cleaned up and folder is removed or empty of thumbnails
    assert not (new_folder / "thumbnail_fsort.jpg").exists()
