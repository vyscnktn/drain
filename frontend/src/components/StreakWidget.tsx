'use client';

import React, { useState, useEffect } from 'react';
import { Flame, Check, ShieldCheck, ChevronDown } from 'lucide-react';
import axios from 'axios';
import { supabase } from '@/lib/supabaseClient';
import { API_URL } from '@/lib/api';

interface StreakData {
  current_streak: number;
  last_activity_date: string | null;
  streak_freeze: boolean;
  weekly_history: Record<string, boolean>;
}

interface StreakWidgetProps {
  userId: string;
  backendUrl: string;
  refreshTrigger?: number;
}

export default function StreakWidget({ userId, backendUrl, refreshTrigger }: StreakWidgetProps) {
  const [streakData, setStreakData] = useState<StreakData>({
    current_streak: 0,
    last_activity_date: null,
    streak_freeze: true,
    weekly_history: { Mo: false, Di: false, Mi: false, Do: false, Fr: false, Sa: false, So: false }
  });

  const [showPopover, setShowPopover] = useState<boolean>(false);

  const fetchStreak = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const headers = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {};
      const url = `${backendUrl || `${API_URL}/api/reader`}/streak/${userId}`;
      const res = await axios.get(url, { headers });
      if (res.data) {
        setStreakData(res.data);
      }
    } catch (err) {
      console.error("Failed to fetch streak data", err);
    }
  };

  useEffect(() => {
    fetchStreak();
  }, [userId, refreshTrigger]);

  const daysOrder = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      {/* Header Flame Badge */}
      <button
        type="button"
        onClick={() => setShowPopover(!showPopover)}
        onMouseEnter={() => setShowPopover(true)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '6px 14px',
          borderRadius: '9999px',
          border: '1.5px solid #f97316',
          background: '#fff7ed',
          color: '#ea580c',
          fontWeight: 700,
          fontSize: '0.85rem',
          cursor: 'pointer',
          boxShadow: '0 2px 4px rgba(249, 115, 22, 0.1)'
        }}
      >
        <Flame size={18} fill="#f97316" color="#ea580c" className="animate-bounce-subtle" />
        <span>{streakData.current_streak} {streakData.current_streak === 1 ? 'Tag' : 'Tage'} Streak</span>
        <ChevronDown size={14} style={{ opacity: 0.7 }} />
      </button>

      {/* Expandable Activity Popover */}
      {showPopover && (
        <div
          onMouseLeave={() => setShowPopover(false)}
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            width: '260px',
            background: '#ffffff',
            borderRadius: '16px',
            padding: '1.25rem',
            boxShadow: '0 10px 25px -5px rgba(0,0,0,0.15), 0 8px 10px -6px rgba(0,0,0,0.1)',
            border: '1px solid #fed7aa',
            zIndex: 100
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#9a3412' }}>
              Wöchentliche Aktivität
            </span>
            {streakData.streak_freeze && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '3px', fontSize: '0.7rem', color: '#1A6E6E', background: '#e6f4f4', padding: '2px 8px', borderRadius: '9999px', fontWeight: 600 }}>
                <ShieldCheck size={12} /> Freeze Aktiv
              </span>
            )}
          </div>

          {/* 7-Day Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', textAlign: 'center' }}>
            {daysOrder.map((day) => {
              const isActive = streakData.weekly_history[day];
              return (
                <div key={day} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#64748b' }}>{day}</span>
                  <div
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: isActive ? '#10b981' : '#f1f5f9',
                      color: isActive ? '#ffffff' : '#cbd5e1',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.75rem',
                      fontWeight: 700
                    }}
                  >
                    {isActive ? <Check size={14} strokeWidth={3} /> : '•'}
                  </div>
                </div>
              );
            })}
          </div>

          <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '1rem', marginBottom: 0, textAlign: 'center', lineHeight: '1.4' }}>
            Lese täglich mindestens <strong>1 Text</strong>, um deine Lese-Serie aufrechtzuerhalten!
          </p>
        </div>
      )}
    </div>
  );
}
