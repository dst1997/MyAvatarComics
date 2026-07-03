from __future__ import annotations

import pytest

from app.media import MediaValidationError, evenly_spaced_indexes, validate_media_requirements
from app.models import UploadedMedia


def photo(name: str) -> UploadedMedia:
    return UploadedMedia(kind="photo", original_name=name, stored_name=name, path=name, content_type="image/jpeg", size_bytes=10)


def test_media_requires_one_to_eight_photos() -> None:
    with pytest.raises(MediaValidationError):
        validate_media_requirements([])
    validate_media_requirements([photo("one.jpg")])
    validate_media_requirements([photo(f"{index}.jpg") for index in range(8)])
    with pytest.raises(MediaValidationError):
        validate_media_requirements([photo(f"{index}.jpg") for index in range(9)])


def test_evenly_spaced_indexes_are_inside_frame_count() -> None:
    indexes = evenly_spaced_indexes(total=100, count=3)
    assert indexes == sorted(indexes)
    assert all(0 <= index < 100 for index in indexes)
