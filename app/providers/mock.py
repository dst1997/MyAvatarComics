from __future__ import annotations

from pathlib import Path

from app.models import CharacterProfile, PageSpec, ProjectSpec, StoryScript
from app.rendering import render_mock_art, render_mock_character_sheet
from app.story import build_fallback_profile, build_fallback_story


class MockProvider:
    name = "mock"

    async def describe_character(self, spec: ProjectSpec, media_refs: list[str]) -> CharacterProfile:
        return build_fallback_profile(spec, media_refs)

    async def build_story(self, spec: ProjectSpec, profile: CharacterProfile) -> StoryScript:
        return build_fallback_story(spec, profile)

    async def create_character_sheet(self, profile: CharacterProfile, output_path: Path) -> None:
        render_mock_character_sheet(profile, output_path)

    async def generate_page(
        self,
        profile: CharacterProfile,
        page: PageSpec,
        comic_title: str,
        character_sheet_path: Path | None,
        output_path: Path,
    ) -> None:
        render_mock_art(profile, page, output_path, comic_title=comic_title)
