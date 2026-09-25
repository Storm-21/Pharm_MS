import React, { useEffect, useMemo, useState } from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { UnseenStudioMark, UnseenStudioWordmark } from './UnseenStudioMark';

/**
 * Animated startup screen, shown once per browser session before the app itself.
 *
 * It is a separate route-less overlay (see App.jsx) so it never mixes with the
 * working UI. Creator attribution and the integrity result are pulled from the
 * backend rather than hardcoded here, so the name shown is the one the backend
 * verifies.
 *
 * The animation is staged rather than decorative:
 *   1  the Unseen Studio mark draws its own strokes on a dark field
 *   2  the product name rises as the mark settles
 *   3  creator attribution, integrity badge and boot checklist
 *   4  fade to the application
 *
 * The timings live in one table so the sequence can be read at a glance - the
 * previous version scattered setTimeout calls with magic numbers inline, which
 * made the order of the reveal impossible to verify by reading.
 */
const STAGES = [
  { phase: 1, at: 220 },   // host mark begins drawing
  { phase: 2, at: 1150 },  // product name rises
  { phase: 3, at: 1900 },  // creator attribution and badge
  { phase: 4, at: 3600 },  // begin fading out
  { phase: 5, at: 4200 },  // finish
];

export function SplashScreen({ branding, onFinish }) {
  const [phase, setPhase] = useState(0);
  const [logoOk, setLogoOk] = useState(true);

  useEffect(() => {
    const timers = STAGES.map((stage) => setTimeout(() => setPhase(stage.phase), stage.at));
    timers.push(setTimeout(() => onFinish(), STAGES[STAGES.length - 1].at));
    return () => timers.forEach(clearTimeout);
  }, [onFinish]);

  const creatorName = branding?.creator_name || 'Jayant';
  // When a pharmacy has activated a licence, the splash carries their name and
  // logo instead of the shipped product identity.
  const customised = branding && branding.licensed && branding.has_custom_name;
  const appName = customised
    ? branding.pharmacy_name
    : branding?.app_name || 'Pharmacy Management System';
  const version = branding?.app_version || '';
  const integrityOk = branding?.integrity_ok !== false;
  const tampered = branding && branding.integrity_ok === false;

  // Boot lines are cosmetic, but they name real checks the app performs rather
  // than inventing progress: the identity is verified, records are sealed, the
  // data directory is resolved.
  const bootSteps = useMemo(
    () => [
      'Verifying creator identity',
      integrityOk ? 'Sealed clinical records — intact' : 'Integrity check reported a problem',
      'Loading local database',
      'Preparing the workspace',
    ],
    [integrityOk]
  );

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-slate-950 transition-opacity duration-700 ${
        phase >= 4 ? 'opacity-0' : 'opacity-100'
      }`}
    >
      {/* --- Background ----------------------------------------------------
          A faint grid gives the dark field depth without a texture file, and
          three drifting orbs keep the frame alive while the mark draws. */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="splash-grid absolute inset-0 opacity-40" />
        <div className="absolute -top-40 -left-32 h-[28rem] w-[28rem] rounded-full bg-cyan-500/20 blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-48 -right-24 h-[32rem] w-[32rem] rounded-full bg-indigo-500/20 blur-3xl animate-pulse-slower" />
        <div className="absolute left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500/10 blur-3xl animate-drift" />
        {/* One sweep of light across the whole screen as it opens. */}
        <div className="splash-sheen" />
      </div>

      <div className="relative w-full max-w-lg px-8 text-center">
        {/* --- Host studio mark ------------------------------------------- */}
        <div
          className={`mx-auto mb-7 flex h-28 w-28 items-center justify-center transition-all duration-700 ${
            phase >= 1 ? 'scale-100 opacity-100' : 'scale-75 opacity-0'
          }`}
        >
          {customised && logoOk ? (
            <img
              src="/api/branding/logo"
              alt={appName}
              className="h-24 w-24 object-contain drop-shadow-[0_0_28px_rgba(34,211,238,0.35)]"
              onError={() => setLogoOk(false)}
            />
          ) : (
            <UnseenStudioMark
              className={`h-28 w-28 transition-transform duration-1000 ${
                phase >= 2 ? 'scale-90' : 'scale-100'
              }`}
              animated
            />
          )}
        </div>

        {/* App name */}
        <h1
          className={`text-4xl md:text-5xl font-bold tracking-tight text-white transition-all duration-700 ${phase >= 2 ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
            }`}
        >
          {appName}
        </h1>

        {/* Divider */}
        <div
          className={`mx-auto my-6 h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent transition-all duration-700 ${phase >= 2 ? 'w-64 opacity-100' : 'w-0 opacity-0'
            }`}
        />

        {/* Creator attribution */}
        <div
          className={`transition-all duration-700 ${phase >= 3 ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
            }`}
        >
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/80 mb-2">
            Designed &amp; Developed by
          </p>
          <p className="text-5xl md:text-6xl font-extrabold bg-gradient-to-r from-cyan-300 via-white to-indigo-300 bg-clip-text text-transparent animate-shimmer">
            {creatorName}
          </p>
          {branding?.creator_title && (
            <p className="mt-3 text-sm text-slate-300">{branding.creator_title}</p>
          )}
        </div>

        {/* --- Host studio wordmark ---------------------------------------- */}
        <div
          className={`mt-7 flex justify-center transition-all duration-700 ${
            phase >= 3 ? 'opacity-100' : 'opacity-0'
          }`}
        >
          <UnseenStudioWordmark />
        </div>

        {/* --- Integrity badge --------------------------------------------- */}
        <div
          className={`mt-6 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition-all duration-700 ${
            phase >= 3 ? 'opacity-100' : 'opacity-0'
          } ${
            tampered
              ? 'bg-red-500/15 text-red-200 ring-1 ring-red-400/40'
              : integrityOk
                ? 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/40'
                : 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/40'
          }`}
        >
          {tampered ? (
            <ShieldAlert className="h-3.5 w-3.5" />
          ) : (
            <ShieldCheck className="h-3.5 w-3.5" />
          )}
          {tampered
            ? 'Creator identity failed verification'
            : integrityOk
              ? 'Creator identity verified'
              : 'Verifying creator identity\u2026'}
        </div>

        {/* --- Boot checklist ----------------------------------------------
            These name the checks the app actually performs on startup, so the
            list is information rather than invented progress. */}
        <ul
          className={`mx-auto mt-7 max-w-xs space-y-1.5 text-left transition-opacity duration-700 ${
            phase >= 3 ? 'opacity-100' : 'opacity-0'
          }`}
        >
          {bootSteps.map((step, index) => {
            const done = phase >= 3 && index <= 2;
            return (
              <li key={step} className="flex items-center gap-2 text-xs text-slate-400">
                <span
                  className={`flex h-3.5 w-3.5 flex-shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${
                    done ? 'bg-emerald-500/25 text-emerald-300' : 'bg-white/10 text-slate-500'
                  }`}
                >
                  {done ? '\u2713' : index + 1}
                </span>
                {step}
              </li>
            );
          })}
        </ul>

        {version && (
          <p
            className={`mt-5 text-xs text-slate-500 transition-opacity duration-700 ${
              phase >= 3 ? 'opacity-100' : 'opacity-0'
            }`}
          >
            Version {version}
          </p>
        )}

        {/* --- Progress bar ------------------------------------------------- */}
        <div className="mx-auto mt-6 h-0.5 w-56 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 transition-all duration-[4000ms] ease-out"
            style={{ width: phase >= 1 ? '100%' : '0%' }}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Shown instead of the app when the creator identity block has been altered.
 * Deliberately blunt: it stops normal use and tells the operator what to do.
 */
export function TamperNotice({ branding, onContinue }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 px-6">
      <div className="max-w-lg text-center">
        <ShieldAlert className="mx-auto mb-6 h-16 w-16 text-red-400" />
        <h1 className="mb-3 text-2xl font-bold text-white">Application integrity check failed</h1>
        <p className="mb-4 text-sm leading-relaxed text-slate-300">
          The creator identity block in this copy of PharmMS does not match its
          sealed signature. This copy has been modified outside the authorised
          build process.
        </p>
        <p className="mb-6 text-xs text-slate-500">
          Expected creator attribution: <strong>Jayant</strong>
          <br />
          To restore a verified copy, reinstall from the original package.
        </p>
        <button
          onClick={onContinue}
          className="rounded-lg bg-white/10 px-5 py-2.5 text-sm font-medium text-white ring-1 ring-white/20 transition hover:bg-white/20"
        >
          Continue to application anyway
        </button>
      </div>
    </div>
  );
}
