import React, { useCallback, useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navigation } from './components/Navigation';
import { SplashScreen, TamperNotice } from './components/SplashScreen';
import { DashboardPage } from './pages/Dashboard';
import { MedicineDatabase } from './pages/MedicineDatabase';
import { DosageCalculator } from './pages/DosageCalculator';
import { MedicineRecommender } from './pages/MedicineRecommender';
import { InventoryManagement } from './pages/InventoryManagement';
import { PatientManagement } from './pages/PatientManagement';
import { PrescriptionManagement } from './pages/PrescriptionManagement';
import { AlternativeMedicines } from './pages/AlternativeMedicines';
import { DataStorage } from './pages/DataStorage';
import { BrandingSettings } from './pages/BrandingSettings';
import { ClinicalWorkbench } from './pages/ClinicalWorkbench';
import { apiClient } from './api';
import './App.css';

// The splash shows once per browser session, not on every route change.
const SPLASH_KEY = 'pharms.splash.shown';

function App() {
  const [branding, setBranding] = useState(null);
  const [showSplash, setShowSplash] = useState(true);
  const [tamperAcknowledged, setTamperAcknowledged] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // Merge the product identity (creator, integrity) with the pharmacy
    // branding (licensed name/logo), so one object drives the splash and nav.
    Promise.allSettled([apiClient.getBranding(), apiClient.getPharmacyBranding()])
      .then(([identityRes, pharmacyRes]) => {
        if (cancelled) return;
        const identity =
          identityRes.status === 'fulfilled' && identityRes.value && identityRes.value.success
            ? identityRes.value.data
            : null;
        const pharmacy =
          pharmacyRes.status === 'fulfilled' && pharmacyRes.value && pharmacyRes.value.success
            ? pharmacyRes.value.data
            : null;

        if (identity || pharmacy) {
          setBranding({ ...(identity || {}), ...(pharmacy || {}) });
          return;
        }

        // Backend unreachable: fall back to local branding so the splash still
        // renders rather than hanging on a blank screen.
        setBranding({
          app_name: 'Pharmacy Management System',
          creator_name: 'Jayant',
          creator_title: 'Creator & Lead Developer',
          integrity_ok: true,
          offline: true,
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined' && sessionStorage.getItem(SPLASH_KEY) === '1') {
      setShowSplash(false);
    }
  }, []);

  const finishSplash = useCallback(() => {
    if (typeof window !== 'undefined') sessionStorage.setItem(SPLASH_KEY, '1');
    setShowSplash(false);
  }, []);

  const identityTampered = branding && branding.integrity_ok === false;

  // A failed identity check replaces the splash with a blocking notice.
  if (identityTampered && !tamperAcknowledged) {
    return (
      <TamperNotice
        branding={branding}
        onContinue={() => setTamperAcknowledged(true)}
      />
    );
  }

  if (showSplash) {
    return <SplashScreen branding={branding} onFinish={finishSplash} />;
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navigation branding={branding} />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/workbench" element={<ClinicalWorkbench />} />
            <Route path="/medicines" element={<MedicineDatabase />} />
            <Route path="/dosage" element={<DosageCalculator />} />
            <Route path="/recommender" element={<MedicineRecommender />} />
            <Route path="/alternatives" element={<AlternativeMedicines />} />
            <Route path="/inventory" element={<InventoryManagement />} />
            <Route path="/patients" element={<PatientManagement />} />
            <Route path="/patients/:patientId" element={<PatientManagement />} />
            <Route path="/prescriptions" element={<PrescriptionManagement />} />
            <Route path="/data" element={<DataStorage />} />
            <Route path="/branding" element={<BrandingSettings />} />
          </Routes>
        </main>
        <footer className="border-t border-gray-200 bg-white py-4">
          <p className="text-center text-xs text-gray-500">
            {branding?.app_name || 'Pharmacy Management System'}
            {branding?.app_version ? ` v${branding.app_version}` : ''} &nbsp;&middot;&nbsp;
            {branding?.attribution || 'Designed & Developed by Jayant'}
          </p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
