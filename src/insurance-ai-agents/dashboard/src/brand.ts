// =============================================================================
// Brand configuration — single source of truth for whitelabel demo.
// =============================================================================
// To rebrand the demo for a different company, edit the values in BRAND below
// and replace:
//   - /public/brand-logo.svg   (header / hero / autoplay logo)
//   - /public/favicon.svg      (browser tab icon)
//
// Color palette is configured in `tailwind.config.js` (the `primary` and
// `brand` palettes). The Python voice agent reads its brand from the
// BRAND_NAME / VOICE_ASSISTANT_NAME env vars (see `agents/shared/brand.py`)
// — keep both sides in sync.
// =============================================================================

export interface BrandConfig {
  /** Full legal/marketing name displayed in hero, footers, voice greetings. */
  name: string;
  /** Compact name for headers, small badges. */
  shortName: string;
  /** Product title in the dashboard header. */
  productName: string;
  /** Accent fragment of the product title (rendered in primary color). */
  productNameAccent: string;
  /** Display name of the voice IVR assistant character. */
  voiceAssistantName: string;
  /** Path to the brand logo SVG inside `public/`. */
  logoUrl: string;
  /** Alt text for the logo image (accessibility). */
  logoAlt: string;
  /** Short marketing tagline shown on the hero section. */
  tagline: string;
  /** Long-form case-study description shown under the hero title. */
  caseStudyDescription: string;
  /** Label used for the "powered by partner" badge in the hero use-case grid. */
  partnerBannerName: string;
  /**
   * Primary brand color as a hex string, for raw SVG/canvas fills that cannot
   * use Tailwind classes. Keep in sync with the `primary-600` value in
   * `tailwind.config.js`.
   */
  primaryHex: string;
  /**
   * Whether the logo image already includes the brand name as a wordmark.
   * When false, the UI renders BRAND.name as a text wordmark next to the logo.
   */
  logoHasWordmark: boolean;
}

export const BRAND: BrandConfig = {
  name: 'Helix Insurance',
  shortName: 'Helix',
  productName: 'Insurance AI',
  productNameAccent: 'Claims Intelligence',
  voiceAssistantName: 'Leo',
  logoUrl: '/brand-logo.png',
  logoAlt: 'Helix Insurance',
  tagline: 'Plataforma comercial para tramitación inteligente de siniestros',
  caseStudyDescription:
    'Procesamiento de partes de seguro automatizado con IA gobernada. Resolución de siniestros auditable, trazable y en segundos.',
  partnerBannerName: 'Helix Insurance',
  primaryHex: '#2563EB',
  logoHasWordmark: false,
};
