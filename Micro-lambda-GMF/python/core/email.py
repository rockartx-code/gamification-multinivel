"""Envío de correo por SES."""

import boto3
from .settings import AWS_REGION, SES_FROM_EMAIL


_ses_client = None

def _get_ses():
    global _ses_client
    if _ses_client is None:
        _ses_client = boto3.client("ses", region_name=AWS_REGION)
    return _ses_client

def _send_ses_email(to_email: str, subject: str, text: str, html: str) -> None:
    """Envía un correo vía SES. Falla silenciosamente para no interrumpir el flujo."""
    try:
        _get_ses().send_email(
            Source=SES_FROM_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text, "Charset": "UTF-8"},
                    "Html": {"Data": html, "Charset": "UTF-8"},
                },
            },
        )
    except Exception as e:
        print(f"[SES_ERROR] {to_email}: {e}")


# ── Plantilla base compartida por todos los correos ──────────────────
_EMAIL_BASE_CSS = """
body { margin:0; padding:0; background-color:#F9F7F2; font-family:'Segoe UI',Arial,sans-serif; }
.wrap { width:100%; max-width:600px; margin:0 auto; padding:24px 16px; }
.card { background:#ffffff; border-radius:24px; padding:40px 36px; text-align:center; border:1px solid #e8e3d8; }
.logo { margin-bottom:24px; }
.icon { font-size:48px; margin-bottom:8px; }
.title { color:#2D3436; font-family:Georgia,serif; font-size:26px; font-weight:bold; margin:0 0 16px; }
.lead { color:#636e72; line-height:1.7; font-size:15px; margin:0 0 20px; }
.benefit-item { text-align:left; margin-bottom:14px; padding:14px 16px; background:#FFFDF5; border-radius:14px; display:flex; align-items:flex-start; gap:12px; }
.benefit-icon { font-size:20px; flex-shrink:0; margin-top:2px; }
.benefit-body strong { display:block; color:#2D3436; font-size:14px; }
.benefit-body span { color:#636e72; font-size:13px; }
.info-box { background:#f9f9f9; border-radius:14px; padding:18px 20px; margin:20px 0; text-align:left; }
.info-box p { margin:0 0 6px; color:#333; font-size:14px; }
.info-box p:last-child { margin-bottom:0; }
.btn { background:#D4AF37; color:#333 !important; padding:14px 32px; border-radius:50px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:20px; font-size:15px; }
.otp-box { display:inline-block; background:#FFFDF5; border:2px solid #D4AF37; border-radius:16px; padding:16px 40px; margin:20px 0; font-size:36px; font-weight:bold; letter-spacing:10px; color:#2D3436; }
.divider { border:none; border-top:1px solid #eee; margin:28px 0; }
.footer { font-size:12px; color:#aaa; margin-top:24px; }
"""


def _email_shell(body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{_EMAIL_BASE_CSS}</style></head>
<body>
<div class="wrap">
  <div class="logo" style="text-align:center">
    <img src="https://www.findingu.com.mx/Logo-colores.svg" alt="Finding'u" width="140">
  </div>
  <div class="card">
    {body_html}
    <hr class="divider">
    <div class="footer">&copy; 2026 Finding&rsquo;U &nbsp;&bull;&nbsp; Nutrici&oacute;n que te impulsa</div>
  </div>
</div>
</body></html>"""
