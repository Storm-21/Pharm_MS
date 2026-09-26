/**
 * API client for the PharmMS backend.
 *
 * Base URL resolution:
 *   - dev  : React dev server on :3000 talks to Flask on :5000
 *   - prod : Flask serves the built bundle itself, so same-origin /api works
 */

const isDevServer = typeof window !== 'undefined' && window.location.port === '3000';

// Everything is served from this machine. There is no remote API, no CDN and no
// telemetry: the packaged build talks only to the Flask server on 127.0.0.1,
// which is why the application works with networking disabled entirely.
export const API_BASE_URL = isDevServer
  ? 'http://localhost:5000/api'
  : `${window.location.origin}/api`;

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    cache: 'no-store',
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  // A failed request MUST reject. The old check was
  //     if (!response.ok && !(payload && payload.error)) throw ...
  // so any error response that carried an `error` field - which is every 400
  // the API returns - was treated as success. The caller then stored null as
  // its result and the UI closed the form as if the save had worked, while the
  // server had rejected it. Reject with the server's own message instead, so
  // "A patient with the email ... already exists" reaches the screen.
  if (!response.ok) {
    const message =
      (payload && (payload.error || payload.message)) ||
      `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

const query = (params) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.append(key, value);
  });
  const str = search.toString();
  return str ? `?${str}` : '';
};

export const apiClient = {
  // --- Medicines ----------------------------------------------------------
  // WHY perPage IS 500 RATHER THAN 100
  //
  // Every screen that needs the medicine list calls getMedicines() with no
  // arguments, so the default here IS the catalogue size the user sees. It was
  // 100, and the catalogue has since grown past that - so the database held 172
  // medicines while the Medicine Database, the dosage calculator's picker and
  // the prescription writer could only ever offer the first 100. Nothing on
  // screen said so; the list simply stopped, which reads as "this is everything"
  // and had a user reasonably asking whether India only has 100 medicines.
  //
  // The server-side default is 20 (see medicine_), so the client must
  // be explicit. 500 is a deliberate ceiling rather than "unlimited": it is
  // comfortably above the curated set and the realistic size of an imported
  // regional catalogue, while still bounding one response. A catalogue larger
  // than this should page through the API instead of loading in one go.
  getMedicines: (search = '', page = 1, perPage = 500) =>
    request(`/medicines${query({ search, page, per_page: perPage })}`),
  getMedicine: (id) => request(`/medicines/${id}`),
  createMedicine: (data) => request('/medicines', { method: 'POST', body: JSON.stringify(data) }),
  updateMedicine: (id, data) =>
    request(`/medicines/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMedicine: (id) => request(`/medicines/${id}`, { method: 'DELETE' }),
  searchByCondition: (condition) =>
    request(`/medicines/search/by-condition${query({ condition })}`),

  // --- Patients -----------------------------------------------------------
  getPatients: (search = '', page = 1, perPage = 100) =>
    request(`/patients${query({ search, page, per_page: perPage })}`),
  getPatient: (id) => request(`/patients/${id}`),
  createPatient: (data) => request('/patients', { method: 'POST', body: JSON.stringify(data) }),
  updatePatient: (id, data) =>
    request(`/patients/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePatient: (id) => request(`/patients/${id}`, { method: 'DELETE' }),
  getPatientAllergies: (id) => request(`/patients/${id}/allergies`),
  addAllergy: (patientId, data) =>
    request(`/patients/${patientId}/allergies`, { method: 'POST', body: JSON.stringify(data) }),
  removeAllergy: (patientId, allergyId) =>
    request(`/patients/${patientId}/allergies/${allergyId}`, { method: 'DELETE' }),
  // Aggregate used by the patient detail drawer.
  getPatientProfile: (id) => request(`/patients/${id}/profile`),

  // --- Prescriptions ------------------------------------------------------
  getPrescriptions: (patientId = null, page = 1) =>
    request(`/prescriptions${query({ patient_id: patientId, page, per_page: 100 })}`),
  getPrescription: (id) => request(`/prescriptions/${id}`),
  createPrescription: (data) =>
    request('/prescriptions', { method: 'POST', body: JSON.stringify(data) }),
  updatePrescription: (id, data) =>
    request(`/prescriptions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePrescription: (id) => request(`/prescriptions/${id}`, { method: 'DELETE' }),
  addPrescriptionItem: (prescriptionId, data) =>
    request(`/prescriptions/${prescriptionId}/items`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  removePrescriptionItem: (itemId) =>
    request(`/prescriptions/items/${itemId}`, { method: 'DELETE' }),

  // --- Inventory ----------------------------------------------------------
  getInventory: (status = '', page = 1, perPage = 200) =>
    request(`/inventory${query({ status, page, per_page: perPage })}`),
  getInventoryItem: (id) => request(`/inventory/${id}`),
  createInventory: (data) =>
    request('/inventory', { method: 'POST', body: JSON.stringify(data) }),
  updateInventory: (id, data) =>
    request(`/inventory/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateInventoryStock: (id, quantityChange) =>
    request(`/inventory/${id}/update-stock`, {
      method: 'PUT',
      body: JSON.stringify({ quantity_change: quantityChange }),
    }),
  getStockAlerts: () => request('/inventory/alerts'),
  getInventorySummary: () => request('/inventory/summary'),

  // --- Clinical decision support -----------------------------------------
  calculateDosage: (patientId, medicineId, condition) =>
    request('/recommender/dosage', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, medicine_id: medicineId, condition }),
    }),
  calculateTotalDosage: (dosageAmount, frequency, durationDays) =>
    request('/recommender/total-dosage', {
      method: 'POST',
      body: JSON.stringify({
        dosage_amount: dosageAmount,
        frequency,
        duration_days: durationDays,
      }),
    }),
  getDrugCycle: (medicineId) => request(`/recommender/drug-cycle/${medicineId}`),
  // Full weight-based calculation: formula, inputs, arithmetic and result.
  calculateWeightDose: (patientId, medicineId, options = {}) =>
    request('/recommender/weight-dose', {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        medicine_id: medicineId,
        doses_per_day: options.dosesPerDay,
        mg_per_kg: options.mgPerKg,
        adult_mg: options.adultMg,
        max_mg: options.maxMg,
        dose_per_m2: options.dosePerM2,
        // Lets the prescriber pick the formula instead of the default route.
        method: options.method,
      }),
    }),
  // Every published formula at once, with a flag for each one that cannot be
  // applied and why - so the panel can disable an option rather than hide it.
  getDoseFormulas: (patientId, medicineId, options = {}) =>
    request('/recommender/dose-formulas', {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        medicine_id: medicineId,
        doses_per_day: options.dosesPerDay,
        mg_per_kg: options.mgPerKg,
        adult_mg: options.adultMg,
        max_mg: options.maxMg,
        dose_per_m2: options.dosePerM2,
        combine: options.combine ? true : undefined,
      }),
    }),
  checkAllergies: (patientId, medicineId) =>
    request('/recommender/check-allergies', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, medicine_id: medicineId }),
    }),
  checkInteractions: (medicineId, currentMedicines) =>
    request('/recommender/check-interactions', {
      method: 'POST',
      body: JSON.stringify({ medicine_id: medicineId, current_medicines: currentMedicines }),
    }),
  checkContraindications: (patientId, medicineId) =>
    request('/recommender/check-contraindications', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, medicine_id: medicineId }),
    }),
  recommendMedicines: (patientId, condition, severity = 'mild') =>
    request('/recommender/recommend-medicines', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, condition, severity }),
    }),
  getSimilarCases: (patientId, condition) =>
    request(`/recommender/similar-cases${query({ patient_id: patientId, condition })}`),
  getAlternativeMedicines: (patientId, medicineId) =>
    request('/recommender/alternative-medicines', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, medicine_id: medicineId }),
    }),
  // One-shot safety screen used by the dosage calculator and patient drawer.
  safetyScreen: (patientId, medicineId) =>
    request('/recommender/safety-screen', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, medicine_id: medicineId }),
    }),

  // --- Alternatives / same-disease comparison ----------------------------
  getAlternatives: (medicineId, patientId = null, limit = 10) =>
    request(`/recommender/alternatives${query({ medicine_id: medicineId, patient_id: patientId, limit })}`),
  getMedicinesByCondition: (condition, patientId = null, limit = 20) =>
    request(`/recommender/by-condition${query({ condition, patient_id: patientId, limit })}`),

  // --- Full clinical assessment ------------------------------------------
  // The authoritative safety endpoint: comorbidity, renal, hepatic, age,
  // pregnancy and form checks as well as allergy and interaction, with a
  // graded verdict rather than a yes/no.
  assessSafety: (patientId, medicineId, doseUnit = null) =>
    request('/recommender/assess', {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        medicine_id: medicineId,
        dose_unit: doseUnit,
      }),
    }),

  // Course length, timing, tapering and missed-dose advice.
  getAdministrationPlan: (medicineId, options = {}) =>
    request('/recommender/administration-plan', {
      method: 'POST',
      body: JSON.stringify({
        medicine_id: medicineId,
        frequency: options.frequency,
        duration_days: options.durationDays,
        indication: options.indication,
      }),
    }),

  // --- Substitution: what to dispense when the first choice is unavailable
  getSubstitutes: (medicineId, patientId = null, options = {}) =>
    request(`/recommender/substitutes/${medicineId}${query({
      patient_id: patientId,
      include_different_class: options.includeDifferentClass ? 1 : undefined,
      require_stock: options.requireStock === false ? 0 : 1,
    })}`),

  // Can this be dispensed now, and if not, what is the closest thing that can.
  getDispensePlan: (medicineId, patientId, quantityNeeded = 1) =>
    request('/recommender/dispense-plan', {
      method: 'POST',
      body: JSON.stringify({
        medicine_id: medicineId,
        patient_id: patientId,
        quantity_needed: quantityNeeded,
      }),
    }),

  // "The patient needs something for X" - in stock, out of stock with a
  // substitute, and what was set aside on safety.
  resolveCondition: (condition, patientId = null, limit = 8) =>
    request(`/recommender/resolve${query({ condition, patient_id: patientId, limit })}`),

  // --- Optional live reference lookup (offline-first, cached) -------------
  getLiveReference: (drugName, refresh = false) =>
    request(`/recommender/reference/${encodeURIComponent(drugName)}${query({ refresh: refresh ? 1 : undefined })}`),
  getReferenceCacheStats: () => request('/recommender/reference-cache'),
  clearReferenceCache: () =>
    request('/recommender/reference-cache', { method: 'DELETE' }),
  enrichMedicine: (medicineId) =>
    request(`/recommender/enrich/${medicineId}`, { method: 'POST' }),

  // --- Local storage / backups -------------------------------------------
  getStorageInfo: () => request('/storage/info'),
  getSnapshots: () => request('/storage/snapshots'),
  createSnapshot: () => request('/storage/snapshots', { method: 'POST' }),
  restoreSnapshot: (filename) =>
    request('/storage/snapshots/restore', {
      method: 'POST',
      body: JSON.stringify({ filename }),
    }),
  exportData: (includeMedicines = true) =>
    request('/storage/export', {
      method: 'POST',
      body: JSON.stringify({ include_medicines: includeMedicines }),
    }),
  // Returns a URL to hit directly so the browser handles the download.
  exportDownloadUrl: () => `${API_BASE_URL}/storage/export?download=1`,
  importData: (payload, replacePatients = false) =>
    request(`/storage/import${query({ replace_patients: replacePatients })}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // --- Security / authorship ---------------------------------------------
  getBranding: () => request('/security/branding'),
  verifyIntegrity: () => request('/security/verify'),

  // --- Pharmacy branding / licensing -------------------------------------
  getPharmacyBranding: () => request('/branding'),
  activateLicence: (pharmacyName, licenceKey) =>
    request('/branding/licence', {
      method: 'POST',
      body: JSON.stringify({ pharmacy_name: pharmacyName, licence_key: licenceKey }),
    }),
  clearLicence: () => request('/branding/licence', { method: 'DELETE' }),
  updateProfile: (data) =>
    request('/branding/profile', { method: 'PUT', body: JSON.stringify(data) }),
  deleteLogo: () => request('/branding/logo', { method: 'DELETE' }),

  // Upload needs multipart, so it bypasses the JSON helper.
  uploadLogo: async (file) => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE_URL}/branding/logo`, { method: 'POST', body: form });
    return res.json();
  },

  // --- Printable reports --------------------------------------------------
  reportUrl: {
    prescription: (id) => `${API_BASE_URL}/reports/prescription/${id}`,
    patient: (id) => `${API_BASE_URL}/reports/patient/${id}`,
    inventory: () => `${API_BASE_URL}/reports/inventory`,
  },
};

export default apiClient;
