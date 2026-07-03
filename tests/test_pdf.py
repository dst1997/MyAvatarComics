from __future__ import annotations

from pathlib import Path

import re

from PIL import Image

from app.models import PageSpec
from app.rendering import build_pdf


def test_build_pdf_has_eight_pages(tmp_path: Path) -> None:
    pages = []
    for index in range(1, 9):
        image_path = tmp_path / f"page-{index}.png"
        Image.new("RGB", (240, 320), (index * 20, 100, 180)).save(image_path)
        pages.append(
            PageSpec(
                page_number=index,
                title=f"Page {index}",
                panels=["panel"],
                narration="Narration",
                image_prompt="Prompt",
                image_path=str(image_path),
            )
        )

    pdf_path = tmp_path / "comic.pdf"
    build_pdf(pages, pdf_path)

    assert pdf_path.exists()
    pdf_bytes = pdf_path.read_bytes()
    assert len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) == 8
