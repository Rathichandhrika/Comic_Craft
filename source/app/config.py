import os
from functools import lru_cache
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Settings(BaseModel):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_outline_model: str = os.getenv(
        "GEMINI_OUTLINE_MODEL", os.getenv("GEMINI_FLASH_MODEL", "gemini-3.8-flash")
    )
    gemini_story_model: str = os.getenv(
        "GEMINI_STORY_MODEL", os.getenv("GEMINI_PRO_MODEL", "gemini-3.8-flash")
    )
    image_backend: str = os.getenv("IMAGE_BACKEND", "pollinations")
    hf_token: str = os.getenv("HF_TOKEN", os.getenv("HF_API_KEY", ""))
    hf_image_model: str = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    diffusion_model: str = os.getenv("DIFFUSION_MODEL", "sd-legacy/stable-diffusion-v1-5")
    pollinations_api_key: str = os.getenv("POLLINATIONS_API_KEY", "")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))


@lru_cache()
def get_settings() -> Settings:
    return Settings()
