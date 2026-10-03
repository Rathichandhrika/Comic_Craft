import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Anchor base directory to comiccraft/source
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.routes import router  # noqa: E402

STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure static directories exist
for sub in ("panels", "exports", "fonts", "css"):
    os.makedirs(os.path.join(STATIC_DIR, sub), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure directories exist
    for sub in ("panels", "exports", "fonts", "css"):
        os.makedirs(os.path.join(STATIC_DIR, sub), exist_ok=True)
    yield


app = FastAPI(title="ComicCraft - AI Comic Story Creator", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)