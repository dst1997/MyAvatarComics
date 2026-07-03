from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from app.models import GenerationManifest, ProjectSpec, ProjectStatus, UploadedMedia


PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi"}
ALL_UPLOAD_EXTENSIONS = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS


class StorageError(RuntimeError):
    pass


class ProjectStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_project(self, spec: ProjectSpec) -> str:
        project_id = uuid.uuid4().hex[:12]
        project_dir = self.project_dir(project_id)
        project_dir.mkdir(parents=True)
        for child in ("uploads", "frames", "art", "pages"):
            (project_dir / child).mkdir()
        self.save_model(project_id, "spec.json", spec)
        self.save_status(ProjectStatus(project_id=project_id, status="created", progress=5, message="Project created."))
        self.save_media(project_id, [])
        return project_id

    def project_dir(self, project_id: str) -> Path:
        self._validate_project_id(project_id)
        path = (self.root / project_id).resolve()
        if self.root not in path.parents and path != self.root:
            raise StorageError("Project path escaped storage root.")
        return path

    def require_project_dir(self, project_id: str) -> Path:
        path = self.project_dir(project_id)
        if not path.exists():
            raise StorageError(f"Project {project_id} does not exist.")
        return path

    def uploads_dir(self, project_id: str) -> Path:
        return self.require_project_dir(project_id) / "uploads"

    def frames_dir(self, project_id: str) -> Path:
        return self.require_project_dir(project_id) / "frames"

    def art_dir(self, project_id: str) -> Path:
        return self.require_project_dir(project_id) / "art"

    def pages_dir(self, project_id: str) -> Path:
        return self.require_project_dir(project_id) / "pages"

    def save_model(self, project_id: str, filename: str, model: BaseModel) -> None:
        path = self.require_project_dir(project_id) / filename
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")

    def load_spec(self, project_id: str) -> ProjectSpec:
        return ProjectSpec.model_validate_json((self.require_project_dir(project_id) / "spec.json").read_text(encoding="utf-8"))

    def save_manifest(self, manifest: GenerationManifest) -> None:
        self.save_model(manifest.project_id, "manifest.json", manifest)

    def load_manifest(self, project_id: str) -> GenerationManifest:
        return GenerationManifest.model_validate_json(
            (self.require_project_dir(project_id) / "manifest.json").read_text(encoding="utf-8")
        )

    def save_status(self, status: ProjectStatus) -> None:
        status.updated_at = datetime.now(timezone.utc)
        self.save_model(status.project_id, "status.json", status)

    def load_status(self, project_id: str) -> ProjectStatus:
        return ProjectStatus.model_validate_json(
            (self.require_project_dir(project_id) / "status.json").read_text(encoding="utf-8")
        )

    def save_media(self, project_id: str, media: Iterable[UploadedMedia]) -> None:
        path = self.require_project_dir(project_id) / "media.json"
        data = [item.model_dump() for item in media]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_media(self, project_id: str) -> list[UploadedMedia]:
        path = self.require_project_dir(project_id) / "media.json"
        if not path.exists():
            return []
        return [UploadedMedia.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]

    def add_media_file(self, project_id: str, original_name: str, content_type: str | None, data: bytes) -> UploadedMedia:
        extension = Path(original_name).suffix.lower()
        if extension not in ALL_UPLOAD_EXTENSIONS:
            raise StorageError(f"Unsupported upload type: {extension or 'missing extension'}")
        kind = "photo" if extension in PHOTO_EXTENSIONS else "video"
        safe_name = sanitize_filename(Path(original_name).stem) or "upload"
        stored_name = f"{uuid.uuid4().hex[:8]}-{safe_name}{extension}"
        path = self.uploads_dir(project_id) / stored_name
        path.write_bytes(data)
        media = self.load_media(project_id)
        item = UploadedMedia(
            kind=kind,
            original_name=original_name,
            stored_name=stored_name,
            path=str(path),
            content_type=content_type,
            size_bytes=len(data),
        )
        media.append(item)
        self.save_media(project_id, media)
        self.save_status(ProjectStatus(project_id=project_id, status="uploading", progress=20, message="Media uploaded."))
        return item

    def delete_project(self, project_id: str) -> None:
        path = self.project_dir(project_id)
        if path.exists():
            if self.root not in path.parents:
                raise StorageError("Refusing to delete outside storage root.")
            shutil.rmtree(path)

    @staticmethod
    def _validate_project_id(project_id: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{12}", project_id):
            raise StorageError("Invalid project id.")


def sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip())
    clean = re.sub(r"-+", "-", clean).strip(".-")
    return clean[:80]
