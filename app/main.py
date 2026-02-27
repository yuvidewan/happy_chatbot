from io import BytesIO
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import qrcode

from app.api.routes import router
from app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HappyBot", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(router)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def _resolve_public_url(request: Request) -> str:
    configured = (os.getenv("HAPPYBOT_PUBLIC_URL", "") or "").strip()
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


@app.get("/share")
def share_info(request: Request):
    public_url = _resolve_public_url(request)
    return {"public_url": public_url, "qr_png_url": f"{public_url}/qr.png"}


@app.get("/qr.png")
def qr_code_png(request: Request):
    public_url = _resolve_public_url(request)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(public_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health")
def health_check():
    model_backend = (os.getenv("HAPPYBOT_MODEL_BACKEND", "local") or "local").strip().lower()
    return {"status": "ok", "service": "happybot", "model_backend": model_backend}
