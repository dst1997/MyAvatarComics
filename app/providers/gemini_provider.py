from __future__ import annotations

import asyncio
import json
import mimetypes
from pathlib import Path

from PIL import Image

from app.config import Settings
from app.models import CharacterProfile, PageSpec, ProjectSpec, StoryScript
from app.providers.base import ProviderError
from app.story import (
    build_character_prompt,
    build_character_sheet_prompt,
    build_page_prompt,
    build_story_prompt,
)


CHARACTER_PROFILE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "display_name": {"type": "STRING"},
        "description": {"type": "STRING"},
        "palette": {"type": "ARRAY", "items": {"type": "STRING"}, "minItems": 1, "maxItems": 6},
        "outfit_notes": {"type": "STRING"},
        "accessory_notes": {"type": "STRING"},
    },
    "required": ["display_name", "description", "palette", "outfit_notes", "accessory_notes"],
}

STORY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "comic_title": {"type": "STRING"},
        "pages": {
            "type": "ARRAY",
            "minItems": 8,
            "maxItems": 8,
            "items": {
                "type": "OBJECT",
                "properties": {
                    "page_number": {"type": "INTEGER"},
                    "title": {"type": "STRING"},
                    "panels": {"type": "ARRAY", "items": {"type": "STRING"}, "minItems": 1, "maxItems": 4},
                    "narration": {"type": "STRING"},
                    "dialogue": {"type": "ARRAY", "items": {"type": "STRING"}, "maxItems": 4},
                    "image_prompt": {"type": "STRING"},
                },
                "required": ["page_number", "title", "panels", "narration", "dialogue", "image_prompt"],
            },
        },
    },
    "required": ["comic_title", "pages"],
}


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: Settings):
        self.settings = settings
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderError("Install the google-genai package or set COMIC_AI_PROVIDER=mock.") from exc
        self._types = types
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.gemini_timeout_seconds * 1000)),
        )

    async def describe_character(self, spec: ProjectSpec, media_refs: list[str]) -> CharacterProfile:
        prompt = build_character_prompt(spec, len(media_refs))
        parts = [prompt] + self._image_parts(media_refs)

        def call() -> CharacterProfile:
            response = self.client.models.generate_content(
                model=self.settings.gemini_text_model,
                contents=parts,
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CHARACTER_PROFILE_SCHEMA,
                ),
            )
            data = json.loads(response.text)
            data["media_references"] = media_refs
            return CharacterProfile.model_validate(data)

        return await self._run("character profile", call)

    async def build_story(self, spec: ProjectSpec, profile: CharacterProfile) -> StoryScript:
        prompt = build_story_prompt(spec, profile)

        def call() -> StoryScript:
            response = self.client.models.generate_content(
                model=self.settings.gemini_text_model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=STORY_SCHEMA,
                ),
            )
            return StoryScript.model_validate(json.loads(response.text))

        return await self._run("story script", call)

    async def create_character_sheet(self, profile: CharacterProfile, output_path: Path) -> None:
        prompt = build_character_sheet_prompt(profile)
        parts = [prompt] + self._image_parts(profile.media_references)

        def call() -> None:
            response = self._generate_image(parts)
            self._save_image_response(response, output_path)

        await self._run("character sheet", call)

    async def generate_page(
        self,
        profile: CharacterProfile,
        page: PageSpec,
        comic_title: str,
        character_sheet_path: Path | None,
        output_path: Path,
    ) -> None:
        prompt = build_page_prompt(profile, page, comic_title)
        refs: list[str] = []
        if character_sheet_path and character_sheet_path.exists():
            refs.append(str(character_sheet_path))
        refs.extend(profile.media_references[:2])
        parts = [prompt] + self._image_parts(refs)

        def call() -> None:
            response = self._generate_image(parts)
            self._save_image_response(response, output_path)

        await self._run(f"page {page.page_number}", call)

    def _generate_image(self, parts: list[object]) -> object:
        config = self._types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=self._types.ImageConfig(aspect_ratio=self.settings.page_aspect_ratio),
        )
        return self.client.models.generate_content(
            model=self.settings.gemini_image_model,
            contents=parts,
            config=config,
        )

    def _save_image_response(self, response: object, output_path: Path) -> None:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                inline = getattr(part, "inline_data", None)
                if inline is not None and getattr(inline, "data", None):
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(inline.data)
                    ensure_png(output_path)
                    return
        feedback = getattr(response, "prompt_feedback", None)
        detail = f" ({feedback})" if feedback else ""
        raise ProviderError(f"Gemini did not return an image{detail}.")

    def _image_parts(self, paths: list[str]) -> list[object]:
        parts = []
        for raw in paths[: self.settings.max_reference_photos + 1]:
            path = Path(raw)
            if not path.exists():
                continue
            mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            parts.append(self._types.Part.from_bytes(data=path.read_bytes(), mime_type=mime))
        return parts

    async def _run(self, step: str, call, attempts: int = 3):
        # Transient 429/5xx spikes are common; retrying here keeps one blip from
        # failing an 11-call generation run.
        delay = 5.0
        for attempt in range(1, attempts + 1):
            try:
                return await asyncio.to_thread(call)
            except ProviderError:
                raise
            except Exception as exc:
                if attempt < attempts and _is_transient(exc):
                    await asyncio.sleep(delay)
                    delay *= 3
                    continue
                raise ProviderError(f"Gemini {step} request failed: {exc}") from exc


def _is_transient(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return code in {429, 500, 502, 503, 504}


def ensure_png(path: Path) -> None:
    """Re-encode whatever Gemini returned as PNG so the rest of the pipeline can rely on it."""
    with Image.open(path) as image:
        image.convert("RGB").save(path, "PNG")
