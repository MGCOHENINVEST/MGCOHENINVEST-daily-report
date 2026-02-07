# /opt/daily-report/scripts/email_branding.py
from __future__ import annotations


def branding_meta() -> str:
    # Force light mode only (per WNAP weekly rule: light mode styling only).
    # Avoid advertising dark-mode support, which can trigger client inversions.
    return '<meta name="color-scheme" content="light">\n'


def branding_css() -> str:
    # White "pill" behind logo: keeps logo readable on darker headers.
    # No inversion hacks, since we're committing to light-only rendering.
    return """
/* --- Branding: light-mode only --- */
.logo-pill{
  display:inline-block;
  background:#ffffff;
  border-radius:12px;
  padding:8px 12px;
  line-height:0;
}
.logo-img{
  display:block;
  height:auto;
  max-width:160px;
  border:0;
  outline:none;
  text-decoration:none;
}
""".strip() + "\n"


def logo_block_html(width: int = 160, alt: str = "Kairos") -> str:
    # CID must be Content-ID: <logo> in the email wrapper.
    return (
        '<div class="logo-pill">'
        f'<img class="logo-img" src="cid:logo" width="{int(width)}" alt="{alt}">'
        '</div>'
    )
