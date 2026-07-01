# Cloud-ready Passpoint Provisioning Server

This project is a cloud-ready FastAPI server for Android Passpoint web provisioning.

## Objective

Provide Android with a Passpoint provisioning response that can trigger the Android Wi-Fi installer instead of downloading a normal XML file.

## Key Endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Landing page with TRUE and DTAC QR Codes |
| `/install/true` | TRUE installation page |
| `/install/dtac` | DTAC installation page |
| `/passpoint.config?profile=true` | TRUE Android provisioning endpoint |
| `/passpoint.config?profile=dtac` | DTAC Android provisioning endpoint |
| `/health` | Cloud health check |

## Important Concept

A normal `.xml` file usually downloads in Android browser. For Android web-based Passpoint provisioning, the server must return:

```http
Content-Type: application/x-wifi-config
Content-Transfer-Encoding: base64
```

The response body is a base64-encoded multipart MIME payload containing the Passpoint profile XML and optional certificate.

## Project Structure

```text
passpoint-provisioning-server/
├─ main.py
├─ requirements.txt
├─ render.yaml
├─ Procfile
├─ profiles/
│  ├─ true.xml
│  └─ dtac.xml
├─ certificates/
│  └─ README.md
├─ templates/
│  ├─ index.html
│  └─ install.html
└─ static/
   └─ style.css
```

## Deploy on Render via Browser

1. Create a new GitHub repository.
2. Upload all files in this folder.
3. Open Render.
4. Create a new Web Service.
5. Connect the GitHub repository.
6. Render can read `render.yaml` automatically.
7. Deploy.
8. Open the Render public URL.
9. Scan TRUE or DTAC QR from Android Chrome.
10. Tap the Install button.

## Replace Sample Profiles

The included `profiles/true.xml` and `profiles/dtac.xml` are sample placeholders only. Replace them with validated Passpoint profiles before real testing.

## Test Flow

```text
Android Chrome
→ Scan TRUE QR
→ /install/true
→ Tap Install TRUE Passpoint
→ /passpoint.config?profile=true
→ Android Wi-Fi installer should appear if the profile format and device support are correct
```

## Notes

- User approval is still required by Android.
- Silent installation from web is not allowed.
- Android behavior may vary by OS version, browser, OEM implementation, and profile correctness.
- Chrome is recommended for testing.
