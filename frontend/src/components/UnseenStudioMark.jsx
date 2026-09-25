import React from 'react';

/**
 * The Unseen Studio mark: a monogram "US" drawn as vector paths.
 *
 * It is an inline SVG rather than an image file for three reasons that matter
 * to this project: it scales to any size without a raster artefact, it needs no
 * network request (the app is offline by design), and it can be animated by
 * CSS - the stroke draws itself on the splash screen - which a bitmap cannot.
 *
 * The two letters interlock: the S passes through the U rather than sitting
 * beside it, so the mark reads as one monogram rather than two letters. The
 * bowl of the S is on the same optical centre as the U's arc.
 */
export function UnseenStudioMark({ className = '', animated = false, title = 'Unseen Studio' }) {
  return (
    <svg
      viewBox="0 0 120 120"
      role="img"
      aria-label={title}
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title}</title>
      <defs>
        <linearGradient id="us-mark-gradient" x1="0" y1="0" x2="120" y2="120">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="45%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
        <linearGradient id="us-mark-fill" x1="0" y1="0" x2="120" y2="120">
          <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#a78bfa" stopOpacity="0.22" />
        </linearGradient>
      </defs>

      {/* Soft plate behind the monogram so it holds against a dark splash. */}
      <path
        d="M24 6h72a18 18 0 0 1 18 18v72a18 18 0 0 1-18 18H24A18 18 0 0 1 6 96V24A18 18 0 0 1 24 6Z"
        fill="url(#us-mark-fill)"
        stroke="url(#us-mark-gradient)"
        strokeWidth="2"
        strokeOpacity="0.55"
      />

      {/* --- U ------------------------------------------------------------- */}
      {/* THE LAYOUT RULE THAT MAKES THIS LEGIBLE.

          The box is 120 wide and the two letters must sit inside it without
          touching. Earlier versions failed for a reason worth recording: the U
          occupied x 32-72 and the S x 63-93, so they overlapped by nine units
          and the U's right stem ran straight through the S's bowls. At stroke
          width 9 that reads as one undifferentiated glyph, not as "US".

          So the design is arithmetic rather than freehand. Each letter is 40
          units wide, the gap between them is 8, and the pair is centred:
              40 + 8 + 40 = 88,  (120 - 88) / 2 = 16
          => U spans x 16-56, S spans x 64-104.
          Stroke width 7 leaves clear white space inside and between both
          letters, so they stay distinct even at 24 px in the navigation bar.

          The U bottoms at y=76 and the S spans y=36-78, so the two are also
          aligned on the same optical baseline rather than one floating above
          the other, which is what made the first attempt look unbalanced. */}
      <path
        d="M20 38v30a18 18 0 0 0 36 0V38"
        stroke="url(#us-mark-gradient)"
        strokeWidth="7"
        strokeLinecap="square"
        className={animated ? 'us-draw us-draw-u' : undefined}
      />

      {/* --- S ------------------------------------------------------------- */}
      {/* A single-path S in the right half (x 64-104), same optical baseline
          as the U. The two bowls are asymmetric as a real S is - the upper one
          slightly smaller - which is what stops it reading as a figure 8. */}
      <path
        d="M100 47c0-6-7-10-14-10s-14 3.5-14 9.5c0 6 5 8.5 14 10.5s14 4.5 14 11c0 7-7 11.5-14.5 11.5S70 75.5 69 69"
        stroke="url(#us-mark-gradient)"
        strokeWidth="7"
        strokeLinecap="round"
        className={animated ? 'us-draw us-draw-s' : undefined}
      />
    </svg>
  );
}

/**
 * The studio wordmark, for the splash and the site footer.
 * The letters are spaced widely, which is what makes a two-word studio name
 * read as a brand rather than as a line of text.
 */
export function UnseenStudioWordmark({ className = '' }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <UnseenStudioMark className="h-6 w-6" />
      <span className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-300">
        Unseen Studio
      </span>
    </div>
  );
}

export default UnseenStudioMark;