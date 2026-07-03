from __future__ import annotations

from app.models import PAGE_COUNT, CharacterProfile, PageSpec, ProjectSpec, StoryScript


COMIC_STYLE_GUIDE = (
    "Art style: warm, vibrant comic-book illustration with clean bold outlines, expressive faces, "
    "saturated but harmonious colors, dynamic panel compositions, yellow narration caption boxes, "
    "and clean white speech bubbles with dark lettering. Keep the tone celebratory, heartfelt, and "
    "family-friendly. Any text drawn on the page must be short, correctly spelled, and legible."
)


def recipient_phrase(spec: ProjectSpec) -> str:
    if spec.relationship:
        return f"{spec.recipient_name} ({spec.relationship} of the gift-giver)"
    return spec.recipient_name


def build_character_prompt(spec: ProjectSpec, media_count: int) -> str:
    return (
        "You are designing the protagonist of a personalized gift comic. "
        f"The protagonist is {recipient_phrase(spec)}. "
        f"There are {media_count} reference photos of this person attached. "
        "Describe how to draw them as a consistent comic-book character using only visible, "
        "non-sensitive traits: hair style and color, glasses, facial hair, typical expression, "
        "clothing style, and general build. Do not guess age, ethnicity, health, or other "
        "sensitive attributes. Also propose a color palette of 3-5 hex colors that suits the "
        "occasion and an outfit appropriate for the story."
    )


def build_story_prompt(spec: ProjectSpec, profile: CharacterProfile) -> str:
    dedication = f' The dedication message is: "{spec.dedication}".' if spec.dedication else ""
    return (
        f"Write a heartfelt, fun {PAGE_COUNT}-page gift comic starring {recipient_phrase(spec)} "
        "as the main protagonist. It is a dedicated comic made as a personal gift.\n"
        f"Occasion: {spec.occasion}.\n"
        f"What happened / story to capture: {spec.event_details}.{dedication}\n\n"
        "Structure requirements:\n"
        f"- Exactly {PAGE_COUNT} pages, numbered 1 to {PAGE_COUNT}.\n"
        "- Page 1 is the COVER: a striking single illustration with the comic title and the "
        "protagonist front and center. Include the dedication line if one was given.\n"
        f"- Pages 2-{PAGE_COUNT - 1} tell the story of the event with a clear beginning, middle, "
        "and emotional payoff. Mix wide establishing shots with close-ups.\n"
        f"- Page {PAGE_COUNT} is the END PAGE: a warm closing illustration with 'The End', a "
        "final feel-good line, and the dedication if given.\n"
        "- Each page needs: a short title, 1-4 panel descriptions, one narration line, 0-4 short "
        "dialogue lines, and a detailed image_prompt describing the full page for an illustrator.\n"
        f"- Protagonist reference for every image_prompt: {profile.description}\n"
        f"- {COMIC_STYLE_GUIDE}\n"
        "- Keep everything positive and safe: no violence, politics, or embarrassing content.\n"
        "Also invent a short, punchy comic_title for the cover."
    )


def build_character_sheet_prompt(profile: CharacterProfile) -> str:
    return (
        "Create a comic-book character model sheet of the person in the attached reference "
        "photos, drawn as a cartoon protagonist. Show the same character three times on a plain "
        "light background: full body front view, side profile of the head, and a happy close-up "
        "portrait. The character must be clearly recognizable as the person in the photos. "
        f"Character notes: {profile.description}. Outfit: {profile.outfit_notes or 'casual, friendly'}. "
        f"{COMIC_STYLE_GUIDE} No text or labels on the sheet."
    )


