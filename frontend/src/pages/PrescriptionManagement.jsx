import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FileText,
  Plus,
  Trash2,
  Loader2,
  AlertTriangle,
  ShieldCheck,
  Printer,
  X,
} from 'lucide-react';
import { apiClient } from '../api';

/**
 * Prescription management.
 *
 * A prescription is written against a patient and contains one or more
 * medicine items. Each item added is screened against the patient's allergies
 * and current medications before it is accepted, so a blocked combination
 * cannot be saved silently.
 */
export function PrescriptionManagement() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [patients, setPatients] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [viewing, setViewing] = useState(null);

  const [header, setHeader] = useState({
    patient_id: '',
    doctor_name: '',
    diagnosis: '',
    notes: '',
  });
  const [items, setItems] = useState([]);
  const [draft, setDraft] = useState({
    medicine_id: '',
    dosage_amount: '',
    dosage_unit: 'mg',
    frequency: 'Twice daily',
    duration_days: '5',
    special_instructions: '',
  });
  const [screenResult, setScreenResult] = useState(null);
  const [screening, setScreening] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rxRes, patientRes, medRes] = await Promise.all([
        apiClient.getPrescriptions(),
        apiClient.getPatients(),
        apiClient.getMedicines(),
      ]);
      setPrescriptions((rxRes && rxRes.data) || []);
      setPatients((patientRes && patientRes.data) || []);
      setMedicines((medRes && medRes.data) || []);
      setError(null);
    } catch (err) {
      setError('Could not load prescriptions. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selectedPatient = useMemo(
    () => patients.find((p) => String(p.id) === String(header.patient_id)) || null,
    [patients, header.patient_id]
  );

  const resetForm = () => {
    setHeader({ patient_id: '', doctor_name: '', diagnosis: '', notes: '' });
    setItems([]);
    setDraft({
      medicine_id: '',
      dosage_amount: '',
      dosage_unit: 'mg',
      frequency: 'Twice daily',
      duration_days: '5',
      special_instructions: '',
    });
    setScreenResult(null);
  };

  // Screen the chosen medicine as soon as both a patient and medicine are set.
  const runScreen = useCallback(async () => {
    if (!header.patient_id || !draft.medicine_id) {
      setScreenResult(null);
      return;
    }
    setScreening(true);
    try {
      const res = await apiClient.safetyScreen(
        Number(header.patient_id),
        Number(draft.medicine_id)
      );
      setScreenResult(res && res.data ? res.data : null);
    } catch (err) {
      setScreenResult(null);
    } finally {
      setScreening(false);
    }
  }, [header.patient_id, draft.medicine_id]);

  useEffect(() => {
    runScreen();
  }, [runScreen]);

  // Suggest a starting dosage from the patient's age when both are selected.
  useEffect(() => {
    if (!header.patient_id || !draft.medicine_id || draft.dosage_amount) return;
    let cancelled = false;
    apiClient
      .calculateDosage(Number(header.patient_id), Number(draft.medicine_id), header.diagnosis)
      .then((res) => {
        if (cancelled || !res || !res.success || !res.data) return;
        setDraft((d) =>
          d.dosage_amount
            ? d
            : {
                ...d,
                dosage_amount: String(res.data.dosage_amount),
                dosage_unit: res.data.dosage_unit || 'mg',
                frequency: res.data.frequency || d.frequency,
                duration_days: String(res.data.duration_days || d.duration_days),
              }
        );
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [header.patient_id, draft.medicine_id, header.diagnosis, draft.dosage_amount]);

  const addItem = () => {
    if (!draft.medicine_id || !draft.dosage_amount) return;
    if (screenResult && !screenResult.safe) {
      const blocked = window.confirm(
        'This medicine is flagged against the patient:\n\n' +
          screenResult.blockers.map((b) => `- ${b.message}`).join('\n') +
          '\n\nAdd it to the prescription anyway?'
      );
      if (!blocked) return;
    }
    const medicine = medicines.find((m) => String(m.id) === String(draft.medicine_id));
    setItems([
      ...items,
      {
        ...draft,
        medicine_id: Number(draft.medicine_id),
        dosage_amount: Number(draft.dosage_amount),
        duration_days: Number(draft.duration_days),
        medicine_name: medicine ? medicine.name : 'Unknown',
      },
    ]);
    setDraft({
      medicine_id: '',
      dosage_amount: '',
      dosage_unit: 'mg',
      frequency: 'Twice daily',
      duration_days: '5',
      special_instructions: '',
    });
    setScreenResult(null);
  };

  const removeItem = (index) => setItems(items.filter((_, i) => i !== index));

  const savePrescription = async () => {
    if (!header.patient_id || !header.doctor_name || !header.diagnosis) {
      setError('Patient, prescriber and diagnosis are all required.');
      return;
    }
    if (items.length === 0) {
      setError('Add at least one medicine before saving.');
      return;
    }
    setSaving(true);
    try {
      await apiClient.createPrescription({
        patient_id: Number(header.patient_id),
        doctor_name: header.doctor_name,
        diagnosis: header.diagnosis,
        notes: header.notes,
        items: items.map(({ medicine_name, ...rest }) => rest),
      });
      setShowForm(false);
      resetForm();
      setError(null);
      await load();
    } catch (err) {
      setError('Could not save the prescription.');
    } finally {
      setSaving(false);
    }
  };

  const deletePrescription = async (prescription) => {
    const confirmed = window.confirm(
      `Delete the prescription for "${prescription.diagnosis}"?\n\nThis cannot be undone.`
    );
    if (!confirmed) return;
    try {
      await apiClient.deletePrescription(prescription.id);
      if (viewing && viewing.id === prescription.id) setViewing(null);
      await load();
    } catch (err) {
      setError('Could not delete the prescription.');
    }
  };

  const patientName = (id) => {
    const patient = patients.find((p) => p.id === id);
    return patient ? `${patient.first_name} ${patient.last_name}` : `Patient #${id}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-gray-800">Prescriptions</h1>
        <button
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" /> New prescription
        </button>
      </div>

      {error && (
        <div className="flex items-start justify-between gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-700">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading prescriptions...
        </div>
      ) : prescriptions.length === 0 ? (
        <div className="rounded-lg bg-white p-12 text-center shadow">
          <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <p className="text-gray-600">No prescriptions recorded.</p>
          <p className="mt-1 text-sm text-gray-500">
            Use &ldquo;New prescription&rdquo; to write the first one.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg bg-white shadow">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Diagnosis</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Patient</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Prescriber</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Items</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Date</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {prescriptions.map((prescription) => (
                <tr key={prescription.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{prescription.diagnosis}</td>
                  <td className="px-4 py-3 text-gray-600">{patientName(prescription.patient_id)}</td>
                  <td className="px-4 py-3 text-gray-600">{prescription.doctor_name}</td>
                  <td className="px-4 py-3 text-center text-gray-600">
                    {prescription.items ? prescription.items.length : 0}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {new Date(prescription.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => setViewing(prescription)}
                        className="rounded bg-blue-50 px-3 py-1 text-xs text-blue-700 hover:bg-blue-100"
                      >
                        View
                      </button>
                      <a
                        href={apiClient.reportUrl.prescription(prescription.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded bg-gray-100 px-2 py-1 text-gray-700 hover:bg-gray-200"
                        title="Print prescription"
                      >
                        <Printer className="h-3.5 w-3.5" />
                      </a>
                      <button
                        onClick={() => deletePrescription(prescription)}
                        className="rounded bg-red-50 px-2 py-1 text-red-700 hover:bg-red-100"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* --- Writer ---------------------------------------------------------- */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white">
            <div className="sticky top-0 flex items-center justify-between border-b bg-white px-6 py-4">
              <h2 className="text-xl font-bold text-gray-800">New prescription</h2>
              <button onClick={() => setShowForm(false)} className="rounded p-1 hover:bg-gray-100">
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>

            <div className="space-y-5 p-6">
              {/* Header fields */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Patient *</label>
                  <select
                    value={header.patient_id}
                    onChange={(e) => setHeader({ ...header, patient_id: e.target.value })}
                    className="w-full rounded-lg border-gray-300 px-3 py-2"
                  >
                    <option value="">Select patient</option>
                    {patients.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.first_name} {p.last_name} ({p.age} yrs)
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Prescriber *</label>
                  <input
                    value={header.doctor_name}
                    onChange={(e) => setHeader({ ...header, doctor_name: e.target.value })}
                    placeholder="Dr. A. Sharma"
                    className="w-full rounded-lg border-gray-300 px-3 py-2"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Diagnosis *</label>
                  <input
                    value={header.diagnosis}
                    onChange={(e) => setHeader({ ...header, diagnosis: e.target.value })}
                    placeholder="e.g. Acute bronchitis"
                    className="w-full rounded-lg border-gray-300 px-3 py-2"
                  />
                </div>
              </div>

              {/* Patient safety context */}
              {selectedPatient && (
                <div className="rounded-lg bg-blue-50 p-3 text-sm">
                  <p className="font-medium text-blue-900">Safety context for this patient</p>
                  <p className="mt-1 text-blue-800">
                    <strong>Allergies:</strong>{' '}
                    {selectedPatient.allergies && selectedPatient.allergies.length > 0
                      ? selectedPatient.allergies.map((a) => a.allergen).join(', ')
                      : 'none recorded'}
                  </p>
                  <p className="text-blue-800">
                    <strong>Current medications:</strong>{' '}
                    {selectedPatient.current_medications || 'none recorded'}
                  </p>
                  <p className="text-blue-800">
                    <strong>Conditions:</strong>{' '}
                    {selectedPatient.chronic_diseases || 'none recorded'}
                  </p>
                </div>
              )}

              {/* Add medicine */}
              <div className="rounded-lg border p-4">
                <h3 className="mb-3 font-semibold text-gray-800">Add a medicine</h3>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                  <div className="md:col-span-2">
                    <label className="mb-1 block text-xs font-medium text-gray-600">Medicine</label>
                    <select
                      value={draft.medicine_id}
                      onChange={(e) => setDraft({ ...draft, medicine_id: e.target.value })}
                      className="w-full rounded border-gray-300 px-3 py-2 text-sm"
                    >
                      <option value="">Select medicine</option>
                      {medicines.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name} - {m.strength} ({m.form})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">Dose</label>
                    <input
                      type="number"
                      step="0.01"
                      value={draft.dosage_amount}
                      onChange={(e) => setDraft({ ...draft, dosage_amount: e.target.value })}
                      className="w-full rounded border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">Unit</label>
                    <select
                      value={draft.dosage_unit}
                      onChange={(e) => setDraft({ ...draft, dosage_unit: e.target.value })}
                      className="w-full rounded border-gray-300 px-3 py-2 text-sm"
                    >
                      {['mg', 'ml', 'mcg', 'IU', 'tablet', 'capsule', 'puff'].map((u) => (
                        <option key={u}>{u}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">Frequency</label>
                    <input
                      value={draft.frequency}
                      onChange={(e) => setDraft({ ...draft, frequency: e.target.value })}
                      className="w-full rounded border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">Days</label>
                    <input
                      type="number"
                      value={draft.duration_days}
                      onChange={(e) => setDraft({ ...draft, duration_days: e.target.value })}
                      className="w-full rounded border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="md:col-span-3">
                    <label className="mb-1 block text-xs font-medium text-gray-600">
                      Special instructions
                    </label>
                    <input
                      value={draft.special_instructions}
                      onChange={(e) =>
                        setDraft({ ...draft, special_instructions: e.target.value })
                      }
                      placeholder="e.g. Take after food"
                      className="w-full rounded border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>

                {/* Live safety screen */}
                {screening && (
                  <p className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                    <Loader2 className="h-3 w-3 animate-spin" /> Screening against patient record...
                  </p>
                )}
                {screenResult && !screening && (
                  <div
                    className={`mt-3 rounded-lg p-3 text-sm ${
                      screenResult.safe
                        ? 'bg-emerald-50 text-emerald-800'
                        : 'bg-red-50 text-red-800'
                    }`}
                  >
                    <p className="flex items-center gap-2 font-medium">
                      {screenResult.safe ? (
                        <>
                          <ShieldCheck className="h-4 w-4" /> No allergy or contraindication found
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="h-4 w-4" /> Blocked for this patient
                        </>
                      )}
                    </p>
                    <ul className="mt-1 space-y-0.5 text-xs">
                      {screenResult.blockers.map((b, i) => (
                        <li key={`b${i}`}>&bull; {b.message}</li>
                      ))}
                      {screenResult.warnings.map((w, i) => (
                        <li key={`w${i}`}>&bull; {w.message}</li>
                      ))}
                    </ul>
                    <p className="mt-1 text-xs opacity-80">
                      Stock on hand: {screenResult.total_stock} units
                    </p>
                  </div>
                )}

                <button
                  onClick={addItem}
                  disabled={!draft.medicine_id || !draft.dosage_amount}
                  className="mt-3 rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900 disabled:opacity-40"
                >
                  Add to prescription
                </button>
              </div>

              {/* Item list */}
              {items.length > 0 && (
                <div className="overflow-hidden rounded-lg border">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700">Medicine</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700">Dose</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700">Frequency</th>
                        <th className="px-3 py-2 text-center font-semibold text-gray-700">Days</th>
                        <th className="px-3 py-2" />
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item, index) => (
                        <tr key={`${item.medicine_id}-${index}`} className="border-t">
                          <td className="px-3 py-2 text-gray-900">{item.medicine_name}</td>
                          <td className="px-3 py-2 text-gray-600">
                            {item.dosage_amount} {item.dosage_unit}
                          </td>
                          <td className="px-3 py-2 text-gray-600">{item.frequency}</td>
                          <td className="px-3 py-2 text-center text-gray-600">
                            {item.duration_days}
                          </td>
                          <td className="px-3 py-2 text-right">
                            <button
                              onClick={() => removeItem(index)}
                              className="text-red-500 hover:text-red-700"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Notes</label>
                <textarea
                  rows="2"
                  value={header.notes}
                  onChange={(e) => setHeader({ ...header, notes: e.target.value })}
                  className="w-full rounded-lg border-gray-300 px-3 py-2"
                />
              </div>

              <div className="flex justify-end gap-3 border-t pt-4">
                <button
                  onClick={() => setShowForm(false)}
                  className="rounded-lg border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={savePrescription}
                  disabled={saving || items.length === 0}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save prescription
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Viewer ---------------------------------------------------------- */}
      {viewing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white">
            <div className="flex items-center justify-between border-b px-6 py-4">
              <h2 className="text-xl font-bold text-gray-800">Prescription #{viewing.id}</h2>
              <div className="flex items-center gap-2">
                <a
                  href={apiClient.reportUrl.prescription(viewing.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
                  title="Open a printable copy on your pharmacy letterhead"
                >
                  <Printer className="h-4 w-4" /> Print
                </a>
                <button onClick={() => setViewing(null)} className="rounded p-1 hover:bg-gray-100">
                  <X className="h-5 w-5 text-gray-500" />
                </button>
              </div>
            </div>

            <div className="space-y-4 p-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Patient</p>
                  <p className="font-medium text-gray-900">{patientName(viewing.patient_id)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Prescriber</p>
                  <p className="font-medium text-gray-900">{viewing.doctor_name}</p>
                </div>
                <div>
                  <p className="text-gray-500">Diagnosis</p>
                  <p className="font-medium text-gray-900">{viewing.diagnosis}</p>
                </div>
                <div>
                  <p className="text-gray-500">Date</p>
                  <p className="font-medium text-gray-900">
                    {new Date(viewing.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="overflow-hidden rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Medicine</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Dose</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Frequency</th>
                      <th className="px-3 py-2 text-center font-semibold text-gray-700">Days</th>
                    </tr>
                  </thead>
                  <tbody>
                    {viewing.items.map((item) => (
                      <tr key={item.id} className="border-t">
                        <td className="px-3 py-2 text-gray-900">{item.medicine_name}</td>
                        <td className="px-3 py-2 text-gray-600">
                          {item.dosage_amount} {item.dosage_unit}
                        </td>
                        <td className="px-3 py-2 text-gray-600">{item.frequency}</td>
                        <td className="px-3 py-2 text-center text-gray-600">{item.duration_days}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {viewing.notes && (
                <div>
                  <p className="text-sm font-medium text-gray-700">Notes</p>
                  <p className="text-sm text-gray-600">{viewing.notes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
