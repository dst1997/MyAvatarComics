from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


MediaKind = Literal["photo", "video", "frame"]
ProjectStatusValue = Literal["created", "uploading", "queued", "running", "complete", "failed"]

PAGE_COUNT = 8


class ProjectSpec(BaseModel):
    consent_given: bool
    recipient_name: str = Field(min_length=1, max_length=60)
    relationship: str = Field(default="", max_length=60)
    occasion: str = Field(min_length=1, max_length=120)
    event_details: str = Field(min_length=1, max_length=2000)
    dedication: str = Field(default="", max_length=280)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def require_consent(self) -> "ProjectSpec":
        if not self.consent_given:
            raise ValueError("Please confirm you have permission to use the uploaded photos.")
        return self

    @field_validator("recipient_name", "relationship", "occasion", "event_details", "dedication")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return " ".join(value.split())


class UploadedMedia(BaseModel):
    kind: MediaKind
    original_name: str
    stored_name: str
    path: str
    content_type: str | None = None
    size_bytes: int = Field(ge=0)

    @property
    def absolute_path(self) -> Path:
        return Path(self.path)


class CharacterProfile(BaseModel):
    display_name: str
    description: str
    palette: list[str] = Field(default_factory=list, min_length=1, max_length=6)
    outfit_notes: str = ""
    accessory_notes: str = ""
    media_references: list[str] = Field(default_factory=list)
    character_sheet_path: str | None = None


class PageSpec(BaseModel):
    page_number: int = Field(ge=1, le=PAGE_COUNT)
    kind: Literal["cover", "story", "end"] = "story"
    title: str = Field(min_length=1, max_length=80)
    panels: list[str] = Field(default_factory=list, min_length=1, max_length=4)
    narration: str = Field(min_length=1, max_length=700)
    dialogue: list[str] = Field(default_factory=list, max_length=4)
    image_prompt: str = Field(min_length=1, max_length=2200)
    image_path: str | None = None

    @model_validator(mode="after")
    def align_kind_with_page_number(self) -> "PageSpec":
        if self.page_number == 1:
            self.kind = "cover"
        elif self.page_number == PAGE_COUNT:
            self.kind = "end"
        else:
            self.kind = "story"
        return self


class StoryScript(BaseModel):
    comic_title: str = Field(min_length=1, max_length=90)
    pages: list[PageSpec] = Field(min_length=PAGE_COUNT, max_length=PAGE_COUNT)

    @model_validator(mode="after")
    def require_full_page_run(self) -> "StoryScript":
        numbers = sorted(page.page_number for page in self.pages)
        if numbers != list(range(1, PAGE_COUNT + 1)):
            raise ValueError(f"Story must contain pages 1 through {PAGE_COUNT} exactly once.")
        return self


class GenerationManifest(BaseModel):
    project_id: str
    title: str
    character_profile: CharacterProfile
    pages: list[PageSpec] = Field(min_length=PAGE_COUNT, max_length=PAGE_COUNT)
    pdf_path: str
    warnings: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, str] = Field(default_factory=dict)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectStatus(BaseModel):
    project_id: str
    status: ProjectStatusValue = "created"
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    error: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
