import React, { useState } from 'react';
import { X, LogIn, UserPlus, Eye, EyeOff, Lock, Mail, User as UserIcon, ShieldAlert, Sparkles } from 'lucide-react';
import { login, signup, User } from '../services/authService';

interface AuthModalProps {
  isOpen: boolean;
  initialMode?: 'login' | 'signup';
  notice?: string;
  onClose: () => void;
  onSuccess: (user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  initialMode = 'login',
  notice,
  onClose,
  onSuccess,
}) => {
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === 'signup') {
      if (!name.trim()) {
        setError('Please enter your full name.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setLoading(true);
    try {
      let user: User;
      if (mode === 'login') {
        user = await login(email, password, name.trim() || undefined);
      } else {
        user = await signup(name.trim(), email, password);
      }
      onSuccess(user);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please check your credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-[#111827] border border-[#1E2D45] rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl relative text-[#E8EDF5]">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-[#7A8FA8] hover:text-[#E8EDF5] hover:bg-[#162033] rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Tab Headers */}
        <div className="flex border-b border-[#1E2D45] pb-3">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setError(null);
            }}
            className={`flex-1 text-center py-2 text-sm font-bold flex items-center justify-center gap-2 border-b-2 transition-colors ${
              mode === 'login'
                ? 'border-[#2D7DD2] text-[#2D7DD2]'
                : 'border-transparent text-[#7A8FA8] hover:text-[#E8EDF5]'
            }`}
          >
            <LogIn className="w-4 h-4" />
            <span>Log In</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('signup');
              setError(null);
            }}
            className={`flex-1 text-center py-2 text-sm font-bold flex items-center justify-center gap-2 border-b-2 transition-colors ${
              mode === 'signup'
                ? 'border-[#2D7DD2] text-[#2D7DD2]'
                : 'border-transparent text-[#7A8FA8] hover:text-[#E8EDF5]'
            }`}
          >
            <UserPlus className="w-4 h-4" />
            <span>Sign Up</span>
          </button>
        </div>

        {/* Exploration Limit Notice Banner */}
        {notice && (
          <div className="bg-[#162033] border border-[#2D7DD2]/40 p-3 rounded-xl text-xs text-[#E8EDF5] flex items-center gap-2.5 shadow-md">
            <Sparkles className="w-4 h-4 shrink-0 text-amber-400" />
            <span className="font-medium text-[11px] leading-relaxed">{notice}</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="bg-red-950/30 border border-red-500/30 p-3 rounded-xl text-xs text-red-300 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-[10px] font-bold text-[#7A8FA8] uppercase block mb-1">
              {mode === 'signup' ? 'Full Name' : 'Display Name (Optional)'}
            </label>
            <div className="relative">
              <UserIcon className="w-4 h-4 text-[#7A8FA8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required={mode === 'signup'}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Yash Pandey"
                className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg pl-9 pr-3 py-2 text-xs text-[#E8EDF5] placeholder-[#7A8FA8] focus:border-[#2D7DD2]/50 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-[10px] font-bold text-[#7A8FA8] uppercase block mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-[#7A8FA8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@thermaltrace.org"
                className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg pl-9 pr-3 py-2 text-xs text-[#E8EDF5] placeholder-[#7A8FA8] focus:border-[#2D7DD2]/50 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-[10px] font-bold text-[#7A8FA8] uppercase block mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-[#7A8FA8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg pl-9 pr-10 py-2 text-xs text-[#E8EDF5] placeholder-[#7A8FA8] focus:border-[#2D7DD2]/50 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#7A8FA8] hover:text-[#E8EDF5]"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {mode === 'signup' && (
            <div>
              <label className="text-[10px] font-bold text-[#7A8FA8] uppercase block mb-1">Confirm Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#7A8FA8] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg pl-9 pr-3 py-2 text-xs text-[#E8EDF5] placeholder-[#7A8FA8] focus:border-[#2D7DD2]/50 focus:outline-none"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#2D7DD2] hover:bg-[#2D7DD2]/90 disabled:opacity-50 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center gap-2 shadow-lg"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : mode === 'login' ? (
              <>
                <LogIn className="w-4 h-4" />
                <span>Log In</span>
              </>
            ) : (
              <>
                <UserPlus className="w-4 h-4" />
                <span>Create Account</span>
              </>
            )}
          </button>
        </form>

        <div className="text-center text-xs text-[#7A8FA8] pt-2 border-t border-[#1E2D45]">
          {mode === 'login' ? (
            <span>
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('signup');
                  setError(null);
                }}
                className="text-[#2D7DD2] hover:underline font-semibold"
              >
                Sign Up
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  setMode('login');
                  setError(null);
                }}
                className="text-[#2D7DD2] hover:underline font-semibold"
              >
                Log In
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