def build_page_prompt(profile: CharacterProfile, page: PageSpec, comic_title: str) -> str:
    if page.kind == "cover":
        layout = (
            f'Design a comic book COVER. Draw the title "{comic_title}" in large hand-lettered '
            "comic type at the top. One dramatic full-page illustration, no panel grid."
        )
    elif page.kind == "end":
        layout = (
            'Design the final END PAGE of the comic. Include the words "The End" in comic '
            "lettering. One warm full-page closing illustration, no panel grid."
        )
    else:
        panel_count = max(1, len(page.panels))
        layout = (
            f"Design an interior comic page with {panel_count} panel(s) separated by clean white "
            "gutters and bold black borders."
        )
    dialogue = ""
    if page.dialogue:
        lines = " ".join(f'"{line}"' for line in page.dialogue[:4])
        dialogue = f" Speech bubbles (use this text exactly, keep it short): {lines}."
    return (
        f"{layout}\n"
        f"Scene: {page.image_prompt}\n"
        f"Narration caption: \"{page.narration}\".{dialogue}\n"
        "The main character must match the attached character model sheet exactly: same face, "
        "same hair, same glasses or facial hair, same proportions, drawn in the same style. "
        "Dress the character in clothing that fits this specific scene (sportswear, formal wear, "
        "costume, etc. as the scene demands), not necessarily the model sheet outfit. Use the "
        f"attached photos only to reinforce the likeness. {COMIC_STYLE_GUIDE}"
    )


def build_fallback_profile(spec: ProjectSpec, media_refs: list[str]) -> CharacterProfile:
    return CharacterProfile(
        display_name=spec.recipient_name,
        description=(
            f"{spec.recipient_name}, drawn as a friendly comic-book protagonist inspired by the "
            "uploaded reference photos, with a warm confident smile and expressive eyes"
        ),
        palette=["#f4a261", "#2a9d8f", "#e9c46a", "#264653"],
        outfit_notes=f"An outfit that suits the occasion: {spec.occasion}.",
        accessory_notes="",
        media_references=media_refs,
    )


def build_fallback_story(spec: ProjectSpec, profile: CharacterProfile) -> StoryScript:
    """Deterministic 8-page script used by the mock provider and as a safety net."""
    name = spec.recipient_name
    title = f"The Legend of {name}"
    dedication = spec.dedication or f"For {name}, with love."
    event = spec.event_details
    beats = [
        ("An Ordinary Day", f"It started like any other day for {name}.", f"{name} going about a normal day, unaware of what is coming"),
        ("Something Is Coming", f"But this was no ordinary day. {spec.occasion} was here!", f"{name} realizing the big moment is near: {event}"),
        ("The Big Moment", f"And then it happened: {event}", f"the key scene of the event: {event}, with {name} at the center"),
        ("Rising to the Occasion", f"{name} handled it the way only {name} can.", f"{name} shining during the event, friends or family reacting with joy"),
        ("A Moment to Remember", "It was a moment nobody would forget.", f"an emotional highlight of {event}, warm lighting, close-up on {name}"),
        ("Celebration", f"Everyone celebrated {name}!", f"a joyful celebration scene for {spec.occasion} with {name} beaming"),
    ]
    pages = [
        PageSpec(
            page_number=1,
            title=title,
            panels=[f"Cover: {name} in a heroic pose, celebrating {spec.occasion}."],
            narration=dedication,
            dialogue=[],
            image_prompt=f"heroic comic cover of {profile.description}, themed around {spec.occasion}",
        )
    ]
    for index, (page_title, narration, scene) in enumerate(beats, start=2):
        pages.append(
            PageSpec(
                page_number=index,
                title=page_title,
                panels=[scene],
                narration=narration,
                dialogue=[],
                image_prompt=f"{scene}; protagonist: {profile.description}",
            )
        )
    pages.append(
        PageSpec(
            page_number=PAGE_COUNT,
            title="The End",
            panels=[f"Closing scene: {name} smiling, sunset colors, celebration winding down."],
            narration=f"The End. {dedication}",
            dialogue=[],
            image_prompt=f"warm closing illustration of {profile.description} after {spec.occasion}",
        )
    )
    return StoryScript(comic_title=title, pages=pages)
