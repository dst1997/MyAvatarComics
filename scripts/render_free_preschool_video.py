from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "test-output" / "free-preschool-video"


@dataclass(frozen=True)
class Scene:
    title: str
    narration: str
    background: tuple[int, int, int]
    prop: str
    mood: str
    seconds: float


@dataclass(frozen=True)
class VideoSpec:
    title: str
    lesson: str
    scenes: list[Scene]


def slugify(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    clean = re.sub(r"-+", "-", clean)
    return clean or "video"


def build_kind_hands_story() -> VideoSpec:
    return VideoSpec(
        title="Kind Hands",
        lesson="sharing toys",
        scenes=[
            Scene(
                title="A sunny playroom",
                narration="Milo had a red truck. He rolled it round and round on the soft yellow rug.",
                background=(255, 235, 197),
                prop="truck",
                mood="happy",
                seconds=8,
            ),
            Scene(
                title="A friend asks",
                narration="Lulu came over with quiet feet and asked, May I have a turn, please?",
                background=(211, 238, 255),
                prop="truck",
                mood="curious",
                seconds=9,
            ),
            Scene(
                title="A small pause",
                narration="Milo hugged the truck close. He wanted to keep playing for one more minute.",
                background=(239, 231, 255),
                prop="truck",
                mood="thinking",
                seconds=9,
            ),
            Scene(
                title="Kind hands remember",
                narration="Then Milo took a little breath and remembered: kind hands can share with friends.",
                background=(218, 248, 219),
                prop="heart",
                mood="kind",
                seconds=9,
            ),
            Scene(
                title="Taking turns",
                narration="He gave Lulu a turn. Lulu rolled the truck gently and said, thank you, Milo.",
                background=(255, 245, 202),
                prop="truck",
                mood="happy",
                seconds=10,
            ),
            Scene(
                title="Playing together",
                narration="Soon they made a road together with blocks. Sharing made the whole game bigger.",
                background=(214, 241, 232),
                prop="stars",
                mood="celebrate",
                seconds=10,
            ),
            Scene(
                title="The kind idea",
                narration="When we share, everyone gets a smile. Kind hands help friends play, learn, and laugh together.",
                background=(255, 229, 226),
                prop="heart",
                mood="celebrate",
                seconds=10,
            ),
        ],
    )


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def ease_in_out(progress: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, progress)))


def draw_video_frame(spec: VideoSpec, scene: Scene, progress: float, size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, scene.background)
    draw = ImageDraw.Draw(image)
    title_font = load_font(70, bold=True)
    caption_font = load_font(52, bold=True)
    small_font = load_font(34)

    draw_background(draw, width, height, progress)
    draw_rug(draw, width, height)

    motion = ease_in_out(progress)
    bob = int(math.sin(progress * math.tau * 2) * 10)
    milo_x = int(width * 0.34 - 35 * motion)
    lulu_x = int(width * 0.66 + 25 * motion)
    character_y = int(height * 0.48) + bob

    draw_character(draw, milo_x, character_y, "Milo", (105, 168, 255), scene.mood in {"happy", "celebrate", "kind"})
    draw_character(draw, lulu_x, character_y + 8, "Lulu", (255, 153, 180), scene.mood in {"happy", "celebrate"})
    draw_prop(draw, scene.prop, int(width * (0.48 + 0.04 * math.sin(progress * math.tau))), int(height * 0.63))

    draw_badge(draw, spec.lesson, 44, 40, small_font)
    draw_title(draw, spec.title, title_font, width)
    draw_caption(draw, scene.narration, caption_font, width, height)
    return image


def draw_background(draw: ImageDraw.ImageDraw, width: int, height: int, progress: float) -> None:
    sun_x = int(width * (0.12 + 0.02 * math.sin(progress * math.tau)))
    draw.ellipse((sun_x - 70, 70, sun_x + 70, 210), fill=(255, 214, 93))
    for index, x in enumerate((260, 760, 1260, 1660)):
        y = 120 + (index % 2) * 40
        draw_cloud(draw, x, y, scale=1.0 + index * 0.06)


