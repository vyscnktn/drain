'use client';

import React, { useState } from 'react';
import { Star, ChevronRight, CheckCircle, Sparkles, RefreshCw, Globe, Mail, Lock, User, AlertCircle, Eye, EyeOff } from 'lucide-react';
import axios from 'axios';
import styles from '../app/page.module.css';
import { supabase } from '@/lib/supabaseClient';
import { API_URL } from '@/lib/api';

type Language = 'EN' | 'ES' | 'TR' | 'DE';

interface CalibrationText {
  id: number;
  step: number;
  level: string;
  content: string;
  target_word: any;
  anchors: any[];
}

interface OnboardingProps {
  userId: string;
  backendUrl: string;
  onComplete: (user: any, calibratedMastery: number, level: string, profession: string) => void;
  onCancel?: () => void;
}

const UI_STRINGS: Record<Language, Record<string, string>> = {
  EN: {
    welcome: 'Create Account & Calibrate Level',
    subtext: 'Enter your credentials, select your field, and complete a quick 3-step reading calibration to create your account.',
    currentLevelLabel: 'Your Current German Level:',
    targetLevelLabel: 'Your Target Level:',
    professionLabel: 'Your Field in Germany:',
    startBtn: 'Start 3-Text Calibration',
    stepHeader: 'Step',
    of: 'of 3 (Level:',
    feedbackQ: 'How was this text for you?',
    tooEasy: 'Too easy',
    justRight: 'Just right',
    tooHard: 'Too hard',
    nextBtn: 'Next Text',
    finishBtn: 'Create Account & Start',
    doneTitle: 'Account Created & Calibrated!',
    doneSub: 'Your vocabulary profile has been initialized for',
    doneMastery: 'Initial mastery score:',
    startJourneyBtn: 'Start Reading Journey'
  },
  ES: {
    welcome: 'Crear Cuenta y Calibrar Nivel',
    subtext: 'Ingresa tus datos, elige tu campo de trabajo y completa una calibración de 3 textos para crear tu cuenta.',
    currentLevelLabel: 'Tu Nivel Actual de Alemán:',
    targetLevelLabel: 'Tu Nivel Objetivo:',
    professionLabel: 'Tu Campo de Trabajo en Alemania:',
    startBtn: 'Iniciar Calibración de 3 Textos',
    stepHeader: 'Paso',
    of: 'de 3 (Nivel:',
    feedbackQ: '¿Qué tal estuvo este texto para ti?',
    tooEasy: 'Demasiado fácil',
    justRight: 'Perfecto',
    tooHard: 'Demasiado difícil',
    nextBtn: 'Siguiente Texto',
    finishBtn: 'Crear Cuenta y Comenzar',
    doneTitle: '¡Cuenta Creada y Calibrada!',
    doneSub: 'Tu perfil de vocabulario se ha inicializado para',
    doneMastery: 'Puntuación inicial:',
    startJourneyBtn: 'Comenzar Viaje de Lectura'
  },
  TR: {
    welcome: 'Hesap Oluştur ve Seviyeni Ölç',
    subtext: 'Bilgilerinizi girin, meslek alanınızı seçin ve 3 metinli hızlı seviye kalibrasyonu ile hesabınızı hemen açın.',
    currentLevelLabel: 'Mevcut Almanca Seviyeniz:',
    targetLevelLabel: 'Hedeflediğiniz Seviye:',
    professionLabel: 'Almanya\'daki Meslek Alanınız:',
    startBtn: '3 Metinli Kalibrasyonu Başlat',
    stepHeader: 'Adım',
    of: '/ 3 (Seviye:',
    feedbackQ: 'Bu metin sizin için nasıldı?',
    tooEasy: 'Çok kolay',
    justRight: 'Tam kıvamında',
    tooHard: 'Çok zor',
    nextBtn: 'Sonraki Metin',
    finishBtn: 'Hesabı Oluştur ve Başlat',
    doneTitle: 'Kayıt ve Kalibrasyon Tamamlandı!',
    doneSub: 'Kelime profiliniz başarıyla ayarlandı:',
    doneMastery: 'Başlangıç hakimiyet seviyesi:',
    startJourneyBtn: 'Okuma Yolculuğunu Başlat'
  },
  DE: {
    welcome: 'Konto erstellen & Niveau kalibrieren',
    subtext: 'Gib deine Daten ein, wähle dein Berufsfeld und absolviere eine kurze 3-Schritt-Kalibrierung zur Kontoerstellung.',
    currentLevelLabel: 'Dein aktuelles Deutsch-Niveau:',
    targetLevelLabel: 'Dein Ziel-Niveau:',
    professionLabel: 'Dein Berufsfeld in Deutschland:',
    startBtn: '3-Schritt-Kalibrierung starten',
    stepHeader: 'Schritt',
    of: 'von 3 (Niveau:',
    feedbackQ: 'Wie war dieser Text für dich?',
    tooEasy: 'Zu einfach',
    justRight: 'Genau richtig',
    tooHard: 'Zu schwer',
    nextBtn: 'Nächster Text',
    finishBtn: 'Konto erstellen & Starten',
    doneTitle: 'Konto erstellt & Kalibriert!',
    doneSub: 'Dein Wortschatz-Profil wurde initialisiert für',
    doneMastery: 'Start-Bekanntheitsgrad:',
    startJourneyBtn: 'Lese-Reise starten'
  }
};

