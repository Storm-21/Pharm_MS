import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Pill, Users, FileText, Package, Brain, Menu, X, Calculator, GitCompare, Database,
  Store, Stethoscope,
} from 'lucide-react';

export function Navigation({ branding }) {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Pill },
    { path: '/workbench', label: 'Workbench', icon: Stethoscope },
    { path: '/medicines', label: 'Medicine Database', icon: Pill },
    { path: '/patients', label: 'Patients', icon: Users },
    { path: '/prescriptions', label: 'Prescriptions', icon: FileText },
    { path: '/inventory', label: 'Inventory', icon: Package },
    { path: '/dosage', label: 'Dosage', icon: Calculator },
    { path: '/recommender', label: 'Recommender', icon: Brain },
    { path: '/alternatives', label: 'Alternatives', icon: GitCompare },
    { path: '/data', label: 'Data', icon: Database },
    { path: '/branding', label: 'Branding', icon: Store },
  ];

  // Treat /patients/7 as an active "Patients" tab.
  const isActivePath = (path) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  return (
    <nav className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center gap-2">
            <Pill className="w-8 h-8" />
            <span className="text-2xl font-bold">
              {branding?.app_short_name || 'PharmMS'}
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden xl:flex gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = isActivePath(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-3 py-2 rounded transition ${isActive ? 'bg-white bg-opacity-20' : 'hover:bg-white hover:bg-opacity-10'
                    }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Mobile Menu Button */}
          <button className="xl:hidden" onClick={() => setIsOpen(!isOpen)} aria-label="Toggle menu">
            {isOpen ? <X /> : <Menu />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="xl:hidden pb-4 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = isActivePath(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-3 py-2 rounded transition block ${isActive ? 'bg-white bg-opacity-20' : 'hover:bg-white hover:bg-opacity-10'
                    }`}
                  onClick={() => setIsOpen(false)}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </nav>
  );
}
