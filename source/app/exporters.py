import os
import time
import base64
import io
import urllib.request
from fpdf import FPDF
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
EXPORT_DIR = os.path.join(BASE_DIR, "static", "exports")
TEMP_CACHE_DIR = os.path.join(BASE_DIR, "static", "temp_images")


def _resolve_image_file(img_path: str, panel_idx: int = 0) -> str:
    """Resolve web URLs, base64 strings, relative paths, and absolute paths to a usable local file."""
    if not img_path:
        return ""

    raw = str(img_path).strip()
    os.makedirs(TEMP_CACHE_DIR, exist_ok=True)

    # 1. Handle Remote Image URLs (Pollinations / HuggingFace / CDN)
    if raw.startswith("http://") or raw.startswith("https://"):
        try:
            cache_file = os.path.join(TEMP_CACHE_DIR, f"web_panel_{panel_idx}_{int(time.time())}.png")
            req = urllib.request.Request(raw, headers={"User-Agent": "ComicCraft/1.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
            with Image.open(io.BytesIO(img_data)) as im:
                im.convert("RGB").save(cache_file, "PNG")
            return cache_file
        except Exception as e:
            print(f"[PDF Resolve Warning] Failed downloading web image: {e}")
            return ""

    # 2. Handle Base64 Data URIs
    if raw.startswith("data:image"):
        try:
            base64_data = raw.split(",", 1)[1] if "," in raw else raw
            decoded = base64.b64decode(base64_data)
            cache_file = os.path.join(TEMP_CACHE_DIR, f"b64_panel_{panel_idx}_{int(time.time())}.png")
            with Image.open(io.BytesIO(decoded)) as im:
                im.convert("RGB").save(cache_file, "PNG")
            return cache_file
        except Exception as e:
            print(f"[PDF Resolve Warning] Failed decoding base64 image: {e}")
            return ""

    # 3. Clean query parameters from local paths
    clean_path = raw.split("?")[0].strip()

    # 4. Direct file check if already absolute
    if os.path.isfile(clean_path):
        return _ensure_compatible_format(clean_path, panel_idx)

    # Strip leading slashes to prevent Windows path collisions
    norm_rel = clean_path.lstrip("/\\")

    # 5. Check directly relative to BASE_DIR (e.g., static/panels/filename.png)
    candidate = os.path.join(BASE_DIR, norm_rel)
    if os.path.isfile(candidate):
        return _ensure_compatible_format(candidate, panel_idx)

    # 6. Check if norm_rel needs "static" prefix (e.g., panels/filename.png)
    candidate = os.path.join(BASE_DIR, "static", norm_rel)
    if os.path.isfile(candidate):
        return _ensure_compatible_format(candidate, panel_idx)

    # 7. Check by filename inside static/panels
    fname = os.path.basename(clean_path)
    if fname:
        candidate = os.path.join(BASE_DIR, "static", "panels", fname)
        if os.path.isfile(candidate):
            return _ensure_compatible_format(candidate, panel_idx)

        # 8. Check in workspace root static/panels
        workspace_root = os.path.dirname(BASE_DIR)
        candidate = os.path.join(workspace_root, "static", "panels", fname)
        if os.path.isfile(candidate):
            return _ensure_compatible_format(candidate, panel_idx)

    return ""


def _ensure_compatible_format(file_path: str, panel_idx: int) -> str:
    """Converts WebP or unusual image formats to PNG so FPDF can load them reliably."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".png", ".jpg", ".jpeg"]:
        return file_path
    try:
        os.makedirs(TEMP_CACHE_DIR, exist_ok=True)
        converted = os.path.join(TEMP_CACHE_DIR, f"conv_panel_{panel_idx}_{int(time.time())}.png")
        with Image.open(file_path) as im:
            im.convert("RGB").save(converted, "PNG")
        return converted
    except Exception:
        return file_path


def save_pdf(layout, comic_title: str = "ComicCraft Graphic Novel"):
    os.makedirs(EXPORT_DIR, exist_ok=True)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # Check for Unicode TTF font availability
    font_name = "ComicFont"
    unicode_ok = False

    candidate_regular = [
        FONT_PATH,
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    candidate_bold = [
        os.path.join(BASE_DIR, "static", "fonts", "DejaVuSans-Bold.ttf"),
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    candidate_italic = [
        os.path.join(BASE_DIR, "static", "fonts", "DejaVuSans-Oblique.ttf"),
        r"C:\Windows\Fonts\ariali.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    ]

    reg_font = next((p for p in candidate_regular if os.path.isfile(p)), None)
    bold_font = next((p for p in candidate_bold if os.path.isfile(p)), reg_font)
    italic_font = next((p for p in candidate_italic if os.path.isfile(p)), reg_font)

    if reg_font:
        try:
            pdf.add_font("ComicFont", "", reg_font)
            if bold_font:
                pdf.add_font("ComicFont", "B", bold_font)
            if italic_font:
                pdf.add_font("ComicFont", "I", italic_font)
            unicode_ok = True
        except Exception as fe:
            print(f"[PDF Export Notice] Font load fallback: {fe}")
            font_name = "Helvetica"
    else:
        font_name = "Helvetica"

    def safe(text: str) -> str:
        if unicode_ok:
            return str(text)
        return str(text).encode("latin-1", "replace").decode("latin-1")

    # Add each panel as an illustrated graphic novel page
    for idx, panel in enumerate(layout):
        pdf.add_page()
        panel_num = panel.get("panel", idx + 1)
        panel_title = panel.get("title", f"Panel {panel_num}")

        # Page Header Banner / Panel title
        pdf.set_fill_color(17, 24, 39)
        pdf.rect(0, 0, pdf.w, 22, "F")
        pdf.set_xy(10, 5)
        pdf.set_text_color(255, 87, 34)
        pdf.set_font(font_name, "B", 14)
        pdf.cell(pdf.w - 20, 10, safe(f"PANEL {panel_num}  |  {panel_title.upper()}"), ln=1, align="C")

        # Resolve image (URL, base64, or local path)
        raw_img_path = panel.get("image_path") or panel.get("image_url") or panel.get("image") or ""
        resolved_img = _resolve_image_file(raw_img_path, panel_num)

        # Image display container specs
        box_x = 15
        box_y = 28
        box_w = pdf.w - 30
        box_h = 112

        image_rendered = False
        if resolved_img and os.path.isfile(resolved_img):
            try:
                with Image.open(resolved_img) as pil_img:
                    orig_w, orig_h = pil_img.size

                img_ratio = orig_w / max(orig_h, 1)
                box_ratio = box_w / box_h

                if img_ratio > box_ratio:
                    render_w = box_w
                    render_h = box_w / img_ratio
                else:
                    render_h = box_h
                    render_w = box_h * img_ratio

                render_x = box_x + (box_w - render_w) / 2
                render_y = box_y + (box_h - render_h) / 2

                pdf.set_fill_color(15, 23, 42)
                pdf.rect(box_x, box_y, box_w, box_h, "F")

                pdf.image(resolved_img, x=render_x, y=render_y, w=render_w, h=render_h)

                pdf.set_draw_color(30, 41, 59)
                pdf.set_line_width(0.8)
                pdf.rect(box_x, box_y, box_w, box_h)

                image_rendered = True
                print(f"[PDF Export] Successfully embedded image for Panel {panel_num}: {resolved_img}")
            except Exception as exc:
                print(f"[PDF Export Warning] Image render failed for Panel {panel_num} ({resolved_img}): {exc}")

        if not image_rendered:
            pdf.set_fill_color(24, 24, 27)
            pdf.rect(box_x, box_y, box_w, box_h, "F")
            pdf.set_draw_color(249, 115, 22)
            pdf.set_line_width(0.8)
            pdf.rect(box_x, box_y, box_w, box_h)

            pdf.set_xy(box_x, box_y + 45)
            pdf.set_text_color(251, 146, 60)
            pdf.set_font(font_name, "B", 13)
            pdf.cell(box_w, 8, safe(f"[ PANEL {panel_num} ART ]"), align="C", ln=1)

            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(156, 163, 175)
            scene_hint = panel.get("scene_description", panel.get("caption", ""))[:120]
            if scene_hint:
                pdf.set_x(box_x + 10)
                pdf.multi_cell(box_w - 20, 5, safe(scene_hint), align="C")

        # SFX Banner if available
        curr_y = box_y + box_h + 6
        sfx_text = panel.get("sfx", "")
        if sfx_text:
            pdf.set_xy(box_x, curr_y)
            pdf.set_font(font_name, "B", 13)
            pdf.set_text_color(245, 158, 11)
            pdf.cell(box_w, 7, safe(f"*** {sfx_text.upper()} ***"), align="C", ln=1)
            curr_y += 8

        # Narration Box
        caption_text = panel.get("caption", "")
        if caption_text:
            pdf.set_xy(box_x, curr_y)
            pdf.set_fill_color(254, 243, 199)
            pdf.set_draw_color(217, 119, 6)
            pdf.set_text_color(30, 30, 30)
            pdf.set_font(font_name, "I" if unicode_ok else "", 10)
            pdf.multi_cell(box_w, 6, safe(f"NARRATION: {caption_text}"), border=1, fill=True)
            curr_y = pdf.get_y() + 4

        # Character Dialogue Box
        dialogue_text = panel.get("dialogue", "")
        if dialogue_text:
            pdf.set_xy(box_x, curr_y)
            pdf.set_fill_color(241, 245, 249)
            pdf.set_draw_color(100, 116, 139)
            pdf.set_text_color(15, 23, 42)
            pdf.set_font(font_name, "B", 10)
            pdf.multi_cell(box_w, 6, safe(f"DIALOGUE:\n{dialogue_text}"), border=1, fill=True)
            curr_y = pdf.get_y() + 4
        elif not caption_text:
            fallback_text = panel.get("text", "")
            if fallback_text:
                pdf.set_xy(box_x, curr_y)
                pdf.set_text_color(20, 20, 20)
                pdf.set_font(font_name, "", 10)
                pdf.multi_cell(box_w, 6, safe(fallback_text))

        # Comic Page Footer
        pdf.set_xy(box_x, pdf.h - 12)
        pdf.set_font(font_name, "", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(box_w / 2, 6, safe(comic_title), align="L")
        pdf.cell(box_w / 2, 6, safe(f"Page {idx + 1} of {len(layout)}"), align="R")

    pdf_path = os.path.join(EXPORT_DIR, f"comiccraft_{int(time.time())}.pdf")
    pdf.output(pdf_path)
    return pdf_path.replace("\\", "/")