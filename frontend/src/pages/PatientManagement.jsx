import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Users,
  Plus,
  Edit,
  Eye,
  Trash2,
  Loader2,
  AlertTriangle,
  Heart,
  Phone,
  Mail,
  MapPin,
  FileText,
  Printer,
  X,
} from 'lucide-react';
import { apiClient } from '../api';

const EMPTY_PATIENT = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  date_of_birth: '',
  gender: 'Male',
  chronic_diseases: '',
  current_medications: '',
  allergies_description: '',
  address: '',
  city: '',
  country: '',
};

/**
 * Patient management: list, create, edit, delete, and a detail drawer that
 * pulls the patient's allergies, prescription history and condition-based
 * medicine suggestions from /patients/:id/profile.
 */
export function PatientManagement() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState(EMPTY_PATIENT);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [allergyForm, setAllergyForm] = useState({ allergen: '', reaction: '', severity: 'Mild' });

  const fetchPatients = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.getPatients(search);
      setPatients((response && response.data) || []);
      setError(null);
    } catch (err) {
      setError('Could not load patients. Is the backend running?');
      setPatients([]);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  const openProfile = useCallback(async (id) => {
    setProfileLoading(true);
    setProfile(null);
    try {
      const response = await apiClient.getPatientProfile(id);
      if (response && response.success) setProfile(response.data);
    } catch (err) {
      setError('Could not load that patient record.');
    } finally {
      setProfileLoading(false);
    }
  }, []);

  // Support deep-linking straight to a patient drawer via /patients/:id.
  useEffect(() => {
    if (patientId) openProfile(Number(patientId));
  }, [patientId, openProfile]);

  const closeProfile = () => {
    setProfile(null);
    if (patientId) navigate('/patients');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await apiClient.updatePatient(editingId, formData);
      } else {
        await apiClient.createPatient(formData);
      }
      setShowModal(false);
      setEditingId(null);
      setFormData(EMPTY_PATIENT);
      await fetchPatients();
    } catch (err) {
      setError('Could not save the patient record.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (patient) => {
    const confirmed = window.confirm(
      `Delete ${patient.first_name} ${patient.last_name}?\n\n` +
        'This also removes their allergies and prescription history. This cannot be undone.'
    );
    if (!confirmed) return;
    try {
      await apiClient.deletePatient(patient.id);
      if (profile && profile.patient.id === patient.id) closeProfile();
      await fetchPatients();
    } catch (err) {
      setError('Could not delete the patient.');
    }
  };

  const handleAddAllergy = async (e) => {
    e.preventDefault();
    if (!profile) return;
    try {
      await apiClient.addAllergy(profile.patient.id, allergyForm);
      setAllergyForm({ allergen: '', reaction: '', severity: 'Mild' });
      await openProfile(profile.patient.id);
    } catch (err) {
      setError('Could not add the allergy.');
    }
  };

  const handleRemoveAllergy = async (allergyId) => {
    if (!profile) return;
    try {
      await apiClient.removeAllergy(profile.patient.id, allergyId);
      await openProfile(profile.patient.id);
    } catch (err) {
      setError('Could not remove the allergy.');
    }
  };

  const severityClass = (severity) => {
    switch ((severity || '').toLowerCase()) {
      case 'severe':
        return 'bg-red-100 text-red-700';
      case 'moderate':
        return 'bg-orange-100 text-orange-700';
      default:
        return 'bg-yellow-100 text-yellow-700';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-gray-800">Patients</h1>
        <button
          onClick={() => {
            setEditingId(null);
            setFormData(EMPTY_PATIENT);
            setShowModal(true);
          }}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" /> Add patient
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="relative">
        <input
          type="text"
          placeholder="Search by name, email or phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading patients...
        </div>
      ) : patients.length === 0 ? (
        <div className="rounded-lg bg-white p-12 text-center shadow">
          <Users className="mx-auto mb-3 h-10 w-10 text-gray-300" />
          <p className="text-gray-600">No patients found.</p>
          <p className="mt-1 text-sm text-gray-500">
            Use &ldquo;Add patient&rdquo; to register the first one.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {patients.map((patient) => (
            <div key={patient.id} className="rounded-lg bg-white p-5 shadow transition hover:shadow-lg">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {patient.first_name} {patient.last_name}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {patient.age} yrs &middot; {patient.gender}
                  </p>
                </div>
                {patient.allergies && patient.allergies.length > 0 && (
                  <span className="flex items-center gap-1 rounded bg-red-100 px-2 py-1 text-xs font-semibold text-red-700">
                    <AlertTriangle className="h-3 w-3" /> {patient.allergies.length}
                  </span>
                )}
              </div>

              <div className="space-y-1 text-sm text-gray-600">
                {patient.email && (
                  <p className="flex items-center gap-2 truncate">
                    <Mail className="h-3.5 w-3.5 flex-shrink-0 text-gray-400" />
                    {patient.email}
                  </p>
                )}
                {patient.phone && (
                  <p className="flex items-center gap-2">
                    <Phone className="h-3.5 w-3.5 flex-shrink-0 text-gray-400" />
                    {patient.phone}
                  </p>
                )}
                {patient.city && (
                  <p className="flex items-center gap-2">
                    <MapPin className="h-3.5 w-3.5 flex-shrink-0 text-gray-400" />
                    {patient.city}
                  </p>
                )}
              </div>

              {patient.chronic_diseases && (
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Conditions
                  </p>
                  <p className="text-sm text-orange-700">{patient.chronic_diseases}</p>
                </div>
              )}

              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => navigate(`/patients/${patient.id}`)}
                  className="flex flex-1 items-center justify-center gap-1 rounded bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100"
                >
                  <Eye className="h-4 w-4" /> View
                </button>
                <button
                  onClick={() => {
                    setEditingId(patient.id);
                    setFormData({ ...EMPTY_PATIENT, ...patient });
                    setShowModal(true);
                  }}
                  className="flex flex-1 items-center justify-center gap-1 rounded bg-green-50 px-3 py-2 text-sm text-green-700 hover:bg-green-100"
                >
                  <Edit className="h-4 w-4" /> Edit
                </button>
                <button
                  onClick={() => handleDelete(patient)}
                  className="rounded bg-red-50 px-3 py-2 text-red-700 hover:bg-red-100"
                  title="Delete patient"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* --- Patient detail drawer ------------------------------------------ */}
      {(profile || profileLoading) && (
        <div className="fixed inset-0 z-40 flex justify-end bg-black/40" onClick={closeProfile}>
          <div
            className="h-full w-full max-w-2xl overflow-y-auto bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 flex items-center justify-between border-b bg-white px-6 py-4">
              <h2 className="text-xl font-bold text-gray-800">Patient record</h2>
              <button onClick={closeProfile} className="rounded p-1 hover:bg-gray-100">
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>

            {profileLoading ? (
              <div className="flex items-center justify-center py-20 text-gray-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading record...
              </div>
            ) : profile ? (
              <div className="space-y-6 p-6">
                {/* Header */}
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">
                    {profile.patient.first_name} {profile.patient.last_name}
                  </h3>
                  <p className="mt-1 text-sm text-gray-600">
                    {profile.patient.age} yrs &middot; {profile.patient.gender}
                    {profile.patient.city ? ` \u00b7 ${profile.patient.city}` : ''}
                  </p>
                  <div className="mt-3 flex-wrap gap-4 text-sm text-gray-600">
                    {profile.patient.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3.5 w-3.5" /> {profile.patient.phone}
                      </span>
                    )}
                    {profile.patient.email && (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3.5 w-3.5" /> {profile.patient.email}
                      </span>
                    )}
                  </div>
                </div>

                {/* Summary tiles */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Allergies', value: profile.stats.allergy_count, cls: 'text-red-600' },
                    { label: 'Prescriptions', value: profile.stats.prescription_count, cls: 'text-blue-600' },
                    { label: 'Conditions', value: profile.stats.condition_count, cls: 'text-orange-600' },
                  ].map((tile) => (
                    <div key={tile.label} className="rounded-lg bg-gray-50 p-3 text-center">
                      <p className={`text-2xl font-bold ${tile.cls}`}>{tile.value}</p>
                      <p className="text-xs text-gray-500">{tile.label}</p>
                    </div>
                  ))}
                </div>

                {/* Allergies */}
                <section>
                  <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-800">
                    <AlertTriangle className="h-4 w-4 text-red-500" /> Recorded allergies
                  </h4>
                  {profile.allergies.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      No allergies recorded. {profile.patient.allergies_description || ''}
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {profile.allergies.map((allergy) => (
                        <li
                          key={allergy.id}
                          className="flex items-start justify-between rounded-lg border-red-100 bg-red-50 p-3"
                        >
                          <div>
                            <p className="font-medium text-red-800">{allergy.allergen}</p>
                            <p className="text-sm text-red-700">{allergy.reaction}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`rounded px-2 py-0.5 text-xs font-semibold ${severityClass(allergy.severity)}`}>
                              {allergy.severity}
                            </span>
                            <button
                              onClick={() => handleRemoveAllergy(allergy.id)}
                              className="text-red-400 hover:text-red-700"
                              title="Remove allergy"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Add allergy */}
                  <form onSubmit={handleAddAllergy} className="mt-3 space-y-2 rounded-lg bg-gray-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Add allergy
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        required
                        placeholder="Allergen (e.g. Penicillin)"
                        value={allergyForm.allergen}
                        onChange={(e) => setAllergyForm({ ...allergyForm, allergen: e.target.value })}
                        className="rounded border-gray-300 px-3 py-1.5 text-sm"
                      />
                      <select
                        value={allergyForm.severity}
                        onChange={(e) => setAllergyForm({ ...allergyForm, severity: e.target.value })}
                        className="rounded border-gray-300 px-3 py-1.5 text-sm"
                      >
                        <option>Mild</option>
                        <option>Moderate</option>
                        <option>Severe</option>
                      </select>
                    </div>
                    <input
                      required
                      placeholder="Observed reaction"
                      value={allergyForm.reaction}
                      onChange={(e) => setAllergyForm({ ...allergyForm, reaction: e.target.value })}
                      className="w-full rounded border-gray-300 px-3 py-1.5 text-sm"
                    />
                    <button
                      type="submit"
                      className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                    >
                      Add allergy
                    </button>
                  </form>
                </section>

                {/* Medical background */}
                <section>
                  <h4 className="mb-2 font-semibold text-gray-800">Medical background</h4>
                  <dl className="space-y-2 text-sm">
                    <div>
                      <dt className="text-gray-500">Chronic conditions</dt>
                      <dd className="text-gray-800">{profile.patient.chronic_diseases || 'None recorded'}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-500">Current medications</dt>
                      <dd className="text-gray-800">{profile.patient.current_medications || 'None recorded'}</dd>
                    </div>
                    {profile.patient.address && (
                      <div>
                        <dt className="text-gray-500">Address</dt>
                        <dd className="text-gray-800">
                          {profile.patient.address}
                          {profile.patient.country ? `, ${profile.patient.country}` : ''}
                        </dd>
                      </div>
                    )}
                  </dl>
                </section>

                {/* Condition-based suggestions */}
                {profile.condition_suggestions.length > 0 && (
                  <section>
                    <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-800">
                      <Heart className="h-4 w-4 text-blue-500" /> Suggested medicines by condition
                    </h4>
                    <div className="space-y-3">
                      {profile.condition_suggestions.map((group) => (
                        <div key={group.condition} className="rounded-lg border p-3">
                          <p className="mb-2 text-sm font-semibold text-gray-800">{group.condition}</p>
                          {group.recommendations.length === 0 ? (
                            <p className="text-xs text-gray-500">
                              No allergy-safe match found in the database for this condition.
                            </p>
                          ) : (
                            <ul className="space-y-2">
                              {group.recommendations.map((rec) => (
                                <li key={rec.medicine_id} className="text-sm">
                                  <div className="flex items-center justify-between">
                                    <span className="font-medium text-gray-800">{rec.medicine_name}</span>
                                    <span className="text-xs text-gray-500">
                                      score {rec.recommendation_score}
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-500">
                                    {rec.dosage
                                      ? `${rec.dosage.dosage_amount} ${rec.dosage.dosage_unit} - ${rec.dosage.frequency}`
                                      : 'No dosage guide'}
                                  </p>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Prescription history */}
                <section>
                  <h4 className="mb-3 flex items-center gap-2 font-semibold text-gray-800">
                    <FileText className="h-4 w-4 text-gray-500" /> Prescription history
                  </h4>
                  {profile.prescriptions.length === 0 ? (
                    <p className="text-sm text-gray-500">No prescriptions recorded yet.</p>
                  ) : (
                    <ul className="space-y-3">
                      {profile.prescriptions.map((prescription) => (
                        <li key={prescription.id} className="rounded-lg border p-3">
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-gray-800">{prescription.diagnosis}</p>
                            <span className="text-xs text-gray-500">
                              {new Date(prescription.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500">Dr. {prescription.doctor_name}</p>
                          <ul className="mt-2 space-y-1">
                            {prescription.items.map((item) => (
                              <li key={item.id} className="text-sm text-gray-700">
                                &bull; {item.medicine_name} &mdash; {item.dosage_amount} {item.dosage_unit},{' '}
                                {item.frequency} for {item.duration_days} days
                              </li>
                            ))}
                          </ul>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                {/* Actions */}
                <div className="flex-wrap gap-2 border-t pt-4">
                  <a
                    href={apiClient.reportUrl.patient(profile.patient.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-white hover:bg-gray-900"
                    title="Print the full patient record on your pharmacy letterhead"
                  >
                    <Printer className="h-4 w-4" /> Print full report
                  </a>
                  <button
                    onClick={() => {
                      setEditingId(profile.patient.id);
                      setFormData({ ...EMPTY_PATIENT, ...profile.patient });
                      setShowModal(true);
                    }}
                    className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                  >
                    <Edit className="h-4 w-4" /> Edit patient
                  </button>
                  <button
                    onClick={() => handleDelete(profile.patient)}
                    className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-red-700 hover:bg-red-100"
                  >
                    <Trash2 className="h-4 w-4" /> Delete
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* --- Add / edit modal ------------------------------------------------ */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6">
            <h2 className="mb-6 text-2xl font-bold">
              {editingId ? 'Edit patient' : 'Add new patient'}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {[
                  { key: 'first_name', label: 'First name', required: true },
                  { key: 'last_name', label: 'Last name', required: true },
                  { key: 'email', label: 'Email', type: 'email' },
                  { key: 'phone', label: 'Phone', type: 'tel' },
                  { key: 'date_of_birth', label: 'Date of birth', type: 'date', required: true },
                  { key: 'city', label: 'City' },
                  { key: 'country', label: 'Country' },
                ].map((field) => (
                  <div key={field.key}>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      {field.label} {field.required && '*'}
                    </label>
                    <input
                      type={field.type || 'text'}
                      required={field.required}
                      value={formData[field.key] || ''}
                      onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                      className="w-full rounded-lg border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                ))}
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Gender *</label>
                  <select
                    required
                    value={formData.gender}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full rounded-lg border-gray-300 px-3 py-2"
                  >
                    <option>Male</option>
                    <option>Female</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Chronic conditions (comma separated)
                </label>
                <input
                  value={formData.chronic_diseases || ''}
                  onChange={(e) => setFormData({ ...formData, chronic_diseases: e.target.value })}
                  placeholder="e.g. Diabetes, Hypertension, Asthma"
                  className="w-full rounded-lg border-gray-300 px-3 py-2"
                />
                <p className="mt-1 text-xs text-gray-500">
                  These drive the condition-based medicine suggestions in the patient record.
                </p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Current medications (comma separated)
                </label>
                <input
                  value={formData.current_medications || ''}
                  onChange={(e) => setFormData({ ...formData, current_medications: e.target.value })}
                  placeholder="e.g. Metformin, Lisinopril"
                  className="w-full rounded-lg border-gray-300 px-3 py-2"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Used for drug interaction screening.
                </p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Free-text allergy notes
                </label>
                <textarea
                  rows="2"
                  value={formData.allergies_description || ''}
                  onChange={(e) => setFormData({ ...formData, allergies_description: e.target.value })}
                  placeholder="Anything not captured by structured allergy entries"
                  className="w-full rounded-lg border-gray-300 px-3 py-2"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {editingId ? 'Update' : 'Add'} patient
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
