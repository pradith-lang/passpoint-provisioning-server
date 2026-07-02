import base64
import uuid
from pathlib import Path
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Passpoint Provisioning Server", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "profiles"
CERT_DIR = BASE_DIR / "certificates"

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

PROFILE_MAP = {
    "true": {
        "display_name": "TRUE Passpoint",
        "profile_file": "true.xml",
        # Optional CA certificate. Leave as None if not required for EAP-SIM / EAP-AKA lab testing.
        "ca_file": None,
    },
    "dtac": {
        "display_name": "DTAC Passpoint",
        "profile_file": "dtac.xml",
        "ca_file": None,
    },
}


def _read_file_bytes(path: Path) -> bytes:
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")
    return path.read_bytes()


def build_android_wifi_config(profile_key: str) -> bytes:
    """
    Build Android Passpoint web provisioning payload.

    Android web-based Passpoint provisioning expects:
    - HTTP Content-Type: application/x-wifi-config
    - HTTP Content-Transfer-Encoding: base64
    - HTTP body: base64-encoded multipart/mixed MIME content

    Replace the sample XML profiles with validated operator profiles before production use.
    """
    item = PROFILE_MAP.get(profile_key)
    if not item:
        raise HTTPException(status_code=400, detail="Invalid profile. Use true or dtac.")

    profile_bytes = _read_file_bytes(PROFILE_DIR / item["profile_file"])
    boundary = f"----passpoint-{uuid.uuid4().hex}"

    parts = []
    profile_part = "\r\n".join([
        f"--{boundary}",
        "Content-Type: application/x-passpoint-profile",
        "Content-Transfer-Encoding: base64",
        "",
        base64.b64encode(profile_bytes).decode("ascii"),
    ])
    parts.append(profile_part)

    ca_file = item.get("ca_file")
    if ca_file:
        cert_bytes = _read_file_bytes(CERT_DIR / ca_file)
        cert_part = "\r\n".join([
            f"--{boundary}",
            "Content-Type: application/x-x509-ca-cert",
            "Content-Transfer-Encoding: base64",
            f"Content-Disposition: attachment; filename=\"{ca_file}\"",
            "",
            base64.b64encode(cert_bytes).decode("ascii"),
        ])
        parts.append(cert_part)

    closing = f"--{boundary}--"
    multipart_text = "\r\n".join(parts + [closing, ""])
    return base64.b64encode(multipart_text.encode("utf-8"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Passpoint Installation Portal", "profiles": PROFILE_MAP},
    )


@app.get("/install/{profile_key}", response_class=HTMLResponse)
def install_page(request: Request, profile_key: str):
    if profile_key not in PROFILE_MAP:
        raise HTTPException(status_code=404, detail="Profile not found")
    return templates.TemplateResponse(
        "install.html",
        {
            "request": request,
            "profile_key": profile_key,
            "display_name": PROFILE_MAP[profile_key]["display_name"],
        },
    )


@app.get("/passpoint.config")
def passpoint_config(profile: str):
    payload = build_android_wifi_config(profile.lower())
    return Response(
        content=payload,
        media_type="application/x-wifi-config",
        headers={
            "Content-Transfer-Encoding": "base64",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
