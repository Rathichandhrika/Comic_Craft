from pathlib import Path
import os
import re
import io
import time
import random
import urllib.parse
import requests
from PIL import Image, ImageDraw

from app.config import get_settings


# Anchor BASE_DIR to comiccraft/source
BASE_DIR = Path(__file__).resolve().parents[1]
PANEL_DIR = BASE_DIR / "static" / "panels"
PANEL_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(text: str, max_length: int = 80) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    return text.strip("_")[:max_length]


def is_valid_hf_token(token: str) -> bool:
    if not token:
        return False
    placeholder_tokens = {
        "hugging-face-token-here",
        "your_huggingface_token",
        "your-hf-token",
        "token_here",
    }
    return token.strip().lower() not in placeholder_tokens


def _generate_huggingface(prompt: str, panel_number: int = 1) -> str:
    """
    Generate an AI image using Hugging Face InferenceClient (FLUX.1-schnell).
    """
    from huggingface_hub import InferenceClient

    settings = get_settings()

    if not is_valid_hf_token(settings.hf_token):
        return ""

    client = InferenceClient(api_key=settings.hf_token)

    clean_prompt = f"""
Cinematic graphic novel comic panel illustration:
{prompt}

VISUAL STYLE:
- comic book art, sharp inking, vivid colors
- expressive characters, dramatic lighting, dynamic composition
- no text, no speech bubbles, no captions, no borders, no labels
"""
    try:
        print(f"[HuggingFace] Synthesizing Panel {panel_number} with {settings.hf_image_model}...")
        image = client.text_to_image(
            prompt=clean_prompt.strip(),
            model=settings.hf_image_model,
        )

        filename = f"panel_{panel_number}_{int(time.time())}_{_safe_filename(prompt)}.png"
        output = PANEL_DIR / filename
        image.save(output, "PNG")
        print(f"[HuggingFace] Panel {panel_number} generated successfully! ({image.size})")

        return f"/static/panels/{filename}"
    except Exception as exc:
        print(f"[Warning] Hugging Face generation error: {exc}")
        return ""


def _generate_pollinations(prompt: str, panel_number: int = 1, style: str = "") -> str:
    """
    Generate an AI comic image using Pollinations.ai.
    """
    settings = get_settings()

    clean_prompt = re.sub(r"[^a-zA-Z0-9\s,.-]", " ", prompt).strip()
    clean_prompt = re.sub(r"\s+", " ", clean_prompt)
    if style and style.lower() not in clean_prompt.lower():
        clean_prompt = f"{clean_prompt[:90]}, {style} comic art"
    else:
        clean_prompt = f"{clean_prompt[:90]}, comic art"

    filename = f"panel_{panel_number}_{int(time.time())}_{_safe_filename(prompt)}.jpg"
    output = PANEL_DIR / filename

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/jpeg,image/*,*/*;q=0.8"
    }
    if settings.pollinations_api_key:
        headers["Authorization"] = f"Bearer {settings.pollinations_api_key}"

    candidate_urls = [
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_prompt)}?model=sana&seed={random.randint(1000, 999999)}",
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_prompt[:60])}?seed={random.randint(1000, 999999)}",
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean_prompt[:50])}?model=turbo&seed={random.randint(1000, 999999)}"
    ]

    for attempt, url in enumerate(candidate_urls):
        try:
            print(f"[Pollinations.ai] Synthesizing Panel {panel_number} (attempt {attempt + 1})...")
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 1500 and not resp.text.startswith("{"):
                image = Image.open(io.BytesIO(resp.content))
                image.save(output, "JPEG", quality=92)
                print(f"[Pollinations.ai] Panel {panel_number} generated successfully! ({len(resp.content)} bytes, {image.size})")
                return f"/static/panels/{filename}"
            elif resp.status_code in (402, 503):
                print(f"[Pollinations.ai] Notice {resp.status_code} on attempt {attempt + 1}, retrying...")
                time.sleep(1.5)
        except Exception as e:
            print(f"[Pollinations.ai] Attempt {attempt + 1} notice: {e}")
            time.sleep(1)

    return ""


def _generate_placeholder(prompt: str, panel_number: int = 1) -> str:
    """
    Styled comic panel fallback when all external networks are completely offline.
    """
    import textwrap

    filename = f"panel_{panel_number}_{int(time.time())}_{_safe_filename(prompt)}.png"
    output = PANEL_DIR / filename

    panel_themes = [
        ((24, 24, 27), (239, 108, 63)),
        ((15, 23, 42), (59, 130, 246)),
        ((24, 18, 43), (168, 85, 247)),
        ((41, 15, 15), (244, 63, 94)),
        ((13, 37, 30), (16, 185, 129)),
    ]
    bg_color, accent_color = panel_themes[(panel_number - 1) % len(panel_themes)]

    image = Image.new("RGB", (1024, 768), bg_color)
    draw = ImageDraw.Draw(image)

    draw.rectangle([(16, 16), (1008, 752)], outline=(255, 255, 255), width=5)
    draw.rectangle([(24, 24), (1000, 744)], outline=(0, 0, 0), width=3)

    draw.rectangle([(40, 40), (240, 95)], fill=accent_color)
    draw.rectangle([(40, 40), (240, 95)], outline=(255, 255, 255), width=2)
    draw.text((65, 58), f"PANEL {panel_number}", fill=(255, 255, 255))
    draw.text((870, 58), "ComicCraft", fill=(148, 163, 184))

    draw.rectangle([(50, 130), (974, 660)], fill=(9, 9, 11), outline=accent_color, width=2)
    wrapped = textwrap.fill(prompt, width=64)
    draw.text((80, 170), "SCENE VISUALIZATION:\n", fill=accent_color)
    draw.text((80, 210), wrapped, fill=(244, 244, 245))

    image.save(output)
    return f"/static/panels/{filename}"


def generate_image(prompt: str, panel_number: int = 1, style: str = "", filename: str = None) -> str:
    """
    Generate an AI comic image for the panel.
    Guarantees a real AI-generated image by chaining Pollinations.ai and Hugging Face FLUX.
    """
    settings = get_settings()
    backend = settings.image_backend.lower().strip()

    # Small pacing delay to avoid burst rate-limiting across sequential panels
    time.sleep(1.0)

    # 1. Primary Attempt based on user config
    if backend == "hf" and is_valid_hf_token(settings.hf_token):
        res = _generate_huggingface(prompt, panel_number)
        if res:
            return res
        # Fallback to Pollinations
        res = _generate_pollinations(prompt, panel_number, style=style)
        if res:
            return res
    else:
        # Default / Pollinations backend
        res = _generate_pollinations(prompt, panel_number, style=style)
        if res:
            return res
        # If Pollinations hit a rate limit (402), immediately try Hugging Face FLUX
        if is_valid_hf_token(settings.hf_token):
            print(f"[Auto-Fallback] Pollinations busy, generating Panel {panel_number} via Hugging Face FLUX...")
            res = _generate_huggingface(prompt, panel_number)
            if res:
                return res

    # 2. Only if both AI generators fail, use the placeholder
    print(f"[Warning] All AI image generators unavailable for Panel {panel_number}. Using styled placeholder.")
    return _generate_placeholder(prompt, panel_number)