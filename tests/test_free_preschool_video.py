from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "render_free_preschool_video.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("render_free_preschool_video", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_kind_hands_story_matches_free_pilot_constraints() -> None:
    module = load_script_module()

    spec = module.build_kind_hands_story()
    total_seconds = sum(scene.seconds for scene in spec.scenes)
    narration_words = " ".join(scene.narration for scene in spec.scenes).split()

    assert spec.title == "Kind Hands"
    assert spec.lesson == "sharing toys"
    assert 60 <= total_seconds <= 90
    assert 90 <= len(narration_words) <= 140
    assert 5 <= len(spec.scenes) <= 7


def test_slugify_and_easing_are_stable() -> None:
    module = load_script_module()

    assert module.slugify("Kind Hands!") == "kind-hands"
    assert module.slugify("!!!") == "video"
    assert module.ease_in_out(-1) == 0
    assert module.ease_in_out(2) == 1


def test_tiny_render_writes_video_and_support_files(tmp_path: Path) -> None:
    module = load_script_module()

    video_path = module.render_video(module.build_kind_hands_story(), tmp_path, fps=2, size=(640, 360))

    assert video_path.exists()
    assert video_path.stat().st_size > 0
    assert (tmp_path / "kind-hands-thumbnail.jpg").exists()
    assert (tmp_path / "kind-hands-narration.txt").exists()
    assert (tmp_path / "kind-hands-notes.md").exists()
