import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '../api';
import {
  Brain,
  AlertCircle,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Loader2,
  Info,
  Scale,
  Ruler,
  Layers,
  Check,
  Slash,
} from 'lucide-react';

/**
 * The formulas the prescriber may choose between.
 *
 * ``key`` matches the backend's formula key exactly, so selecting one here is
 * the same instruction as passing ``method`` to /weight-dose. ``short`` is the
 * one-line reason shown on the card, because "Clark's rule" alone tells a user
 * nothing about whether it applies to their patient.
 */
const FORMULA_OPTIONS = [
  {
    key: 'mg/kg',
    label: 'mg/kg',
    title: 'Weight-based (mg/kg)',
    short: 'The published paediatric method — dose per kilogram of body weight.',
  },
  {
    key: 'bsa',
    label: 'BSA',
    title: 'Body surface area (Mosteller)',
    short: 'Doses per square metre, from height and weight.',
  },
  {
    key: 'clark',
    label: "Clark's rule",
    title: "Clark's rule",
    short: 'The adult dose scaled by body weight (lb ÷ 150).',
  },
  {
    key: 'young',
    label: "Young's rule",
    title: "Young's rule",
    short: 'Adult dose scaled by age alone — ignores weight entirely.',
  },
];

/**
 * Dosage calculator.
 *
 * Fixes carried over from the previous version:
 *   - patient and medicine are chosen from the real records, not typed as raw IDs
 *   - interactions are screened against the patient's own current medications
 *     (the old call passed an empty string, so it always reported "none")
 *   - contraindications are fetched with the arguments in the correct order
 *   - the safety verdict comes from one /safety-screen call, so allergy,
 *     contraindication and interaction results cannot disagree with each other
 */
