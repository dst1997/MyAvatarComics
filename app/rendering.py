from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.models import CharacterProfile, PageSpec


MOCK_PAGE_SIZE = (1024, 1536)


def render_mock_art(
    profile: CharacterProfile,
    page: PageSpec,
    output_path: Path,
    comic_title: str = "",
) -> None:
    """Placeholder page used by the mock provider so the full flow works without an API key."""
    width, height = MOCK_PAGE_SIZE
    palette = profile.palette or ["#f4a261", "#2a9d8f", "#e9c46a"]
    bg = palette[(page.page_number - 1) % len(palette)]
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    title_font = load_font(64, bold=True)
    body_font = load_font(36)
    small_font = load_font(28)

    draw.rounded_rectangle((50, 50, width - 50, height - 50), radius=40, fill="#fff8e8", outline="#243447", width=8)

    heading = comic_title if page.kind == "cover" and comic_title else page.title
    draw.multiline_text((100, 120), wrap_text(heading, 22), fill="#243447", font=title_font, spacing=8)

    if page.kind == "cover":
        label = "COVER"
    elif page.kind == "end":
        label = "THE END"
    else:
        label = f"PAGE {page.page_number}"
    draw.text((100, 380), label, fill="#e76f51", font=load_font(44, bold=True))

    # Simple stand-in figure so previews read as "a character page".
    cx = width // 2
    draw.ellipse((cx - 90, 500, cx + 90, 680), fill="#f6c7b6", outline="#243447", width=6)
    draw.rounded_rectangle((cx - 130, 690, cx + 130, 1060), radius=60, fill=palette[0], outline="#243447", width=6)
    draw.arc((cx - 45, 590, cx + 45, 650), 0, 180, fill="#243447", width=5)
    draw.ellipse((cx - 55, 555, cx - 35, 575), fill="#243447")
    draw.ellipse((cx + 35, 555, cx + 55, 575), fill="#243447")

    draw.rounded_rectangle((90, 1120, width - 90, 1340), radius=20, fill="#ffffff", outline="#243447", width=5)
    draw.multiline_text((120, 1150), wrap_text(page.narration, 44), fill="#243447", font=body_font, spacing=6)
    draw.text((90, height - 110), f"Mock preview — page {page.page_number}", fill="#243447", font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG")


def render_mock_character_sheet(profile: CharacterProfile, output_path: Path) -> None:
    width, height = 1024, 768
    image = Image.new("RGB", (width, height), "#fdf6ec")
    draw = ImageDraw.Draw(image)
    title_font = load_font(48, bold=True)
    body_font = load_font(30)
    draw.text((60, 50), f"Character sheet: {profile.display_name}", fill="#243447", font=title_font)
    draw.multiline_text((60, 140), wrap_text(profile.description, 60), fill="#243447", font=body_font, spacing=6)
    for index in range(3):
        x = 90 + index * 300
        draw.ellipse((x, 380, x + 160, 540), fill="#f6c7b6", outline="#243447", width=5)
        draw.rounded_rectangle((x + 20, 550, x + 140, 700), radius=30, fill="#2a9d8f", outline="#243447", width=5)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG")


def build_pdf(pages: list[PageSpec], pdf_path: Path) -> None:
    images: list[Image.Image] = []
    for page in sorted(pages, key=lambda item: item.page_number):
        if not page.image_path:
            raise ValueError(f"Page {page.page_number} has no rendered image.")
        images.append(Image.open(page.image_path).convert("RGB"))
    if not images:
        raise ValueError("No pages available for PDF.")
    first, rest = images[0], images[1:]
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    first.save(pdf_path, "PDF", resolution=150.0, save_all=True, append_images=rest)
    for image in images:
        image.close()


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def wrap_text(text: str, chars: int) -> str:
    return "\n".join(textwrap.wrap(text, width=chars, break_long_words=False))
