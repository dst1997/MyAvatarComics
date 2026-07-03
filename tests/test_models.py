from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import PageSpec, ProjectSpec, StoryScript


def make_spec(**overrides) -> ProjectSpec:
    data = {
        "consent_given": True,
        "recipient_name": "Priya",
        "occasion": "Graduation day",
        "event_details": "She graduated with honors and the family celebrated.",
    }
    data.update(overrides)
    return ProjectSpec(**data)


def test_project_spec_requires_consent() -> None:
    with pytest.raises(ValidationError):
        make_spec(consent_given=False)


def test_project_spec_strips_whitespace() -> None:
    spec = make_spec(recipient_name="  Priya  ", occasion=" Graduation   day ")
    assert spec.recipient_name == "Priya"
    assert spec.occasion == "Graduation day"


def test_page_kind_follows_page_number() -> None:
    def page(number: int) -> PageSpec:
        return PageSpec(page_number=number, title="T", panels=["p"], narration="n", image_prompt="i")

    assert page(1).kind == "cover"
    assert page(4).kind == "story"
    assert page(8).kind == "end"


def test_story_script_requires_pages_one_through_eight() -> None:
    pages = [
        PageSpec(page_number=number, title="T", panels=["p"], narration="n", image_prompt="i")
        for number in [1, 2, 3, 4, 5, 6, 7, 7]
    ]
    with pytest.raises(ValidationError):
        StoryScript(comic_title="Title", pages=pages)
