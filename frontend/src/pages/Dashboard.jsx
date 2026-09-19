import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp,
  AlertCircle,
  Package,
  Clock,
  ShieldCheck,
  ShieldAlert,
  IndianRupee,
  Pill,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { apiClient } from '../api';

/**
 * Operational dashboard: counts, stock alerts and integrity status only.
 * The previous version carried large self-promotional feature lists, which have
 * been removed in favour of information a pharmacist actually acts on.
 */
export function DashboardPage() {
  const [stats, setStats] = useState({
    totalMedicines: 0,
    totalPatients: 0,
    lowStockItems: 0,
    expiredItems: 0,
    outOfStock: 0,
  });
  const [alerts, setAlerts] = useState([]);
  const [integrity, setIntegrity] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [medicinesRes, patientsRes, alertsRes, integrityRes] = await Promise.all([
          apiClient.getMedicines(),
          apiClient.getPatients(),
          apiClient.getStockAlerts(),
          apiClient.verifyIntegrity().catch(() => null),
        ]);
        if (cancelled) return;

        const alertList = (alertsRes && alertsRes.data) || [];
        setAlerts(alertList);
        setStats({
          totalMedicines: (medicinesRes && medicinesRes.data && medicinesRes.data.length) || 0,
          totalPatients: (patientsRes && patientsRes.data && patientsRes.data.length) || 0,
          lowStockItems: alertList.filter((a) => a.type === 'LOW_STOCK').length,
          expiredItems: alertList.filter((a) => a.type === 'EXPIRED').length,
          outOfStock: alertList.filter((a) => a.type === 'OUT_OF_STOCK').length,
        });
        if (integrityRes && integrityRes.data) setIntegrity(integrityRes.data);
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-gray-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading dashboard...
      </div>
    );
  }

  const cards = [
    {
      label: 'Medicines on file',
      value: stats.totalMedicines,
      icon: Package,
      className: 'from-blue-500 to-blue-600',
      to: '/medicines',
    },
    {
      label: 'Registered patients',
      value: stats.totalPatients,
      icon: TrendingUp,
      className: 'from-green-500 to-green-600',
      to: '/patients',
    },
    {
      label: 'Low stock lines',
      value: stats.lowStockItems + stats.outOfStock,
      icon: AlertCircle,
      className: 'from-yellow-500 to-yellow-600',
      to: '/inventory',
    },
    {
      label: 'Expired batches',
      value: stats.expiredItems,
      icon: Clock,
      className: 'from-red-500 to-red-600',
      to: '/inventory',
    },
  ];

  const integrityOk = integrity ? integrity.ok : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-bold text-gray-800">Dashboard</h1>
        {integrity && (
          <div
            className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ring-1 ${integrityOk
                ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                : 'bg-red-50 text-red-700 ring-red-200'
              }`}
          >
            {integrityOk ? (
              <ShieldCheck className="h-3.5 w-3.5" />
            ) : (
              <ShieldAlert className="h-3.5 w-3.5" />
            )}
            {integrityOk
              ? `Reference data verified (${integrity.counts.INTACT || 0} records)`
              : `${integrity.compromised?.length || 0} record(s) failed integrity check`}
          </div>
        )}
      </div>

      {/* Stat cards - each links to the relevant screen */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <Link
              key={card.label}
              to={card.to}
              className={`bg-gradient-to-br ${card.className} rounded-lg shadow-lg p-6 text-white transition hover:shadow-xl`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-white/80 text-sm">{card.label}</p>
                  <p className="text-4xl font-bold">{card.value}</p>
                </div>
                <Icon className="w-8 h-8 text-white/70" />
              </div>
            </Link>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Stock alerts */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow">
          <div className="flex items-center justify-between border-b px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-800">Stock alerts</h2>
            <Link
              to="/inventory"
              className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
            >
              Open inventory <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          {alerts.length === 0 ? (
            <p className="px-6 py-10 text-center text-sm text-gray-500">
              No stock alerts. All lines are above their reorder level and unexpired.
            </p>
          ) : (
            <ul className="divide-y">
              {alerts.slice(0, 8).map((alert, index) => (
                <li key={`${alert.type}-${index}`} className="flex items-center justify-between px-6 py-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{alert.medicine_name}</p>
                    <p className="text-xs text-gray-500">
                      {alert.type === 'LOW_STOCK' &&
                        `${alert.current_stock} in stock (reorder at ${alert.reorder_level})`}
                      {alert.type === 'OUT_OF_STOCK' && 'No stock remaining'}
                      {alert.type === 'EXPIRED' && `Expired ${alert.expiry_date}`}
                    </p>
                  </div>
                  <span
                    className={`rounded px-2 py-1 text-xs font-semibold ${alert.urgency === 'HIGH'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                      }`}
                  >
                    {alert.urgency}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Quick actions */}
        <div className="bg-white rounded-lg shadow">
          <div className="border-b px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-800">Quick actions</h2>
          </div>
          <div className="space-y-1 p-3">
            {[
              { to: '/prescriptions', label: 'Write a prescription', icon: ArrowRight },
              { to: '/dosage', label: 'Calculate a dosage', icon: ArrowRight },
              { to: '/recommender', label: 'Screen a patient', icon: ArrowRight },
              { to: '/alternatives', label: 'Find alternative medicines', icon: ArrowRight },
              { to: '/medicines', label: 'Look up a medicine', icon: ArrowRight },
              { to: '/inventory', label: 'Receive stock', icon: ArrowRight },
              { to: '/data', label: 'Back up your data', icon: ArrowRight },
            ].map((action) => (
              <Link
                key={action.to + action.label}
                to={action.to}
                className="flex items-center justify-between rounded px-3 py-2.5 text-sm text-gray-700 transition hover:bg-gray-50"
              >
                <span className="flex items-center gap-2">
                  <Pill className="h-4 w-4 text-blue-500" />
                  {action.label}
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-gray-400" />
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Inventory value summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">At a glance</h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-lg bg-gray-50 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">In stock</p>
            <p className="text-2xl font-bold text-gray-800">
              {Math.max(0, stats.totalMedicines - 0)}
            </p>
            <p className="text-xs text-gray-500">medicine lines</p>
          </div>
          <div className="rounded-lg bg-gray-50 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Out of stock</p>
            <p className="text-2xl font-bold text-red-600">{stats.outOfStock}</p>
            <p className="text-xs text-gray-500">lines to reorder</p>
          </div>
          <div className="rounded-lg bg-gray-50 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Total alerts</p>
            <p className="text-2xl font-bold text-yellow-600">{alerts.length}</p>
            <p className="text-xs text-gray-500">need attention</p>
          </div>
          <div className="rounded-lg bg-gray-50 p-4">
            <p className="flex items-center gap-1 text-xs uppercase tracking-wide text-gray-500">
              <IndianRupee className="h-3 w-3" /> Currency
            </p>
            <p className="text-2xl font-bold text-gray-800">INR</p>
            <p className="text-xs text-gray-500">all prices</p>
          </div>
        </div>
      </div>
    </div>
  );
}
