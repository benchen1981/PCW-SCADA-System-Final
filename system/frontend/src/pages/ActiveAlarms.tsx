import React, { useEffect, useState } from 'react';
import { useScadaStore } from '../store/scadaStore';
import { pcwDataService } from '../services/PcwDataService';
import type { AlarmEvent } from '../domain/alarmTypes';

export const ActiveAlarms = () => {
  const activeAlarms = useScadaStore((s) => s.alarms);
  const acknowledgeAlarm = useScadaStore((s) => s.acknowledgeAlarm);
  const acknowledgeAllAlarms = useScadaStore((s) => s.acknowledgeAllAlarms);
  const shelveAlarm = useScadaStore((s) => s.shelveAlarm);
  const openTagDetail = useScadaStore((s) => s.openTagDetail);

  const [tab, setTab] = useState<'ALL' | 'ENG' | 'DRIFT' | 'QUALITY' | 'HISTORICAL'>('ALL');
  const [historical, setHistorical] = useState<AlarmEvent[]>([]);
  const [sysFilter, setSysFilter] = useState('');
  const [searchTag, setSearchTag] = useState('');

  useEffect(() => {
    if (tab === 'HISTORICAL') {
      pcwDataService.getAlarmHistory({}).then(setHistorical);
    }
  }, [tab]);

  const sourceList = tab === 'HISTORICAL' ? historical : activeAlarms;
  const engCount = activeAlarms.filter((a) => ['HIGH_HIGH', 'HIGH', 'LOW', 'LOW_LOW'].includes(a.alarmType)).length;
  const driftCount = activeAlarms.filter((a) => a.alarmType === 'DRIFT').length;
  const errCount = activeAlarms.filter((a) => a.alarmType === 'ERROR').length;

  const filtered = sourceList.filter((a) => {
    if (tab === 'ENG' && !['HIGH_HIGH', 'HIGH', 'LOW', 'LOW_LOW'].includes(a.alarmType)) return false;
    if (tab === 'DRIFT' && a.alarmType !== 'DRIFT') return false;
    if (tab === 'QUALITY' && a.alarmType !== 'ERROR') return false;
    if (sysFilter && a.systemId !== sysFilter) return false;
    if (searchTag && !a.tagId.toLowerCase().includes(searchTag.toLowerCase())) return false;
    return true;
  });

  const exportCsv = () => {
    const header = 'AlarmID,TagID,System,Type,Priority,State,Value,Limit,Unit,ActivatedAt,AcknowledgedAt,ClearedAt,Source\n';
    const rows = filtered
      .map((a) => [a.alarmId, a.tagId, a.systemId, a.alarmType, a.priority, a.state, a.value, a.limit, a.unit, a.activatedAt, a.acknowledgedAt ?? '', a.clearedAt ?? '', a.source].join(','))
      .join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pcw_alarms_${tab.toLowerCase()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', height: '100%' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.6rem' }}>
        <div>
          <h2 className="panel-title">5. ISA-18.2 Alarm & Early-Warning Center</h2>
          <div className="panel-subtitle">Strict separation between Hard Engineering Alarms (HH/H/L/LL) and Predictive Warnings (DRIFT)</div>
        </div>
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
          <button className={`btn ${tab === 'ALL' ? 'primary' : ''}`} onClick={() => setTab('ALL')}>All Active ({activeAlarms.length})</button>
          <button className={`btn ${tab === 'ENG' ? 'primary' : ''}`} onClick={() => setTab('ENG')}>Engineering ({engCount})</button>
          <button className={`btn ${tab === 'DRIFT' ? 'primary' : ''}`} onClick={() => setTab('DRIFT')}>Predictive Drift ({driftCount})</button>
          <button className={`btn ${tab === 'QUALITY' ? 'primary' : ''}`} onClick={() => setTab('QUALITY')}>Quality Error ({errCount})</button>
          <button className={`btn ${tab === 'HISTORICAL' ? 'primary' : ''}`} onClick={() => setTab('HISTORICAL')}>Archive</button>
          <button className="btn success" onClick={() => acknowledgeAllAlarms('HMI_OPERATOR')}>ACK ALL</button>
          <button className="btn" onClick={exportCsv}>Export CSV</button>
        </div>
      </div>

      <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.65rem', overflow: 'hidden' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <input className="input" placeholder="Search Tag ID..." value={searchTag} onChange={(e) => setSearchTag(e.target.value)} style={{ minWidth: '220px' }} />
          <select className="select" value={sysFilter} onChange={(e) => setSysFilter(e.target.value)}>
            <option value="">All Systems</option>
            {Array.from({ length: 8 }, (_, i) => `PCW0${i + 1}`).map((sys) => <option key={sys} value={sys}>{sys}</option>)}
          </select>
        </div>

        <div className="table-wrap" style={{ flex: 1 }}>
          <table>
            <thead>
              <tr>
                <th>Time (Local)</th>
                <th>Tag ID</th>
                <th>Type</th>
                <th>Source</th>
                <th>Priority</th>
                <th>State</th>
                <th>Value / Limit</th>
                <th>Message</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={9} style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--ink-muted)' }}>No alarms match current filter.</td></tr>
              ) : (
                filtered.map((a) => (
                  <tr key={a.alarmId}>
                    <td className="mono">{new Date(a.activatedAt).toLocaleString()}</td>
                    <td className="mono" style={{ fontWeight: 700, cursor: 'pointer', color: 'var(--brand-primary)' }} onClick={() => openTagDetail(a.tagId)}>{a.tagId}</td>
                    <td><span className={`badge ${a.alarmType === 'DRIFT' ? 't30' : a.alarmType === 'ERROR' ? 'warning' : 'alarm'}`}>{a.alarmType}</span></td>
                    <td className="mono" style={{ fontSize: '0.7rem' }}>{a.source}</td>
                    <td><span className={`badge ${a.priority === 'CRITICAL' ? 'alarm' : a.priority === 'HIGH' ? 't20' : 't30'}`}>{a.priority}</span></td>
                    <td><span className={`badge ${a.state.includes('UNACK') ? 'warning' : 'neutral'}`}>{a.state}</span></td>
                    <td className="mono">{a.value.toFixed(3)} / {a.limit} {a.unit}</td>
                    <td>{a.message}</td>
                    <td style={{ display: 'flex', gap: '0.3rem' }}>
                      {a.state.includes('UNACK') && (
                        <button className="btn primary" style={{ padding: '0.18rem 0.45rem', fontSize: '0.7rem' }} onClick={() => acknowledgeAlarm(a.alarmId, 'HMI_OPERATOR')}>ACK</button>
                      )}
                      {a.state.startsWith('ACTIVE') && (
                        <button className="btn" style={{ padding: '0.18rem 0.45rem', fontSize: '0.7rem' }} onClick={() => shelveAlarm(a.alarmId)}>Shelve</button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
