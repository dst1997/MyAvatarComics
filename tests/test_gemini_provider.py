from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from app.config import Settings
from app.models import CharacterProfile, PageSpec
from app.providers.base import ProviderError

pytest.importorskip("google.genai")

from app.providers.gemini_provider import GeminiProvider


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        storage_dir=tmp_path,
        provider="gemini",
        gemini_api_key="test-key",
        gemini_text_model="text-model",
        gemini_image_model="image-model",
        gemini_timeout_seconds=30,
        max_reference_photos=4,
        page_aspect_ratio="2:3",
    )


def make_profile(refs: list[str]) -> CharacterProfile:
    return CharacterProfile(
        display_name="Priya",
        description="a cheerful heroine",
        palette=["#f4a261"],
        media_references=refs,
    )


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 96), "purple").save(buffer, "PNG")
    return buffer.getvalue()


def image_response(data: bytes | None) -> SimpleNamespace:
    parts = [] if data is None else [SimpleNamespace(inline_data=SimpleNamespace(data=data), text=None)]
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=parts))],
        prompt_feedback=None,
    )


class StubModels:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_provider(tmp_path: Path, response) -> tuple[GeminiProvider, StubModels]:
    provider = GeminiProvider(make_settings(tmp_path))
    stub = StubModels(response)
    provider.client = SimpleNamespace(models=stub)
    return provider, stub


def test_generate_page_saves_png(tmp_path: Path) -> None:
    provider, stub = make_provider(tmp_path, image_response(png_bytes()))
    page = PageSpec(page_number=2, title="T", panels=["p"], narration="n", image_prompt="scene")
    output = tmp_path / "pages" / "page-02.png"

    asyncio.run(provider.generate_page(make_profile([]), page, "My Comic", None, output))

    assert output.exists()
    with Image.open(output) as image:
        assert image.format == "PNG"
    assert stub.calls[0]["model"] == "image-model"


def test_generate_page_raises_provider_error_without_image(tmp_path: Path) -> None:
    provider, _ = make_provider(tmp_path, image_response(None))
    page = PageSpec(page_number=2, title="T", panels=["p"], narration="n", image_prompt="scene")

    with pytest.raises(ProviderError):
        asyncio.run(provider.generate_page(make_profile([]), page, "My Comic", None, tmp_path / "out.png"))


def test_build_story_parses_json_schema_response(tmp_path: Path) -> None:
    pages = [
        {
            "page_number": number,
            "title": f"Page {number}",
            "panels": ["a panel"],
            "narration": "narration",
            "dialogue": [],
            "image_prompt": "prompt",
        }
        for number in range(1, 9)
    ]
    payload = {"comic_title": "The Big Day", "pages": pages}
    response = SimpleNamespace(text=json.dumps(payload))
    provider, stub = make_provider(tmp_path, response)
    spec_kwargs = dict(
        consent_given=True,
        recipient_name="Priya",
        occasion="Graduation",
        event_details="She graduated.",
    )
    from app.models import ProjectSpec

    script = asyncio.run(provider.build_story(ProjectSpec(**spec_kwargs), make_profile([])))

    assert script.comic_title == "The Big Day"
    assert len(script.pages) == 8
    assert stub.calls[0]["model"] == "text-model"
