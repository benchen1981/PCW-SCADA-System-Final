import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useScadaStore } from './store/scadaStore';
import { SystemOverview } from './pages/SystemOverview';
import { LiveSensors } from './pages/LiveSensors';
import { HistorianTrend } from './pages/HistorianTrend';
import { ActiveAlarms } from './pages/ActiveAlarms';
import { PredictionT30 } from './pages/PredictionT30';
import { ModbusMonitor } from './pages/ModbusMonitor';
import { PredictionModelInfo } from './components/PredictionModelInfo';
import { PredictionSettings } from './pages/PredictionSettings';
import { GlobalTagDetail } from './pages/GlobalTagDetail';
import { LiveTrend } from './pages/LiveTrend';
import { GlobalAlarmSummary } from './components/GlobalAlarmSummary';
import { API_CONFIG } from './api/config';
import './index.css';

const GlobalClock = () => {
  const [timeStr, setTimeStr] = useState('--');
  useEffect(() => {
    const update = () => {
      try {
        const parts = new Intl.DateTimeFormat('en-CA', {
          timeZone: 'Asia/Taipei',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }).formatToParts(new Date());
        const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '--';
        setTimeStr(`${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')}`);
      } catch {
        setTimeStr('--');
      }
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);
  return <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--ink-secondary)', fontWeight: 700 }}>{timeStr} CST</span>;
};

const TopNavigation = () => {
  const location = useLocation();
  const alarms = useScadaStore((s) => s.alarms);
  const connectionMode = useScadaStore((s) => s.connectionMode);
  const unackCount = alarms.filter((a) => a.state.includes('UNACK')).length;

  const navs = [
    { path: '/', label: '1. Plant Overview' },
    { path: '/sensors', label: '2. Live Sensor Data' },
    { path: '/historian', label: '3. Historian Trend' },
    { path: '/live-trend', label: '4. Live Trend' },
    { path: '/alarms', label: '5. Alarm Center', badge: unackCount > 0 ? `${unackCount}` : null },
    { path: '/t30', label: '6. System Prediction' },
    { path: '/settings', label: '7. Prediction Tuning' },
    { path: '/modbus', label: '8. Modbus Simulator' },
    { path: '/model-info', label: '9. Prediction Model Info' },
  ];

  const modeBadge =
    connectionMode === 'WS_LIVE'
      ? { label: 'LIVE STREAM', cls: 'normal' }
      : connectionMode === 'REST_POLL'
      ? { label: 'REST SYNC', cls: 'info' }
      : { label: 'LOCAL SIM', cls: 'warning' };

  return (
    <header className="top-navigation">
      <div className="top-nav-logo">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          <h2>PCW SCADA</h2>
          <span className={`badge ${modeBadge.cls}`} style={{ fontSize: '0.64rem', padding: '0.08rem 0.35rem' }}>
            {modeBadge.label}
          </span>
        </div>
        <GlobalClock />
      </div>

      <nav className="top-nav-links" aria-label="Main SCADA Navigation">
        {navs.map((n) => {
          const isActive = location.pathname === n.path || (n.path === '/' && location.pathname === '');
          return (
            <Link key={n.path} to={n.path} className={`top-nav-item ${isActive ? 'active' : ''}`}>
              <span>{n.label}</span>
              {n.badge && (
                <span className="badge alarm alarm-flash" style={{ fontSize: '0.66rem', padding: '0.05rem 0.35rem' }}>
                  ALARM {n.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </header>
  );
};

export default function App() {
  const startPolling = useScadaStore((s) => s.startPolling);
  const stopPolling = useScadaStore((s) => s.stopPolling);
  const [alarmState, setAlarmState] = useState<'normal' | 'collapsed' | 'expanded'>('normal');

  useEffect(() => {
    startPolling(1000);
    if (API_CONFIG.USE_MOCK) {
      useScadaStore.getState().setSimulatorControl('START', 1000);
    }
    return () => stopPolling();
  }, [startPolling, stopPolling]);

  return (
    <BrowserRouter>
      <div className={`scada-shell ${alarmState === 'collapsed' ? 'alarm-collapsed' : alarmState === 'expanded' ? 'alarm-expanded' : ''}`}>
        <TopNavigation />
        <main className="scada-workspace">
          <Routes>
            <Route path="/" element={<SystemOverview />} />
            <Route path="/submain/:systemId" element={<LiveSensors />} />
            <Route path="/sensors" element={<LiveSensors />} />
            <Route path="/historian" element={<HistorianTrend />} />
            <Route path="/live-trend" element={<LiveTrend />} />
            <Route path="/alarms" element={<ActiveAlarms />} />
            <Route path="/t30" element={<PredictionT30 />} />
            <Route path="/modbus" element={<ModbusMonitor />} />
            <Route path="/model-info" element={<PredictionModelInfo />} />
            <Route path="/settings" element={<PredictionSettings />} />
          </Routes>
        </main>
        <GlobalAlarmSummary alarmState={alarmState} setAlarmState={setAlarmState} />
        <GlobalTagDetail />
      </div>
    </BrowserRouter>
  );
}
