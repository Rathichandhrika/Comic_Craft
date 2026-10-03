import os
import time
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()

def safe_log(*args):
    msg = " ".join(str(a) for a in args)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None

PREFERRED_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-3.8-flash")
CANDIDATE_MODELS = [
    PREFERRED_MODEL,
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]
CANDIDATE_MODELS = list(dict.fromkeys([m for m in CANDIDATE_MODELS if m]))

def generate_story(outline: list) -> str:
    """Generate dynamic comic captions, sound effects, and character dialogues using Gemini 3.5 Flash Lite."""
    formatted_outline = "\n".join([
        f"Panel {item.get('panel', i+1)} - {item.get('title', '')}: {item.get('scene_description', '')}"
        for i, item in enumerate(outline)
    ])

    prompt = f"""
You are an expert comic book scriptwriter.
Given the comic panel outline below, write authentic comic-style narration, sound effects (SFX), and character dialogues for EACH panel.

PANEL BREAKDOWN:
{formatted_outline}

RULES FOR YOUR OUTPUT:
- For each panel, format strictly as:
  **Panel [Number]: [Panel Title]**
  **CAPTION:** (1-2 sentences of atmospheric scene setting or internal monologue)
  **DIALOGUE:** (Expressive character speech with character names in CAPS, e.g., ARIA: "We don't have much time!")
  **SFX:** (Optional punchy comic sound effect in asterisks, e.g., *KRA-KOOM!*, *WHIRRR*, *FWSHHH*)

- Keep each panel punchy, energetic, and visually synchronized with the outline.
- Do not add meta-commentary or explanations.
"""

    if client:
        for model_name in CANDIDATE_MODELS:
            safe_log(f"Attempting comic story generation with model: {model_name}")
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text and len(response.text.strip()) > 30:
                    safe_log(f"Comic story written successfully using {model_name}!")
                    return response.text.strip()
            except Exception as e:
                safe_log(f"Story generation attempt with {model_name} notice: {str(e)[:120]}")
                time.sleep(1)

    safe_log("Generating fallback narration from outline scene descriptions.")
    fallback_segments = []
    for i, item in enumerate(outline):
        p_num = item.get("panel", i + 1)
        title = item.get("title", f"Panel {p_num}")
        desc = item.get("scene_description", "")
        fallback_segments.append(
            f"**Panel {p_num}: {title}**\n"
            f"**CAPTION:** {desc}\n"
            f"**SFX:** *VWOOOSH!*\n"
            f"**DIALOGUE:** HERO: \"The adventure is only beginning!\""
        )
    return "\n\n".join(fallback_segments)