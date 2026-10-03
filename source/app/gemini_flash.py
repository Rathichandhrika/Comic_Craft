import os
import json
import re
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

PREFERRED_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-3.8-flash")
CANDIDATE_MODELS = [
    PREFERRED_MODEL,
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]
# Deduplicate while preserving order
CANDIDATE_MODELS = list(dict.fromkeys([m for m in CANDIDATE_MODELS if m]))

def generate_outline(user_prompt: str, panel_count: int = 5) -> list:
    """Generate a structured multi-panel comic outline using Gemini 3.5 Flash Lite with smart fallbacks."""
    prompt = f"""
You are a master comic book architect and visual storyteller.
Generate a strictly formatted JSON array containing EXACTLY {panel_count} panel descriptions for an epic graphic novel based on the story idea below.
Do NOT include any conversational filler, markdown intro/outro or explanations. Return ONLY the raw JSON array.

STORY IDEA: "{user_prompt}"

Each JSON object in the array must strictly have these keys:
- "panel": integer (1 to {panel_count})
- "title": short punchy comic panel title (e.g., "The Awakening", "Shadows Fall")
- "scene_description": vivid setting and action description for the narrative
- "image_prompt": concise visual prompt for AI image generation, describing the subject, environment, lighting and perspective (e.g. "Cyberpunk ninja standing on rain-slick rooftop at night with glowing neon reflections")
"""

    if client:
        for model_name in CANDIDATE_MODELS:
            safe_log(f"Attempting comic outline with Gemini model: {model_name}")
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    output_text = response.text.strip() if response and response.text else ""
                    
                    # Clean markdown code blocks if wrapped
                    if "```" in output_text:
                        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", output_text)
                        if match:
                            output_text = match.group(1).strip()

                    # Fallback regex finding bracketed json array
                    if not output_text.startswith("["):
                        array_match = re.search(r"\[[\s\S]*\]", output_text)
                        if array_match:
                            output_text = array_match.group(0).strip()

                    panel_data = json.loads(output_text)
                    if isinstance(panel_data, list) and len(panel_data) >= 3:
                        safe_log(f"Comic outline generated successfully with {len(panel_data)} panels via {model_name}!")
                        return panel_data

                except Exception as e:
                    safe_log(f"Outline attempt with {model_name} (try {attempt+1}) notice: {str(e)[:120]}")
                    time.sleep(1)

    safe_log("Gemini outline generation fallback activated.")
    return _build_fallback_outline(user_prompt, panel_count)


def _build_fallback_outline(prompt: str, count: int = 5) -> list:
    """Intelligent dynamic fallback comic outline if API encounters quotas or outages."""
    titles = [
        "The Genesis",
        "The Discovery",
        "Rising Tension",
        "Climactic Confrontation",
        "A New Dawn",
        "Beyond the Horizon"
    ]
    outline = []
    for i in range(count):
        num = i + 1
        title = titles[i] if i < len(titles) else f"Chapter {num}"
        outline.append({
            "panel": num,
            "title": title,
            "scene_description": f"Panel {num}: {prompt} - Scene {num} unfolds with dramatic tension.",
            "image_prompt": f"Dramatic comic panel {num}, graphic novel scene, {prompt}, dynamic lighting, high quality",
        })
    return outline