def draw_cloud(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float) -> None:
    color = (255, 255, 255)
    parts = [
        (0, 20, 100, 70),
        (45, 0, 150, 80),
        (110, 25, 220, 75),
    ]
    for left, top, right, bottom in parts:
        box = (
            x + int(left * scale),
            y + int(top * scale),
            x + int(right * scale),
            y + int(bottom * scale),
        )
        draw.ellipse(box, fill=color)


def draw_rug(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    draw.ellipse((width * 0.20, height * 0.58, width * 0.80, height * 0.88), fill=(255, 255, 255), outline=(80, 120, 150), width=8)
    draw.ellipse((width * 0.30, height * 0.64, width * 0.70, height * 0.82), outline=(255, 183, 77), width=10)


def draw_character(draw: ImageDraw.ImageDraw, x: int, y: int, name: str, shirt: tuple[int, int, int], smiling: bool) -> None:
    outline = (46, 60, 82)
    skin = (255, 207, 170)
    hair = (92, 66, 48)
    draw.ellipse((x - 78, y - 190, x + 78, y - 34), fill=skin, outline=outline, width=7)
    draw.pieslice((x - 88, y - 205, x + 88, y - 80), 180, 360, fill=hair, outline=outline, width=5)
    draw.rounded_rectangle((x - 92, y - 30, x + 92, y + 190), radius=55, fill=shirt, outline=outline, width=7)
    draw.line((x - 95, y + 30, x - 165, y + 120), fill=outline, width=16)
    draw.line((x + 95, y + 30, x + 165, y + 120), fill=outline, width=16)
    draw.line((x - 45, y + 185, x - 70, y + 285), fill=outline, width=18)
    draw.line((x + 45, y + 185, x + 70, y + 285), fill=outline, width=18)
    draw.ellipse((x - 45, y - 122, x - 24, y - 101), fill=outline)
    draw.ellipse((x + 24, y - 122, x + 45, y - 101), fill=outline)
    if smiling:
        draw.arc((x - 35, y - 105, x + 35, y - 50), 10, 170, fill=outline, width=6)
    else:
        draw.arc((x - 30, y - 70, x + 30, y - 20), 190, 350, fill=outline, width=6)
    label_font = load_font(28, bold=True)
    bbox = draw.textbbox((0, 0), name, font=label_font)
    draw.rounded_rectangle((x - 62, y + 205, x + 62, y + 252), radius=18, fill=(255, 255, 255), outline=outline, width=4)
    draw.text((x - (bbox[2] - bbox[0]) / 2, y + 210), name, fill=outline, font=label_font)


def draw_prop(draw: ImageDraw.ImageDraw, prop: str, x: int, y: int) -> None:
    outline = (46, 60, 82)
    if prop == "truck":
        draw.rounded_rectangle((x - 120, y - 60, x + 120, y + 30), radius=22, fill=(242, 88, 88), outline=outline, width=7)
        draw.rectangle((x + 10, y - 120, x + 105, y - 60), fill=(255, 188, 88), outline=outline, width=7)
        draw.ellipse((x - 90, y + 10, x - 35, y + 65), fill=(55, 70, 90), outline=outline, width=4)
        draw.ellipse((x + 50, y + 10, x + 105, y + 65), fill=(55, 70, 90), outline=outline, width=4)
    elif prop == "heart":
        draw.ellipse((x - 80, y - 80, x, y), fill=(255, 103, 137), outline=outline, width=6)
        draw.ellipse((x, y - 80, x + 80, y), fill=(255, 103, 137), outline=outline, width=6)
        draw.polygon([(x - 82, y - 35), (x + 82, y - 35), (x, y + 95)], fill=(255, 103, 137), outline=outline)
    else:
        for index in range(6):
            angle = index * math.tau / 6
            sx = x + int(math.cos(angle) * 120)
            sy = y + int(math.sin(angle) * 70)
            draw.regular_polygon((sx, sy, 28), 5, rotation=18, fill=(255, 214, 93), outline=outline)


def draw_badge(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font: ImageFont.ImageFont) -> None:
    label = f"Lesson: {text}"
    bbox = draw.textbbox((0, 0), label, font=font)
    draw.rounded_rectangle((x, y, x + bbox[2] + 44, y + bbox[3] + 32), radius=24, fill=(255, 255, 255), outline=(46, 60, 82), width=5)
    draw.text((x + 22, y + 14), label, fill=(46, 60, 82), font=font)


def draw_title(draw: ImageDraw.ImageDraw, title: str, font: ImageFont.ImageFont, width: int) -> None:
    bbox = draw.textbbox((0, 0), title, font=font)
    x = (width - (bbox[2] - bbox[0])) / 2
    draw.text((x + 4, 248), title, fill=(255, 255, 255), font=font)
    draw.text((x, 244), title, fill=(46, 60, 82), font=font)


def draw_caption(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int, height: int) -> None:
    lines = wrap_text(text, font, width - 260)
    line_height = 64
    box_height = 72 + line_height * len(lines)
    top = height - box_height - 54
    draw.rounded_rectangle((95, top, width - 95, height - 55), radius=34, fill=(255, 255, 255), outline=(46, 60, 82), width=7)
    y = top + 34
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((width - (bbox[2] - bbox[0])) / 2, y), line, fill=(46, 60, 82), font=font)
        y += line_height


