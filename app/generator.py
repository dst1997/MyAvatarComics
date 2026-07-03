from __future__ import annotations

from pathlib import Path

from app.config import Settings, get_settings
from app.media import extract_video_frames, prepare_photo_references, validate_media_requirements
from app.models import GenerationManifest, PageSpec, ProjectStatus, StoryScript
from app.providers.base import AIProvider
from app.rendering import build_pdf
from app.storage import ProjectStorage
from app.story import build_fallback_profile, build_fallback_story


CHARACTER_SHEET_NAME = "character-sheet.png"


class ComicGenerator:
    def __init__(self, storage: ProjectStorage, provider: AIProvider, settings: Settings | None = None):
        self.storage = storage
        self.provider = provider
        self.settings = settings or get_settings()

    async def generate_project(self, project_id: str) -> GenerationManifest:
        self._status(project_id, "running", 10, "Checking uploaded photos.")
        spec = self.storage.load_spec(project_id)
        media = self.storage.load_media(project_id)
        validate_media_requirements(media)

        extracted, warnings = extract_video_frames(media, self.storage.frames_dir(project_id))
        if extracted:
            media = media + extracted
            self.storage.save_media(project_id, media)
        refs = prepare_photo_references(media, max_refs=self.settings.max_reference_photos)

        self._status(project_id, "running", 20, "Studying the photos to design the comic hero.")
        try:
            profile = await self.provider.describe_character(spec, refs)
        except Exception:
            warnings.append("Character analysis failed; using a generic character profile.")
            profile = build_fallback_profile(spec, refs)
        profile = profile.model_copy(update={"media_references": refs})

        self._status(project_id, "running", 30, "Writing the story.")
        try:
            script = await self.provider.build_story(spec, profile)
        except Exception:
            warnings.append("Story writing failed; using a simple fallback story.")
            script = build_fallback_story(spec, profile)

        self._status(project_id, "running", 38, "Drawing the character model sheet.")
        sheet_path = self.storage.art_dir(project_id) / CHARACTER_SHEET_NAME
        await self.provider.create_character_sheet(profile, sheet_path)
        profile = profile.model_copy(update={"character_sheet_path": str(sheet_path)})

        rendered_pages = await self._render_pages(project_id, script.pages, profile, script.comic_title, base_progress=40)

        self._status(project_id, "running", 95, "Building the downloadable PDF.")
        pdf_path = self.storage.require_project_dir(project_id) / "comic.pdf"
        build_pdf(rendered_pages, pdf_path)
        manifest = GenerationManifest(
            project_id=project_id,
            title=script.comic_title,
            character_profile=profile,
            pages=rendered_pages,
            pdf_path=str(pdf_path),
            warnings=warnings,
            provider_metadata={
                "provider": self.provider.name,
                "reference_photo_count": str(len(refs)),
                "api_call_plan": "1 character + 1 story + 1 sheet + 8 pages" if self.provider.name == "gemini" else "0 API calls (mock)",
            },
        )
        self.storage.save_manifest(manifest)
        self._status(project_id, "complete", 100, "Comic ready.")
        return manifest

    async def regenerate_page(self, project_id: str, page_number: int) -> GenerationManifest:
        manifest = self.storage.load_manifest(project_id)
        if not any(page.page_number == page_number for page in manifest.pages):
            raise ValueError(f"Page number must be between 1 and {len(manifest.pages)}.")
        self._status(project_id, "running", 60, f"Redrawing page {page_number}.")
        page = next(page for page in manifest.pages if page.page_number == page_number)
        profile = manifest.character_profile
        sheet_path = Path(profile.character_sheet_path) if profile.character_sheet_path else None
        if sheet_path and not sheet_path.exists():
            self._status(project_id, "running", 65, "Redrawing the character model sheet.")
            await self.provider.create_character_sheet(profile, sheet_path)
        updated_page = (
            await self._render_pages(project_id, [page], profile, manifest.title, base_progress=70)
        )[0]
        pages = [updated_page if item.page_number == page_number else item for item in manifest.pages]
        build_pdf(pages, Path(manifest.pdf_path))
        updated = manifest.model_copy(update={"pages": pages})
        self.storage.save_manifest(updated)
        self._status(project_id, "complete", 100, "Page regenerated.")
        return updated

    async def _render_pages(
        self,
        project_id: str,
        pages: list[PageSpec],
        profile,
        comic_title: str,
        base_progress: int,
    ) -> list[PageSpec]:
        sheet_path = Path(profile.character_sheet_path) if profile.character_sheet_path else None
        rendered: list[PageSpec] = []
        ordered = sorted(pages, key=lambda item: item.page_number)
        for index, page in enumerate(ordered, start=1):
            progress = base_progress + int(index / len(ordered) * (94 - base_progress))
            self._status(project_id, "running", progress, f"Drawing page {page.page_number} of {len(ordered)}.")
            output_path = self.storage.pages_dir(project_id) / f"page-{page.page_number:02d}.png"
            await self.provider.generate_page(profile, page, comic_title, sheet_path, output_path)
            rendered.append(page.model_copy(update={"image_path": str(output_path)}))
        return rendered

    def _status(self, project_id: str, status: str, progress: int, message: str, error: str | None = None) -> None:
        self.storage.save_status(ProjectStatus(project_id=project_id, status=status, progress=progress, message=message, error=error))
