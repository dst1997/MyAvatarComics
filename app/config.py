from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    storage_dir: Path
    provider: str
    gemini_api_key: str | None
    gemini_text_model: str
    gemini_image_model: str
    gemini_timeout_seconds: float
    max_reference_photos: int
    page_aspect_ratio: str

    @property
    def use_gemini(self) -> bool:
        return self.provider == "gemini" and bool(self.gemini_api_key)


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from .env into os.environ without overriding existing values."""
    env_path = path or (ROOT_DIR / ".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_settings() -> Settings:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    provider = os.getenv("COMIC_AI_PROVIDER", "gemini" if api_key else "mock").strip().lower()
    storage_dir = Path(os.getenv("MYAVATAR_STORAGE_DIR", ROOT_DIR / ".data" / "projects"))
    return Settings(
        storage_dir=storage_dir,
        provider=provider,
        gemini_api_key=api_key,
        gemini_text_model=os.getenv("GEMINI_TEXT_MODEL", "gemini-3.5-flash"),
        gemini_image_model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
        gemini_timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "300")),
        max_reference_photos=_env_int("MYAVATAR_MAX_REFERENCE_PHOTOS", 4, minimum=1),
        page_aspect_ratio=os.getenv("MYAVATAR_PAGE_ASPECT_RATIO", "2:3"),
    )


def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    if minimum is not None:
        return max(minimum, value)
    return value