export default function Onboarding({ userId, backendUrl, onComplete, onCancel }: OnboardingProps) {
  const [uiLang] = useState<Language>('DE'); // Interior app is 100% immersive German
  const [step, setStep] = useState<'form' | 'calibrating' | 'done'>('form');
  
  // Registration Form Fields
  const [fullName, setFullName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);

  const [currentLevel, setCurrentLevel] = useState<string>('A2');
  const [targetLevel, setTargetLevel] = useState<string>('B2');
  const [profession, setProfession] = useState<string>('HEALTH');
  
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [calibrationTexts, setCalibrationTexts] = useState<CalibrationText[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  
  const [currentRating, setCurrentRating] = useState<number>(0);
  const [currentDifficulty, setCurrentDifficulty] = useState<string | null>(null);
  const [ratings, setRatings] = useState<Array<{ text_id: number; rating: number; difficulty: string }>>([]);
  const [resultMastery, setResultMastery] = useState<number>(0.55);
  const [registeredUser, setRegisteredUser] = useState<any>(null);

  const t = UI_STRINGS[uiLang];

  const startCalibration = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!fullName.trim() || !email.trim() || !password) {
      setErrorMsg("Lütfen tüm alanları doldurun.");
      return;
    }

    if (password.length < 6) {
      setErrorMsg("Şifre en az 6 karakter olmalıdır.");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/onboarding/start`, {
        user_id: userId,
        current_level: currentLevel,
        target_level: targetLevel,
        domain: profession,   // sends strictly 'IT', 'HEALTH', or 'ACADEMIC'
      });
      setCalibrationTexts(response.data.calibration_texts || []);
      setCurrentIndex(0);
      setStep('calibrating');
    } catch (err: any) {
      console.error("Calibration start failed", err);
      const serverMsg = err?.response?.data?.detail;
      setErrorMsg(serverMsg || "Kalibrasyon metinleri oluşturulamadı. Lütfen tekrar deneyin.");
    }
    setLoading(false);
  };

  const handleNextText = async () => {
    if (currentRating === 0 || !currentDifficulty) return;
    
    const currentText = calibrationTexts[currentIndex];
    const newRating = {
      text_id: currentText.id,
      rating: currentRating,
      difficulty: currentDifficulty
    };
    
    const updatedRatings = [...ratings, newRating];
    setRatings(updatedRatings);
    
    setCurrentRating(0);
    setCurrentDifficulty(null);
    
    if (currentIndex + 1 < calibrationTexts.length) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setLoading(true);
      setErrorMsg(null);
      try {
        // 1. Create Supabase Auth Account
        const { data: authData, error: authError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
              profession: profession,
              target_level: targetLevel
            }
          }
        });

        if (authError) throw authError;

        const activeUser = authData.user;
        const newUserId = activeUser ? activeUser.id : userId;
        setRegisteredUser(activeUser);

        // 2. Save domain & level into the profiles table (real user_id now available)
        if (newUserId && newUserId !== userId) {
          const { error: profileError } = await supabase
            .from('profiles')
            .upsert({
              id: newUserId,
              full_name: fullName,
              email: email,
              target_domain: profession,
              domain: profession,
              target_level: targetLevel,
              current_level: currentLevel,
            });
          if (profileError) {
            console.warn("Profile upsert warning:", profileError.message);
          }
        }

        // 3. Submit Calibration Ratings to Backend
        const res = await axios.post(`${API_URL}/api/onboarding/submit`, {
          user_id: newUserId,
          current_level: currentLevel,
          target_level: targetLevel,
          domain: profession,
          full_name: fullName,
          email: email,
          ratings: updatedRatings
        });

        const mastery = res.data.calibrated_mastery || 0.5;
        setResultMastery(mastery);
        setStep('done');
      } catch (err: any) {
        console.error("Failed to complete registration and onboarding", err);
        setErrorMsg(err.message || "Hesap oluşturma veya kalibrasyon kaydedilemedi.");
      }
      setLoading(false);
    }
  };

  const renderTextDisplay = (textObj: CalibrationText) => {
    const words = textObj.content.split(/(\s+|[.,!?]+)/);
    const targetLemma = textObj.target_word?.lemma?.toLowerCase();
    
    return (
      <div className={styles.textDisplay}>
        {words.map((w, i) => {
          const wLower = w.toLowerCase();
          const cleanWLower = wLower.replace(/[^a-zäöüß]/g, '');
          let matchedGloss = null;
          let isTarget = false;
          
          if (targetLemma && cleanWLower === targetLemma) {
            isTarget = true;
            matchedGloss = textObj.target_word?.german_gloss;
          } else {
            const anchor = textObj.anchors?.find(a => {
              const aLemma = a.lemma?.toLowerCase();
              return aLemma && cleanWLower === aLemma;
            });
            if (anchor) {
              matchedGloss = anchor.german_gloss;
            }
          }
          
          if (w.trim() === '') return <span key={i}>{w}</span>;
          
          return (
            <span key={i} className={`${styles.word} ${isTarget ? styles.targetWord : ''}`}>
              {w}
              {matchedGloss && <span className={styles.tooltip}>{matchedGloss}</span>}
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: '680px', margin: '2rem auto', padding: '0 1rem' }}>
      {onCancel && (
        <div style={{ marginBottom: '1rem' }}>
          <button
            onClick={onCancel}
            style={{ border: 'none', background: 'none', color: '#64748b', fontSize: '0.88rem', cursor: 'pointer', fontWeight: 600 }}
          >
            ← Zurück zur Startseite
          </button>
        </div>
      )}

      {step === 'form' && (
        <form onSubmit={startCalibration} className="card" style={{ padding: '2.5rem', background: '#fff', borderRadius: '20px', boxShadow: '0 15px 30px -5px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem', color: '#1A6E6E' }}>
            <Sparkles size={28} />
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0 }}>{t.welcome}</h2>
          </div>
          <p style={{ color: '#64748b', marginBottom: '1.75rem', lineHeight: '1.5', fontSize: '0.92rem' }}>
            {t.subtext}
          </p>

          {errorMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '10px 14px',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '10px',
              color: '#991b1b',
              fontSize: '0.85rem',
              marginBottom: '1.25rem'
            }}>
              <AlertCircle size={18} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Account Credentials */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
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
                  style={{ width: '100%', padding: '10px 12px 10px 38px', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '0.9rem', outline: 'none' }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
                E-Mail Adresse
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                <input
                  type="email"
                  required
                  placeholder="name@beispiel.de"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px 10px 38px', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '0.9rem', outline: 'none' }}
                />
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
              Passwort
            </label>
            <div style={{ position: 'relative' }}>
              <Lock size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={6}
                placeholder="Mindestens 6 Zeichen"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: '100%', padding: '10px 38px 10px 38px', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '0.9rem', outline: 'none' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Berufsfeld / Profession Selector */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.85rem', color: '#334155' }}>
              {t.professionLabel}
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.6rem' }}>
              {[
                { id: 'HEALTH', label: '🏥 Medizin & Gesundheit' },
                { id: 'IT', label: '💻 IT & Software' },
                { id: 'ACADEMIC', label: '🎓 Akademisches Deutsch' }
              ].map((prof) => (
                <button
                  key={prof.id}
                  type="button"
                  onClick={() => setProfession(prof.id)}
                  style={{
                    padding: '11px 12px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    borderRadius: '10px',
                    border: profession === prof.id ? '2px solid #1A6E6E' : '1px solid #e2e8f0',
                    background: profession === prof.id ? '#e6f4f4' : '#f8fafc',
                    color: profession === prof.id ? '#1A6E6E' : '#334155',
                    textAlign: 'left',
                    cursor: 'pointer'
                  }}
                >
                  {prof.label}
                </button>
              ))}
            </div>
          </div>

          {/* Current Level Selector */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.85rem', color: '#334155' }}>
              {t.currentLevelLabel}
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem' }}>
              {['A1', 'A2', 'B1', 'B2', 'C1'].map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setCurrentLevel(lvl)}
                  style={{
                    padding: '9px',
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: currentLevel === lvl ? '2px solid #1A6E6E' : '1px solid #e2e8f0',
                    background: currentLevel === lvl ? '#1A6E6E' : '#f8fafc',
                    color: currentLevel === lvl ? '#fff' : '#334155',
                    cursor: 'pointer'
                  }}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* Target Level Selector */}
          <div style={{ marginBottom: '1.75rem' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.85rem', color: '#334155' }}>
              {t.targetLevelLabel}
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem' }}>
              {['A1', 'A2', 'B1', 'B2', 'C1'].map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setTargetLevel(lvl)}
                  style={{
                    padding: '9px',
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: targetLevel === lvl ? '2px solid #1A6E6E' : '1px solid #e2e8f0',
                    background: targetLevel === lvl ? '#1A6E6E' : '#f8fafc',
                    color: targetLevel === lvl ? '#fff' : '#334155',
                    cursor: 'pointer'
                  }}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ width: '100%', padding: '14px', fontSize: '1rem', background: '#1A6E6E', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', borderRadius: '12px' }}
          >
            {loading ? <RefreshCw className="animate-spin" size={20} /> : <>{t.startBtn} <ChevronRight size={20} /></>}
          </button>
        </form>
      )}

      {step === 'calibrating' && calibrationTexts.length > 0 && (
        <div className="card" style={{ padding: '2rem', background: '#fff', borderRadius: '20px', boxShadow: '0 15px 30px -5px rgba(0,0,0,0.08)' }}>
          {errorMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '10px 14px',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '10px',
              color: '#991b1b',
              fontSize: '0.85rem',
              marginBottom: '1.25rem'
            }}>
              <AlertCircle size={18} />
              <span>{errorMsg}</span>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1A6E6E', background: '#e6f4f4', padding: '4px 12px', borderRadius: '9999px' }}>
              {t.stepHeader} {currentIndex + 1} {t.of} {calibrationTexts[currentIndex].level})
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              {[0, 1, 2].map((idx) => (
                <div
                  key={idx}
                  style={{
                    width: '32px',
                    height: '6px',
                    borderRadius: '9999px',
                    background: idx === currentIndex ? '#1A6E6E' : idx < currentIndex ? '#10b981' : '#e2e8f0'
                  }}
                />
              ))}
            </div>
          </div>

          {renderTextDisplay(calibrationTexts[currentIndex])}

          <div style={{ marginTop: '2rem', borderTop: '1px solid #f1f5f9', paddingTop: '1.5rem' }}>
            <p style={{ fontSize: '0.9rem', fontWeight: 600, color: '#475569', marginBottom: '0.75rem' }}>
              {t.feedbackQ}
            </p>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => setCurrentRating(star)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: currentRating >= star ? '#f59e0b' : '#cbd5e1' }}
                  >
                    <Star size={26} fill={currentRating >= star ? 'currentColor' : 'none'} />
                  </button>
                ))}
              </div>

              {currentRating > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {[
                    { key: 'Zu einfach', label: t.tooEasy },
                    { key: 'Genau richtig', label: t.justRight },
                    { key: 'Zu schwer', label: t.tooHard }
                  ].map((diff) => (
                    <button
                      key={diff.key}
                      type="button"
                      onClick={() => setCurrentDifficulty(diff.key)}
                      style={{
                        padding: '6px 12px',
                        fontSize: '0.8rem',
                        fontWeight: 500,
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        background: currentDifficulty === diff.key ? '#1A6E6E' : '#fff',
                        color: currentDifficulty === diff.key ? '#fff' : '#334155',
                        cursor: 'pointer'
                      }}
                    >
                      {diff.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ marginTop: '1.5rem', textAlign: 'right' }}>
              <button
                onClick={handleNextText}
                disabled={loading || currentRating === 0 || !currentDifficulty}
                className="btn btn-primary"
                style={{ padding: '10px 24px', background: '#1A6E6E' }}
              >
                {loading ? (
                  <RefreshCw className="animate-spin" size={18} />
                ) : (
                  <>{currentIndex === 2 ? t.finishBtn : t.nextBtn} <ChevronRight size={18} /></>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === 'done' && (
        <div className="card" style={{ padding: '3rem', textAlign: 'center', background: '#fff', borderRadius: '20px', boxShadow: '0 15px 30px -5px rgba(0,0,0,0.08)' }}>
          <CheckCircle size={56} color="#10b981" style={{ margin: '0 auto 1.5rem' }} />
          <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#0f172a', marginBottom: '0.5rem' }}>
            {t.doneTitle}
          </h2>
          <p style={{ color: '#64748b', marginBottom: '1.5rem', fontSize: '0.95rem' }}>
            {t.doneSub} <strong>{targetLevel}</strong> ({t.doneMastery} {(resultMastery * 100).toFixed(0)}%).
          </p>

          {/* Email Verification Alert Banner */}
          <div style={{
            margin: '0 auto 2rem',
            maxWidth: '480px',
            padding: '12px 16px',
            background: '#eff6ff',
            border: '1.5px solid #60a5fa',
            borderRadius: '12px',
            color: '#1e40af',
            fontSize: '0.88rem',
            textAlign: 'left',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem'
          }}>
            <Mail size={22} color="#2563eb" style={{ flexShrink: 0 }} />
            <div>
              <strong style={{ color: '#1e3a8a' }}>Bestätigungs-E-Mail gesendet!</strong>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.82rem', color: '#1e40af' }}>
                Wir haben eine Bestätigungs-E-Mail an <u>{email}</u> gesendet. Bitte schaue in dein Postfach, um dein Konto zu verifizieren.
              </p>
            </div>
          </div>

          <button
            onClick={() => onComplete(registeredUser, resultMastery, targetLevel, profession)}
            className="btn btn-primary"
            style={{ padding: '14px 32px', fontSize: '1.05rem', background: '#1A6E6E', borderRadius: '12px' }}
          >
            {t.startJourneyBtn} <ChevronRight size={20} />
          </button>
        </div>
      )}
    </div>
  );
}
