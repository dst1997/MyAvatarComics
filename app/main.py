from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.config import ROOT_DIR, get_settings
from app.generator import ComicGenerator
from app.models import ProjectSpec, ProjectStatus
from app.providers import create_provider
from app.storage import ProjectStorage, StorageError, sanitize_filename


settings = get_settings()
storage = ProjectStorage(settings.storage_dir)
templates = Jinja2Templates(directory=str(ROOT_DIR / "app" / "templates"))

app = FastAPI(title="My Avatar Comics", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        context={
            "provider": settings.provider,
            "gemini_enabled": settings.use_gemini,
        },
    )


@app.post("/api/projects")
async def create_project(spec: ProjectSpec) -> dict[str, str]:
    try:
        project_id = storage.create_project(spec)
        return {"project_id": project_id}
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@app.post("/api/projects/{project_id}/uploads")
async def upload_media(project_id: str, files: list[UploadFile] = File(...)) -> dict[str, object]:
    try:
        items = []
        for upload in files:
            data = await upload.read()
            if not data:
                continue
            item = storage.add_media_file(project_id, upload.filename or "upload", upload.content_type, data)
            items.append(item.model_dump())
        return {"media": items}
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/generate")
async def generate_project(project_id: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    try:
        storage.require_project_dir(project_id)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    background_tasks.add_task(run_generation, project_id)
    return {"status": "queued", "project_id": project_id}


@app.post("/api/projects/{project_id}/pages/{page_number}/regenerate")
async def regenerate_page(project_id: str, page_number: int, background_tasks: BackgroundTasks) -> dict[str, str]:
    try:
        storage.require_project_dir(project_id)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    background_tasks.add_task(run_page_regeneration, project_id, page_number)
    return {"status": "queued", "project_id": project_id}


@app.get("/api/projects/{project_id}/status")
async def project_status(project_id: str) -> JSONResponse:
    try:
        status = storage.load_status(project_id).model_dump(mode="json")
        response: dict[str, object] = {"status": status}
        manifest_path = storage.require_project_dir(project_id) / "manifest.json"
        if manifest_path.exists():
            manifest = storage.load_manifest(project_id).model_dump(mode="json")
            for page in manifest["pages"]:
                page["image_url"] = f"/api/projects/{project_id}/pages/{page['page_number']}.png"
            manifest["download_url"] = f"/api/projects/{project_id}/download.pdf"
            response["manifest"] = manifest
        return JSONResponse(response)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/pages/{page_number}.png")
async def page_image(project_id: str, page_number: int) -> FileResponse:
    try:
        manifest = storage.load_manifest(project_id)
        page = next((item for item in manifest.pages if item.page_number == page_number), None)
        if not page or not page.image_path or not Path(page.image_path).exists():
            raise HTTPException(status_code=404, detail="Page image not found.")
        return FileResponse(page.image_path, media_type="image/png")
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/download.pdf")
async def download_pdf(project_id: str) -> FileResponse:
    try:
        manifest = storage.load_manifest(project_id)
        if not Path(manifest.pdf_path).exists():
            raise HTTPException(status_code=404, detail="PDF not found.")
        filename = f"{sanitize_filename(manifest.title) or 'my-avatar-comic'}.pdf"
        return FileResponse(manifest.pdf_path, filename=filename, media_type="application/pdf")
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str) -> dict[str, str]:
    try:
        storage.delete_project(project_id)
        return {"status": "deleted"}
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def run_generation(project_id: str) -> None:
    try:
        provider = create_provider(settings)
        generator = ComicGenerator(storage, provider, settings)
        await generator.generate_project(project_id)
    except Exception as exc:
        storage.save_status(
            ProjectStatus(project_id=project_id, status="failed", progress=100, message="Generation failed.", error=str(exc))
        )


async def run_page_regeneration(project_id: str, page_number: int) -> None:
    try:
        provider = create_provider(settings)
        generator = ComicGenerator(storage, provider, settings)
        await generator.regenerate_page(project_id, page_number)
    except Exception as exc:
        storage.save_status(
            ProjectStatus(project_id=project_id, status="failed", progress=100, message="Page regeneration failed.", error=str(exc))
        )
