import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useScadaStore } from '../store/scadaStore';

interface GlobalAlarmSummaryProps {
  alarmState: 'normal' | 'collapsed' | 'expanded';
  setAlarmState: (state: 'normal' | 'collapsed' | 'expanded') => void;
}

export const GlobalAlarmSummary: React.FC<GlobalAlarmSummaryProps> = ({ alarmState, setAlarmState }) => {
  const alarms = useScadaStore((s) => s.alarms);
  const acknowledgeAlarm = useScadaStore((s) => s.acknowledgeAlarm);
  const acknowledgeAllAlarms = useScadaStore((s) => s.acknowledgeAllAlarms);
  const navigate = useNavigate();

  const activeAlarmsList = [...alarms]
    .filter((a) => a.state.startsWith('ACTIVE') || a.state === 'CLEARED_UNACK')
    .sort((a, b) => new Date(b.activatedAt || 0).getTime() - new Date(a.activatedAt || 0).getTime())
    .slice(0, 12);

  const unackAlarms = activeAlarmsList.filter((a) => a.state.includes('UNACK'));
  const highest = unackAlarms.find((a) => a.priority === 'CRITICAL') || unackAlarms[0];

  const formatTime = (iso?: string) => {
    if (!iso) return '--';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '--';
    return d.toLocaleTimeString('en-GB', { hour12: false });
  };

  const toggleState = () => {
    if (alarmState === 'collapsed') setAlarmState('normal');
    else if (alarmState === 'normal') setAlarmState('expanded');
    else setAlarmState('collapsed');
  };

  return (
    <footer className="global-alarm-summary">
      <div
        className={`alarm-summary-header ${highest ? 'alarm-flash' : ''}`}
        onClick={toggleState}
        style={{
          background: highest ? (highest.priority === 'CRITICAL' ? '#fee2e2' : '#fef3c7') : 'var(--bg-subtle)',
          color: 'var(--ink-primary)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', fontSize: '0.8rem', fontWeight: 800 }}>
          <span>{highest ? `UNACK ALARM: ${highest.tagId} — ${highest.message}` : 'ISA-18.2 GLOBAL ALARM STREAM'}</span>
          <span className={`badge ${unackAlarms.length ? 'alarm' : 'normal'}`}>UNACK {unackAlarms.length}</span>
          <span className="badge warning">ACTIVE {activeAlarmsList.length}</span>
        </div>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {unackAlarms.length > 0 && (
            <button
              className="btn success"
              style={{ padding: '0.22rem 0.55rem', fontSize: '0.72rem' }}
              onClick={(e) => {
                e.stopPropagation();
                acknowledgeAllAlarms('HMI_OPERATOR');
              }}
            >
              ACK ALL
            </button>
          )}
          <button className="btn" style={{ padding: '0.22rem 0.55rem', fontSize: '0.72rem' }} onClick={(e) => { e.stopPropagation(); navigate('/alarms'); }}>
            Alarm Center
          </button>
          <button className="btn" style={{ padding: '0.22rem 0.55rem', fontSize: '0.72rem' }} onClick={(e) => { e.stopPropagation(); toggleState(); }}>
            {alarmState === 'collapsed' ? 'Expand' : alarmState === 'expanded' ? 'Collapse' : 'Height'}
          </button>
        </div>
      </div>

      <div className="alarm-summary-content">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Tag</th>
              <th>Type</th>
              <th>Value / Limit</th>
              <th>Priority</th>
              <th>State</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {activeAlarmsList.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--ink-muted)', padding: '1rem' }}>No active or unacknowledged alarms.</td>
              </tr>
            ) : (
              activeAlarmsList.map((a) => (
                <tr key={a.alarmId}>
                  <td className="mono">{formatTime(a.activatedAt)}</td>
                  <td className="mono" style={{ fontWeight: 700 }}>{a.tagId}</td>
                  <td><span className={`badge ${a.alarmType === 'DRIFT' ? 't30' : 'alarm'}`}>{a.alarmType}</span></td>
                  <td className="mono">{a.value.toFixed(3)} / {a.limit} {a.unit}</td>
                  <td><span className={`badge ${a.priority === 'CRITICAL' ? 'alarm' : a.priority === 'HIGH' ? 't20' : 't30'}`}>{a.priority}</span></td>
                  <td><span className={`badge ${a.state.includes('UNACK') ? 'warning' : 'neutral'}`}>{a.state}</span></td>
                  <td>
                    {a.state.includes('UNACK') && (
                      <button className="btn primary" style={{ padding: '0.16rem 0.45rem', fontSize: '0.68rem' }} onClick={() => acknowledgeAlarm(a.alarmId, 'HMI_OPERATOR')}>
                        ACK
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </footer>
  );
};
