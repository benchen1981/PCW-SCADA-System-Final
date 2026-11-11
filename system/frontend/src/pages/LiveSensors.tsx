import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useScadaStore } from '../store/scadaStore';

export const LiveSensors = () => {
  const sensors = useScadaStore((s) => s.sensors);
  const predictions = useScadaStore((s) => s.predictions);
  const lastFetch = useScadaStore((s) => s.lastFetch);
  const openTagDetail = useScadaStore((s) => s.openTagDetail);
  const [searchParams] = useSearchParams();
  const querySys = searchParams.get('systemId');

  const [viewMode, setViewMode] = useState<'PROCESS' | 'TABLE'>('PROCESS');
  const [selectedPcw, setSelectedPcw] = useState(querySys || 'PCW01');
  const [selectedSubmain, setSelectedSubmain] = useState('Submain01');

  const [search, setSearch] = useState('');
  const [sysFilter, setSysFilter] = useState(querySys || '');
  const [measFilter, setMeasFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    if (querySys) {
      setSelectedPcw(querySys);
      setSysFilter(querySys);
    }
  }, [querySys]);

  const predMap = new Map(predictions.map((p) => [p.tagId, p]));
  const subSensors = sensors.filter((s) => s.systemId === selectedPcw && s.submainId === selectedSubmain);
  const findPos = (suffix: string) => subSensors.find((s) => s.tagId.endsWith(suffix));
  const pts = findPos('.PTS');
  const ft = findPos('.FT');
  const ptr = findPos('.PTR');
  const pdt = findPos('.PDT');

  const filtered = sensors.filter((s) => {
    if (search && !s.tagId.toLowerCase().includes(search.toLowerCase())) return false;
    if (sysFilter && s.systemId !== sysFilter) return false;
    if (measFilter && s.measurementType !== measFilter) return false;
    if (statusFilter && s.status !== statusFilter) return false;
    return true;
  });

  const limitPct = (val: number, ll: number, hh: number) =>
    hh > ll ? Math.max(2, Math.min(98, ((val - ll) / (hh - ll)) * 100)) : 50;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', height: '100%' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.65rem 1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <div className="panel-title">2. Live Sensor Data & Submain P&ID Schematic</div>
          <div className="panel-subtitle mono">Last Telemetry Frame: {lastFetch ? new Date(lastFetch).toLocaleTimeString() : '--'} · Total {sensors.length} Points</div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className={`btn ${viewMode === 'PROCESS' ? 'primary' : ''}`} onClick={() => setViewMode('PROCESS')}>Process P&ID View</button>
          <button className={`btn ${viewMode === 'TABLE' ? 'primary' : ''}`} onClick={() => setViewMode('TABLE')}>320-Tag Matrix ({filtered.length})</button>
        </div>
      </div>

      {viewMode === 'PROCESS' ? (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Loop:</label>
            <select className="select" value={selectedPcw} onChange={(e) => setSelectedPcw(e.target.value)}>
              {Array.from({ length: 8 }, (_, i) => `PCW0${i + 1}`).map((id) => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
            <label style={{ fontSize: '0.8rem', fontWeight: 700 }}>Submain Pair:</label>
            <select className="select" value={selectedSubmain} onChange={(e) => setSelectedSubmain(e.target.value)}>
              {Array.from({ length: 10 }, (_, i) => `Submain${String(i + 1).padStart(2, '0')}`).map((id) => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
            <span className="badge info">Each Submain: 1 PTS + 1 FT + 1 PTR + 1 PDT (Closed Hydraulic Loop)</span>
          </div>

          {/* Clean SVG P&ID Loop Diagram */}
          <div style={{ background: 'var(--bg-subtle)', border: '1.5px solid var(--border-strong)', borderRadius: '8px', padding: '1rem' }}>
            <svg viewBox="0 0 920 260" style={{ width: '100%', maxHeight: '260px', display: 'block' }}>
              {/* Supply Header -> Tool */}
              <line x1="50" y1="65" x2="720" y2="65" stroke="#0369a1" strokeWidth="6" />
              <line x1="720" y1="65" x2="720" y2="195" stroke="#475569" strokeWidth="5" strokeDasharray="6 4" />
              {/* Tool -> Return Header */}
              <line x1="720" y1="195" x2="50" y2="195" stroke="#0f766e" strokeWidth="6" />
              {/* Differential bridge */}
              <line x1="170" y1="65" x2="170" y2="195" stroke="#64748b" strokeWidth="2.5" strokeDasharray="4 4" />

              {/* Tool Heat Exchanger Block */}
              <rect x="650" y="95" width="190" height="70" rx="8" fill="#ffffff" stroke="#0f172a" strokeWidth="2.5" />
              <text x="745" y="125" textAnchor="middle" fontWeight="800" fontSize="14" fill="#0f172a">FAB PROCESS TOOL</text>
              <text x="745" y="147" textAnchor="middle" fontSize="12" fill="#475569">{selectedPcw} · {selectedSubmain}</text>

              {/* Instrument Nodes */}
              {[
                { x: 280, y: 65, title: 'PTS (Supply Pressure)', s: pts, color: '#0369a1' },
                { x: 500, y: 65, title: 'FT (Supply Flow)', s: ft, color: '#1d4ed8' },
                { x: 390, y: 195, title: 'PTR (Return Pressure)', s: ptr, color: '#0f766e' },
                { x: 170, y: 130, title: 'PDT (Supply - Return ΔP)', s: pdt, color: '#b45309' },
              ].map((node, i) => {
                const p = node.s ? predMap.get(node.s.tagId) : undefined;
                return (
                  <g key={i} style={{ cursor: 'pointer' }} onClick={() => node.s && openTagDetail(node.s.tagId)}>
                    <rect x={node.x - 95} y={node.y - 32} width="190" height="64" rx="8" fill="#ffffff" stroke={node.s?.status === 'ALARM' ? '#b91c1c' : node.color} strokeWidth="2.5" />
                    <text x={node.x} y={node.y - 11} textAnchor="middle" fontSize="11" fontWeight="700" fill="#475569">{node.title}</text>
                    <text x={node.x} y={node.y + 11} textAnchor="middle" fontSize="15" fontWeight="900" fontFamily="monospace" fill="#0f172a">
                      {node.s ? `${node.s.value.toFixed(3)} ${node.s.unit}` : '--'}
                    </text>
                    <text x={node.x} y={node.y + 25} textAnchor="middle" fontSize="10" fontWeight="700" fill={p?.state && p.state !== 'NORMAL' ? '#b45309' : '#15803d'}>
                      {p ? `${p.state} · N10=${p.n10.toFixed(2)}` : 'NORMAL'}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* 4 Instrument Cards with Engineering Band Gauges */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
            {[pts, ft, ptr, pdt].filter(Boolean).map((s: any) => {
              const lim = s.engineeringLimits;
              const p = predMap.get(s.tagId);
              const pct = limitPct(s.value, lim.lowLow, lim.highHigh);
              return (
                <div key={s.tagId} className="card" style={{ cursor: 'pointer' }} onClick={() => openTagDetail(s.tagId)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong className="mono" style={{ fontSize: '0.8rem' }}>{s.tagId}</strong>
                    <span className={`badge ${s.status === 'ALARM' ? 'alarm' : p?.state !== 'NORMAL' ? 't30' : 'normal'}`}>{p?.state ?? s.status}</span>
                  </div>
                  <div className="mono" style={{ fontSize: '1.4rem', fontWeight: 900, margin: '0.35rem 0' }}>
                    {s.value.toFixed(3)} <span style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>{s.unit}</span>
                  </div>
                  <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '999px', position: 'relative', border: '1px solid var(--border-strong)' }}>
                    <div style={{ position: 'absolute', left: `calc(${pct}% - 3px)`, top: '-2px', width: '6px', height: '10px', background: 'var(--ink-primary)' }} />
                  </div>
                  <div className="mono" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--ink-muted)', marginTop: '0.3rem' }}>
                    <span>LO {lim.low}</span><span>Base {lim.baseline}</span><span>HI {lim.high}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1, overflow: 'hidden' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input className="input" placeholder="Search Tag (e.g. PCW01.Submain01.PTS)" value={search} onChange={(e) => setSearch(e.target.value)} style={{ minWidth: '230px' }} />
            <select className="select" value={sysFilter} onChange={(e) => setSysFilter(e.target.value)}>
              <option value="">All Systems (PCW01–08)</option>
              {Array.from({ length: 8 }, (_, i) => `PCW0${i + 1}`).map((sys) => <option key={sys} value={sys}>{sys}</option>)}
            </select>
            <select className="select" value={measFilter} onChange={(e) => setMeasFilter(e.target.value)}>
              <option value="">All Measurements (320)</option>
              <option value="PRESSURE">PRESSURE (160 PT)</option>
              <option value="FLOW">FLOW (80 FT)</option>
              <option value="DP">DIFFERENTIAL PRESSURE (80 PDT)</option>
            </select>
            <select className="select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Status</option>
              <option value="NORMAL">NORMAL</option>
              <option value="ALARM">ALARM</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>

          <div className="table-wrap" style={{ flex: 1 }}>
            <table>
              <thead>
                <tr>
                  <th>Tag ID</th>
                  <th>Type</th>
                  <th>Position</th>
                  <th>Value</th>
                  <th>Baseline</th>
                  <th>Limits (LO / HI)</th>
                  <th>Quality</th>
                  <th>Alarm / Pred</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => {
                  const p = predMap.get(s.tagId);
                  return (
                    <tr key={s.tagId} style={{ cursor: 'pointer' }} onClick={() => openTagDetail(s.tagId)}>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--brand-primary)' }}>{s.tagId}</td>
                      <td>{s.measurementType === 'DP' || s.measurementType === 'DIFFERENTIAL_PRESSURE' ? 'PDT' : s.measurementType === 'FLOW' ? 'FT' : 'PT'}</td>
                      <td>{s.position}</td>
                      <td className="mono" style={{ fontWeight: 800 }}>{s.value.toFixed(3)} {s.unit}</td>
                      <td className="mono">{s.engineeringLimits.baseline}</td>
                      <td className="mono">{s.engineeringLimits.low} ~ {s.engineeringLimits.high}</td>
                      <td><span className={`badge ${s.quality === 'GOOD' ? 'normal' : 'alarm'}`}>{s.quality}</span></td>
                      <td><span className={`badge ${s.status === 'ALARM' ? 'alarm' : p && p.state !== 'NORMAL' ? 't30' : 'normal'}`}>{s.status} / {p?.state ?? 'NORMAL'}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
