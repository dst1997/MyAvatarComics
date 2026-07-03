from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from app.models import UploadedMedia
from app.storage import PHOTO_EXTENSIONS


class MediaValidationError(ValueError):
    pass


def validate_media_requirements(media: list[UploadedMedia]) -> None:
    photos = [item for item in media if item.kind == "photo"]
    if len(photos) < 1:
        raise MediaValidationError("Please upload at least 1 clear photo of the person the comic is for.")
    if len(photos) > 8:
        raise MediaValidationError("Please upload no more than 8 photos.")


def prepare_photo_references(media: list[UploadedMedia], max_refs: int = 6) -> list[str]:
    refs: list[str] = []
    for item in media:
        path = Path(item.path)
        if item.kind in {"photo", "frame"} and path.suffix.lower() in PHOTO_EXTENSIONS and path.exists():
            normalize_image(path)
            refs.append(str(path))
        if len(refs) >= max_refs:
            break
    return refs


def extract_video_frames(media: list[UploadedMedia], frames_dir: Path, max_frames_per_video: int = 3) -> tuple[list[UploadedMedia], list[str]]:
    warnings: list[str] = []
    extracted: list[UploadedMedia] = []
    videos = [item for item in media if item.kind == "video"]
    if not videos:
        return extracted, warnings
    try:
        import cv2  # type: ignore
    except ImportError:
        warnings.append("Video uploads were saved, but frame extraction needs opencv-python-headless installed.")
        return extracted, warnings

    frames_dir.mkdir(parents=True, exist_ok=True)
    for video in videos:
        capture = cv2.VideoCapture(video.path)
        if not capture.isOpened():
            warnings.append(f"Could not open video {video.original_name} for frame extraction.")
            continue
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            warnings.append(f"Could not read frames from video {video.original_name}.")
            capture.release()
            continue
        sample_indexes = evenly_spaced_indexes(total_frames, max_frames_per_video)
        for index in sample_indexes:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                continue
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            stored_name = f"{Path(video.stored_name).stem}-frame-{index}.jpg"
            path = frames_dir / stored_name
            image.save(path, "JPEG", quality=88)
            extracted.append(
                UploadedMedia(
                    kind="frame",
                    original_name=f"{video.original_name} frame {index}",
                    stored_name=stored_name,
                    path=str(path),
                    content_type="image/jpeg",
                    size_bytes=path.stat().st_size,
                )
            )
        capture.release()
    return extracted, warnings


def evenly_spaced_indexes(total: int, count: int) -> list[int]:
    if count <= 0:
        return []
    if total <= count:
        return list(range(total))
    step = (total - 1) / (count + 1)
    return [max(0, min(total - 1, round(step * (i + 1)))) for i in range(count)]


def normalize_image(path: Path, max_side: int = 1600) -> None:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((max_side, max_side))
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            image.save(path, "JPEG", quality=90)
        else:
            image.save(path)

