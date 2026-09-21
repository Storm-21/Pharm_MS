import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  KeyRound,
  Upload,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Store,
  Image as ImageIcon,
  ExternalLink,
} from 'lucide-react';
import { apiClient, API_BASE_URL } from '../api';

/**
 * Branding panel.
 *
 * Replacing the product name and logo is gated behind a licence key issued
 * against the pharmacy's exact name. Until a valid key is entered, the fields
 * are locked and the application keeps its shipped identity.
 */
export function BrandingSettings() {
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const [nameInput, setNameInput] = useState('');
  const [keyInput, setKeyInput] = useState('');
  const [profile, setProfile] = useState({
    pharmacy_address: '',
    pharmacy_phone: '',
    pharmacy_email: '',
    pharmacy_registration_no: '',
    pharmacy_gstin: '',
    pharmacist_name: '',
    prescription_footer: '',
    prescriber_name: '',
    prescriber_qualifications: '',
    prescriber_registration_no: '',
    prescriber_contact: '',
    pharmacist_registration_no: '',
  });

  const fileRef = useRef(null);
  const [logoStamp, setLogoStamp] = useState(Date.now());

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getBranding();
      if (res && res.success) {
        setBranding(res.data);
        setProfile({
          pharmacy_address: res.data.pharmacy_address || '',
          pharmacy_phone: res.data.pharmacy_phone || '',
          pharmacy_email: res.data.pharmacy_email || '',
          pharmacy_registration_no: res.data.pharmacy_registration_no || '',
          pharmacy_gstin: res.data.pharmacy_gstin || '',
          pharmacist_name: res.data.pharmacist_name || '',
          prescription_footer: res.data.prescription_footer || '',
          prescriber_name: res.data.prescriber_name || '',
          prescriber_qualifications: res.data.prescriber_qualifications || '',
          prescriber_registration_no: res.data.prescriber_registration_no || '',
          prescriber_contact: res.data.prescriber_contact || '',
          pharmacist_registration_no: res.data.pharmacist_registration_no || '',
        });
        setLogoStamp(Date.now());
      }
    } catch (err) {
      setError('Could not load branding settings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (label, fn, successMessage) => {
    setBusy(label);
    setMessage(null);
    setError(null);
    try {
      const res = await fn();
      if (res && res.success === false) {
        setError(res.error || 'That did not work.');
      } else {
        setMessage(successMessage || (res && res.message) || 'Saved.');
      }
      await load();
      return res;
    } catch (err) {
      setError('Request failed. Is the backend running?');
    } finally {
      setBusy(null);
    }
  };

  const activate = async (e) => {
    e.preventDefault();
    const res = await run(
      'licence',
      () => apiClient.activateLicence(nameInput.trim(), keyInput.trim()),
      null
    );
    if (res && res.success) {
      setMessage(res.message);
      setNameInput('');
      setKeyInput('');
    }
  };

  const saveProfile = (e) => {
    e.preventDefault();
    run('profile', () => apiClient.updateProfile(profile), 'Pharmacy details saved.');
  };

  const uploadLogo = (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    run('logo', () => apiClient.uploadLogo(file), 'Logo uploaded.');
    event.target.value = '';
  };

  const removeLogo = () => {
    if (!window.confirm('Remove the custom logo and revert to the default?')) return;
    run('logo-remove', () => apiClient.deleteLogo(), 'Custom logo removed.');
  };

  const deactivate = () => {
    const confirmed = window.confirm(
      'Remove the licence key?\n\nThe application will revert to its original name\n' +
      'and logo. Your patient data is not affected.'
    );
    if (!confirmed) return;
    run('deactivate', () => apiClient.clearLicence(), 'Licence removed.');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-gray-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading branding...
      </div>
    );
  }

  const licensed = branding && branding.licensed;
  const field = (key, label, placeholder) => (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <input
        value={profile[key]}
        onChange={(e) => setProfile({ ...profile, [key]: e.target.value })}
        placeholder={placeholder}
        disabled={!licensed}
        className="w-full rounded-lg border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-400"
      />
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Pharmacy branding</h1>
        <p className="mt-1 text-sm text-gray-600">
          Put your own pharmacy name, logo and details on the application and on
          every printed prescription.
        </p>
      </div>

      {message && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-emerald-500 bg-emerald-50 p-4">
          <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-600" />
          <p className="text-sm text-emerald-800">{message}</p>
        </div>
      )}
      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Status banner */}
      <div
        className={`rounded-lg p-4 ring-1 ${licensed
            ? 'bg-emerald-50 text-emerald-900 ring-emerald-200'
            : 'bg-amber-50 text-amber-900 ring-amber-200'
          }`}
      >
        <div className="flex items-start gap-3">
          {licensed ? (
            <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0" />
          ) : (
            <Lock className="mt-0.5 h-5 w-5 flex-shrink-0" />
          )}
          <div className="text-sm">
            <p className="font-semibold">
              {licensed ? 'Branding unlocked' : 'Branding locked'}
            </p>
            <p className="mt-0.5">
              {licensed ? (
                <>
                  This copy is licensed to <strong>{branding.pharmacy_name}</strong>.
                  {branding.licence_key_masked && (
                    <span className="ml-1 text-emerald-700">
                      Key {branding.licence_key_masked}
                    </span>
                  )}
                </>
              ) : (
                <>
                  Showing the default product identity. Enter your licence key below
                  to replace it with your pharmacy name and logo.
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* --- Activation ---------------------------------------------------- */}
      {!licensed && (
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-800">
            <KeyRound className="h-5 w-5 text-blue-500" /> Activate your licence
          </h2>
          <p className="mb-4 text-sm text-gray-600">
            A licence key unlocks your own pharmacy name and logo. It is a{' '}
            <strong>one-time &#8377;{branding ? branding.price_inr : 500}</strong> fee and the
            key is bound to your exact pharmacy name.
          </p>

          <form onSubmit={activate} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Your pharmacy name *
              </label>
              <input
                required
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                placeholder="e.g. Sri Balaji Medicals"
                className="w-full rounded-lg border-gray-300 px-3 py-2"
              />
              <p className="mt-1 text-xs text-gray-500">
                Enter it exactly as you want it printed. Capitalisation and spacing
                are ignored during checking.
              </p>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Licence key *
              </label>
              <input
                required
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                placeholder={branding ? branding.key_format : 'PMS-XXXX-XXXX-XXXX-XXXX'}
                className="w-full rounded-lg border-gray-300 px-3 py-2 font-mono tracking-wide"
              />
            </div>
            <button
              type="submit"
              disabled={busy === 'licence'}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy === 'licence' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <KeyRound className="h-4 w-4" />
              )}
              Activate licence
            </button>
          </form>

          <div className="mt-5 rounded-lg bg-gray-50 p-4">
            <p className="flex items-start gap-2 text-xs text-gray-600">
              <ExternalLink className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
              <span>
                Need a key? Request one with your pharmacy name at the project site.
                Keys are issued manually and verified offline, so the application
                never needs an internet connection.
              </span>
            </p>
          </div>
        </div>
      )}

      {/* --- Logo ---------------------------------------------------------- */}
      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-800">
          <ImageIcon className="h-5 w-5 text-gray-500" /> Logo
        </h2>
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-xl border bg-gray-50">
            <img
              src={`${API_BASE_URL}/branding/logo?v=${logoStamp}`}
              alt="Pharmacy logo"
              className="h-20 w-20 object-contain"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-600">
              {branding && branding.has_custom_logo
                ? 'Your custom logo is in use.'
                : 'The default logo is shown. Upload your own to replace it.'}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              PNG, JPG, SVG or WEBP, up to 2 MB. A square image around 512&times;512 px
              gives the best result on printed prescriptions.
            </p>
            <div className="mt-3 flex-wrap gap-2">
              <label
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm text-white ${licensed
                    ? 'cursor-pointer bg-blue-600 hover:bg-blue-700'
                    : 'cursor-not-allowed bg-gray-300'
                  }`}
              >
                {busy === 'logo' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                Upload logo
                <input
                  ref={fileRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.svg,.webp"
                  className="hidden"
                  disabled={!licensed}
                  onChange={uploadLogo}
                />
              </label>
              {branding && branding.has_custom_logo && (
                <button
                  onClick={removeLogo}
                  disabled={busy === 'logo-remove'}
                  className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700 hover:bg-red-100 disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" /> Remove
                </button>
              )}
            </div>
            {!licensed && (
              <p className="mt-2 flex items-center gap-1 text-xs text-amber-700">
                <Lock className="h-3 w-3" /> Activate a licence key to upload a logo.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* --- Prescription header details ----------------------------------- */}
      <form onSubmit={saveProfile} className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-800">
          <Store className="h-5 w-5 text-gray-500" /> Letterhead details
        </h2>
        <p className="mb-4 text-sm text-gray-600">
          These appear at the top of every printed prescription and patient report.
        </p>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {field('pharmacy_address', 'Address', '12 MG Road, Pune 411001')}
          {field('pharmacy_phone', 'Phone', '020-2345 6789')}
          {field('pharmacy_email', 'Email', 'contact@pharmacy.in')}
          {field('pharmacy_registration_no', 'Drug licence number', 'MH-PN-20B-12345')}
          {field('pharmacy_gstin', 'GSTIN', '27ABCDE1234F1Z5')}
          {field('pharmacist_name', 'Pharmacist in charge', 'Name, qualification')}
        </div>

        <h3 className="mb-2 mt-6 text-sm font-semibold text-gray-700">
          Prescriber details (printed on the prescription)
        </h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {field('prescriber_name', 'Prescriber name', 'Dr. A. Sharma, MBBS, MD')}
          {field('prescriber_qualifications', 'Qualifications', 'MBBS, MD (General Medicine)')}
          {field('prescriber_registration_no', 'Medical registration number', 'MCI-123456')}
          {field('prescriber_contact', 'Prescriber contact', '020-2345 6789 / doc@clinic.in')}
          {field('pharmacist_registration_no', 'Pharmacist registration number', 'DPharm-98765')}
        </div>

        <div className="mt-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Prescription footer note
          </label>
          <textarea
            rows="2"
            value={profile.prescription_footer}
            onChange={(e) =>
              setProfile({ ...profile, prescription_footer: e.target.value })
            }
            placeholder="e.g. Keep all medicines out of reach of children. Store in a cool dry place."
            disabled={!licensed}
            className="w-full rounded-lg border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50"
          />
        </div>

        <button
          type="submit"
          disabled={!licensed || busy === 'profile'}
          className="mt-4 flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {busy === 'profile' && <Loader2 className="h-4 w-4 animate-spin" />}
          Save details
        </button>
        {!licensed && (
          <p className="mt-2 flex items-center gap-1 text-xs text-amber-700">
            <Lock className="h-3 w-3" /> Activate a licence key to edit these.
          </p>
        )}
      </form>

      {licensed && (
        <div className="rounded-lg border-gray-200 bg-gray-50 p-4">
          <button
            onClick={deactivate}
            disabled={busy === 'deactivate'}
            className="text-sm text-gray-600 underline hover:text-red-700"
          >
            Remove licence and revert to default branding
          </button>
        </div>
      )}
    </div>
  );
}

export default BrandingSettings;
