import React, { useCallback, useEffect, useState } from 'react';
import {
  Search,
  Plus,
  Eye,
  Edit,
  Trash2,
  Loader2,
  AlertTriangle,
  ShieldCheck,
  X,
  FlaskConical,
  Factory,
  BookOpen,
} from 'lucide-react';
import { apiClient } from '../api';

const EMPTY_MEDICINE = {
  name: '',
  generic_name: '',
  brand_name: '',
  manufacturer: '',
  manufacturer_country: '',
  manufacturer_site: '',
  manufacturer_licence_no: '',
  marketed_by: '',
  country_origin: '',
  salt_composition: '',
  molecular_formula: '',
  chemical_formula_weight: '',
  strength: '',
  form: 'tablet',
  route_of_administration: '',
  therapeutic_class: '',
  pharmacological_class: '',
  use_case: '',
  mechanism_of_action: '',
  side_effects: '',
  contraindications: '',
  warnings: '',
  drug_interactions: '',
  food_interactions: '',
  pregnancy_category: '',
  onset_of_action: '',
  half_life: '',
  bioavailability: '',
  protein_binding: '',
  metabolism: '',
  excretion: '',
  max_daily_dose: '',
  indian_pharmacopoeia_ref: '',
  global_pharmacopoeia_ref: '',
  pharmacopoeia_monograph: '',
  ip_status: '',
  schedule_classification: '',
  hsn_code: '',
  gst_rate: '',
  barcode: '',
  cost_price: '',
  selling_price: '',
  requires_prescription: true,
  storage_temp: '',
};

/* Small presentational helpers, defined at module scope so they keep a stable
   identity across renders of MedicineDetail. */
function DetailSection({ title, icon: Icon, children }) {
  return (
    <section className="border-t pt-4">
      <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
        {Icon && <Icon className="h-4 w-4" />}
        {title}
      </h4>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm md:grid-cols-2">{children}</dl>
    </section>
  );
}

function DetailField({ label, value, wide }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div className={wide ? 'md:col-span-2' : ''}>
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-gray-900">{value}</dd>
    </div>
  );
}