export function DosageCalculator() {
  const [patients, setPatients] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [medicineId, setMedicineId] = useState('');
  const [condition, setCondition] = useState('');
  const [dosage, setDosage] = useState(null);
  const [totalDosage, setTotalDosage] = useState(null);
  const [drugCycle, setDrugCycle] = useState(null);
  const [safety, setSafety] = useState(null);
  const [weightDose, setWeightDose] = useState(null);
  const [dosesPerDay, setDosesPerDay] = useState('3');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Which formula the prescriber chose. 'auto' is the evidence-ranked default;
  // 'all' asks for every formula at once with the agreement between them.
  const [methodChoice, setMethodChoice] = useState('auto');
  const [formulaData, setFormulaData] = useState(null);
  const [combining, setCombining] = useState(false);

  const selectedPatient = patients.find((p) => String(p.id) === String(patientId)) || null;

  // Fetch the whole formula set whenever the patient, medicine or dose count
  // changes, so each option can be shown enabled or disabled-with-a-reason
  // before the user commits to it. Selecting a formula is then instant: the
  // numbers are already on screen.
  const loadFormulas = useCallback(async () => {
    if (!patientId || !medicineId) {
      setFormulaData(null);
      return;
    }
    setCombining(true);
    try {
      const res = await apiClient.getDoseFormulas(
        Number(patientId),
        Number(medicineId),
        { dosesPerDay: Number(dosesPerDay) || undefined, combine: true }
      );
      setFormulaData(res && res.success ? res.data : null);
    } catch (err) {
      setFormulaData(null);
    } finally {
      setCombining(false);
    }
  }, [patientId, medicineId, dosesPerDay]);

  useEffect(() => {
    loadFormulas();
  }, [loadFormulas]);

  const formulas = useMemo(
    () => (formulaData && formulaData.formulas) || [],
    [formulaData]
  );
  const selectedFormula = useMemo(
    () =>
      formulas.find((f) => f.key === methodChoice) ||
      formulas.find((f) => f.usable) ||
      null,
    [formulas, methodChoice]
  );

  // Only offer a method the backend reported as applicable; the rest are shown
  // disabled with the reason, never silently dropped.
  const usableCount = formulas.filter((f) => f.usable).length;

  useEffect(() => {
    Promise.all([apiClient.getPatients(), apiClient.getMedicines()])
      .then(([patientRes, medicineRes]) => {
        setPatients((patientRes && patientRes.data) || []);
        setMedicines((medicineRes && medicineRes.data) || []);
      })
      .catch(() => setError('Could not load patients and medicines.'));
  }, []);

  const handleCalculate = async () => {
    if (!patientId || !medicineId) {
      setError('Select both a patient and a medicine.');
      return;
    }
    setLoading(true);
    setError(null);
    setDosage(null);
    setTotalDosage(null);
    setDrugCycle(null);
    setSafety(null);
    setWeightDose(null);
    const pid = Number(patientId);
    const mid = Number(medicineId);

    try {
      const dosageResult = await apiClient.calculateDosage(pid, mid, condition);
      // A rejected calculation is reported, not swallowed. The API client
      // throws on a non-2xx response, so this only runs on a genuine success.
      if (!dosageResult || !dosageResult.success) {
        setError((dosageResult && dosageResult.error) || 'Could not calculate a dosage.');
      } else {
        setDosage(dosageResult.data);

        const [totalResult, cycleResult, safetyResult, weightResult] = await Promise.all([
          apiClient.calculateTotalDosage(
            dosageResult.data.dosage_amount,
            dosageResult.data.frequency,
            dosageResult.data.duration_days
          ),
          apiClient.getDrugCycle(mid),
          apiClient.safetyScreen(pid, mid),
          // The full weight-based working, shown separately so the arithmetic
          // is visible even when the stored guide supplied the dose. The
          // prescriber's chosen formula is passed through, so the manual and
          // the automatic paths cannot disagree.
          apiClient
            .calculateWeightDose(pid, mid, {
              dosesPerDay: Number(dosesPerDay) || undefined,
              method: methodChoice === 'auto' ? undefined : methodChoice,
            })
            .catch(() => null),
        ]);

        if (totalResult && totalResult.success) setTotalDosage(totalResult.data);
        if (cycleResult && cycleResult.success) setDrugCycle(cycleResult.data);
        if (safetyResult && safetyResult.success) setSafety(safetyResult.data);
        if (weightResult && weightResult.success) setWeightDose(weightResult.data);
      }
    } catch (err) {
      setError(err.message || 'Could not calculate a dosage. Check the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Dosage Calculator</h1>

      {/* Input Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Calculate Dosage</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Patient *</label>
            <select
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a patient</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name} ({p.age} yrs
                  {p.weight_kg ? `, ${p.weight_kg} kg` : ', no weight'})
                </option>
              ))}
            </select>
            {/* The weight and BSA drive the whole calculation, so they are
                shown here rather than hidden inside the patient record. */}
            {selectedPatient && (
              <p className="mt-1 text-xs text-gray-500">
                {selectedPatient.weight_kg
                  ? `Weight ${selectedPatient.weight_kg} kg`
                  : 'No weight recorded - doses fall back to an age formula'}
                {selectedPatient.bsa_m2 ? ` \u00b7 BSA ${selectedPatient.bsa_m2} m\u00b2` : ''}
                {selectedPatient.bmi ? ` \u00b7 BMI ${selectedPatient.bmi}` : ''}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Medicine *</label>
            <select
              value={medicineId}
              onChange={(e) => setMedicineId(e.target.value)}
              className="w-full px-3 py-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a medicine</option>
              {medicines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} - {m.strength} ({m.form})
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">Condition/Indication</label>
            <input
              type="text"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              placeholder="e.g., Fever, Headache, Bacterial Infection"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Doses per day (for the daily maximum check)
            </label>
            <input
              type="number"
              min="1"
              max="12"
              value={dosesPerDay}
              onChange={(e) => setDosesPerDay(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* --- Which formula to use --------------------------------------
            Every published method is offered, each one shown with its own
            arithmetic. A method whose inputs are missing (Clark with no weight
            recorded) is shown disabled with the reason rather than hidden, so
            the prescriber knows why it is unavailable instead of assuming the
            option does not exist. "Compare all" works every formula at once
            and reports how far apart they are. */}
        <div className="mb-5 rounded-xl border border-gray-200 bg-gray-50/70 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-gray-800">
                Dosage formula
              </h3>
              {combining && (
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <Loader2 className="h-3 w-3 animate-spin" /> checking availability
                </span>
              )}
            </div>
            {patientId && medicineId && (
              <span className="text-xs text-gray-500">
                {usableCount} of {formulas.length || 4} formulas applicable to this
                patient
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {/* Automatic choice */}
            <FormulaCard
              active={methodChoice === 'auto'}
              onClick={() => setMethodChoice('auto')}
              title="Automatic (recommended)"
              tag="auto"
              description={
                selectedFormula
                  ? `Uses ${selectedFormula.method} — the strongest method whose inputs are on file.`
                  : 'Uses the strongest method whose inputs are on file.'
              }
            />

            {FORMULA_OPTIONS.map((option) => {
              const found = formulas.find((f) => f.key === option.key);
              // Before a patient/medicine pair is chosen nothing is known yet,
              // so the cards stay selectable rather than showing as disabled.
              const known = Boolean(formulaData);
              const usable = !known || (found ? found.usable : false);
              return (
                <FormulaCard
                  key={option.key}
                  active={methodChoice === option.key}
                  disabled={!usable}
                  onClick={() => usable && setMethodChoice(option.key)}
                  title={option.title}
                  tag={option.label}
                  description={option.short}
                  reason={!usable && found ? found.reason : null}
                  dose={found && found.usable ? found.dose : null}
                  unit={found ? found.unit : 'mg'}
                />
              );
            })}

            {/* Compare every formula at once */}
            <FormulaCard
              active={methodChoice === 'all'}
              onClick={() => setMethodChoice('all')}
              title="Compare / combine all"
              tag="all"
              description="Works out every applicable formula and reports the agreement between them."
            />
          </div>

          {methodChoice === 'all' && formulaData && formulaData.combined && (
            <CombinedSummary combined={formulaData.combined} />
          )}
        </div>

        <button
          onClick={handleCalculate}
          disabled={loading}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Calculating...
            </>
          ) : (
            <>
              <Brain className="w-5 h-5" />
              Calculate dosage
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Results Section */}
      {dosage && (
        <div className="space-y-4">
          {/* Safety verdict - single source of truth from /safety-screen */}
          {safety && (
            <div className="space-y-3">
              {safety.blockers.map((blocker, index) => (
                <div
                  key={`blocker-${index}`}
                  className="flex gap-3 rounded border-l-4 border-red-500 bg-red-50 p-4"
                >
                  <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
                  <div>
                    <h3 className="font-semibold text-red-800">
                      {blocker.kind === 'ALLERGY' ? 'Allergy alert' : 'Contraindication alert'}
                    </h3>
                    <p className="text-red-700">{blocker.message}</p>
                    {blocker.detail && (
                      <p className="mt-1 text-sm text-red-600">{blocker.detail}</p>
                    )}
                  </div>
                </div>
              ))}

              {safety.warnings.map((warning, index) => (
                <div
                  key={`warning-${index}`}
                  className="flex gap-3 rounded border-l-4 border-yellow-500 bg-yellow-50 p-4"
                >
                  <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-600" />
                  <div>
                    <h3 className="font-semibold text-yellow-800">Warning</h3>
                    <p className="text-yellow-700">{warning.message}</p>
                  </div>
                </div>
              ))}

              {safety.safe && safety.warnings.length === 0 && (
                <div className="flex gap-3 rounded border-l-4 border-green-500 bg-green-50 p-4">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
                  <p className="text-green-700">
                    No allergy, contraindication or interaction found against this patient
                    record. Stock on hand: {safety.total_stock} units.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Dosage Information */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Dosage Information
              {dosage.is_weight_based && (
                <span className="flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                  <Scale className="h-3 w-3" /> weight-based
                </span>
              )}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">Dosage amount</p>
                <p className="text-2xl font-bold text-blue-600">
                  {dosage.dosage_amount} {dosage.dosage_unit}
                </p>
              </div>

              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">Frequency</p>
                <p className="text-2xl font-bold text-green-600">{dosage.frequency}</p>
              </div>

              <div className="bg-purple-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">Duration</p>
                <p className="text-2xl font-bold text-purple-600">{dosage.duration_days} days</p>
              </div>

              <div className="bg-orange-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">For Patient Age</p>
                <p className="text-2xl font-bold text-orange-600">{dosage.patient_age} years</p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">Weight</p>
                <p className="text-2xl font-bold text-gray-700">
                  {dosage.patient_weight_kg != null
                    ? `${dosage.patient_weight_kg} kg`
                    : 'not recorded'}
                </p>
              </div>

              {dosage.patient_bsa_m2 != null && (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Body surface area</p>
                  <p className="text-2xl font-bold text-gray-700">
                    {dosage.patient_bsa_m2} m²
                  </p>
                </div>
              )}
            </div>

            {/* The age-band guide is shown alongside a weight-based dose so
                the coarser figure is visible for comparison, not hidden. */}
            {dosage.age_band_guide && (
              <div className="mt-4 rounded border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
                <p className="font-semibold">Stored age-band guide ({dosage.age_band_guide.age_group} years)</p>
                <p className="mt-1">
                  {dosage.age_band_guide.dosage_amount} {dosage.age_band_guide.dosage_unit},{' '}
                  {dosage.age_band_guide.frequency} — a band average that does not
                  account for this patient’s weight.
                </p>
              </div>
            )}

            {!dosage.is_weight_based && dosage.calculation_method && (
              <div className="mt-4 flex items-start gap-2 rounded border-l-4 border-yellow-400 bg-yellow-50 p-3 text-sm text-yellow-800">
                <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>
                  This dose is not weight-based. Record the patient’s weight
                  on their record to enable an mg/kg calculation.
                </p>
              </div>
            )}

            {dosage.special_notes && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-800">
                <strong>Note:</strong> {dosage.special_notes}
              </div>
            )}

            {/* Where the dose came from. This form captures no weight, so a
                calculated dose is an estimate and is labelled as one. */}
            {dosage.calculation_method && (
              <div className="mt-3 flex items-start gap-2 rounded border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <div>
                  <p>
                    Derived using <strong>{dosage.calculation_method}</strong>.
                    {dosage.source ? ` ${dosage.source}.` : ''}
                  </p>
                  {dosage.confidence === 'low' && (
                    <p className="mt-1 font-medium">
                      Low confidence - no adult reference dose is on file for this generic.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Both formulas, side by side.
              The point of showing both is the disagreement: for a 24 kg
              eight-year-old the weight-based method gives 412.5 mg where the
              age band gives 250 mg, and hiding the loser would hide exactly
              the number worth seeing. */}
          {weightDose && weightDose.formulas && weightDose.formulas.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
                <Scale className="w-5 h-5" />
                Both formulas, compared
              </h2>
              <p className="mb-4 text-sm text-gray-500">
                The same patient and the same medicine, worked out two ways.
              </p>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {weightDose.formulas.filter(Boolean).map((f, index) => (
                  <div
                    key={index}
                    className={`rounded-lg border p-4 ${
                      f.selected
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-gray-800">{f.method}</p>
                      {f.selected && (
                        <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-semibold text-white">
                          used
                        </span>
                      )}
                    </div>
                    <p className="mt-2 font-mono text-sm text-blue-700">{f.formula}</p>
                    <p className="mt-2 text-2xl font-bold text-gray-900">
                      {f.dose} {f.unit}
                    </p>
                    {f.is_weight_based ? (
                      <p className="mt-1 text-xs text-green-700">
                        Uses this patient&rsquo;s recorded weight.
                      </p>
                    ) : (
                      <p className="mt-1 text-xs text-gray-500">
                        {f.assumes || 'An age-based estimate.'}
                      </p>
                    )}
                    {f.capped && (
                      <p className="mt-1 text-xs text-orange-700">
                        Capped at the maximum single dose.
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {weightDose.is_weight_based &&
                weightDose.formulas.length > 1 &&
                weightDose.formulas[1] &&
                weightDose.formulas[0].dose !== weightDose.formulas[1].dose && (
                  <p className="mt-4 rounded border-l-4 border-blue-400 bg-blue-50 p-3 text-sm text-blue-800">
                    The two methods differ by{' '}
                    <strong>
                      {Math.abs(
                        weightDose.formulas[0].dose - weightDose.formulas[1].dose
                      ).toFixed(1)}{' '}
                      mg
                    </strong>
                    . The weight-based figure is the more precise one for this
                    patient, because it uses their actual body weight rather
                    than an average for their age.
                  </p>
                )}

              {!weightDose.is_weight_based && (
                <p className="mt-4 rounded border-l-4 border-amber-400 bg-amber-50 p-3 text-sm text-amber-800">
                  Both figures here are age-based, because no weight is recorded
                  for this patient. Recording the weight would allow an accurate
                  mg/kg dose.
                </p>
              )}
            </div>
          )}

          {/* Weight-based calculation - the arithmetic, shown in full so it
              can be checked by hand rather than taken on trust. */}
          {weightDose && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
                <Scale className="w-5 h-5" />
                Weight-based calculation
              </h2>
              <p className="mb-4 text-sm text-gray-500">
                {weightDose.is_weight_based
                  ? 'This dose is calculated from the patient\u2019s body weight.'
                  : 'No weight-based dose is published for this medicine; the figure below is shown for transparency.'}
              </p>

              <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="rounded-lg bg-gray-50 p-3">
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <Scale className="h-3 w-3" /> Weight
                  </div>
                  <p className="text-lg font-bold text-gray-800">
                    {weightDose.weight_kg != null ? `${weightDose.weight_kg} kg` : 'not recorded'}
                  </p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <Ruler className="h-3 w-3" /> BSA
                  </div>
                  <p className="text-lg font-bold text-gray-800">
                    {weightDose.bsa_m2 != null ? `${weightDose.bsa_m2} m²` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">Age</p>
                  <p className="text-lg font-bold text-gray-800">
                    {weightDose.age_months < 24
                      ? `${weightDose.age_months} months`
                      : `${weightDose.age_years} years`}
                  </p>
                </div>
                <div className="rounded-lg bg-blue-50 p-3">
                  <p className="text-xs text-gray-500">Single dose</p>
                  <p className="text-lg font-bold text-blue-700">
                    {weightDose.dose} {weightDose.unit}
                  </p>
                </div>
              </div>

              {/* The formula, then the arithmetic step by step. */}
              <div className="rounded-lg border border-gray-200 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Method
                </p>
                <p className="font-medium text-gray-800">{weightDose.method}</p>
                <p className="mt-1 font-mono text-sm text-blue-700">{weightDose.formula}</p>

                <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Working
                </p>
                <ol className="mt-1 space-y-1">
                  {(weightDose.steps || []).map((step, index) => (
                    <li key={index} className="font-mono text-sm text-gray-700">
                      {index + 1}. {step}
                    </li>
                  ))}
                </ol>

                <div className="mt-3 flex flex-wrap gap-4 text-sm">
                  <span className="text-gray-600">
                    Daily total:{' '}
                    <strong className="text-gray-800">
                      {weightDose.daily_total_mg} {weightDose.unit}
                    </strong>
                    {weightDose.doses_per_day ? ` (${weightDose.doses_per_day}×/day)` : ''}
                  </span>
                  {weightDose.max_single_dose_mg != null && (
                    <span className="text-gray-600">
                      Max single dose:{' '}
                      <strong className="text-gray-800">
                        {weightDose.max_single_dose_mg} {weightDose.unit}
                      </strong>
                    </span>
                  )}
                  <span className="text-gray-600">
                    Confidence: <strong className="text-gray-800">{weightDose.confidence}</strong>
                  </span>
                </div>

                {weightDose.capped && (
                  <p className="mt-3 rounded border-l-4 border-orange-400 bg-orange-50 p-2 text-sm text-orange-800">
                    Dose capped to stay within:{' '}
                    {(weightDose.caps_applied || []).join(' and ')}.
                  </p>
                )}

                {(weightDose.warnings || []).map((warning, index) => (
                  <p
                    key={index}
                    className="mt-2 rounded border-l-4 border-yellow-400 bg-yellow-50 p-2 text-sm text-yellow-800"
                  >
                    {warning}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Total Dosage */}
          {totalDosage && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Total Medication Required</h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
                  <p className="text-sm text-gray-600">Total Amount</p>
                  <p className="text-2xl font-bold text-blue-700">{totalDosage.total_amount} {dosage.dosage_unit}</p>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                  <p className="text-sm text-gray-600">Total Doses</p>
                  <p className="text-2xl font-bold text-green-700">{totalDosage.total_doses}</p>
                </div>

                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
                  <p className="text-sm text-gray-600">Per Day</p>
                  <p className="text-2xl font-bold text-purple-700">{totalDosage.total_amount_per_day} {dosage.dosage_unit}</p>
                </div>
              </div>
            </div>
          )}

          {/* Drug Cycle Information */}
          {drugCycle && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Drug Cycle Information</h2>

              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="font-medium text-gray-700">Drug Type:</span>
                  <span className="text-gray-900 font-semibold">{drugCycle.type}</span>
                </div>

                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="font-medium text-gray-700">Standard cycle:</span>
                  <span className="text-gray-900 font-semibold">{drugCycle.standard_cycle} days</span>
                </div>

                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="font-medium text-gray-700">Break Required:</span>
                  <span className={`font-semibold ${drugCycle.break_required ? 'text-red-600' : 'text-green-600'}`}>
                    {drugCycle.break_required ? 'Yes' : 'No'}
                  </span>
                </div>

                {drugCycle.tapering_required && (
                  <div className="flex justify-between items-center p-3 bg-yellow-50 rounded border border-yellow-200">
                    <span className="font-medium text-yellow-800">Tapering Required:</span>
                    <span className="text-yellow-900 font-semibold">Yes</span>
                  </div>
                )}

                <div className="p-3 bg-blue-50 border-l-4 border-blue-500 rounded">
                  <p className="text-blue-800"><strong>⚠️ Important:</strong> {drugCycle.notes}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
/**
 * One selectable dosage formula.
 *
 * A disabled card is never simply greyed out: it carries the backend's own
 * reason ("The patient has no weight recorded."), because an option that
 * refuses without explaining why is indistinguishable from a broken one.
 */
function FormulaCard({
  active,
  disabled,
  onClick,
  title,
  tag,
  description,
  reason,
  dose,
  unit = 'mg',
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={reason || description}
      className={`flex h-full flex-col rounded-lg border p-3 text-left transition ${
        disabled
          ? 'cursor-not-allowed border-dashed border-gray-200 bg-gray-100/60 opacity-70'
          : active
            ? 'border-blue-500 bg-white ring-2 ring-blue-500/25'
            : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className={`text-sm font-semibold ${disabled ? 'text-gray-500' : 'text-gray-800'}`}>
          {title}
        </span>
        <span
          className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border text-[10px] font-bold uppercase ${
            disabled
              ? 'border-gray-300 text-gray-400'
              : active
                ? 'border-blue-600 bg-blue-600 text-white'
                : 'border-gray-300 text-gray-500'
          }`}
        >
          {disabled ? <Slash className="h-3 w-3" /> : active ? <Check className="h-3 w-3" /> : tag.slice(0, 2)}
        </span>
      </div>

      <p className={`mt-1 text-xs leading-relaxed ${disabled ? 'text-gray-400' : 'text-gray-500'}`}>
        {description}
      </p>

      {dose != null && (
        <p className="mt-2 text-lg font-bold text-blue-700">
          {dose} <span className="text-sm font-medium text-blue-600">{unit}</span>
        </p>
      )}

      {reason && (
        <p className="mt-2 rounded bg-amber-50 px-2 py-1 text-[11px] leading-snug text-amber-800">
          Not applicable — {reason}
        </p>
      )}
    </button>
  );
}

/**
 * The "combine them all" verdict.
 *
 * It deliberately does not average the formulas. Averaging clinical doses has
 * no published basis, so instead this states the spread and tells the
 * prescriber which figure to prefer, leaving the judgement where it belongs.
 */
function CombinedSummary({ combined }) {
  if (!combined) return null;

  if (!combined.usable_count) {
    return (
      <p className="mt-3 rounded-lg border-l-4 border-amber-400 bg-amber-50 p-3 text-sm text-amber-800">
        {combined.summary}
      </p>
    );
  }

  const tone = {
    close: 'border-emerald-400 bg-emerald-50 text-emerald-800',
    moderate: 'border-blue-400 bg-blue-50 text-blue-800',
    wide: 'border-orange-400 bg-orange-50 text-orange-800',
    // One formula is not agreement. Amber, and worded as a limitation, so it
    // cannot be read as the green "close agreement" reassurance.
    single: 'border-amber-400 bg-amber-50 text-amber-800',
  }[combined.agreement] || 'border-gray-300 bg-gray-50 text-gray-800';

  const headline =
    combined.agreement === 'single'
      ? `${combined.usable_count} formula applied — nothing to compare`
      : `${combined.usable_count} formulas applied — spread ${combined.spread_mg} mg (${combined.spread_pct}%)`;

  return (
    <div className={`mt-3 rounded-lg border-l-4 p-3 ${tone}`}>
      <p className="text-sm font-semibold">{headline}</p>
      <p className="mt-1 text-sm">{combined.verdict}</p>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left opacity-70">
              <th className="py-1 pr-3 font-semibold">Formula</th>
              <th className="py-1 pr-3 font-semibold">Single dose</th>
              <th className="py-1 font-semibold">Daily total</th>
            </tr>
          </thead>
          <tbody>
            {combined.daily_totals.map((row) => (
              <tr key={row.method} className="border-t border-black/5">
                <td className="py-1 pr-3">
                  {row.method}
                  {row.method === combined.reference_method && (
                    <span className="ml-2 rounded bg-white/70 px-1.5 py-0.5 text-[10px] font-semibold uppercase">
                      preferred
                    </span>
                  )}
                </td>
                <td className="py-1 pr-3 font-medium">{row.single} mg</td>
                <td className="py-1 font-medium">
                  {row.daily} mg
                  {row.capped && (
                    <span className="ml-2 text-[10px] uppercase opacity-80">capped</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}