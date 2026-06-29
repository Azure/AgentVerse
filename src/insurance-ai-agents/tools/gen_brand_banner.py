"""Generate brand-banner.svg: Microsoft logo × whitelabel brand logo that works on light & dark backgrounds.

The banner pairs the Microsoft "four squares" mark with a neutral hexagonal
brand mark + wordmark. To rebrand for a different company, edit the right-
hand side (the hexagon fill, the inner letter, and the wordmark text).
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "images" / "brand-banner.svg"

# Brand tokens — edit here to rebrand the banner.
BRAND_NAME = "Helix Insurance"
BRAND_MARK_LETTER = "A"
BRAND_PRIMARY = "#2563EB"   # blue-600
BRAND_PRIMARY_DARK = "#1E40AF"   # blue-800
BRAND_TEXT = "#1E3A8A"   # blue-800/900 for the wordmark

# Banner uses neutral mid-tone colors that work on both light and dark GitHub README backgrounds.
SVG = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 720 120\" width=\"720\" height=\"120\" role=\"img\" aria-label=\"Microsoft × {BRAND_NAME}\">
  <title>Microsoft × {BRAND_NAME}</title>

  <!-- Microsoft 4-square logo (vibrant colors visible on any background) -->
  <g transform=\"translate(40, 30)\">
    <rect x=\"0\"  y=\"0\"  width=\"28\" height=\"28\" fill=\"#F25022\"/>
    <rect x=\"32\" y=\"0\"  width=\"28\" height=\"28\" fill=\"#7FBA00\"/>
    <rect x=\"0\"  y=\"32\" width=\"28\" height=\"28\" fill=\"#00A4EF\"/>
    <rect x=\"32\" y=\"32\" width=\"28\" height=\"28\" fill=\"#FFB900\"/>
  </g>

  <!-- Microsoft text (mid-gray, readable on both light and dark bg) -->
  <text x=\"148\" y=\"70\" font-family=\"'Segoe UI', system-ui, sans-serif\" font-size=\"34\" font-weight=\"600\" fill=\"#737373\">Microsoft</text>

  <!-- Separator -->
  <text x=\"332\" y=\"76\" font-family=\"'Segoe UI', system-ui, sans-serif\" font-size=\"42\" font-weight=\"200\" fill=\"#A0A0A0\">×</text>

  <!-- Whitelabel hex mark — replace with customer logo by editing this group -->
  <g transform=\"translate(380, 30)\">
    <polygon points=\"30,2 55,16 55,44 30,58 5,44 5,16\" fill=\"{BRAND_PRIMARY_DARK}\"/>
    <polygon points=\"30,12 45,21 45,39 30,48 15,39 15,21\" fill=\"{BRAND_PRIMARY}\"/>
    <text x=\"30\" y=\"39\" text-anchor=\"middle\" font-family=\"'Segoe UI', system-ui, sans-serif\" font-size=\"22\" font-weight=\"700\" fill=\"#FFFFFF\">{BRAND_MARK_LETTER}</text>
  </g>

  <!-- Brand wordmark -->
  <text x=\"450\" y=\"70\" font-family=\"'Segoe UI', system-ui, sans-serif\" font-size=\"34\" font-weight=\"600\" fill=\"{BRAND_TEXT}\">{BRAND_NAME}</text>
</svg>
"""

OUT.write_text(SVG, encoding="utf-8")
print(f"Wrote {OUT.relative_to(ROOT)} - {len(SVG):,} chars")

