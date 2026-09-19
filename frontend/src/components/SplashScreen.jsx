import React, { useEffect, useState } from 'react';
import { Pill, ShieldCheck, ShieldAlert } from 'lucide-react';

/**
 * Animated startup screen, shown once per browser session before the app itself.
 *
 * It is a separate route-less overlay (see App.jsx) so it never mixes with the
 * working UI. Creator attribution and the integrity result are pulled from the
 * backend rather than hardcoded here, so the name shown is the one the backend
 * verifies.
 */
export function SplashScreen({ branding, onFinish }) {
  const [phase, setPhase] = useState(0);
  const [logoOk, setLogoOk] = useState(true);

  // Staged animation: logo -> title -> attribution -> fade out.
  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 150),
      setTimeout(() => setPhase(2), 700),
      setTimeout(() => setPhase(3), 1500),
      setTimeout(() => setPhase(4), 3000),
      setTimeout(() => onFinish(), 3600),
    ];
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

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 transition-opacity duration-600 ${phase >= 4 ? 'opacity-0' : 'opacity-100'
        }`}
    >
      {/* Animated background orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-blue-500/20 blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-40 -right-24 w-[28rem] h-[28rem] rounded-full bg-indigo-500/20 blur-3xl animate-pulse-slower" />
        <div className="absolute top-1/3 left-1/2 w-72 h-72 rounded-full bg-cyan-400/10 blur-3xl animate-drift" />
      </div>

      <div className="relative text-center px-6">
        {/* Logo mark */}
        <div
          className={`mx-auto mb-8 flex h-24 w-24 items-center justify-center rounded-3xl bg-white/10 ring-1 ring-white/20 backdrop-blur transition-all duration-700 ${phase >= 1 ? 'scale-100 opacity-100' : 'scale-50 opacity-0'
            }`}
        >
          {customised && logoOk ? (
            <img
              src="/api/branding/logo"
              alt={appName}
              className="h-20 w-20 object-contain"
              onError={() => setLogoOk(false)}
            />
          ) : (
            <Pill className="h-12 w-12 text-cyan-300 animate-float" />
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

        {/* Integrity badge */}
        <div
          className={`mt-8 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition-all duration-700 ${phase >= 3 ? 'opacity-100' : 'opacity-0'
            } ${tampered
              ? 'bg-red-500/15 text-red-200 ring-1 ring-red-400/40'
              : integrityOk
                ? 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/40'
                : 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/40'
            }`}
        >
          {tampered ? <ShieldAlert className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
          {tampered
            ? 'Creator identity failed verification'
            : integrityOk
              ? 'Creator identity verified'
              : 'Verifying creator identity...'}
        </div>

        {version && (
          <p
            className={`mt-4 text-xs text-slate-400 transition-opacity duration-700 ${phase >= 3 ? 'opacity-100' : 'opacity-0'
              }`}
          >
            Version {version}
          </p>
        )}

        {/* Progress bar */}
        <div className="mx-auto mt-10 h-0.5 w-56 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full bg-gradient-to-r from-cyan-400 to-indigo-400 transition-all duration-[3400ms] ease-out"
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
