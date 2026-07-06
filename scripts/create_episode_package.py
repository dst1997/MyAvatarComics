from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_DIR = ROOT_DIR / "video-production" / "templates" / "episode-package"
DEFAULT_EPISODES_DIR = ROOT_DIR / "video-production" / "episodes"

TEMPLATE_FILES = (
    "brief.md",
    "script.md",
    "shot-list.csv",
    "prompts.md",
    "clip-log.csv",
    "metadata.md",
    "upload-checklist.md",
    "review.md",
)

MEDIA_DIRS = (
    "assets/clips/accepted",
    "assets/clips/rejected",
    "assets/narration",
    "assets/music-sfx",
    "exports",
    "thumbnail",
)


class EpisodePackageError(RuntimeError):
    pass


@dataclass(frozen=True)
class EpisodePackage:
    title: str
    lesson: str
    production_date: str
    episode_code: str
    path: Path


def slugify(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    clean = re.sub(r"-+", "-", clean)
    return clean or "episode"


def render_template(text: str, package: EpisodePackage) -> str:
    replacements = {
        "{{title}}": package.title,
        "{{lesson}}": package.lesson,
        "{{date}}": package.production_date,
        "{{episode_code}}": package.episode_code,
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


def create_episode_package(
    title: str,
    lesson: str,
    production_date: str | None = None,
    root: Path = DEFAULT_EPISODES_DIR,
    template_dir: Path = DEFAULT_TEMPLATE_DIR,
    episode_code: str | None = None,
    force: bool = False,
) -> EpisodePackage:
    production_date = production_date or date.today().isoformat()
    slug = slugify(title)
    episode_code = episode_code or f"{production_date}-{slug}"
    destination = (root / episode_code).resolve()

    if destination.exists() and not force:
        raise EpisodePackageError(f"Episode package already exists: {destination}")

    if not template_dir.exists():
        raise EpisodePackageError(f"Template directory not found: {template_dir}")

    package = EpisodePackage(
        title=title.strip(),
        lesson=lesson.strip(),
        production_date=production_date,
        episode_code=episode_code,
        path=destination,
    )

    destination.mkdir(parents=True, exist_ok=True)
    for media_dir in MEDIA_DIRS:
        (destination / media_dir).mkdir(parents=True, exist_ok=True)

    for filename in TEMPLATE_FILES:
        template_path = template_dir / filename
        if not template_path.exists():
            raise EpisodePackageError(f"Missing template: {template_path}")
        output_path = destination / filename
        if output_path.exists() and not force:
            raise EpisodePackageError(f"Refusing to overwrite existing file: {output_path}")
        output_path.write_text(render_template(template_path.read_text(encoding="utf-8"), package), encoding="utf-8")

    return package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a preschool AI video episode production package.")
    parser.add_argument("title", help="Working episode title, for example: Kind Hands")
    parser.add_argument("--lesson", required=True, help="One life-skill lesson, for example: sharing toys")
    parser.add_argument("--date", dest="production_date", help="Production date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--root", type=Path, default=DEFAULT_EPISODES_DIR, help="Episode package root directory.")
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR, help="Template directory.")
    parser.add_argument("--episode-code", help="Override generated folder name.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files in the episode package.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        package = create_episode_package(
            title=args.title,
            lesson=args.lesson,
            production_date=args.production_date,
            root=args.root,
            template_dir=args.template_dir,
            episode_code=args.episode_code,
            force=args.force,
        )
    except EpisodePackageError as exc:
        print(f"error: {exc}")
        return 1

    print(f"created: {package.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
