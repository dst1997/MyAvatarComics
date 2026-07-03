from __future__ import annotations

from app.models import CharacterProfile, ProjectSpec
from app.story import (
    build_character_prompt,
    build_fallback_story,
    build_page_prompt,
    build_story_prompt,
)


def make_spec() -> ProjectSpec:
    return ProjectSpec(
        consent_given=True,
        recipient_name="Priya",
        relationship="my sister",
        occasion="Graduation day",
        event_details="She graduated with honors and we surprised her with a party.",
        dedication="For Priya, with love.",
    )


def make_profile() -> CharacterProfile:
    return CharacterProfile(
        display_name="Priya",
        description="a cheerful comic heroine with curly dark hair and glasses",
        palette=["#f4a261", "#2a9d8f"],
        outfit_notes="graduation gown",
    )


def test_fallback_story_covers_all_eight_pages() -> None:
    script = build_fallback_story(make_spec(), make_profile())
    assert len(script.pages) == 8
    assert [page.page_number for page in script.pages] == list(range(1, 9))
    assert script.pages[0].kind == "cover"
    assert script.pages[-1].kind == "end"
    assert "Priya" in script.comic_title


def test_story_prompt_mentions_occasion_and_structure() -> None:
    prompt = build_story_prompt(make_spec(), make_profile())
    assert "Graduation day" in prompt
    assert "COVER" in prompt
    assert "END PAGE" in prompt
    assert "For Priya, with love." in prompt


def test_character_prompt_avoids_sensitive_traits() -> None:
    prompt = build_character_prompt(make_spec(), media_count=3)
    assert "non-sensitive traits" in prompt
    assert "Do not guess" in prompt


def test_page_prompt_varies_by_page_kind() -> None:
    script = build_fallback_story(make_spec(), make_profile())
    cover = build_page_prompt(make_profile(), script.pages[0], script.comic_title)
    interior = build_page_prompt(make_profile(), script.pages[3], script.comic_title)
    end = build_page_prompt(make_profile(), script.pages[-1], script.comic_title)
    assert "COVER" in cover and script.comic_title in cover
    assert "panel(s)" in interior
    assert "The End" in end
