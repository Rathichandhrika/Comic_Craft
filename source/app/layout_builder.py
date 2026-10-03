import re

def build_comic_layout(image_paths: list, full_story: str, outline: list) -> list:
    """Combine images, structured per-panel story narration, dialogues, and outline into rich panel dicts."""
    # Split story by panel headers: e.g. "**Panel 1:", "## Panel 1", "Panel 1:"
    pattern = r"(?:\*\*|#{1,3}\s*)?Panel\s+\d+[:\-\s*]*[^\n]*"
    segments = re.split(pattern, full_story, flags=re.IGNORECASE)

    # Segments after the initial split match each panel's story
    story_panels = [seg.strip() for seg in segments[1:] if seg.strip()] if len(segments) > 1 else []

    layout = []
    total_panels = max(len(image_paths), len(outline))

    for i in range(total_panels):
        panel_num = i + 1
        img = image_paths[i] if i < len(image_paths) else ""
        outline_item = outline[i] if i < len(outline) else {}

        title = outline_item.get("title", f"Panel {panel_num}")
        scene_desc = outline_item.get("scene_description", "")
        raw_text = story_panels[i] if i < len(story_panels) else scene_desc

        # Parse structured elements: Caption, Dialogue, SFX
        caption = ""
        dialogue = ""
        sfx = ""

        # Extract CAPTION
        cap_match = re.search(r"\*\*?CAPTION:\*\*?\s*([^\n]+(?:\n(?!\*\*?[A-Z]+:)[^\n]+)*)", raw_text, re.IGNORECASE)
        if cap_match:
            caption = cap_match.group(1).strip()

        # Extract DIALOGUE
        diag_match = re.search(r"\*\*?DIALOGUE:\*\*?\s*([^\n]+(?:\n(?!\*\*?[A-Z]+:)[^\n]+)*)", raw_text, re.IGNORECASE)
        if diag_match:
            dialogue = diag_match.group(1).strip()

        # Extract SFX
        sfx_match = re.search(r"\*\*?SFX:\*\*?\s*([^\n]+)", raw_text, re.IGNORECASE)
        if sfx_match:
            sfx = sfx_match.group(1).replace("*", "").strip()

        # Clean fallback text if tags weren't parsed
        cleaned_text = raw_text
        cleaned_text = re.sub(r"\*\*?(?:CAPTION|NARRATION|DIALOGUE|IMAGE PROMPT|SFX):\*\*?\s*", "", cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"^\*+.*?\*+\s*", "", cleaned_text)
        cleaned_text = re.sub(r"\*+", "", cleaned_text).strip()

        # Default fallback assignments
        if not caption and not dialogue:
            caption = cleaned_text or scene_desc
        elif not caption:
            caption = scene_desc

        layout.append({
            "panel": panel_num,
            "title": title,
            "image_path": img.replace("\\", "/"),
            "text": cleaned_text or scene_desc,
            "caption": caption,
            "dialogue": dialogue,
            "sfx": sfx,
            "scene_description": scene_desc,
        })

    return layout