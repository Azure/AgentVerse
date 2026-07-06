# Whitelabel guide (optional)

> Delete this file if your demo isn't a reskinnable/whitelabel preset. If it is, ship a
> brand-agnostic default and let presenters swap the brand in minutes.

Keep **one source of truth** per surface so a rebrand is a handful of edits:

## 1. Frontend brand — a single config module

Put every brand string and asset reference in one file (e.g. `frontend/src/brand.ts` or a
`brand.json` for vanilla JS):

```ts
export const BRAND = {
  name: '{{Brand Name}}',
  shortName: '{{Brand}}',
  productName: '{{Product}}',
  logoUrl: '/brand-logo.png',
  tagline: '{{Tagline}}',
};
```

## 2. Logo & favicon

Replace the files in `frontend/public/` but **keep the file names** so no code changes:

| File | What it is |
|---|---|
| `brand-logo.png` | Header / hero logo |
| `favicon.svg` | Browser tab icon |

## 3. Color palette

Keep the dominant color in one place (Tailwind `primary` scale, or a CSS variable). Document
which hex to replace.

## 4. Backend brand — env vars

If prompts embed the brand name, read it from an env var at startup rather than hardcoding
it, and document the variable in `.env.example`.

> Tip: a second brand can live on a separate git branch — same app, branding only.
