import base64
from pathlib import Path
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Passpoint Provisioning Server", version="1.1.0")

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "profiles"

# Keep existing portal UI files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Map URL profile name to actual XML file in /profiles
PROFILE_MAP = {
    "true": {
        "display_name": "TRUE Passpoint",
        "profile_file": "true.xml",
    },
    "dtac": {
        "display_name": "DTAC Passpoint",
        "profile_file": "dtac.xml",
    },
    "single": {
        "display_name": "Single Passpoint",
        "profile_file": "single.xml",
    },
}

# Use a stable boundary similar to android_passpoint reference implementation.
# The value only needs to be unique enough not to appear inside the MIME body.
BOUNDARY = "l1ZMD64Ujevti9JwYOrJoLo4YmoJLJZU"


def _get_profile_item(profile_key: str) -> dict:
    key = profile_key.lower().replace(".xml", "")
    item = PROFILE_MAP.get(key)
    if not item:
        raise HTTPException(status_code=400, detail="Invalid profile. Use true or dtac.")
    return item


def _read_profile_xml(profile_key: str) -> str:
    item = _get_profile_item(profile_key)
    profile_path = PROFILE_DIR / item["profile_file"]

    if not profile_path.exists() or not profile_path.is_file():
        raise HTTPException(status_code=404, detail=f"Profile file not found: {item['profile_file']}")

    # Read exactly as UTF-8 text. Do not modify the XML content here.
    return profile_path.read_text(encoding="utf-8")


def build_android_passpoint_payload(profile_xml: str) -> str:
    """
    Build Android Passpoint R1 web provisioning payload.

    Outer HTTP response:
      Content-Type: application/x-wifi-config
      Content-Transfer-Encoding: base64

    HTTP body:
      base64( multipart/mixed MIME document )

    MIME document:
      Content-Type: multipart/mixed; boundary=<BOUNDARY>
      Content-Transfer-Encoding: base64

      --<BOUNDARY>
      Content-Type: application/x-passpoint-profile
      Content-Transfer-Encoding: base64

      base64(profile XML)
      --<BOUNDARY>--
    """

    profile_b64 = base64.b64encode(profile_xml.encode("utf-8")).decode("ascii")

    # This structure follows the android_passpoint style used for Passpoint web provisioning.
    # Keep CRLF line endings for MIME compatibility.
    multipart_payload = (
        f"Content-Type: multipart/mixed; boundary={BOUNDARY}\r\n"
        f"Content-Transfer-Encoding: base64\r\n"
        f"\r\n"
        f"--{BOUNDARY}\r\n"
        f"Content-Type: application/x-passpoint-profile\r\n"
        f"Content-Transfer-Encoding: base64\r\n"
        f"\r\n"
        f"{profile_b64}\r\n"
        f"--{BOUNDARY}--\r\n"
    )

    return base64.b64encode(multipart_payload.encode("ascii")).decode("ascii")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Passpoint Installation Portal",
            "profiles": PROFILE_MAP,
        },
    )


@app.get("/install/{profile_key}", response_class=HTMLResponse)
def install_page(request: Request, profile_key: str):
    item = _get_profile_item(profile_key)
    return templates.TemplateResponse(
        "install.html",
        {
            "request": request,
            "profile_key": profile_key.lower().replace(".xml", ""),
            "display_name": item["display_name"],
        },
    )


@app.get("/passpoint.config")
def passpoint_config(profile: str):
    profile_xml = _read_profile_xml(profile)
    payload = build_android_passpoint_payload(profile_xml)

    return Response(
        content=payload,
        media_type="application/x-wifi-config",
        headers={
            "Content-Transfer-Encoding": "base64",
            "Cache-Control": "no-store",
            # Important: Do NOT set Content-Disposition.
            # Android web provisioning expects no Content-Disposition header.
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
