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
    <nav className="bg-gradient-to-r from-blue-700 via-purple-600 to-indigo-700 text-white shadow-lg relative z-50">
      <div className="max-w-screen-2xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-white/15 backdrop-blur-sm border border-white/20 group-hover:bg-white/25 transition-all duration-300">
              <Pill className="w-5 h-5 text-cyan-300" />
            </div>
            <span className="text-xl font-bold tracking-tight">
              {branding?.app_short_name || 'PharmMS'}
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden xl:flex items-center gap-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = isActivePath(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-white/20 text-white shadow-sm'
                      : 'text-white/80 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Mobile Menu Button */}
          <button className="xl:hidden p-2 rounded-lg text-white/80 hover:bg-white/10 transition-all duration-200" onClick={() => setIsOpen(!isOpen)} aria-label="Toggle menu">
            {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="xl:hidden pb-4 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = isActivePath(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-white/20 text-white'
                      : 'text-white/80 hover:bg-white/10 hover:text-white'
                  }`}
                  onClick={() => setIsOpen(false)}
                >
                  <Icon className="w-5 h-5" />
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
