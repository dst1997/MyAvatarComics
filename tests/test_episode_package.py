from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "create_episode_package.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("create_episode_package", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_create_episode_package_writes_required_files(tmp_path: Path) -> None:
    module = load_script_module()

    result = module.main([
        "Kind Hands",
        "--lesson",
        "sharing toys",
        "--date",
        "2026-07-06",
        "--root",
        str(tmp_path),
    ])

    assert result == 0
    package_dir = tmp_path / "2026-07-06-kind-hands"
    assert (package_dir / "brief.md").exists()
    assert (package_dir / "script.md").exists()
    assert (package_dir / "shot-list.csv").exists()
    assert (package_dir / "prompts.md").exists()
    assert (package_dir / "clip-log.csv").exists()
    assert (package_dir / "metadata.md").exists()
    assert (package_dir / "upload-checklist.md").exists()
    assert (package_dir / "review.md").exists()
    assert (package_dir / "assets" / "clips" / "accepted").is_dir()
    assert (package_dir / "assets" / "clips" / "rejected").is_dir()
    assert (package_dir / "exports").is_dir()
    assert "Lesson: sharing toys" in (package_dir / "brief.md").read_text(encoding="utf-8")


def test_create_episode_package_refuses_existing_package_without_force(tmp_path: Path) -> None:
    module = load_script_module()
    args = [
        "Kind Hands",
        "--lesson",
        "sharing toys",
        "--date",
        "2026-07-06",
        "--root",
        str(tmp_path),
    ]

    assert module.main(args) == 0
    assert module.main(args) == 1


def test_slugify_has_safe_fallback() -> None:
    module = load_script_module()

    assert module.slugify("Kind Hands!") == "kind-hands"
    assert module.slugify("!!!") == "episode"
