'use client';

import { useState, useEffect } from 'react';
import { BookOpen, Star, RefreshCw, ChevronRight, Brain, Flame, User, LogIn, LogOut, UserPlus } from 'lucide-react';
import styles from './page.module.css';
import axios from 'axios';
import Onboarding from '../components/Onboarding';
import KnowledgeGraph from '../components/KnowledgeGraph';
import StreakWidget from '../components/StreakWidget';
import DailyGoalBar from '../components/DailyGoalBar';
import { AuthModal } from '../components/AuthModal';
import { AuthGate } from '../components/AuthGate';
import { supabase } from '@/lib/supabaseClient';
import { API_URL } from '@/lib/api';

const BACKEND_URL = `${API_URL}/api/reader`;
const FALLBACK_USER_ID = "b99cf3a3-c5fe-473e-8305-7be69a6ba848"; // Fallback test user UUID

interface GeneratedText {
  id: number;
  content: string;
  target_word: any;
  anchors: any[];
}

export default function Home() {
  const [user, setUser] = useState<any>(null);
  const [userId, setUserId] = useState<string>(FALLBACK_USER_ID);
  
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');

  const [showOnboarding, setShowOnboarding] = useState<boolean>(false);
  const [showGraph, setShowGraph] = useState<boolean>(false);
  const [currentLevel, setCurrentLevel] = useState<string>("B1");
  const [userProfession, setUserProfession] = useState<string>("HEALTH");
  const [userSubdomain, setUserSubdomain] = useState<string | null>(null);
  const [streakTrigger, setStreakTrigger] = useState<number>(0);
  const [showStreakToast, setShowStreakToast] = useState<boolean>(false);
  const [currentText, setCurrentText] = useState<GeneratedText | null>(null);
  const [loading, setLoading] = useState(false);
  const [rating, setRating] = useState(0);
  const [difficulty, setDifficulty] = useState<string | null>(null);
  const [submittingRating, setSubmittingRating] = useState(false);
  const [progress, setProgress] = useState(12);

  // Helper: load domain & level from profiles table (authoritative source)
  const loadUserProfile = async (uid: string) => {
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('domain, target_domain, subdomain, current_level, target_level')
        .eq('id', uid)
        .single();
      if (data && !error) {
        const rawDomain = data.target_domain || data.domain;
        if (rawDomain) {
          const normDomain = ['IT', 'HEALTH', 'ACADEMIC'].includes(rawDomain) ? rawDomain : 'HEALTH';
          setUserProfession(normDomain);
        }
        if (data.subdomain) setUserSubdomain(data.subdomain);
        if (data.target_level) setCurrentLevel(data.target_level);
      }
    } catch (_) {
      // profiles table may not exist yet — fall back to user_metadata
    }
  };

  // 1. Supabase Auth Session Listener
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) {
        setUser(user);
        setUserId(user.id);
        if (user.user_metadata?.profession) {
          const p = user.user_metadata.profession;
          const normP = ['IT', 'HEALTH', 'ACADEMIC'].includes(p) ? p : 'HEALTH';
          setUserProfession(normP);
        }
        if (user.user_metadata?.subdomain) setUserSubdomain(user.user_metadata.subdomain);
        if (user.user_metadata?.target_level) setCurrentLevel(user.user_metadata.target_level);
        loadUserProfile(user.id);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const activeUser = session?.user || null;
      setUser(activeUser);
      if (activeUser) {
        setUserId(activeUser.id);
        if (activeUser.user_metadata?.profession) {
          const p = activeUser.user_metadata.profession;
          const normP = ['IT', 'HEALTH', 'ACADEMIC'].includes(p) ? p : 'HEALTH';
          setUserProfession(normP);
        }
        if (activeUser.user_metadata?.subdomain) setUserSubdomain(activeUser.user_metadata.subdomain);
        if (activeUser.user_metadata?.target_level) setCurrentLevel(activeUser.user_metadata.target_level);
        loadUserProfile(activeUser.id);
      } else {
        setUserId(FALLBACK_USER_ID);
      }
    });

    return () => subscription.unsubscribe();
  }, []);
  
  const getAuthHeaders = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      return { Authorization: `Bearer ${session.access_token}` };
    }
    return {};
  };

  const handleExport = async () => {
    const headers = await getAuthHeaders();
    const token = headers.Authorization ? headers.Authorization.replace('Bearer ', '') : '';
    window.location.href = `${BACKEND_URL}/export/${userId}?token=${token}`;
  };

  const fetchNextText = async (targetLvl?: string, targetProf?: string, targetSub?: string | null) => {
    setLoading(true);
    setRating(0);
    setDifficulty(null);
    try {
      const rawDomain = targetProf || userProfession || "HEALTH";
      const domain = ['IT', 'HEALTH', 'ACADEMIC'].includes(rawDomain) ? rawDomain : 'HEALTH';
      const sub = targetSub !== undefined ? targetSub : userSubdomain;
      const headers = await getAuthHeaders();
      if (!headers.Authorization) {
        console.warn("[Reader] No active auth session token found. Skipping protected fetch.");
        setLoading(false);
        return;
      }
      const response = await axios.post(
        `${BACKEND_URL}/generate`,
        {
          user_id: userId,
          target_level: targetLvl || currentLevel,
          target_domain: domain,
          subdomain: sub || undefined,
        },
        { headers }
      );
      setCurrentText(response.data);
    } catch (error: any) {
      console.error("Failed to fetch text", error);
      if (error?.response?.status === 401) {
        console.warn("[Reader] 401 Unauthorized received. Session is invalid or email unconfirmed.");
        setUser(null);
        setAuthModalMode('login');
        setShowAuthModal(true);
      }
    }
    setLoading(false);
  };

  const getProfessionBadge = (prof: string, sub?: string | null) => {
    if (sub === 'MEDIZIN') return '🩺 Arzt / Ärztin';
    if (sub === 'PFLEGE') return '🏥 Pflegekraft';
    if (sub === 'PHYSIO') return '🏋️ Physiotherapie';
    if (sub === 'PHARMA') return '💊 Pharmazie';

    switch(prof) {
      case 'PFLEGE': return '🏥 Pflegekraft';
      case 'MEDIZIN': return '🩺 Arzt / Ärztin';
      case 'PHYSIO': return '🏋️ Physiotherapie';
      case 'PHARMA': return '💊 Pharmazie';
      case 'HEALTH': return '🏥 Medizin & Gesundheit';
      case 'IT': return '💻 IT & Software';
      case 'ACADEMIC': return '🎓 Akademisch';
      default: return '💻 IT & Software';
    }
  };

  const fetchProgress = async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await axios.get(`${BACKEND_URL}/progress/${userId}`, { headers });
      setProgress(response.data.percentage);
    } catch (error) {
      console.error("Failed to fetch progress", error);
    }
  };

  useEffect(() => {
    if (user && !currentText && !loading) {
      fetchNextText();
      fetchProgress();
    }
  }, [user?.id]);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
    setUserId(FALLBACK_USER_ID);
  };

  const handleRate = async () => {
    if (!currentText || rating === 0 || !difficulty) return;
    
    setSubmittingRating(true);
    
    try {
      const headers = await getAuthHeaders();
      await axios.post(
        `${BACKEND_URL}/rate`,
        {
          user_id: userId,
          generated_text_id: currentText.id,
          rating: rating,
          difficulty: difficulty
        },
        { headers }
      );
      
      setStreakTrigger(prev => prev + 1);
      setShowStreakToast(true);
      setTimeout(() => setShowStreakToast(false), 4000);

      setTimeout(() => {
        fetchNextText();
        fetchProgress();
      }, 1000);
      
    } catch (error) {
      console.error("Failed to submit rating", error);
    }
    
    setSubmittingRating(false);
  };

  // Simple tokenization for MVP highlight
  const renderText = () => {
    if (!currentText) return null;
    
    const words = currentText.content.split(/(\s+|[.,!?]+)/);
    const targetLemma = currentText.target_word?.lemma?.toLowerCase();
    
    const targetCount = 1; 
    let anchorCount = 0;
    const contentLower = currentText.content.toLowerCase();
    currentText.anchors?.forEach(a => {
      if (a.lemma && contentLower.includes(a.lemma.toLowerCase())) {
        anchorCount++;
      }
    });
    
    return (
      <div className={styles.textDisplay}>
        <div style={{fontSize: '0.875rem', color: '#10b981', marginBottom: '1rem', fontWeight: 500}}>
          🏆 Heute hast du {targetCount} neues Wort und {anchorCount} bekannte Wörter geübt.
        </div>
        {words.map((w, i) => {
          const wLower = w.toLowerCase();
          const cleanWLower = wLower.replace(/[^a-zäöüß]/g, '');
          
          let matchedGloss = null;
          let isTarget = false;
          
          if (targetLemma && cleanWLower === targetLemma) {
            isTarget = true;
            matchedGloss = currentText.target_word?.german_gloss;
          } else {
            const anchor = currentText.anchors?.find(a => {
              const aLemma = a.lemma?.toLowerCase();
              return aLemma && cleanWLower === aLemma;
            });
            if (anchor) {
              matchedGloss = anchor.german_gloss;
            }
          }
          
          if (w.trim() === '') return <span key={i}>{w}</span>;
          
          return (
            <span 
              key={i} 
              className={`${styles.word} ${isTarget ? styles.targetWord : ''}`}
            >
              {w}
              {matchedGloss && <span className={styles.tooltip}>{matchedGloss}</span>}
            </span>
          );
        })}
      </div>
    );
  };

  // 1. Mandatory Auth Gate: If user is not logged in and not in onboarding wizard
  if (!user && !showOnboarding) {
    return (
      <AuthGate
        onSuccessLogin={(loggedInUser) => {
          setUser(loggedInUser);
          setUserId(loggedInUser.id);
          if (loggedInUser.user_metadata?.profession) setUserProfession(loggedInUser.user_metadata.profession);
          if (loggedInUser.user_metadata?.target_level) setCurrentLevel(loggedInUser.user_metadata.target_level);
        }}
        onStartRegistration={() => {
          setShowOnboarding(true);
        }}
      />
    );
  }

  // 2. Registration Calibration Wizard Step
  if (showOnboarding) {
    return (
      <main className={styles.main}>
        <Onboarding
          userId={userId}
          backendUrl={BACKEND_URL}
          onCancel={user ? () => setShowOnboarding(false) : undefined}
          onComplete={(newAuthUser, _mastery, level, prof, sub, hasSession) => {
            // Persist profession & level from onboarding into state
            if (prof) {
              const normP = ['IT', 'HEALTH', 'ACADEMIC'].includes(prof) ? prof : 'HEALTH';
              setUserProfession(normP);
            }
            if (sub) setUserSubdomain(sub);
            if (level) setCurrentLevel(level);

            setShowOnboarding(false);

            if (hasSession && newAuthUser) {
              setUser(newAuthUser);
              setUserId(newAuthUser.id);
              fetchNextText(level, prof, sub);
              fetchProgress();
            } else {
              // Email confirmation strictly required -> prompt login
              setAuthModalMode('login');
              setShowAuthModal(true);
            }
          }}
        />
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <header className={styles.header} style={{ width: '100%', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', width: '100%', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <img src="/logos/drain-wordmark-logo-teal.svg" alt="Drain" style={{ height: '72px', width: 'auto' }} />
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{
              padding: '6px 12px',
              fontSize: '0.85rem',
              fontWeight: 700,
              borderRadius: '8px',
              background: '#e6f4f4',
              color: '#1A6E6E',
              border: '1.5px solid #1A6E6E'
            }}>
              {getProfessionBadge(userProfession, userSubdomain)}
            </span>
            <StreakWidget 
              userId={userId} 
              backendUrl={BACKEND_URL} 
              refreshTrigger={streakTrigger} 
            />
            <button 
              onClick={() => { setShowGraph(!showGraph); setShowOnboarding(false); }} 
              className="btn btn-secondary"
              style={{
                padding: '7px 14px', 
                fontSize: '0.85rem', 
                fontWeight: 600,
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.4rem',
                borderRadius: '8px',
                border: '1.5px solid #1A6E6E',
                background: showGraph ? '#1A6E6E' : '#fff',
                color: showGraph ? '#fff' : '#1A6E6E',
                cursor: 'pointer'
              }}
            >
              <Brain size={16} /> {showGraph ? "Hauptansicht" : "Wort-Netzwerk"}
            </button>


            {/* Auth Profile Controls */}
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '0.25rem' }}>
                <span style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  color: '#334155',
                  padding: '6px 10px',
                  borderRadius: '8px',
                  background: '#f1f5f9',
                  border: '1px solid #cbd5e1'
                }}>
                  <User size={15} color="#1A6E6E" />
                  {user.user_metadata?.full_name || user.email?.split('@')[0]}
                </span>
                <button
                  onClick={handleSignOut}
                  title="Abmelden"
                  style={{
                    padding: '7px 10px',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: '1px solid #fecaca',
                    background: '#fef2f2',
                    color: '#991b1b',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem'
                  }}
                >
                  <LogOut size={15} /> Abmelden
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '0.4rem', marginLeft: '0.25rem' }}>
                <button
                  onClick={() => { setAuthModalMode('login'); setShowAuthModal(true); }}
                  style={{
                    padding: '7px 12px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: '1.5px solid #1A6E6E',
                    background: '#ffffff',
                    color: '#1A6E6E',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem'
                  }}
                >
                  <LogIn size={15} /> Anmelden
                </button>
                <button
                  onClick={() => { setAuthModalMode('register'); setShowAuthModal(true); }}
                  style={{
                    padding: '7px 12px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, #1A6E6E 0%, #0d4b4b 100%)',
                    color: '#ffffff',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    boxShadow: '0 2px 4px rgba(26, 110, 110, 0.2)'
                  }}
                >
                  <UserPlus size={15} /> Registrieren
                </button>
              </div>
            )}
          </div>
        </div>
        <p className={styles.subtitle} style={{ margin: 0, textAlign: 'left', fontSize: '0.95rem' }}>Meaningful input for faster learning.</p>

        {showStreakToast && (
          <div style={{
            margin: '0.75rem 0 0',
            padding: '10px 16px',
            background: '#fff7ed',
            border: '1.5px solid #f97316',
            borderRadius: '10px',
            color: '#c2410c',
            fontWeight: 600,
            fontSize: '0.9rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Flame size={20} fill="#f97316" color="#ea580c" />
            <span>🔥 Daily Streak Aktiv! Tolle Arbeit, dein tägliches Leseziel wurde erreicht!</span>
          </div>
        )}
      </header>

      {showGraph ? (
        <KnowledgeGraph 
          userId={userId} 
          backendUrl={BACKEND_URL} 
        />
      ) : (
        <>
          <div className={`card ${styles.readerContainer}`}>
            {loading ? (
              <div style={{display: 'flex', justifyContent: 'center', padding: '4rem', color: '#94a3b8'}}>
                <RefreshCw className="animate-spin" size={32} />
              </div>
            ) : currentText ? (
              <div className="animate-in">
                {renderText()}
                
                <div className={styles.controls}>
                  <div className={styles.ratingSection}>
                    <span className={styles.ratingLabel}>Wie war dieser Text für dich?</span>
                    
                    <div style={{display: 'flex', gap: '1rem', alignItems: 'center'}}>
                      <div className={styles.stars}>
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button 
                            key={star}
                            onClick={() => setRating(star)}
                            disabled={submittingRating}
                            className={`${styles.star} ${rating >= star ? styles.active : ''}`}
                          >
                            <Star size={24} fill={rating >= star ? "currentColor" : "none"} />
                          </button>
                        ))}
                      </div>

                      {rating > 0 && (
                        <div style={{display: 'flex', gap: '0.5rem'}}>
                          {["Zu einfach", "Genau richtig", "Zu schwer"].map((diff) => (
                            <button
                              key={diff}
                              onClick={() => setDifficulty(diff)}
                              disabled={submittingRating}
                              className={`btn ${difficulty === diff ? 'btn-primary' : 'btn-secondary'}`}
                              style={{padding: '6px 12px', fontSize: '0.8rem'}}
                            >
                              {diff}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <button 
                    onClick={handleRate} 
                    className={`btn btn-primary`}
                    disabled={loading || submittingRating || !difficulty}
                  >
                    Senden <ChevronRight size={18} />
                  </button>
                </div>
              </div>
            ) : (
              <div style={{textAlign: 'center', padding: '2rem'}}>
                <p>Fehler beim Laden des Textes.</p>
                <button onClick={() => fetchNextText()} className="btn btn-primary" style={{marginTop: '1rem'}}>
                  Erneut versuchen
                </button>
              </div>
            )}
          </div>

          <DailyGoalBar 
            userId={userId} 
            backendUrl={BACKEND_URL} 
            refreshTrigger={streakTrigger} 
          />
        </>
      )}

      <AuthModal
        isOpen={showAuthModal}
        initialMode={authModalMode}
        onClose={() => setShowAuthModal(false)}
        onSuccess={(authenticatedUser, prof, lvl) => {
          setUser(authenticatedUser);
          setUserId(authenticatedUser.id);
          if (prof) setUserProfession(prof);
          if (lvl) setCurrentLevel(lvl);
          setShowAuthModal(false);
          fetchNextText(lvl, prof);
          fetchProgress();
        }}
      />
      
      <div style={{position: 'fixed', bottom: '2rem', left: '2rem'}}>
        <button onClick={handleExport} className="btn btn-secondary" style={{fontSize: '0.875rem', padding: '8px 16px', background: 'var(--card-bg)', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'}}>
          📥 Digitales Gehirn herunterladen (.zip)
        </button>
      </div>
    </main>
  );
}
