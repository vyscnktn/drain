import React, { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { formatAuthError, FormattedAuthError } from '@/lib/authErrorMapper';
import { LogIn, UserPlus, Mail, Lock, Sparkles, Brain, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck, Eye, EyeOff, Globe } from 'lucide-react';

type LandingLanguage = 'DE' | 'TR' | 'ES' | 'EN';

interface AuthGateProps {
  onSuccessLogin: (user: any) => void;
  onStartRegistration: () => void;
}

const UI_STRINGS: Record<LandingLanguage, Record<string, string>> = {
  TR: {
    hero_title: 'Mesleki Almancanı tam seviyene göre öğren.',
    hero_subtitle: 'Pflege, doktorluk dil sınavı, IT veya bilim — her gün mesleğine ve dil seviyene uygun metinler alırsın.',
    feature_level_title: 'Her zaman seviyene uygun',
    feature_level_description: 'Bildiğin kelimelerle kendinden emin ilerler, her metinde hedefli olarak 1 yeni mesleki terim öğrenirsin.',
    feature_graph_title: 'Kelime haznen görünür şekilde büyür',
    feature_graph_description: 'Görsel kelime ağını anlık takip et ve istediğin zaman indir.',
    feature_profession_title: 'Mesleğin için tasarlandı',
    feature_profession_description: 'Gerçek iş hayatından terimler ve diyaloglar — genel bir dil kursu değil.',
    tabLogin: 'Giriş Yap',
    tabRegister: 'Kayıt Ol',
    welcomeBack: 'Hoş Geldiniz!',
    loginSub: 'Okuma antrenmanınıza devam etmek için bilgilerinizi girin.',
    emailLabel: 'E-Posta Adresi',
    passwordLabel: 'Şifre',
    loginBtn: 'Giriş Yap',
    loginLoading: 'Giriş yapılıyor...',
    regTitle: 'Konto Erstellen & Seviyeni Ölç',
    regSub: 'Mesleğinizi seçin ve 3 kısa metinli seviye kalibrasyonu ile Almanca okuma serüveninize hemen başlayın.',
    regBtn: 'Şimdi Kayıt Ol & Kalibre Et'
  },
  DE: {
    hero_title: 'Lerne dein Fach-Deutsch\nGenau auf deinem Niveau!',
    hero_subtitle: 'Pflege, Arzt FSP, IT oder Wissenschaft — jeden Tag bekommst du Texte, die zu deinem Beruf und deinem Sprachstand passen.',
    feature_level_title: 'Immer auf deinem Niveau',
    feature_level_description: 'Du bleibst bei bekannten Wörtern sicher, lernst aber gezielt 1 neues Fachwort pro Text.',
    feature_graph_title: 'Dein Wortschatz wächst sichtbar',
    feature_graph_description: 'Verfolge dein visuelles Wörternetzwerk live — und lade es dir jederzeit herunter.',
    feature_profession_title: 'Für deinen Beruf gemacht',
    feature_profession_description: 'Begriffe und Dialoge aus deinem echten Arbeitsalltag — kein allgemeiner Sprachkurs.',
    tabLogin: 'Einloggen',
    tabRegister: 'Konto erstellen',
    welcomeBack: 'Willkommen zurück!',
    loginSub: 'Gib deine Anmeldedaten ein, um dein Lesetraining fortzusetzen.',
    emailLabel: 'E-Mail Adresse',
    passwordLabel: 'Passwort',
    loginBtn: 'Anmelden',
    loginLoading: 'Wird angemeldet...',
    regTitle: 'Konto erstellen & Niveau kalibrieren',
    regSub: 'Wähle dein Berufsfeld und starte mit einer kurzen 3-Schritt-Kalibrierung deine Lese-Reise.',
    regBtn: 'Jetzt registrieren & Kalibrieren'
  },
  ES: {
    hero_title: 'Aprende alemán profesional, exactamente a tu nivel.',
    hero_subtitle: 'Enfermería, examen de idioma para médicos, informática o ciencia: cada día recibes textos adaptados a tu profesión y a tu nivel de alemán.',
    feature_level_title: 'Siempre a tu nivel',
    feature_level_description: 'Te mueves con seguridad entre palabras que ya conoces y aprendes de forma específica un nuevo término profesional en cada texto.',
    feature_graph_title: 'Tu vocabulario crece de forma visible',
    feature_graph_description: 'Sigue tu red visual de palabras en tiempo real y descárgala cuando quieras.',
    feature_profession_title: 'Hecho para tu profesión',
    feature_profession_description: 'Términos y diálogos de tu día a día laboral real, no un curso de idiomas general.',
    tabLogin: 'Iniciar Sesión',
    tabRegister: 'Crear Cuenta',
    welcomeBack: '¡Bienvenido de nuevo!',
    loginSub: 'Ingresa tus datos para continuar tu entrenamiento de lectura.',
    emailLabel: 'Correo Electrónico',
    passwordLabel: 'Contraseña',
    loginBtn: 'Iniciar Sesión',
    loginLoading: 'Iniciando sesión...',
    regTitle: 'Crear Cuenta y Calibrar Nivel',
    regSub: 'Elige tu profesión y comienza tu viaje de lectura con una calibración rápida de 3 pasos.',
    regBtn: 'Registrarse y Calibrar Ahora'
  },
  EN: {
    hero_title: 'Learn professional German, exactly at your level.',
    hero_subtitle: 'Nursing, medical language exams, IT, or science — every day, you receive texts tailored to your profession and your German level.',
    feature_level_title: 'Always at your level',
    feature_level_description: 'Stay confident with words you already know while learning one new professional term in every text.',
    feature_graph_title: 'Watch your vocabulary grow',
    feature_graph_description: 'Follow your visual word network in real time and download it whenever you want.',
    feature_profession_title: 'Built for your profession',
    feature_profession_description: 'Terms and dialogues from your real working life — not a general language course.',
    tabLogin: 'Log In',
    tabRegister: 'Create Account',
    welcomeBack: 'Welcome back!',
    loginSub: 'Enter your credentials to continue your reading practice.',
    emailLabel: 'Email Address',
    passwordLabel: 'Password',
    loginBtn: 'Log In',
    loginLoading: 'Logging in...',
    regTitle: 'Create Account & Calibrate Level',
    regSub: 'Choose your profession and complete a quick 3-step reading calibration to start.',
    regBtn: 'Register & Calibrate Now'
  }
};

export const AuthGate: React.FC<AuthGateProps> = ({
  onSuccessLogin,
  onStartRegistration
}) => {
  const [uiLang, setUiLang] = useState<LandingLanguage>('EN');
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [errorInfo, setErrorInfo] = useState<FormattedAuthError | null>(null);

  // Geo-IP & Browser Language Auto-Detection
  useEffect(() => {
    const detectBrowserLang = (): LandingLanguage => {
      if (typeof window === 'undefined') return 'EN';
      const lang = (navigator.language || (navigator as any).userLanguage || '').toLowerCase();
      if (lang.startsWith('tr')) return 'TR';
      if (lang.startsWith('de')) return 'DE';
      if (lang.startsWith('es')) return 'ES';
      return 'EN';
    };

    // Set browser language immediately
    const initialLang = detectBrowserLang();
    setUiLang(initialLang);

    // Fetch Geo-IP for precision country fallback
    fetch('https://ipapi.co/json/')
      .then(res => res.json())
      .then(data => {
        const country = (data.country_code || '').toUpperCase();
        if (country === 'TR') setUiLang('TR');
        else if (['DE', 'AT', 'CH'].includes(country)) setUiLang('DE');
        else if (['ES', 'MX', 'AR', 'CO', 'CL', 'PE'].includes(country)) setUiLang('ES');
      })
      .catch(() => {
        // Fallback to browser language
      });
  }, []);

  const t = UI_STRINGS[uiLang] || UI_STRINGS.EN;

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorInfo(null);

    try {
      if (activeTab === 'login') {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password
        });
        if (error) throw error;
        if (data.user) {
          onSuccessLogin(data.user);
        }
      }
    } catch (err: any) {
      console.error('Auth error:', err);
      setErrorInfo(formatAuthError(err, 'DE'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      background: 'linear-gradient(135deg, #f0fdfa 0%, #ffffff 50%, #f8fafc 100%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem 1rem',
      boxSizing: 'border-box',
      position: 'relative'
    }}>
      {/* Top Header Language Switcher Bar */}
      <div style={{
        width: '100%',
        maxWidth: '1000px',
        display: 'flex',
        justifyContent: 'flex-end',
        marginBottom: '1rem'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.35rem',
          background: '#ffffff',
          padding: '5px 10px',
          borderRadius: '12px',
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05), 0 0 0 1px rgba(26,110,110,0.1)'
        }}>
          <Globe size={18} color="#1A6E6E" style={{ marginRight: '4px' }} />
          {(['DE', 'TR', 'ES', 'EN'] as LandingLanguage[]).map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setUiLang(lang)}
              style={{
                padding: '4px 9px',
                fontSize: '0.8rem',
                fontWeight: 700,
                borderRadius: '6px',
                border: uiLang === lang ? '1.5px solid #1A6E6E' : '1px solid transparent',
                background: uiLang === lang ? '#1A6E6E' : 'transparent',
                color: uiLang === lang ? '#ffffff' : '#64748b',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>

      <div style={{
        maxWidth: '1000px',
        width: '100%',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 340px), 1fr))',
        gap: 'clamp(1.75rem, 4vw, 3rem)',
        alignItems: 'center'
      }}>
        
        {/* Left Side: Brand & Hero Description */}
        <div>
          <div style={{ marginBottom: '1.5rem' }}>
            <img src="/logos/drain-wordmark-logo-teal.svg" alt="Drain" style={{ height: '72px', width: 'auto' }} />
          </div>

          <h1 style={{
            fontSize: 'clamp(1.7rem, 4.5vw, 2.3rem)',
            fontWeight: 800,
            color: '#0f172a',
            lineHeight: 1.25,
            marginBottom: '1rem',
            letterSpacing: '-0.02em',
            whiteSpace: 'pre-line'
          }}>
            {t.hero_title}
          </h1>

          <p style={{
            fontSize: '1rem',
            color: '#475569',
            lineHeight: 1.6,
            marginBottom: '2rem'
          }}>
            {t.hero_subtitle}
          </p>

          {/* Feature Highlights */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {[
              { icon: <Sparkles size={20} color="#1A6E6E" />, title: t.feature_level_title, desc: t.feature_level_description },
              { icon: <Brain size={20} color="#1A6E6E" />, title: t.feature_graph_title, desc: t.feature_graph_description },
              { icon: <ShieldCheck size={20} color="#1A6E6E" />, title: t.feature_profession_title, desc: t.feature_profession_description }
            ].map((f, i) => (
              <div key={i} style={{ display: 'flex', gap: '0.85rem', alignItems: 'flex-start' }}>
                <div style={{
                  padding: '8px',
                  borderRadius: '10px',
                  background: '#ffffff',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(26, 110, 110, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {f.icon}
                </div>
                <div>
                  <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#1e293b' }}>{f.title}</h4>
                  <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Side: Auth Action Card */}
        <div style={{
          background: '#ffffff',
          borderRadius: '24px',
          padding: 'clamp(1.5rem, 4vw, 2.5rem)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04), 0 0 0 1px rgba(26, 110, 110, 0.12)'
        }}>
          
          {/* Tab Switcher */}
          <div style={{
            display: 'flex',
            background: '#f1f5f9',
            borderRadius: '12px',
            padding: '4px',
            marginBottom: '1.75rem'
          }}>
            <button
              type="button"
              onClick={() => { setActiveTab('login'); setErrorInfo(null); }}
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.9rem',
                fontWeight: 700,
                background: activeTab === 'login' ? '#ffffff' : 'transparent',
                color: activeTab === 'login' ? '#1A6E6E' : '#64748b',
                boxShadow: activeTab === 'login' ? '0 2px 4px rgba(0,0,0,0.08)' : 'none',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {t.tabLogin}
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab('register'); setErrorInfo(null); }}
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.9rem',
                fontWeight: 700,
                background: activeTab === 'register' ? '#ffffff' : 'transparent',
                color: activeTab === 'register' ? '#1A6E6E' : '#64748b',
                boxShadow: activeTab === 'register' ? '0 2px 4px rgba(0,0,0,0.08)' : 'none',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {t.tabRegister}
            </button>
          </div>

          {/* TAB 1: LOGIN FORM */}
          {activeTab === 'login' && (
            <form onSubmit={handleLoginSubmit}>
              <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                {t.welcomeBack}
              </h3>
              <p style={{ margin: '0 0 1.5rem 0', fontSize: '0.88rem', color: '#64748b' }}>
                {t.loginSub}
              </p>

              {errorInfo && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  padding: '12px 16px',
                  background: '#fef2f2',
                  border: '1.5px solid #fecaca',
                  borderRadius: '12px',
                  color: '#991b1b',
                  fontSize: '0.86rem',
                  fontWeight: 600,
                  marginBottom: '1.25rem',
                  boxShadow: '0 2px 4px rgba(239, 68, 68, 0.08)'
                }}>
                  <AlertCircle size={18} style={{ flexShrink: 0, color: '#ef4444' }} />
                  <span>{errorInfo.message}</span>
                </div>
              )}

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                  {t.emailLabel}
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: errorInfo?.field === 'email' ? '#ef4444' : '#94a3b8' }} />
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
                      padding: '11px 14px 11px 42px',
                      borderRadius: '12px',
                      border: errorInfo?.field === 'email' ? '1.5px solid #ef4444' : '1.5px solid #cbd5e1',
                      background: errorInfo?.field === 'email' ? '#fff5f5' : '#ffffff',
                      fontSize: '0.92rem',
                      outline: 'none',
                      transition: 'all 0.2s'
                    }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '1.75rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                  {t.passwordLabel}
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: errorInfo?.field === 'password' ? '#ef4444' : '#94a3b8' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errorInfo) setErrorInfo(null);
                    }}
                    style={{
                      width: '100%',
                      padding: '11px 42px 11px 42px',
                      borderRadius: '12px',
                      border: errorInfo?.field === 'password' ? '1.5px solid #ef4444' : '1.5px solid #cbd5e1',
                      background: errorInfo?.field === 'password' ? '#fff5f5' : '#ffffff',
                      fontSize: '0.92rem',
                      outline: 'none',
                      transition: 'all 0.2s'
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '14px',
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

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '13px',
                  borderRadius: '12px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #1A6E6E 0%, #0d4b4b 100%)',
                  color: '#ffffff',
                  fontSize: '1rem',
                  fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  boxShadow: '0 4px 12px rgba(26, 110, 110, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                {loading ? t.loginLoading : <>{t.loginBtn} <ArrowRight size={18} /></>}
              </button>
            </form>
          )}

          {/* TAB 2: REGISTER & CALIBRATE INVITATION */}
          {activeTab === 'register' && (
            <div style={{ textAlign: 'center', padding: '0.5rem 0' }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '20px',
                background: '#e6f4f4',
                color: '#1A6E6E',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1rem'
              }}>
                <UserPlus size={32} />
              </div>

              <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.3rem', fontWeight: 800, color: '#0f172a' }}>
                {t.regTitle}
              </h3>
              <p style={{ margin: '0 0 1.75rem 0', fontSize: '0.9rem', color: '#64748b', lineHeight: 1.5 }}>
                {t.regSub}
              </p>

              <button
                type="button"
                onClick={onStartRegistration}
                style={{
                  width: '100%',
                  padding: '14px',
                  borderRadius: '12px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #1A6E6E 0%, #0d4b4b 100%)',
                  color: '#ffffff',
                  fontSize: '1.02rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 6px 16px rgba(26, 110, 110, 0.35)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.6rem'
                }}
              >
                {t.regBtn} <ArrowRight size={20} />
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
