import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Beaker,
  CheckCircle2,
  ClipboardList,
  HelpCircle,
  Loader2,
  Pill,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { apiClient } from '../api';

/**
 * Clinical workbench.
 *
 * Puts the whole decision in one place: pick a patient and a condition, and
 * see what can be dispensed safely, what has to be substituted, and what was
 * rejected and why. Built this way because the safety verdict, the
 * availability answer and the dosing plan are one decision at a counter, not
 * three separate screens to visit in sequence.
 *
 * Colour and icon coding is deliberately conservative. Only a SAFE verdict is
 * green; CAUTION and UNKNOWN are amber and must not read as approval.
 */

const VERDICT_STYLES = {
  SAFE: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-500',
    text: 'text-emerald-800',
    icon: ShieldCheck,
    label: 'Safe to recommend',
  },
  CAUTION: {
    bg: 'bg-amber-50',
    border: 'border-amber-500',
    text: 'text-amber-800',
    icon: AlertTriangle,
    label: 'Caution - pharmacist review required',
  },
  UNSAFE: {
    bg: 'bg-red-50',
    border: 'border-red-500',
    text: 'text-red-800',
    icon: ShieldAlert,
    label: 'Not safe for this patient',
  },
  BLOCKED: {
    bg: 'bg-red-50',
    border: 'border-red-600',
    text: 'text-red-900',
    icon: XCircle,
    label: 'Contraindicated - do not dispense',
  },
  UNKNOWN: {
    bg: 'bg-slate-50',
    border: 'border-slate-400',
    text: 'text-slate-800',
    icon: HelpCircle,
    label: 'Cannot verify - treat as unsafe',
  },
  NOT_ASSESSED: {
    bg: 'bg-gray-50',
    border: 'border-gray-300',
    text: 'text-gray-700',
    icon: HelpCircle,
    label: 'Not assessed',
  },
};

function VerdictBadge({ verdict }) {
  const style = VERDICT_STYLES[verdict] || VERDICT_STYLES.NOT_ASSESSED;
  const Icon = style.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.border} ${style.text}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {style.label}
    </span>
  );
}

