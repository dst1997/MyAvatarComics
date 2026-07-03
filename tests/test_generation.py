from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image

from app.generator import ComicGenerator
from app.models import CharacterProfile, ProjectSpec, StoryScript
from app.providers.mock import MockProvider
from app.storage import ProjectStorage


def make_spec() -> ProjectSpec:
    return ProjectSpec(
        consent_given=True,
        recipient_name="Priya",
        relationship="my sister",
        occasion="Graduation day",
        event_details="She graduated with honors and we surprised her with a party.",
        dedication="For Priya, with love.",
    )


def make_photo(path: Path, color: str) -> bytes:
    Image.new("RGB", (320, 320), color).save(path, "JPEG")
    return path.read_bytes()


def make_project(tmp_path: Path, photo_count: int = 2) -> tuple[ProjectStorage, str]:
    storage = ProjectStorage(tmp_path / "projects")
    project_id = storage.create_project(make_spec())
    colors = ["red", "green", "blue", "orange"]
    for index in range(photo_count):
        source = tmp_path / f"photo-{index}.jpg"
        storage.add_media_file(project_id, source.name, "image/jpeg", make_photo(source, colors[index % len(colors)]))
    return storage, project_id


def test_mock_generation_creates_assets_and_manifest(tmp_path: Path) -> None:
    storage, project_id = make_project(tmp_path)

    manifest = asyncio.run(ComicGenerator(storage, MockProvider()).generate_project(project_id))

    assert manifest.project_id == project_id
    assert len(manifest.pages) == 8
    assert manifest.pages[0].kind == "cover"
    assert manifest.pages[-1].kind == "end"
    assert Path(manifest.pdf_path).exists()
    assert all(page.image_path and Path(page.image_path).exists() for page in manifest.pages)
    assert manifest.character_profile.character_sheet_path
    assert Path(manifest.character_profile.character_sheet_path).exists()
    assert "Priya" in manifest.title
    assert storage.load_status(project_id).status == "complete"


class FailingTextProvider(MockProvider):
    """Simulates AI text failures to exercise the fallback path."""

    async def describe_character(self, spec, media_refs) -> CharacterProfile:
        raise RuntimeError("character model unavailable")

    async def build_story(self, spec, profile) -> StoryScript:
        raise RuntimeError("story model unavailable")


def test_generation_falls_back_when_text_steps_fail(tmp_path: Path) -> None:
    storage, project_id = make_project(tmp_path)

    manifest = asyncio.run(ComicGenerator(storage, FailingTextProvider()).generate_project(project_id))

    assert len(manifest.pages) == 8
    assert len(manifest.warnings) == 2
    assert manifest.character_profile.display_name == "Priya"
    assert storage.load_status(project_id).status == "complete"


def test_regenerate_single_page(tmp_path: Path) -> None:
    storage, project_id = make_project(tmp_path)
    generator = ComicGenerator(storage, MockProvider())
    asyncio.run(generator.generate_project(project_id))

    page_path = Path(storage.load_manifest(project_id).pages[2].image_path)
    before = page_path.stat().st_mtime_ns
    page_path.unlink()

    updated = asyncio.run(generator.regenerate_page(project_id, 3))

    assert Path(updated.pages[2].image_path).exists()
    assert Path(updated.pages[2].image_path).stat().st_mtime_ns != before
    assert storage.load_status(project_id).status == "complete"


def test_delete_project_removes_local_files(tmp_path: Path) -> None:
    storage = ProjectStorage(tmp_path / "projects")
    project_id = storage.create_project(make_spec())
    project_dir = storage.require_project_dir(project_id)
    storage.delete_project(project_id)
    assert not project_dir.exists()
