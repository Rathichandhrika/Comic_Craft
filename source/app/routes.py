import os
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.exporters import save_pdf
from app.gemini_flash import generate_outline
from app.gemini_pro import generate_story
from app.image_generator import generate_image
from app.layout_builder import build_comic_layout

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class PromptRequest(BaseModel):
    prompt: str
    character_name: str
    setting: str
    tone: str
    style: str
    panel_count: Optional[int] = 5


class RegeneratePanelRequest(BaseModel):
    prompt: str
    style: Optional[str] = "Comic Book"
    panel_index: Optional[int] = 1


def _combine(prompt: str, character_name: str, setting: str, tone: str, style: str) -> str:
    return (
        f"Story idea: {prompt}\n"
        f"Main character: {character_name}\n"
        f"Setting: {setting}\n"
        f"Tone: {tone}\n"
        f"Art style: {style}"
    )


def _to_web_path(path: str) -> str:
    """Ensure filesystem paths are converted to relative 'static/...' web paths."""
    if os.path.isabs(path):
        path = os.path.relpath(path, BASE_DIR)
    return path.replace("\\", "/")


def _run_pipeline(full_prompt: str, style: str = "", panel_count: int = 5):
    outline = generate_outline(full_prompt, panel_count=panel_count)
    if not outline or len(outline) < 3:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate a valid comic outline. Check your GEMINI_API_KEY and terminal logs."
        )

    try:
        full_story = generate_story(outline)
    except Exception as e:
        print(f"Warning: Story generation fallback triggered ({e})")
        full_story = "\n".join([f"**Panel {i+1}: {item.get('title', '')}**\n**CAPTION:** {item.get('scene_description', '')}" for i, item in enumerate(outline)])

    if not full_story:
        full_story = ""

    images = []
    for i, panel in enumerate(outline):
        img_prompt = panel.get("image_prompt", "")
        panel_num = panel.get("panel", i + 1)
        img_path = generate_image(img_prompt, panel_number=panel_num, style=style)
        images.append(_to_web_path(img_path))

    layout = build_comic_layout(images, full_story, outline)
    pdf_path = save_pdf(layout)
    web_pdf_path = _to_web_path(pdf_path)
    return layout, web_pdf_path


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )


@router.post("/generate")
def generate(
    request: Request,
    prompt: str = Form(...),
    character_name: str = Form(...),
    setting: str = Form(...),
    tone: str = Form(...),
    style: str = Form(...),
    panel_count: int = Form(5),
):
    full_prompt = _combine(prompt, character_name, setting, tone, style)
    layout, web_pdf_path = _run_pipeline(full_prompt, style=style, panel_count=panel_count)
    
    # Story title from prompt or first panel
    story_title = layout[0]["title"] if layout and "title" in layout[0] else prompt[:30]

    return templates.TemplateResponse(
        request=request,
        name="comic_preview.html",
        context={
            "request": request,
            "layout": layout,
            "pdf_path": web_pdf_path,
            "story_title": story_title,
            "prompt": prompt,
            "character_name": character_name,
            "setting": setting,
            "tone": tone,
            "style": style,
            "panel_count": len(layout)
        },
    )


@router.post("/generate-comic/json")
def generate_comic_json(body: PromptRequest):
    full_prompt = _combine(body.prompt, body.character_name, body.setting, body.tone, body.style)
    layout, web_pdf_path = _run_pipeline(full_prompt, style=body.style, panel_count=body.panel_count or 5)
    return {"layout": layout, "pdf_path": web_pdf_path}


@router.post("/api/regenerate-panel")
def regenerate_panel(body: RegeneratePanelRequest):
    img_path = generate_image(body.prompt, panel_number=body.panel_index or 1, style=body.style or "Comic Book")
    web_path = _to_web_path(img_path)
    return {"success": True, "image_path": web_path}


@router.get("/export-success")
def export_success(request: Request, pdf_path: str):
    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={"request": request, "pdf_path": pdf_path},
    )


@router.get("/test-image")
def test_image(prompt: str = "A futuristic city at sunset, sci-fi, cinematic, comic book style"):
    image_path = generate_image(prompt, style="Cyberpunk")
    return {"message": "Image generated successfully", "path": _to_web_path(image_path)}