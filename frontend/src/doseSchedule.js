/**
 * The dosing-pattern notation, mirrored from the backend's
 * app/models/prescription.py so the writer screen can validate and describe
 * the pattern LIVE rather than waiting for the server to refuse a malformed
 * one on submit.
 *
 * The two implementations must stay in step: if you change one, change both.
 * (A shared module is not possible because the backend is Python and this is
 * the frontend bundle - the duplication is deliberate and documented.)
 */

const SLOTS = ['Morning', 'Midday', 'Night'];

const WORDS = {
  '1/2': 'half', '0.5': 'half', '½': 'half',
  '1/4': 'quarter', '0.25': 'quarter', '¼': 'quarter',
  '3/4': 'three quarters', '0.75': 'three quarters', '¾': 'three quarters',
  '1 1/2': 'one and a half', '1.5': 'one and a half',
  '2': 'two', '3': 'three', '4': 'four',
  '1': 'one',
};

/** Three hyphen-separated slot values, each a number or simple fraction. */
export function doseScheduleValid(value) {
  if (!value) return false;
  const parts = String(value).trim().split('-');
  if (parts.length !== 3) return false;
  return parts.every(
    (p) => p === '' || /^\d+(\.\d+)?$|^\d+\/\d+$/.test(p.trim()),
  );
}

/** '1-1/2-0' -> 'Morning: one, Midday: one and a half'. Null when malformed. */
export function describeDosePattern(value) {
  if (!doseScheduleValid(value)) return null;
  const parts = String(value).trim().split('-').map((p) => p.trim());
  const taken = [];
  SLOTS.forEach((slot, i) => {
    const amount = parts[i];
    if (amount === '' || amount === '0' || amount === '0.0') return;
    taken.push(`${slot}: ${WORDS[amount] || amount}`);
  });
  return taken.length ? taken.join(', ') : null;
}