/** Sectioned read-only view of one medicine, covering every stored field. */
function MedicineDetail({ medicine, onClose, onEdit }) {
  const Section = DetailSection;
  const Field = DetailField;

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/40" onClick={onClose}>
      <div
        className="h-full w-full max-w-3xl overflow-y-auto bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-start justify-between border-b bg-white px-6 py-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{medicine.name}</h2>
            <p className="text-sm text-gray-500">
              {medicine.generic_name}
              {medicine.brand_name ? ` \u00b7 ${medicine.brand_name}` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onEdit(medicine)}
              className="flex items-center gap-1 rounded bg-blue-50 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-100"
            >
              <Edit className="h-3.5 w-3.5" /> Edit
            </button>
            <button onClick={onClose} className="rounded p-1 hover:bg-gray-100">
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        <div className="space-y-5 p-6">
          {/* Integrity badge for this record */}
          {medicine.record_hash && (
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
              <ShieldCheck className="h-3.5 w-3.5" /> Sealed record
            </div>
          )}

          <Section title="Identity">
            <Field label="Brand name" value={medicine.brand_name} />
            <Field label="Strength" value={medicine.strength} />
            <Field label="Dosage form" value={medicine.form} />
            <Field label="Route" value={medicine.route_of_administration} />
            <Field label="Prescription required" value={medicine.requires_prescription ? 'Yes' : 'No'} />
            <Field label="Storage" value={medicine.storage_temp} />
          </Section>

          <Section title="Composition & chemistry" icon={FlaskConical}>
            <Field label="Salt composition" value={medicine.salt_composition} wide />
            <Field label="Molecular formula" value={medicine.molecular_formula} />
            <Field label="Formula weight" value={medicine.chemical_formula_weight} />
            <Field label="Therapeutic class" value={medicine.therapeutic_class} />
            <Field label="Pharmacological class" value={medicine.pharmacological_class} />
          </Section>

          <Section title="Manufacturer" icon={Factory}>
            <Field label="Manufacturer" value={medicine.manufacturer} />
            <Field label="Manufacturing site" value={medicine.manufacturer_site} />
            <Field label="Licence number" value={medicine.manufacturer_licence_no} />
            <Field label="Marketed by" value={medicine.marketed_by} />
            <Field label="Manufacturer country" value={medicine.manufacturer_country} />
            <Field label="Country of origin" value={medicine.country_origin} />
          </Section>

          <Section title="Pharmacopoeia references" icon={BookOpen}>
            <Field label="Indian Pharmacopoeia" value={medicine.indian_pharmacopoeia_ref} wide />
            <Field label="Global pharmacopoeia" value={medicine.global_pharmacopoeia_ref} wide />
            <Field label="IP status" value={medicine.ip_status} wide />
            <Field label="Monograph notes" value={medicine.pharmacopoeia_monograph} wide />
          </Section>

          <Section title="Clinical use">
            <Field label="Indications" value={medicine.use_case} wide />
            <Field label="Mechanism of action" value={medicine.mechanism_of_action} wide />
            <Field label="Side effects" value={medicine.side_effects} wide />
            <Field label="Contraindications" value={medicine.contraindications} wide />
            <Field label="Warnings" value={medicine.warnings} wide />
            <Field label="Drug interactions" value={medicine.drug_interactions} wide />
            <Field label="Food interactions" value={medicine.food_interactions} wide />
            <Field label="Pregnancy category" value={medicine.pregnancy_category} wide />
          </Section>

          <Section title="Pharmacokinetics">
            <Field label="Onset of action" value={medicine.onset_of_action} />
            <Field label="Half-life" value={medicine.half_life} />
            <Field label="Bioavailability" value={medicine.bioavailability} />
            <Field label="Protein binding" value={medicine.protein_binding} />
            <Field label="Metabolism" value={medicine.metabolism} />
            <Field label="Excretion" value={medicine.excretion} />
            <Field label="Maximum daily dose" value={medicine.max_daily_dose} />
          </Section>

          <Section title="Regulatory & commercial">
            <Field label="Schedule" value={medicine.schedule_classification} />
            <Field label="HSN code" value={medicine.hsn_code} />
            <Field label="GST rate" value={medicine.gst_rate} />
            <Field label="Barcode" value={medicine.barcode} />
            <Field label="Cost price" value={medicine.cost_price != null ? `\u20b9${medicine.cost_price}` : null} />
            <Field label="Selling price" value={medicine.selling_price != null ? `\u20b9${medicine.selling_price}` : null} />
          </Section>

          {medicine.inventory && medicine.inventory.length > 0 && (
            <Section title="Stock on hand">
              <div className="md:col-span-2 overflow-hidden rounded border">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Batch</th>
                      <th className="px-3 py-2 text-center font-semibold text-gray-700">Qty</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Expiry</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Location</th>
                    </tr>
                  </thead>
                  <tbody>
                    {medicine.inventory.map((batch) => (
                      <tr key={batch.id} className="border-t">
                        <td className="px-3 py-2 text-gray-600">{batch.batch_number}</td>
                        <td className="px-3 py-2 text-center font-semibold text-gray-900">
                          {batch.quantity_in_stock}
                        </td>
                        <td className="px-3 py-2 text-gray-600">{batch.expiry_date}</td>
                        <td className="px-3 py-2 text-gray-600">{batch.storage_location}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

export function MedicineDatabase() {
  const [medicines, setMedicines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState(EMPTY_MEDICINE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);

  const fetchMedicines = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.getMedicines(search);
      setMedicines((response && response.data) || []);
      setError(null);
    } catch (err) {
      setError('Could not load medicines. Is the backend running?');
      setMedicines([]);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchMedicines();
  }, [fetchMedicines]);

  const openDetail = async (id) => {
    try {
      const res = await apiClient.getMedicine(id);
      if (res && res.success) setDetail(res.data);
    } catch (err) {
      setError('Could not load that medicine.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await apiClient.updateMedicine(editingId, formData);
      } else {
        await apiClient.createMedicine(formData);
      }
      setShowModal(false);
      setEditingId(null);
      setFormData(EMPTY_MEDICINE);
      await fetchMedicines();
    } catch (err) {
      setError('Could not save the medicine.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (medicine) => {
    const confirmed = window.confirm(
      `Delete "${medicine.name}"?\n\nThis also removes its batches and dosage guides. This cannot be undone.`
    );
    if (!confirmed) return;
    try {
      await apiClient.deleteMedicine(medicine.id);
      if (detail && detail.id === medicine.id) setDetail(null);
      await fetchMedicines();
    } catch (err) {
      setError('Could not delete the medicine.');
    }
  };

  const setField = (key, value) => setFormData((d) => ({ ...d, [key]: value }));

  const textField = (key, label, opts = {}) => (
    <div key={key} className={opts.wide ? 'md:col-span-2' : ''}>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      {opts.textarea ? (
        <textarea
          rows={opts.rows || 2}
          value={formData[key] || ''}
          onChange={(e) => setField(key, e.target.value)}
          className="w-full rounded-lg border-gray-300 px-3 py-2 text-sm"
        />
      ) : (
        <input
          type={opts.type || 'text'}
          value={formData[key] || ''}
          onChange={(e) => setField(key, e.target.value)}
          className="w-full rounded-lg border-gray-300 px-3 py-2 text-sm"
        />
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-gray-800">Medicine database</h1>
        <button
          onClick={() => {
            setEditingId(null);
            setFormData(EMPTY_MEDICINE);
            setShowModal(true);
          }}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" /> Add medicine
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search by name, generic name, or brand..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border-gray-300 py-2 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="overflow-x-auto rounded-lg bg-white shadow">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading medicines...
          </div>
        ) : medicines.length === 0 ? (
          <p className="p-8 text-center text-gray-500">No medicines found.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Name</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Generic</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Formula</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Manufacturer</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Strength</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Price</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {medicines.map((medicine) => (
                <tr key={medicine.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{medicine.name}</td>
                  <td className="px-4 py-3 text-gray-600">{medicine.generic_name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">
                    {medicine.molecular_formula || '\u2014'}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{medicine.manufacturer}</td>
                  <td className="px-4 py-3 text-gray-600">{medicine.strength}</td>
                  <td className="px-4 py-3 font-semibold text-gray-900">
                    {medicine.selling_price != null ? `\u20b9${medicine.selling_price}` : '\u2014'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => openDetail(medicine.id)}
                        className="text-blue-600 hover:text-blue-800"
                        title="View full record"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(medicine.id);
                          setFormData({ ...EMPTY_MEDICINE, ...medicine });
                          setShowModal(true);
                        }}
                        className="text-green-600 hover:text-green-800"
                        title="Edit"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(medicine)}
                        className="text-red-500 hover:text-red-700"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {detail && (
        <MedicineDetail
          medicine={detail}
          onClose={() => setDetail(null)}
          onEdit={(medicine) => {
            setEditingId(medicine.id);
            setFormData({ ...EMPTY_MEDICINE, ...medicine });
            setDetail(null);
            setShowModal(true);
          }}
        />
      )}

      {/* --- Add / edit modal ------------------------------------------------ */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white p-6">
            <h2 className="mb-6 text-2xl font-bold">
              {editingId ? 'Edit medicine' : 'Add new medicine'}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Identity & composition
                </h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {textField('name', 'Medicine name *')}
                  {textField('generic_name', 'Generic name *')}
                  {textField('brand_name', 'Brand name')}
                  {textField('salt_composition', 'Salt composition *')}
                  {textField('molecular_formula', 'Molecular formula')}
                  {textField('chemical_formula_weight', 'Formula weight')}
                  {textField('strength', 'Strength *')}
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Form *</label>
                    <select
                      value={formData.form}
                      onChange={(e) => setField('form', e.target.value)}
                      className="w-full rounded-lg border-gray-300 px-3 py-2 text-sm"
                    >
                      {['tablet', 'capsule', 'syrup', 'injection', 'cream', 'inhaler', 'powder'].map(
                        (f) => (
                          <option key={f}>{f}</option>
                        )
                      )}
                    </select>
                  </div>
                  {textField('route_of_administration', 'Route of administration')}
                  {textField('therapeutic_class', 'Therapeutic class')}
                  {textField('pharmacological_class', 'Pharmacological class')}
                </div>
              </div>

              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Manufacturer
                </h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {textField('manufacturer', 'Manufacturer *')}
                  {textField('manufacturer_site', 'Manufacturing site')}
                  {textField('manufacturer_licence_no', 'Drug licence number')}
                  {textField('marketed_by', 'Marketed by')}
                  {textField('manufacturer_country', 'Manufacturer country')}
                  {textField('country_origin', 'Country of origin')}
                </div>
              </div>

              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Pharmacopoeia
                </h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {textField('indian_pharmacopoeia_ref', 'Indian Pharmacopoeia reference', { wide: true })}
                  {textField('global_pharmacopoeia_ref', 'Global pharmacopoeia reference (BP/USP)', { wide: true })}
                  {textField('ip_status', 'IP status', { wide: true })}
                  {textField('pharmacopoeia_monograph', 'Monograph notes', { textarea: true, wide: true })}
                </div>
              </div>

              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Clinical information
                </h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {textField('use_case', 'Indications / use case *', { textarea: true, wide: true })}
                  {textField('mechanism_of_action', 'Mechanism of action', { textarea: true, wide: true })}
                  {textField('side_effects', 'Side effects', { textarea: true, wide: true })}
                  {textField('contraindications', 'Contraindications', { textarea: true, wide: true })}
                  {textField('warnings', 'Warnings', { textarea: true, wide: true })}
                  {textField('drug_interactions', 'Drug interactions', { textarea: true, wide: true })}
                  {textField('food_interactions', 'Food interactions', { textarea: true, wide: true })}
                  {textField('pregnancy_category', 'Pregnancy category')}
                </div>
              </div>

              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Pharmacokinetics
                </h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {textField('onset_of_action', 'Onset of action')}
                  {textField('half_life', 'Half-life')}
                  {textField('bioavailability', 'Bioavailability')}
                  {textField('protein_binding', 'Protein binding')}
                  {textField('metabolism', 'Metabolism')}
                  {textField('excretion', 'Excretion')}
                  {textField('max_daily_dose', 'Maximum daily dose', { wide: true })}
                </div>
              </div>

              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Regulatory & pricing
                </h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {textField('schedule_classification', 'Schedule classification')}
                  {textField('hsn_code', 'HSN code')}
                  {textField('gst_rate', 'GST rate')}
                  {textField('barcode', 'Barcode')}
                  {textField('cost_price', 'Cost price *', { type: 'number' })}
                  {textField('selling_price', 'Selling price *', { type: 'number' })}
                  {textField('storage_temp', 'Storage conditions')}
                  <div className="flex items-center gap-2 pt-6">
                    <input
                      id="rx"
                      type="checkbox"
                      checked={!!formData.requires_prescription}
                      onChange={(e) => setField('requires_prescription', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <label htmlFor="rx" className="text-sm text-gray-700">
                      Prescription required
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 border-t pt-4">
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
                  {editingId ? 'Update' : 'Add'} medicine
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