def render_video(spec: VideoSpec, output_dir: Path, fps: int = 30, size: tuple[int, int] = (1920, 1080)) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / f"{slugify(spec.title)}-free-prototype.mp4"
    thumbnail_path = output_dir / f"{slugify(spec.title)}-thumbnail.jpg"
    narration_path = output_dir / f"{slugify(spec.title)}-narration.txt"
    notes_path = output_dir / f"{slugify(spec.title)}-notes.md"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, fps, size)
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer for {video_path}")

    thumbnail_saved = False
    for scene in spec.scenes:
        frame_count = max(1, int(scene.seconds * fps))
        for frame_index in range(frame_count):
            progress = frame_index / max(1, frame_count - 1)
            image = draw_video_frame(spec, scene, progress, size)
            if not thumbnail_saved:
                image.save(thumbnail_path, "JPEG", quality=92)
                thumbnail_saved = True
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            writer.write(frame)
    writer.release()

    narration_path.write_text("\n".join(scene.narration for scene in spec.scenes), encoding="utf-8")
    notes_path.write_text(build_notes(spec, video_path, thumbnail_path, narration_path), encoding="utf-8")
    return video_path


def build_notes(spec: VideoSpec, video_path: Path, thumbnail_path: Path, narration_path: Path) -> str:
    total_seconds = sum(scene.seconds for scene in spec.scenes)
    return (
        f"# {spec.title} Free Prototype\n\n"
        f"- Lesson: {spec.lesson}\n"
        f"- Runtime: {total_seconds:.0f} seconds\n"
        f"- Video: `{video_path.name}`\n"
        f"- Thumbnail: `{thumbnail_path.name}`\n"
        f"- Narration text: `{narration_path.name}`\n"
        "- Cost: $0 local render, no paid AI video or voice tools used.\n"
        "- Limitation: this prototype has captions but no recorded voiceover.\n"
        "- Suggested next free step: record the narration manually on a phone or with a free desktop recorder, then add it in CapCut or DaVinci Resolve.\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a free local preschool video prototype.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for the rendered MP4 and support files.")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second.")
    parser.add_argument("--width", type=int, default=1920, help="Video width.")
    parser.add_argument("--height", type=int, default=1080, help="Video height.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = build_kind_hands_story()
    video_path = render_video(spec, args.output_dir, fps=args.fps, size=(args.width, args.height))
    print(f"created: {video_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
