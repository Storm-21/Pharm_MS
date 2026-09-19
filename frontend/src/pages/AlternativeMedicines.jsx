import React, { useCallback, useEffect, useState } from 'react';
import {
  Search,
  Loader2,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  IndianRupee,
  Package,
  ArrowRight,
  Layers,
} from 'lucide-react';
import { apiClient } from '../api';

/**
 * Compare medicines that treat the same disease.
 *
 * Two ways in:
 *   - pick a medicine  -> "what else works for the same thing?" (similarity ranked)
 *   - type a condition -> "everything we stock for X", grouped by drug class
 *
 * When a patient is selected every result is screened for allergies and
 * contraindications, so unsafe options are pushed to the bottom and flagged
 * rather than hidden.
 */
export function AlternativeMedicines() {
  const [mode, setMode] = useState('medicine'); // 'medicine' | 'condition'
  const [medicines, setMedicines] = useState([]);
  const [patients, setPatients] = useState([]);
  const [medicineId, setMedicineId] = useState('');
  const [condition, setCondition] = useState('');
  const [patientId, setPatientId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [source, setSource] = useState(null);
  const [results, setResults] = useState(null);
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    Promise.all([apiClient.getMedicines(), apiClient.getPatients()])
      .then(([medRes, patRes]) => {
        setMedicines((medRes && medRes.data) || []);
        setPatients((patRes && patRes.data) || []);
      })
      .catch(() => setError('Could not load medicines and patients.'));
  }, []);

  const runSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    setSource(null);
    setMeta(null);

    try {
      if (mode === 'medicine') {
        if (!medicineId) {
          setError('Select a medicine to compare against.');
          return;
        }
        const res = await apiClient.getAlternatives(medicineId, patientId || null, 20);
        if (res && res.success) {
          setSource(res.data.source);
          setResults(res.data.alternatives);
          setMeta({
            matched: res.data.total_matched,
            considered: res.data.total_considered,
          });
        } else {
          setError((res && res.error) || 'No alternatives found.');
        }
      } else {
        if (!condition.trim()) {
          setError('Enter a condition to search for.');
          return;
        }
        const res = await apiClient.getMedicinesByCondition(condition.trim(), patientId || null, 25);
        if (res && res.success) {
          setResults(res.data.groups);
          setMeta({ found: res.data.total_found });
        } else {
          setError((res && res.error) || 'No medicines found for that condition.');
        }
      }
    } catch (err) {
      setError('Search failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [mode, medicineId, condition, patientId]);

  const safeBadge = (safe) => {
    if (safe === null || safe === undefined) {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          not screened
        </span>
      );
    }
    return safe ? (
      <span className="inline-flex items-center gap-1 rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
        <ShieldCheck className="h-3 w-3" /> safe
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        <ShieldAlert className="h-3 w-3" /> blocked
      </span>
    );
  };

  const priceDelta = (delta) => {
    if (delta === null || delta === undefined || delta === 0) return null;
    const cheaper = delta < 0;
    return (
      <span className={`text-xs font-medium ${cheaper ? 'text-emerald-600' : 'text-orange-600'}`}>
        {cheaper ? '' : '+'}
        {delta.toFixed(2)} {cheaper ? 'cheaper' : 'costlier'}
      </span>
    );
  };

  const MedicineCard = ({ item, showSimilarity, showDelta }) => (
    <div className="rounded-lg border bg-white p-4 transition hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="truncate font-semibold text-gray-900">{item.name}</h4>
          <p className="truncate text-xs text-gray-500">
            {item.generic_name}
            {item.brand_name ? ` \u00b7 ${item.brand_name}` : ''}
          </p>
        </div>
        <div className="flex flex-shrink-0 flex-col items-end gap-1">
          {item.safe_for_patient !== undefined && safeBadge(item.safe_for_patient)}
          {showSimilarity && item.similarity_score != null && (
            <span className="text-xs text-gray-500">{item.similarity_score}% match</span>
          )}
        </div>
      </div>

      <div className="mt-3 flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600">
        <span className="inline-flex items-center gap-1">
          <IndianRupee className="h-3 w-3" />
          {item.selling_price != null ? item.selling_price.toFixed(2) : '\u2014'}
        </span>
        <span className="inline-flex items-center gap-1">
          <Package className="h-3 w-3" />
          {item.in_stock ? `${item.total_stock} in stock` : 'out of stock'}
        </span>
        <span>{item.strength}</span>
        <span className="rounded bg-gray-100 px-1.5 py-0.5">{item.form}</span>
        {item.requires_prescription && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">Rx</span>
        )}
      </div>

      {item.molecular_formula && (
        <p className="mt-2 font-mono text-xs text-gray-500">{item.molecular_formula}</p>
      )}

      {item.therapeutic_class && (
        <p className="mt-2 text-xs text-gray-600">
          <span className="text-gray-400">Class:</span> {item.therapeutic_class}
        </p>
      )}

      {showDelta && priceDelta(item.price_difference)}

      {item.safety_note && (
        <p className="mt-2 flex items-start gap-1 text-xs text-red-700">
          <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
          {item.safety_note}
        </p>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Alternative medicines</h1>
        <p className="mt-1 text-sm text-gray-600">
          Find other options for the same disease or condition, screened against a patient
          record where one is selected.
        </p>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        {/* Mode switch */}
        <div className="mb-4 flex gap-2">
          <button
            onClick={() => setMode('medicine')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${mode === 'medicine'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
          >
            <Layers className="h-4 w-4" /> By medicine
          </button>
          <button
            onClick={() => setMode('condition')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${mode === 'condition'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
          >
            <Search className="h-4 w-4" /> By condition
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {mode === 'medicine' ? (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Medicine to compare against
              </label>
              <select
                value={medicineId}
                onChange={(e) => setMedicineId(e.target.value)}
                className="w-full rounded-lg border-gray-300 px-3 py-2"
              >
                <option value="">Select a medicine</option>
                {medicines.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} &mdash; {m.generic_name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Returns other medicines whose indications and drug class overlap with this one.
              </p>
            </div>
          ) : (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Condition</label>
              <input
                type="text"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                placeholder="e.g. Fever, Diabetes, Asthma, Urinary tract infection"
                className="w-full rounded-lg border-gray-300 px-3 py-2"
              />
              <p className="mt-1 text-xs text-gray-500">
                Lists everything stocked for that condition, grouped by drug class.
              </p>
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Screen against patient (optional)
            </label>
            <select
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="w-full rounded-lg border-gray-300 px-3 py-2"
            >
              <option value="">No patient - show all options</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name} ({p.age} yrs)
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Select a patient to flag allergies and contraindications on every result.
            </p>
          </div>
        </div>

        <button
          onClick={runSearch}
          disabled={loading}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
          {loading ? 'Searching...' : 'Find alternatives'}
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {source && (
        <div className="rounded-lg border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-900">
            <span className="font-semibold">Comparing against:</span> {source.name}
            {source.therapeutic_class ? ` \u2014 ${source.therapeutic_class}` : ''}
          </p>
          <p className="mt-1 text-xs text-blue-800">{source.use_case}</p>
        </div>
      )}

      {/* By-medicine results */}
      {results && mode === 'medicine' && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">
              {results.length} alternative{results.length === 1 ? '' : 's'} found
            </h2>
            {meta && (
              <span className="text-xs text-gray-500">
                from {meta.considered} medicines compared
              </span>
            )}
          </div>

          {results.length === 0 ? (
            <div className="rounded-lg bg-white p-10 text-center shadow">
              <p className="text-gray-600">
                No other medicine in the database treats the same condition.
              </p>
              <p className="mt-1 text-sm text-gray-500">
                The catalogue may be narrow for this medicine &mdash; consider adding
                more entries to the medicine database.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {results.map((item) => (
                <MedicineCard
                  key={item.medicine_id}
                  item={item}
                  showSimilarity
                  showDelta
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* By-condition results */}
      {results && mode === 'condition' && (
        <div className="space-y-5">
          <h2 className="text-lg font-semibold text-gray-800">
            {meta ? `${meta.found} medicine${meta.found === 1 ? '' : 's'} for "${condition}"` : ''}
          </h2>

          {results.length === 0 ? (
            <div className="rounded-lg bg-white p-10 text-center shadow">
              <p className="text-gray-600">Nothing in the database matches that condition.</p>
              <p className="mt-1 text-sm text-gray-500">
                Try a broader term, or use the medicine importer to add a wider catalogue.
              </p>
            </div>
          ) : (
            results.map((group) => (
              <div key={group.therapeutic_class}>
                <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  <ArrowRight className="h-3.5 w-3.5" />
                  {group.therapeutic_class}
                  <span className="font-normal normal-case text-gray-400">
                    ({group.medicines.length})
                  </span>
                </h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {group.medicines.map((item) => (
                    <MedicineCard key={item.medicine_id} item={item} />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default AlternativeMedicines;
