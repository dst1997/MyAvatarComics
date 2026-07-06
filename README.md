# My Avatar Comics

A local Python web app for creating a personalized 8-page gift comic. You upload 1-8 photos of the person the comic is dedicated to, describe the occasion and what happened, and the app generates a comic starring them: page 1 is the cover, pages 2-7 tell the story, and page 8 is the end page. You can preview every page, regenerate individual pages, and download the finished comic as a PDF.

Art and story are generated with the Google Gemini API. The protagonist's likeness is kept consistent across pages by first generating a character model sheet from the uploaded photos and passing it as a reference to every page render.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Put your Gemini API key in a `.env` file at the project root (or set it as an environment variable):

```
GEMINI_API_KEY=your-key
```

Then run the app:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Configuration

All optional, via environment variables or `.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `COMIC_AI_PROVIDER` | `gemini` if key present, else `mock` | `gemini` or `mock` |
| `GEMINI_TEXT_MODEL` | `gemini-3.5-flash` | Story + character analysis |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image` | Character sheet + page art |
| `GEMINI_TIMEOUT_SECONDS` | `300` | Per-request timeout |
| `MYAVATAR_MAX_REFERENCE_PHOTOS` | `4` | Photos sent as references |
| `MYAVATAR_PAGE_ASPECT_RATIO` | `2:3` | Page aspect ratio |
| `MYAVATAR_STORAGE_DIR` | `.data/projects` | Project storage location |

## Generation pipeline

A full comic uses ~11 Gemini calls:

1. **Character brief** (1 text call) — analyzes the photos and writes a drawing guide for the protagonist.
2. **Story script** (1 text call) — writes the 8-page script (cover, 6 story pages, end page) from your occasion and event description, as structured JSON.
3. **Character model sheet** (1 image call) — draws the protagonist as a cartoon character; this anchors the likeness.
4. **Pages** (8 image calls) — renders each full page using the model sheet and photos as references.
5. **PDF assembly** — local, no API.

Regenerating one page costs 1 image call. If a text step fails, the app falls back to a simple built-in story so generation still completes.

Mock mode (`COMIC_AI_PROVIDER=mock`, no key needed) renders placeholder pages locally so the whole flow can be exercised offline; tests run fully offline.

## Product boundaries

- Digital output only: full-page PNGs and a downloadable PDF.
- Uploaded media is stored under `.data/projects` and can be deleted from the app.
- The character brief uses only visible, non-sensitive traits from the photos.
- Video uploads are accepted; representative frames are extracted with `opencv-python-headless` when available.

## Preschool video pilot workflow

This repository also includes a separate content-production workflow for creating
short AI-assisted preschool videos for manual YouTube Studio upload. It does not
change the comic app.

Start here:

```powershell
Get-Content video-production\README.md
python scripts\create_episode_package.py "Kind Hands" --lesson "sharing toys" --date 2026-07-06
python scripts\render_free_preschool_video.py
```

## Tests

```powershell
python -m pytest
```
