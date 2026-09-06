import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Flame,
  Map as MapIcon,
  Home,
  LayoutGrid,
  BarChart2,
  FileText,
  ChevronDown,
  CalendarDays,
  Check,
  AlertCircle,
  AlertTriangle,
  Info,
  X,
  Bell,
  LogIn,
  UserPlus,
  LogOut,
  Menu
} from 'lucide-react';
import { useMapStore } from '../store/mapStore';
import { useAlertsQuery } from '../services/queries/useAlertsQuery';
import type { AlertSeverity, Alert } from '../types/alert';
import { AuthModal } from './AuthModal';
import { getStoredUser, logout as apiLogout, User } from '../services/authService';

import { getRollingISTDates, formatISTDateLabel } from '../utils/dateUtils';

interface NavItem {
  label: string;
  path: string;
  Icon: React.ElementType;
  badge?: string;
}

function formatDateDisplay(isoDate: string): string {
  if (!isoDate) return '';
  return formatISTDateLabel(isoDate, true);
}

export default function Navbar(): React.JSX.Element {
  const navigate = useNavigate();
  const datesList = getRollingISTDates(7);
  const selectedDate = useMapStore((s) => s.selectedDate);
  const setSelectedDate = useMapStore((s) => s.setSelectedDate);
  const selectHotspot = useMapStore((s) => s.selectHotspot);
  const selectFacility = useMapStore((s) => s.selectFacility);

  const [isDatePickerOpen, setIsDatePickerOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(getStoredUser());
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const datePickerRef = useRef<HTMLDivElement>(null);
  const alertsRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  const handleOpenAuth = (mode: 'login' | 'signup') => {
    setAuthMode(mode);
    setIsAuthModalOpen(true);
    setIsMobileMenuOpen(false);
  };

  const handleLogout = async () => {
    await apiLogout();
    setCurrentUser(null);
    setIsUserMenuOpen(false);
    setIsMobileMenuOpen(false);
  };

  const { data: alerts, isLoading: alertsLoading } = useAlertsQuery();
  const unackCount = alerts?.filter((a) => !a.acknowledged).length ?? alerts?.length ?? 6;

  const navItems: NavItem[] = [
    { label: 'Live Map', path: '/', Icon: MapIcon },
    { label: 'Incidents', path: '/incidents', Icon: Home },
    { label: 'Facilities', path: '/facilities', Icon: LayoutGrid },
    { label: 'Analytics', path: '/analytics', Icon: BarChart2 },
    { label: 'Reports', path: '/reports', Icon: FileText },
  ];

  // Close popovers on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (datePickerRef.current && !datePickerRef.current.contains(event.target as Node)) {
        setIsDatePickerOpen(false);
      }
      if (alertsRef.current && !alertsRef.current.contains(event.target as Node)) {
        setIsAlertsOpen(false);
      }
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(event.target as Node)) {
        setIsMobileMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSelectDate = (isoDate: string) => {
    setSelectedDate(isoDate);
    setIsDatePickerOpen(false);
  };

  const handleAlertClick = (alert: Alert) => {
    if (alert.timestamp) {
      const dateStr = alert.timestamp.slice(0, 10);
      setSelectedDate(dateStr);
    }
    if (alert.hotspotId) {
      selectHotspot(alert.hotspotId);
    }
    if (alert.facilityId) {
      selectFacility(alert.facilityId);
    }
    setIsAlertsOpen(false);
    navigate('/');
  };

  const getAlertIcon = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="w-3.5 h-3.5 text-[#FF4444] shrink-0" />;
      case 'warning':
        return <AlertTriangle className="w-3.5 h-3.5 text-[#F97316] shrink-0" />;
      case 'info':
        return <Info className="w-3.5 h-3.5 text-[#2D7DD2] shrink-0" />;
    }
  };

  return (
    <header className="relative z-40 w-full flex items-center justify-between select-none shrink-0 bg-[#0A0E17] border-b border-[#1e293b] px-3 sm:px-4 h-12">
      {/* Brand Branding */}
      <div className="flex items-center gap-2">
        <div className="flex items-center justify-center rounded-lg w-7 h-7 bg-[rgba(255,68,68,0.12)] border border-[rgba(255,68,68,0.3)] shrink-0">
          <Flame className="w-4 h-4 text-[#FF4444]" />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-xs tracking-wider text-[#E8EDF5] leading-none">
            THERMAL<span className="text-[#FF4444]">TRACE</span>
          </span>
          <span className="hidden sm:block text-[8px] text-[#6B7280] font-mono tracking-tight">
            AI-POWERED GEOSPATIAL THERMAL INTELLIGENCE
          </span>
        </div>
      </div>

      {/* Navigation Tabs (Desktop >= 1024px) */}
      <nav className="hidden lg:flex items-center gap-1">
        {navItems.map((item) => {
          const ItemIcon = item.Icon;
          return (
            <NavLink
              key={item.label}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all ${
                  isActive
                    ? 'text-[#2D7DD2] border-b-2 border-[#2D7DD2] bg-[rgba(45,125,210,0.08)]'
                    : 'text-[#8B9BB4] hover:text-[#E8EDF5] hover:bg-[#111827]'
                }`
              }
            >
              <ItemIcon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
              {item.badge && (
                <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-[#2D7DD2] text-white font-bold ml-0.5">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Right Controls */}
      <div className="flex items-center gap-1.5 sm:gap-2.5">
        {/* Navbar Alert Pill Button & Popover */}
        <div className="relative" ref={alertsRef}>
          <button
            type="button"
            onClick={() => setIsAlertsOpen(!isAlertsOpen)}
            className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 rounded-full text-xs font-semibold bg-[rgba(220,38,38,0.15)] border border-[rgba(220,38,38,0.4)] text-[#FF4444] hover:bg-[rgba(220,38,38,0.25)] transition-all cursor-pointer"
          >
            <Bell className="w-3.5 h-3.5 text-[#FF4444] animate-pulse shrink-0" />
            <span className="hidden sm:inline">{unackCount} Alerts</span>
            <span className="sm:hidden font-mono text-[11px]">{unackCount}</span>
          </button>

          {/* Alert Dropdown Popover */}
          {isAlertsOpen && (
            <div
              className="absolute right-0 top-full mt-1.5 z-50 w-72 sm:w-80 rounded-xl bg-[#111827] border border-[#1e293b] shadow-2xl overflow-hidden py-1"
              style={{ boxShadow: '0 12px 40px rgba(0,0,0,0.9)' }}
            >
              <div className="px-3.5 py-2 border-b border-[#1e293b] flex items-center justify-between bg-[#0F1623]">
                <div className="flex items-center gap-2">
                  <Bell className="w-3.5 h-3.5 text-[#FF4444]" />
                  <span className="text-[11px] font-bold text-[#E8EDF5] tracking-wider uppercase">
                    ACTIVE ALERTS
                  </span>
                  <span className="text-[9px] bg-[#FF4444] text-white px-1.5 py-0.2 rounded-full font-bold">
                    {unackCount}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAlertsOpen(false)}
                  className="text-[#6B7280] hover:text-[#E8EDF5] p-0.5 rounded cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="max-h-80 overflow-y-auto p-2 space-y-1.5 custom-scrollbar">
                {alertsLoading && (
                  <p className="text-center text-[#6B7280] text-xs py-4">Loading active alerts...</p>
                )}
                {!alertsLoading && (!alerts || alerts.length === 0) && (
                  <p className="text-center text-[#6B7280] text-xs py-4">No active thermal alerts.</p>
                )}
                {alerts?.map((alert) => {
                  const d = new Date(alert.timestamp);
                  const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

                  return (
                    <button
                      key={alert.id}
                      type="button"
                      onClick={() => handleAlertClick(alert)}
                      className="w-full text-left p-2.5 rounded-lg bg-[#0D131F] border border-[#1e293b] hover:border-[#2D7DD2] transition-colors cursor-pointer"
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <div className="flex items-center gap-1.5">
                          {getAlertIcon(alert.severity)}
                          <span className="text-[11px] font-semibold text-[#E8EDF5]">
                            {alert.title}
                          </span>
                        </div>
                        <span className="text-[9px] font-mono text-[#6B7280]">{time}</span>
                      </div>
                      <p className="text-[10px] text-[#9CA3AF] line-clamp-2 pl-5">
                        {alert.message}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Date Selector Dropdown Button */}
        <div className="relative" ref={datePickerRef}>
          <button
            type="button"
            onClick={() => setIsDatePickerOpen(!isDatePickerOpen)}
            className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 rounded-lg text-xs font-medium bg-[#111827] border border-[#1e293b] text-[#8B9BB4] hover:text-[#E8EDF5] transition-colors cursor-pointer"
          >
            <CalendarDays className="w-3.5 h-3.5 text-[#2D7DD2] shrink-0" />
            <span className="font-mono text-[11px] font-semibold text-[#E8EDF5]">
              {formatDateDisplay(selectedDate)}
            </span>
            <ChevronDown className="w-3 h-3 text-[#6B7280] shrink-0" />
          </button>

          {/* Date Picker Popover */}
          {isDatePickerOpen && (
            <div
              className="absolute right-0 top-full mt-1.5 z-50 w-44 rounded-xl bg-[#111827] border border-[#1e293b] shadow-2xl overflow-hidden py-1"
              style={{ boxShadow: '0 10px 30px rgba(0,0,0,0.8)' }}
            >
              <div className="px-3 py-1.5 border-b border-[#1e293b] text-[10px] font-bold text-[#6B7280] uppercase tracking-wider flex items-center justify-between">
                <span>SELECT DATE</span>
                <span className="text-[9px] text-[#2D7DD2] font-mono">INDIA</span>
              </div>
              <div className="max-h-48 overflow-y-auto custom-scrollbar">
                {datesList.map((item) => {
                  const isSelected = item.isoDate === selectedDate;
                  return (
                    <button
                      key={item.isoDate}
                      type="button"
                      onClick={() => handleSelectDate(item.isoDate)}
                      className="w-full flex items-center justify-between px-3 py-1.5 text-xs text-left hover:bg-[#1E2D45] transition-colors cursor-pointer"
                      style={{
                        backgroundColor: isSelected ? 'rgba(45,125,210,0.15)' : 'transparent',
                        color: isSelected ? '#2D7DD2' : '#E8EDF5',
                        fontWeight: isSelected ? 600 : 400,
                      }}
                    >
                      <span className="font-mono text-[11px]">{item.label}</span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-[#2D7DD2]" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* User Identity / Authentication State (Desktop) */}
        <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-[#1e293b]">
          {currentUser ? (
            <div className="relative" ref={userMenuRef}>
              <button
                type="button"
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#111827] border border-[#1e293b] hover:border-[#2D7DD2]/50 transition-colors"
              >
                <div className="flex items-center justify-center rounded-full w-6 h-6 bg-[#2D7DD2] text-white font-bold text-[11px] uppercase">
                  {currentUser.name.charAt(0)}
                </div>
                <span className="hidden md:block text-xs font-semibold text-[#E8EDF5]">
                  {currentUser.name}
                </span>
                <ChevronDown className="w-3 h-3 text-[#6B7280]" />
              </button>

              {isUserMenuOpen && (
                <div className="absolute right-0 top-full mt-1.5 w-48 rounded-xl bg-[#111827] border border-[#1e293b] shadow-2xl p-2 z-50 text-xs space-y-1.5">
                  <div className="px-2.5 py-1.5 border-b border-[#1e293b]">
                    <p className="font-bold text-[#E8EDF5] truncate">{currentUser.name}</p>
                    <p className="text-[10px] text-[#7A8FA8] truncate">{currentUser.email}</p>
                    <span className="mt-1 inline-block px-1.5 py-0.5 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-500/30 text-[9px] font-semibold uppercase">
                      Authenticated Analyst
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-red-400 hover:bg-red-950/20 transition-colors font-medium text-xs text-left"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Log Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleOpenAuth('login')}
                className="px-2.5 py-1 bg-[#162033] hover:bg-[#1E2D45] text-[#E8EDF5] border border-[#1E2D45] rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <LogIn className="w-3.5 h-3.5 text-[#2D7DD2]" />
                <span>Log In</span>
              </button>
              <button
                type="button"
                onClick={() => handleOpenAuth('signup')}
                className="px-2.5 py-1 bg-[#2D7DD2] hover:bg-[#2D7DD2]/90 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-md"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Sign Up</span>
              </button>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Menu Toggle Button (< 1024px) */}
        <div className="relative lg:hidden" ref={mobileMenuRef}>
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-1.5 text-[#8B9BB4] hover:text-[#E8EDF5] hover:bg-[#111827] rounded-lg transition-colors border border-[#1e293b]"
            aria-label="Toggle navigation menu"
          >
            {isMobileMenuOpen ? <X className="w-4 h-4 text-[#FF4444]" /> : <Menu className="w-4 h-4 text-[#E8EDF5]" />}
          </button>

          {/* Mobile Navigation Drawer Dropdown */}
          {isMobileMenuOpen && (
            <div className="absolute right-0 top-full mt-2 w-64 rounded-xl bg-[#0D121F] border border-[#1e293b] shadow-2xl p-3 z-50 text-xs space-y-2">
              <div className="px-2 py-1 text-[10px] font-bold text-[#6B7280] uppercase tracking-wider border-b border-[#1e293b]">
                NAVIGATION PAGES
              </div>
              <div className="space-y-1">
                {navItems.map((item) => {
                  const ItemIcon = item.Icon;
                  return (
                    <NavLink
                      key={item.label}
                      to={item.path}
                      end={item.path === '/'}
                      onClick={() => setIsMobileMenuOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                          isActive
                            ? 'text-[#2D7DD2] bg-[#162033] border border-[#2D7DD2]/30'
                            : 'text-[#8B9BB4] hover:text-[#E8EDF5] hover:bg-[#111827]'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2">
                        <ItemIcon className="w-4 h-4" />
                        <span>{item.label}</span>
                      </div>
                      {item.badge && (
                        <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#2D7DD2] text-white font-bold">
                          {item.badge}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </div>

              {/* Mobile User Auth Section */}
              <div className="pt-2 border-t border-[#1e293b]">
                {currentUser ? (
                  <div className="p-2 bg-[#111827] rounded-lg border border-[#1e293b] space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center justify-center rounded-full w-6 h-6 bg-[#2D7DD2] text-white font-bold text-[11px] uppercase">
                        {currentUser.name.charAt(0)}
                      </div>
                      <div className="truncate">
                        <p className="font-bold text-[#E8EDF5] truncate">{currentUser.name}</p>
                        <p className="text-[10px] text-[#7A8FA8] truncate">{currentUser.email}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="w-full flex items-center justify-center gap-1.5 py-1 bg-red-950/40 border border-red-500/30 text-red-400 rounded-md font-semibold text-[11px]"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Log Out</span>
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => handleOpenAuth('login')}
                      className="py-1.5 bg-[#162033] hover:bg-[#1E2D45] text-[#E8EDF5] border border-[#1E2D45] rounded-lg font-semibold flex items-center justify-center gap-1 transition-colors"
                    >
                      <LogIn className="w-3.5 h-3.5 text-[#2D7DD2]" />
                      <span>Log In</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleOpenAuth('signup')}
                      className="py-1.5 bg-[#2D7DD2] hover:bg-[#2D7DD2]/90 text-white rounded-lg font-semibold flex items-center justify-center gap-1 transition-colors shadow-md"
                    >
                      <UserPlus className="w-3.5 h-3.5" />
                      <span>Sign Up</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <AuthModal
        isOpen={isAuthModalOpen}
        initialMode={authMode}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={(user) => {
          setCurrentUser(user);
        }}
      />
    </header>
  );
}
