'use client';

import React, { useState, useEffect } from 'react';
import { Zap, Flame, Award, CheckCircle2 } from 'lucide-react';
import axios from 'axios';
import { supabase } from '@/lib/supabaseClient';

interface DailyGoalBarProps {
  userId: string;
  backendUrl: string;
  refreshTrigger?: number;
}

export default function DailyGoalBar({ userId, backendUrl, refreshTrigger }: DailyGoalBarProps) {
  const [goal, setGoal] = useState({
    count: 0,
    target: 10,
    completed: false
  });

  const fetchGoal = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const headers = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {};
      const url = `${backendUrl || 'http://localhost:8000/api/reader'}/streak/${userId}`;
      const res = await axios.get(url, { headers });
      if (res.data && res.data.daily_goal) {
        setGoal(res.data.daily_goal);
      }
    } catch (err) {
      console.error("Failed to fetch daily goal", err);
    }
  };

  useEffect(() => {
    fetchGoal();
  }, [userId, refreshTrigger]);

  const steps = Array.from({ length: 10 }, (_, i) => i + 1);

  return (
    <div style={{
      width: '100%',
      maxWidth: '680px',
      margin: '1.5rem auto 0',
      padding: '1.25rem 1.5rem',
      background: '#ffffff',
      borderRadius: '16px',
      boxShadow: '0 4px 20px -2px rgba(0,0,0,0.05)',
      border: goal.completed ? '2px solid #10b981' : '1px solid #e2e8f0'
    }}>
      {/* Header Info */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {goal.completed ? (
            <CheckCircle2 size={20} color="#10b981" />
          ) : (
            <Zap size={20} color="#f97316" fill="#f97316" className="animate-pulse" />
          )}
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
            {goal.completed ? '🎉 Tagesziel erreicht!' : 'Tägliches Leseziel'}
          </span>
        </div>

        <span style={{
          fontSize: '0.85rem',
          fontWeight: 700,
          color: goal.completed ? '#10b981' : '#1A6E6E',
          background: goal.completed ? '#ecfdf5' : '#e6f4f4',
          padding: '2px 10px',
          borderRadius: '9999px'
        }}>
          {goal.count} / 10 Texte
        </span>
      </div>

      {/* 10-Step Segmented Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(10, 1fr)', gap: '6px', height: '10px' }}>
        {steps.map((stepNum) => {
          const isFilled = stepNum <= goal.count;
          return (
            <div
              key={stepNum}
              style={{
                height: '100%',
                borderRadius: '9999px',
                background: isFilled 
                  ? (goal.completed ? '#10b981' : 'linear-gradient(90deg, #1A6E6E 0%, #10b981 100%)')
                  : '#f1f5f9',
                transition: 'all 0.4s ease-in-out',
                boxShadow: isFilled ? '0 2px 4px rgba(26, 110, 110, 0.2)' : 'none'
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