function SeverityDot({ severity }) {
  const colour = {
    CONTRAINDICATED: 'bg-red-600',
    SERIOUS: 'bg-red-400',
    MODERATE: 'bg-amber-400',
    MINOR: 'bg-slate-300',
    UNKNOWN: 'bg-slate-400',
  }[severity] || 'bg-slate-300';
  return <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${colour}`} />;
}

export function ClinicalWorkbench() {
  const [patients, setPatients] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [patientId, setPatientId] = useState('');
  const [condition, setCondition] = useState('');
  const [selectedMedicine, setSelectedMedicine] = useState('');

  const [resolution, setResolution] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [plan, setPlan] = useState(null);
  const [cycle, setCycle] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [patientRes, medicineRes] = await Promise.all([
        apiClient.getPatients(),
        apiClient.getMedicines(),
      ]);
      setPatients((patientRes && patientRes.data) || []);
      setMedicines((medicineRes && medicineRes.data) || []);
      setError(null);
    } catch (err) {
      setError('Could not load patients and medicines. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const patient = useMemo(
    () => patients.find((p) => String(p.id) === String(patientId)) || null,
    [patients, patientId]
  );

  // --- Actions ------------------------------------------------------------

  const resolveCondition = async () => {
    if (!condition.trim()) {
      setError('Enter a condition or symptom to search for.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await apiClient.resolveCondition(
        condition.trim(),
        patientId ? Number(patientId) : null
      );
      setResolution(res && res.data ? res.data : null);
    } catch (err) {
      setError('Could not resolve that condition.');
    } finally {
      setBusy(false);
    }
  };

  const assessMedicine = async (medicineId) => {
    setSelectedMedicine(String(medicineId));
    setBusy(true);
    setError(null);
    try {
      const tasks = [
        patientId
          ? apiClient.assessSafety(Number(patientId), medicineId)
          : Promise.resolve(null),
        apiClient.getAdministrationPlan(medicineId),
      ];
      // The dispense plan needs a patient to judge safety, but the stock
      // answer is useful on its own, so it is requested either way.
      tasks.push(
        apiClient.getDispensePlan(
          medicineId,
          patientId ? Number(patientId) : null,
          1
        )
      );
      const [safetyRes, planRes, dispenseRes] = await Promise.all(tasks);
      setAssessment(safetyRes && safetyRes.data ? safetyRes.data : null);
      setCycle(planRes && planRes.data ? planRes.data : null);
      setPlan(dispenseRes && dispenseRes.data ? dispenseRes.data : null);
    } catch (err) {
      setError('Could not assess that medicine.');
    } finally {
      setBusy(false);
    }
  };

  // --- Render helpers -----------------------------------------------------

  const renderMedicineRow = (item, keyPrefix, options = {}) => {
    const isSelected = String(selectedMedicine) === String(item.medicine_id);
    const verdict = item.safety_verdict || 'NOT_ASSESSED';
    return (
      <div
        key={`${keyPrefix}-${item.medicine_id}`}
        className={`rounded-lg border p-3 transition ${isSelected ? 'border-blue-500 bg-blue-50/40' : 'border-gray-200 bg-white hover:border-gray-300'
          }`}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-gray-900">{item.name}</p>
            <p className="text-xs text-gray-500">
              {item.generic_name}
              {item.therapeutic_class ? ` - ${item.therapeutic_class}` : ''}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            {options.showVerdict !== false && <VerdictBadge verdict={verdict} />}
            <span className="text-xs text-gray-500">
              {item.total_stock > 0 ? (
                <span className="font-medium text-emerald-700">
                  {item.total_stock} in stock
                </span>
              ) : (
                <span className="font-medium text-red-600">Out of stock</span>
              )}
            </span>
          </div>
        </div>

        {options.substitutionLabel && (
          <p className="mt-2 text-xs text-gray-600">
            <span className="font-medium">{options.substitutionLabel}</span>
            {item.requires_dose_recalculation && (
              <span className="ml-1 text-amber-700">- dose must be recalculated</span>
            )}
          </p>
        )}

        {item.safety_headline && (
          <p className="mt-2 rounded bg-white/70 p-2 text-xs text-gray-700">
            {item.safety_headline}
          </p>
        )}

        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {item.selling_price != null ? `Rs ${item.selling_price}` : ''}
          </span>
          <button
            onClick={() => assessMedicine(item.medicine_id)}
            className="rounded bg-gray-800 px-3 py-1 text-xs font-medium text-white hover:bg-gray-900"
          >
            Assess
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Clinical workbench</h1>
        <p className="mt-1 text-sm text-gray-600">
          Check what is safe, what is available, and what to dispense instead -
          in one place.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* --- Inputs ------------------------------------------------------- */}
      <div className="rounded-lg bg-white p-5 shadow">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Patient
            </label>
            <select
              value={patientId}
              onChange={(e) => {
                setPatientId(e.target.value);
                setAssessment(null);
                setResolution(null);
              }}
              className="w-full rounded-lg border-gray-300 px-3 py-2"
            >
              <option value="">Select a patient</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name} ({p.age} yrs)
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Without a patient, safety cannot be assessed and no option will
              be recommended.
            </p>
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Condition or symptom
            </label>
            <div className="flex gap-2">
              <input
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && resolveCondition()}
                placeholder="e.g. urinary tract infection, asthma, fever"
                className="flex-1 rounded-lg border-gray-300 px-3 py-2"
              />
              <button
                onClick={resolveCondition}
                disabled={busy}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Activity className="h-4 w-4" />
                )}
                Resolve
              </button>
            </div>
          </div>
        </div>

        {/* Patient context - the data the safety engine depends on */}
        {patient && (
          <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm">
            <p className="mb-1 font-medium text-slate-900">
              What the safety checks will use
            </p>
            <div className="grid grid-cols-1 gap-x-6 gap-y-1 text-slate-700 sm:grid-cols-2 lg:grid-cols-3">
              <p>
                <strong>Allergies:</strong>{' '}
                {patient.allergies && patient.allergies.length > 0
                  ? patient.allergies.map((a) => a.allergen).join(', ')
                  : 'none recorded'}
              </p>
              <p>
                <strong>Conditions:</strong>{' '}
                {patient.chronic_diseases || 'none recorded'}
              </p>
              <p>
                <strong>Current medicines:</strong>{' '}
                {patient.current_medications || 'none recorded'}
              </p>
              <p>
                <strong>Weight:</strong>{' '}
                {patient.weight_kg ? `${patient.weight_kg} kg` : 'not recorded'}
              </p>
              <p>
                <strong>eGFR:</strong>{' '}
                {patient.egfr ? `${patient.egfr} mL/min` : 'not calculable'}
                {patient.ckd_stage ? ` (${patient.ckd_stage})` : ''}
              </p>
              <p>
                <strong>Pregnant:</strong>{' '}
                {patient.is_pregnant
                  ? `yes (trimester ${patient.pregnancy_trimester || '?'})`
                  : 'no'}
              </p>
            </div>
            {!patient.weight_kg || !patient.egfr ? (
              <p className="mt-2 text-xs text-amber-700">
                Missing weight or creatinine limits what can be verified - some
                medicines will be returned as &ldquo;cannot verify&rdquo; rather
                than approved.
              </p>
            ) : null}
          </div>
        )}
      </div>

      {/* --- Condition resolution --------------------------------------- */}
      {resolution && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-xl font-bold text-gray-800">
              Results for &ldquo;{resolution.condition}&rdquo;
            </h2>
            <div className="flex gap-3 text-xs text-gray-600">
              <span>{resolution.counts.matched} matched</span>
              <span className="text-emerald-700">
                {resolution.counts.in_stock} in stock
              </span>
              <span className="text-red-600">
                {resolution.counts.out_of_stock} out of stock
              </span>
              <span className="text-slate-600">
                {resolution.counts.set_aside_on_safety} set aside
              </span>
            </div>
          </div>

          {resolution.in_stock.length > 0 && (
            <div className="rounded-lg bg-white p-5 shadow">
              <h3 className="mb-3 flex items-center gap-2 font-semibold text-gray-800">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                Available and safe to dispense now
              </h3>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {resolution.in_stock.map((item) =>
                  renderMedicineRow(item, 'stock')
                )}
              </div>
            </div>
          )}

          {resolution.out_of_stock_with_substitutes.length > 0 && (
            <div className="rounded-lg bg-white p-5 shadow">
              <h3 className="mb-1 flex items-center gap-2 font-semibold text-gray-800">
                <Pill className="h-5 w-5 text-amber-600" />
                Out of stock - closest safe alternatives
              </h3>
              <p className="mb-3 text-xs text-gray-500">
                Options are ranked by how little clinical substitution is
                needed. Anything unsafe for this patient has already been
                removed.
              </p>
              <div className="space-y-4">
                {resolution.out_of_stock_with_substitutes.map((item) => (
                  <div key={`oos-${item.medicine_id}`}>
                    <p className="mb-2 text-sm font-medium text-gray-700">
                      Instead of <strong>{item.name}</strong>:
                    </p>
                    {item.closest_substitutes && item.closest_substitutes.length > 0 ? (
                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                        {item.closest_substitutes.map((sub) =>
                          renderMedicineRow(sub, `sub-${item.medicine_id}`, {
                            substitutionLabel: sub.substitution_label,
                          })
                        )}
                      </div>
                    ) : (
                      <p className="rounded border-dashed border-gray-300 p-3 text-sm text-gray-500">
                        No safe substitute is in stock for this medicine.
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {resolution.reviewed_and_set_aside.length > 0 && (
            <details className="rounded-lg bg-white p-5 shadow">
              <summary className="cursor-pointer font-semibold text-gray-800">
                Reviewed and set aside ({resolution.reviewed_and_set_aside.length})
                <span className="ml-2 text-xs font-normal text-gray-500">
                  not offered as options
                </span>
              </summary>
              <div className="mt-3 space-y-2">
                {resolution.reviewed_and_set_aside.map((item) => (
                  <div
                    key={`aside-${item.medicine_id}`}
                    className="flex items-start gap-3 rounded border-gray-200 p-3"
                  >
                    <SeverityDot severity="UNKNOWN" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-800">
                        {item.name}
                      </p>
                      <p className="text-xs text-gray-600">{item.reason}</p>
                      {item.safety_headline && (
                        <p className="mt-1 text-xs text-gray-500">
                          {item.safety_headline}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}

          {resolution.counts.matched === 0 && (
            <div className="rounded-lg bg-white p-8 text-center shadow">
              <HelpCircle className="mx-auto mb-2 h-10 w-10 text-gray-300" />
              <p className="text-gray-600">
                Nothing in the database treats &ldquo;{resolution.condition}
                &rdquo;.
              </p>
              <p className="mt-1 text-sm text-gray-500">
                Try a broader term such as &ldquo;infection&rdquo; or
                &ldquo;pain&rdquo;, or look the drug up in the reference
                browser.
              </p>
            </div>
          )}

          {/* The important case: medicines exist but none could be offered.
              Saying so plainly, and telling the user what to do about it,
              matters more than the empty list - an unexplained blank screen
              looks like the search failed when it actually worked and
              deliberately withheld everything on safety grounds. */}
          {resolution.counts.matched > 0 &&
            resolution.in_stock.length === 0 &&
            resolution.counts.set_aside_on_safety > 0 && (
              <div className="rounded-lg border-l-4 border-amber-500 bg-amber-50 p-5">
                <h3 className="flex items-center gap-2 font-semibold text-amber-900">
                  <ShieldAlert className="h-5 w-5" />
                  No medicine could be cleared for this patient
                </h3>
                <p className="mt-2 text-sm text-amber-900">
                  {resolution.counts.matched} medicine(s) treat
                  &ldquo;{resolution.condition}&rdquo;, but none passed every
                  safety check. They are listed below with the reason, and the
                  system has deliberately not offered any of them as a
                  recommendation.
                </p>
                {!patientId && (
                  <p className="mt-2 text-sm font-medium text-amber-900">
                    Select a patient first - without one, no safety check can
                    run and nothing can be verified as safe.
                  </p>
                )}
                {(patient && (!patient.weight_kg || !patient.egfr)) && (
                  <p className="mt-2 text-sm text-amber-900">
                    This patient is missing {!patient.weight_kg ? 'a recorded weight' : ''}
                    {!patient.weight_kg && !patient.egfr ? ' and ' : ''}
                    {!patient.egfr ? 'a serum creatinine' : ''}.
                    Some medicines cannot be verified for renal dosing or
                    weight-based dosing until those are recorded.
                  </p>
                )}
                <p className="mt-2 text-sm text-amber-900">
                  A prescriber should decide, or the missing patient data should
                  be recorded so the checks can complete.
                </p>
              </div>
            )}
        </div>
      )}

      {/* --- Assessment of a selected medicine --------------------------- */}
      {assessment && (
        <div className="rounded-lg bg-white p-5 shadow">
          <h2 className="mb-3 flex-wrap items-center gap-3 text-xl font-bold text-gray-800">
            Assessment
            <VerdictBadge verdict={assessment.verdict} />
          </h2>

          {assessment.recommendable === false && assessment.verdict !== 'SAFE' && (
            <div className="mb-4 rounded-lg border-l-4 border-amber-500 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-medium">
                This medicine is not cleared for automatic recommendation.
              </p>
              {assessment.unknown_reason && (
                <p className="mt-1">{assessment.unknown_reason}</p>
              )}
              {assessment.missing_data && assessment.missing_data.length > 0 && (
                <ul className="mt-2 list-inside list-disc">
                  {assessment.missing_data.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {assessment.findings.length > 0 ? (
            <ul className="space-y-2">
              {assessment.findings.map((finding, index) => (
                <li
                  key={`finding-${index}`}
                  className="flex items-start gap-3 rounded border-gray-200 p-3"
                >
                  <SeverityDot severity={finding.severity} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-800">
                      <span className="mr-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs uppercase tracking-wide text-gray-600">
                        {finding.kind}
                      </span>
                      {finding.message}
                    </p>
                    {finding.detail && (
                      <p className="mt-1 text-xs text-gray-500">
                        {finding.detail}
                      </p>
                    )}
                    {finding.source && (
                      <p className="mt-1 text-xs italic text-gray-400">
                        Source: {finding.source}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="flex items-center gap-2 text-sm text-emerald-700">
              <ShieldCheck className="h-4 w-4" />
              No safety findings across {assessment.checks_run.length} checks.
            </p>
          )}

          <details className="mt-3 text-xs text-gray-500">
            <summary className="cursor-pointer">
              Checks performed ({assessment.checks_run.length})
            </summary>
            <p className="mt-1">{assessment.checks_run.join(', ')}</p>
            {assessment.checks_failed.length > 0 && (
              <p className="mt-1 text-red-600">
                Could not run: {assessment.checks_failed.join(', ')}
              </p>
            )}
          </details>
        </div>
      )}

      {/* --- Dispense plan ---------------------------------------------- */}
      {plan && (
        <div className="rounded-lg bg-white p-5 shadow">
          <h2 className="mb-3 flex items-center gap-2 text-xl font-bold text-gray-800">
            <ClipboardList className="h-5 w-5" />
            Dispense plan
          </h2>
          <div
            className={`rounded-lg border-l-4 p-3 text-sm ${plan.can_dispense_now
                ? 'border-emerald-500 bg-emerald-50 text-emerald-900'
                : 'border-red-500 bg-red-50 text-red-900'
              }`}
          >
            <p className="font-medium">
              {plan.can_dispense_now ? 'Can be dispensed' : 'Cannot be dispensed'}
            </p>
            <p className="mt-1">{plan.action}</p>
            {plan.blocked_reason && (
              <p className="mt-1 font-medium">{plan.blocked_reason}</p>
            )}
          </div>

          {plan.substitutes && plan.substitutes.length > 0 && (
            <div className="mt-4">
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-700">
                <RefreshCw className="h-4 w-4" />
                Closest available alternatives
              </h3>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {plan.substitutes.map((sub) =>
                  renderMedicineRow(sub, 'plan', {
                    substitutionLabel: sub.substitution_label,
                  })
                )}
              </div>
            </div>
          )}

          {plan.excluded_on_safety && plan.excluded_on_safety.length > 0 && (
            <p className="mt-3 text-xs text-gray-500">
              {plan.excluded_on_safety.length} candidate(s) were excluded on
              safety grounds and are not listed as options.
            </p>
          )}
        </div>
      )}

      {/* --- Administration plan ---------------------------------------- */}
      {cycle && (
        <div className="rounded-lg bg-white p-5 shadow">
          <h2 className="mb-3 flex items-center gap-2 text-xl font-bold text-gray-800">
            <Beaker className="h-5 w-5" />
            Administration plan
          </h2>
          <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded border-gray-200 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Course
              </p>
              <p className="mt-1 font-semibold text-gray-900">
                {cycle.course_type}
              </p>
              <p className="text-xs text-gray-500">
                {cycle.duration_days} day(s) - from {cycle.duration_source}
              </p>
            </div>
            <div className="rounded border-gray-200 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Frequency
              </p>
              <p className="mt-1 font-semibold text-gray-900">
                {cycle.frequency}
              </p>
              {cycle.interval_hours && (
                <p className="text-xs text-gray-500">
                  every {cycle.interval_hours}h
                  {cycle.doses_per_day ? ` - ${cycle.doses_per_day}/day` : ''}
                </p>
              )}
            </div>
            <div className="rounded border-gray-200 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Quantity
              </p>
              <p className="mt-1 font-semibold text-gray-900">
                {cycle.total_units || '-'}
                {cycle.quantity_is_approximate ? ' (approx.)' : ''}
              </p>
              <p className="text-xs text-gray-500">ends {cycle.end_date}</p>
            </div>
            <div className="rounded border-gray-200 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Finish the course
              </p>
              <p className="mt-1 font-semibold text-gray-900">
                {cycle.complete_full_course ? 'Yes - complete it' : 'As directed'}
              </p>
              {cycle.taper_required && (
                <p className="text-xs text-amber-700">Taper required</p>
              )}
            </div>
          </div>

          {cycle.timing && (
            <p className="mt-3 text-sm text-gray-700">
              <strong>When to take it:</strong> {cycle.timing}
            </p>
          )}
          {cycle.taper_note && (
            <p className="mt-2 rounded border-l-4 border-amber-500 bg-amber-50 p-2 text-sm text-amber-900">
              <strong>Tapering:</strong> {cycle.taper_note}
            </p>
          )}
          {cycle.missed_dose && (
            <p className="mt-2 text-sm text-gray-600">
              <strong>Missed dose:</strong> {cycle.missed_dose}
            </p>
          )}
          {cycle.patient_note && (
            <p className="mt-2 text-sm text-gray-600">
              <strong>Note:</strong> {cycle.patient_note}
            </p>
          )}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-10 text-gray-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading...
        </div>
      )}

      {/* Medicine picker when nothing is selected yet */}
      {!loading && !resolution && !assessment && medicines.length > 0 && (
        <div className="rounded-lg bg-white p-5 shadow">
          <h2 className="mb-3 font-semibold text-gray-800">
            Or assess a specific medicine
          </h2>
          <select
            value={selectedMedicine}
            onChange={(e) => e.target.value && assessMedicine(Number(e.target.value))}
            className="w-full rounded-lg border-gray-300 px-3 py-2 md:w-1/2"
          >
            <option value="">Select a medicine</option>
            {medicines.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} - {m.strength} ({m.form})
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
