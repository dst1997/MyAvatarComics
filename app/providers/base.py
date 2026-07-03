from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.models import CharacterProfile, PageSpec, ProjectSpec, StoryScript


class ProviderError(RuntimeError):
    pass


class AIProvider(Protocol):
    name: str

    async def describe_character(self, spec: ProjectSpec, media_refs: list[str]) -> CharacterProfile:
        ...

    async def build_story(self, spec: ProjectSpec, profile: CharacterProfile) -> StoryScript:
        ...

    async def create_character_sheet(self, profile: CharacterProfile, output_path: Path) -> None:
        ...

    async def generate_page(
        self,
        profile: CharacterProfile,
        page: PageSpec,
        comic_title: str,
        character_sheet_path: Path | None,
        output_path: Path,
    ) -> None:
        ...
