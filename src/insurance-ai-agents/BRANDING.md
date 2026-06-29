# Whitelabel guide — rebranding the Insurance AI demo

This demo is shipped as a **brand-agnostic preset**. The bundled brand is
`Helix Insurance` (a generic placeholder). To present this platform to a
different audience, swap the brand in a few minutes by editing the files
listed below.

---

## 1. Frontend brand — `dashboard/src/brand.ts`

Single source of truth for every brand text and asset reference in the
dashboard:

```ts
export const BRAND: BrandConfig = {
  name: 'Helix Insurance',                  // Full legal/marketing name
  shortName: 'Helix',                       // Compact label
  productName: 'Insurance AI',             // Dashboard header
  productNameAccent: 'Claims Intelligence',// Accent fragment (primary color)
  voiceAssistantName: 'Leo',               // Voice IVR character
  logoUrl: '/brand-logo.png',              // Header / hero / autoplay logo
  logoAlt: 'Helix Insurance',
  tagline: 'Plataforma comercial …',
  caseStudyDescription: 'Procesamiento de partes …',
  partnerBannerName: 'Helix Insurance',
};
```

After editing, run `cd dashboard && npm run build` to validate.

## 2. Frontend logo & favicon — `dashboard/public/`

Replace these two files (keep the file names so no code changes are
needed):

| File | What it is | Recommended size |
|---|---|---|
| `dashboard/public/brand-logo.png` | Horizontal logo shown in header, hero card, autoplay header. | viewBox ~240×64. |
| `dashboard/public/favicon.svg` | Browser tab icon. | 48×48 square or smaller. |

If you only have a raster logo (PNG/JPG), drop it into `public/`, name it
`brand-logo.png`, and update `BRAND.logoUrl` in `brand.ts` to point at it.

## 3. Frontend color palette — `dashboard/tailwind.config.js`

The dashboard uses a semantic `primary` palette plus a `brand` alias for
quick access. Replace these hex values to change the dominant color:

```js
primary: {
  50:  '#EFF6FF',
  100: '#DBEAFE',
  // …
  500: '#2563EB', // Brand main — replace this
  600: '#1D4ED8',
  // …
},
brand: {
  blue:       '#2563EB', // <- alias used in custom CSS
  'blue-700': '#1E40AF',
  // …
},
```

If you also change the *accent* color (used in glow effects, light-slides
and the radar gauge fills), search-and-replace these literals in
`dashboard/src/index.css` (currently `rgba(37, 99, 235, …)`) and
`dashboard/src/components/autoplay/RiskGaugePanel.tsx` (currently
`'#2563EB'`).

## 4. Backend brand — env vars

The Python services interpolate the brand name into the voice agent
prompt and the content-understanding analyzer description at startup.
Set these env vars (typically via `.env` or the Container App
configuration) **before** importing the services:

| Variable | Default | Purpose |
|---|---|---|
| `BRAND_NAME` | `Helix Insurance` | Spoken brand name (voice IVR + analyzer description). |
| `VOICE_ASSISTANT_NAME` | `Leo` | First name of the voice IVR character. |

Source: `agents/shared/brand.py`. The `SYSTEM_PROMPT` (voice agent) and
`PARTE_SINIESTRO_SCHEMA["description"]` (content understanding) both
interpolate these values once, so changes require a **backend restart**.

> ⚠️ **Content Understanding analyzer cache.** The CU analyzer is
> created once and cached by `ensure_analyzer()` (see
> `agents/content_understanding/agent.py`). Changing `BRAND_NAME` does
> not retroactively update an analyzer that already exists in Azure. To
> apply the new brand name in the schema metadata you must either:
> (a) version the analyzer ID, or (b) delete the existing analyzer from
> the Azure AI Services resource before restarting the backend.

## 5. Architecture diagrams — `images/`

The architecture SVGs (`images/architecture.svg`,
`images/architecture-en.svg`) and the README hero banner
(`images/brand-banner.svg`) are generated from Python scripts so they
are easy to rebrand.

Edit the brand tokens at the top of each generator:

* `tools/gen_arch_svg.py` — `BRAND_NAME`, `BRAND_MARK_LETTER`,
  `BRAND_PRIMARY`, `BRAND_PRIMARY_DARK`.
* `tools/gen_brand_banner.py` — `BRAND_NAME`, `BRAND_MARK_LETTER`,
  `BRAND_PRIMARY`, `BRAND_PRIMARY_DARK`, `BRAND_TEXT`.

Then regenerate:

```powershell
python tools\gen_arch_svg.py
python tools\gen_brand_banner.py
```

If you prefer to drop in a full custom logo SVG, edit the
`logoBrand` `<symbol>` block in `tools/gen_arch_svg.py` directly.

## 6. README & docs

Update the top of `README.md` (banner alt text, subtitle, sample brand
references) to match your new brand. The Mermaid sequence diagram's
`themeVariables` block also embeds the brand color — keep it in sync
with the `primary` palette.

---

## Quick rebrand checklist

1. `dashboard/src/brand.ts` ← edit BRAND object
2. `dashboard/public/brand-logo.png` ← drop in new logo
3. `dashboard/public/favicon.svg` ← drop in new favicon
4. `dashboard/tailwind.config.js` ← replace `primary` palette hex
5. `dashboard/src/index.css` ← search-and-replace `rgba(37, 99, 235`
6. `dashboard/src/components/autoplay/RiskGaugePanel.tsx` ← replace `'#2563EB'`
7. `tools/gen_arch_svg.py` + `tools/gen_brand_banner.py` ← update tokens, regenerate
8. `BRAND_NAME` / `VOICE_ASSISTANT_NAME` env vars on the backend
9. (Optional) delete old Content Understanding analyzer to refresh schema metadata
10. `cd dashboard && npm run build` to validate the frontend
11. `python -m py_compile agents/voice/__init__.py agents/content_understanding/agent.py`
    to validate the backend

