import React, { useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { formatAuthError, FormattedAuthError } from '@/lib/authErrorMapper';
import { LogIn, UserPlus, Mail, Lock, User, CheckCircle2, AlertCircle, X, Eye, EyeOff } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: any, profession?: string, level?: string) => void;
  initialMode?: 'login' | 'register';
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialMode = 'login'
}) => {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [profession, setProfession] = useState('HEALTH');
  const [level, setLevel] = useState('B2');
  
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorInfo, setErrorInfo] = useState<FormattedAuthError | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorInfo(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password
        });
        if (error) throw error;
        
        const userProf = data.user?.user_metadata?.profession || 'HEALTH';
        const userLvl = data.user?.user_metadata?.target_level || 'B2';
        onSuccess(data.user, userProf, userLvl);
        onClose();
      } else {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
              profession: profession,
              target_level: level
            }
          }
        });
        if (error) throw error;
        
        if (data.user) {
          onSuccess(data.user, profession, level);
          onClose();
        }
      }
    } catch (err: any) {
      console.error("Auth Error:", err);
      const formatted = formatAuthError(err, 'DE');
      setErrorInfo(formatted);
    } finally {
      setLoading(false);
    }
  };

  const professions = [
    { id: 'PFLEGE', label: '🏥 Pflegekraft', desc: 'Pflege & Betreuung' },
    { id: 'MEDIZIN', label: '🩺 Arzt / Ärztin', desc: 'Fahrprüfung FSP' },
    { id: 'PHYSIO', label: '🤸 Physiotherapeut/in', desc: 'Reha & Therapie' },
    { id: 'PHARMA', label: '💊 Apotheker/in', desc: 'Pharmazie' },
    { id: 'IT', label: '💻 IT & Software', desc: 'Informatik & Tech' },
    { id: 'ACADEMIC', label: '🎓 Akademiker/in', desc: 'Hochschule' }
  ];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '1rem',
      animation: 'fadeIn 0.2s ease-out'
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: '20px',
        maxWidth: '480px',
        width: '100%',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(26, 110, 110, 0.1)',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: '#f1f5f9',
            border: 'none',
            borderRadius: '50%',
            width: '36px',
            height: '36px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: '#64748b',
            transition: 'all 0.2s'
          }}
        >
          <X size={18} />
        </button>

        {/* Modal Header */}
        <div style={{ padding: '2rem 2rem 1.25rem 2rem', textAlign: 'center', background: 'linear-gradient(180deg, #f0fdfa 0%, #ffffff 100%)' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #1A6E6E 0%, #0d4b4b 100%)',
            color: '#ffffff',
            boxShadow: '0 10px 15px -3px rgba(26, 110, 110, 0.3)',
            marginBottom: '1rem'
          }}>
            {mode === 'login' ? <LogIn size={26} /> : <UserPlus size={26} />}
          </div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>
            {mode === 'login' ? 'Willkommen zurück!' : 'Drain Konto erstellen'}
          </h2>
          <p style={{ margin: '0.4rem 0 0 0', fontSize: '0.88rem', color: '#64748b' }}>
            {mode === 'login' ? 'Melde dich an, um dein Deutschniveau fortzusetzen.' : 'Wähle dein Berufsfeld und starte dein Sprachniveau.'}
          </p>

          {/* Mode Switch Tabs */}
          <div style={{
            display: 'flex',
            background: '#e2e8f0',
            borderRadius: '12px',
            padding: '4px',
            marginTop: '1.25rem'
          }}>
            <button
              type="button"
              onClick={() => { setMode('login'); setErrorInfo(null); }}
              style={{
                flex: 1,
                padding: '8px',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: 600,
                background: mode === 'login' ? '#ffffff' : 'transparent',
                color: mode === 'login' ? '#1A6E6E' : '#64748b',
                boxShadow: mode === 'login' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              Einloggen
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setErrorInfo(null); }}
              style={{
                flex: 1,
                padding: '8px',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: 600,
                background: mode === 'register' ? '#ffffff' : 'transparent',
                color: mode === 'register' ? '#1A6E6E' : '#64748b',
                boxShadow: mode === 'register' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              Konto erstellen
            </button>
          </div>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} style={{ padding: '0 2rem 2rem 2rem' }}>
          {errorInfo && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              padding: '12px 14px',
              background: '#fef2f2',
              border: '1.5px solid #fecaca',
              borderRadius: '12px',
              color: '#991b1b',
              fontSize: '0.85rem',
              fontWeight: 600,
              marginBottom: '1rem',
              boxShadow: '0 2px 4px rgba(239, 68, 68, 0.08)'
            }}>
              <AlertCircle size={18} style={{ flexShrink: 0, color: '#ef4444' }} />
              <span>{errorInfo.message}</span>
            </div>
          )}

          {/* Full Name Input (Register Only) */}
          {mode === 'register' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
                Name & Nachname
              </label>
              <div style={{ position: 'relative' }}>
                <User size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                <input
                  type="text"
                  required
                  placeholder="z.B. Dr. Maria Schmidt"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px 10px 38px',
                    borderRadius: '10px',
                    border: '1px solid #cbd5e1',
                    fontSize: '0.9rem',
                    outline: 'none'
                  }}
                />
              </div>
            </div>
          )}

          {/* E-Mail Input */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
              E-Mail Adresse
            </label>
            <div style={{ position: 'relative' }}>
              <Mail size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: errorInfo?.field === 'email' ? '#ef4444' : '#94a3b8' }} />
              <input
                type="email"
                required
                placeholder="name@beispiel.de"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (errorInfo) setErrorInfo(null);
                }}
                style={{
                  width: '100%',
                  padding: '10px 12px 10px 38px',
                  borderRadius: '10px',
                  border: errorInfo?.field === 'email' ? '1.5px solid #ef4444' : '1px solid #cbd5e1',
                  background: errorInfo?.field === 'email' ? '#fff5f5' : '#ffffff',
                  fontSize: '0.9rem',
                  outline: 'none',
                  transition: 'all 0.2s'
                }}
              />
            </div>
          </div>

          {/* Password Input */}
          <div style={{ marginBottom: mode === 'register' ? '1rem' : '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
              Passwort
            </label>
            <div style={{ position: 'relative' }}>
              <Lock size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: errorInfo?.field === 'password' ? '#ef4444' : '#94a3b8' }} />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={6}
                placeholder="Mindestens 6 Zeichen"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errorInfo) setErrorInfo(null);
                }}
                style={{
                  width: '100%',
                  padding: '10px 38px 10px 38px',
                  borderRadius: '10px',
                  border: errorInfo?.field === 'password' ? '1.5px solid #ef4444' : '1px solid #cbd5e1',
                  background: errorInfo?.field === 'password' ? '#fff5f5' : '#ffffff',
                  fontSize: '0.9rem',
                  outline: 'none',
                  transition: 'all 0.2s'
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer'
                }}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Profession Selection (Register Only) */}
          {mode === 'register' && (
            <>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
                  Dein Berufsfeld in Deutschland
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
                  {professions.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setProfession(p.id)}
                      style={{
                        padding: '8px 10px',
                        borderRadius: '8px',
                        border: profession === p.id ? '2px solid #1A6E6E' : '1px solid #e2e8f0',
                        background: profession === p.id ? '#e6f4f4' : '#f8fafc',
                        color: profession === p.id ? '#1A6E6E' : '#334155',
                        textAlign: 'left',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        fontWeight: 600
                      }}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Starting Level Selection */}
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
                  Ziel-Niveau
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.4rem' }}>
                  {['A1', 'A2', 'B1', 'B2', 'C1'].map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setLevel(lvl)}
                      style={{
                        padding: '8px',
                        borderRadius: '8px',
                        border: level === lvl ? '2px solid #1A6E6E' : '1px solid #e2e8f0',
                        background: level === lvl ? '#1A6E6E' : '#f8fafc',
                        color: level === lvl ? '#ffffff' : '#334155',
                        fontWeight: 600,
                        fontSize: '0.82rem',
                        cursor: 'pointer'
                      }}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '12px',
              border: 'none',
              background: 'linear-gradient(135deg, #1A6E6E 0%, #0d4b4b 100%)',
              color: '#ffffff',
              fontSize: '0.95rem',
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 12px rgba(26, 110, 110, 0.25)',
              transition: 'all 0.2s'
            }}
          >
            {loading ? 'Wird geladen...' : (mode === 'login' ? 'Anmelden' : 'Jetzt kostenlos registrieren')}
          </button>
        </form>
      </div>
    </div>
  );
};
