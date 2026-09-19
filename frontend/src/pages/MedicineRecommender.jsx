import React, { useEffect, useState } from 'react';
import { apiClient } from '../api';
import { AlertCircle, Lightbulb, TrendingUp, Loader2 } from 'lucide-react';

// Common presenting complaints, used to populate the condition picker. The
// recommender matches these against each medicine's indications text.
const COMMON_CONDITIONS = [
  'Fever',
  'Pain',
  'Headache',
  'Bacterial infection',
  'Respiratory infection',
  'Urinary tract infection',
  'Acid reflux',
  'GERD',
  'Peptic ulcer',
  'Diabetes',
  'Hypertension',
  'High cholesterol',
  'Asthma',
  'Allergy',
  'Urticaria',
  'Cough',
  'Dehydration',
  'Anaemia',
  'Hypothyroidism',
  'Vitamin D deficiency',
];

export function MedicineRecommender() {
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [condition, setCondition] = useState('');
  const [severity, setSeverity] = useState('mild');
  const [recommendations, setRecommendations] = useState(null);
  const [similarCases, setSimilarCases] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiClient
      .getPatients()
      .then((res) => setPatients((res && res.data) || []))
      .catch(() => setError('Could not load the patient list.'));
  }, []);

  const selectedPatient = patients.find((p) => String(p.id) === String(patientId));

  const handleRecommend = async () => {
    if (!patientId || !condition) {
      setError('Select a patient and enter a condition.');
      return;
    }

    setLoading(true);
    setError(null);
    setRecommendations(null);
    setSimilarCases(null);
    try {
      const result = await apiClient.recommendMedicines(Number(patientId), condition, severity);
      if (result && result.success) {
        setRecommendations(result.data || []);
        const casesResult = await apiClient.getSimilarCases(Number(patientId), condition);
        if (casesResult && casesResult.success) setSimilarCases(casesResult.data || []);
      } else {
        setError((result && result.error) || 'Could not generate recommendations.');
      }
    } catch (err) {
      setError('Could not generate recommendations. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Smart Medicine Recommender</h1>

      {/* Input Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          Recommend Medicines
        </h2>

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
                  {p.first_name} {p.last_name} ({p.age} yrs)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Condition *</label>
            <input
              type="text"
              list="condition-options"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              placeholder="e.g., Fever, Headache, Diabetes"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <datalist id="condition-options">
              {COMMON_CONDITIONS.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleRecommend}
          disabled={loading}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <TrendingUp className="w-5 h-5" />
          {loading ? 'Analyzing...' : 'Get Recommendations'}
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {loading && !recommendations && (
        <div className="flex items-center justify-center py-12 text-gray-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Screening the database...
        </div>
      )}

      {/* Recommendations */}
      {recommendations && (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
            <p className="text-blue-900">
              {recommendations.length === 0 ? (
                <p className="text-blue-900">
                  No allergy-safe medicine in the database matched <strong>{condition}</strong>.
                  Every match either conflicted with a recorded allergy or was contraindicated.
                </p>
              ) : (
                <p className="text-blue-900">
                  <strong>Found {recommendations.length} suitable medicines</strong> for{' '}
                  <strong>{condition}</strong>
                  {selectedPatient
                    ? ` for ${selectedPatient.first_name} ${selectedPatient.last_name}`
                    : ''}
                  , screened against recorded allergies and medical history.
                </p>
              )}
            </p>
          </div>

          {recommendations.map((rec, index) => (
            <div key={index} className="bg-white rounded-lg shadow overflow-hidden hover:shadow-lg transition">
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-4 text-white">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-xl font-bold">{rec.medicine_name}</h3>
                    <p className="text-blue-100">{rec.generic_name}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold">{rec.recommendation_score}</div>
                    <div className="text-sm">Score</div>
                  </div>
                </div>
              </div>

              <div className="p-6">
                {/* Recommendation Reason */}
                <div className="mb-4 p-3 bg-green-50 border-l-4 border-green-500 rounded">
                  <p className="text-green-800">✓ {rec.reason}</p>
                </div>

                {/* Medicine Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-600">Brand Name</p>
                    <p className="font-semibold text-gray-900">{rec.brand_name || 'Generic'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Manufacturer</p>
                    <p className="font-semibold text-gray-900">{rec.manufacturer}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Strength</p>
                    <p className="font-semibold text-gray-900">{rec.strength}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Form</p>
                    <p className="font-semibold text-gray-900">{rec.form}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Price</p>
                    <p className="font-semibold text-gray-900">₹{rec.selling_price}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Use Case</p>
                    <p className="font-semibold text-gray-900">{rec.use_case}</p>
                  </div>
                </div>

                {/* Dosage Information */}
                {rec.dosage && (
                  <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
                    <p className="font-semibold text-gray-900 mb-2">Dosage Recommendation:</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                      <div>
                        <p className="text-gray-600">Amount</p>
                        <p className="font-semibold">{rec.dosage.dosage_amount} {rec.dosage.dosage_unit}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Frequency</p>
                        <p className="font-semibold">{rec.dosage.frequency}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Duration</p>
                        <p className="font-semibold">{rec.dosage.duration_days} days</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Age Group</p>
                        <p className="font-semibold">{rec.dosage.patient_age}y</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Drug Cycle */}
                {rec.cycle_info && (
                  <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded">
                    <p className="font-semibold text-gray-900 mb-2">Drug Cycle Information:</p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-gray-600">Type: {rec.cycle_info.type}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Duration: {rec.cycle_info.standard_cycle} days</p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-gray-700">📌 <strong>{rec.cycle_info.notes}</strong></p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Similar Past Cases */}
      {similarCases && similarCases.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            📋 Similar Past Cases
          </h2>

          <div className="space-y-3">
            {similarCases.map((caseItem, index) => (
              <div key={index} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-gray-900">{caseItem.diagnosis}</h3>
                  <span className="text-xs text-gray-500">{new Date(caseItem.date).toLocaleDateString()}</span>
                </div>
                <p className="text-sm text-gray-600 mb-2">Doctor: {caseItem.doctor}</p>
                <p className="text-sm font-medium text-gray-700 mb-2">Previous Treatment:</p>
                <ul className="space-y-1">
                  {caseItem.medicines.map((med, i) => (
                    <li key={i} className="text-sm text-gray-600">
                      • <strong>{med.name}</strong> - {med.dosage} {med.frequency} for {med.duration}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
