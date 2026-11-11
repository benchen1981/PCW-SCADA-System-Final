import React, { useEffect, useState } from 'react';
import { useScadaStore } from '../store/scadaStore';
import { pcwDataService } from '../services/PcwDataService';

const badgeForState = (st: string) => {
  if (st === 'NORMAL') return 'normal';
  if (st === 'T-30') return 't30';
  if (st === 'T-20') return 't20';
  if (st === 'T-10' || st === 'EVENT') return 'event';
  return 'neutral';
};

export const PredictionT30 = () => {
  const predictions = useScadaStore((s) => s.predictions);
  const pairs = useScadaStore((s) => s.pairs);
  const sensors = useScadaStore((s) => s.sensors);
  const predictionConfig = useScadaStore((s) => s.predictionConfig);
  const sqliteStats = useScadaStore((s) => s.sqliteStats);
  const updatePredictionConfig = useScadaStore((s) => s.updatePredictionConfig);
  const openTagDetail = useScadaStore((s) => s.openTagDetail);

  const [tab, setTab] = useState<'SENSOR' | 'PAIR' | 'AUDIT'>('SENSOR');
  const [sysFilter, setSysFilter] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState<string>('PCW01.Submain01.PTS');
  const [auditRows, setAuditRows] = useState<any[]>([]);

  useEffect(() => {
    if (tab === 'AUDIT') {
      pcwDataService.getPredictionLogs({ tagId: search || undefined, state: stateFilter || undefined, limit: 200 }).then((res) => {
        setAuditRows(res.rows ?? []);
      });
    }
  }, [tab, search, stateFilter]);

  const sensorMap = new Map(sensors.map((s) => [s.tagId, s]));
  const filteredPreds = predictions.filter((p) => {
    if (sysFilter && !p.tagId.startsWith(sysFilter)) return false;
    if (stateFilter && p.state !== stateFilter) return false;
    if (search && !p.tagId.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const filteredPairs = pairs.filter((pr) => {
    if (sysFilter && pr.systemId !== sysFilter) return false;
    if (search && !`${pr.systemId}.${pr.submainId}`.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const inspected = predictions.find((p) => p.tagId === selectedTag) ?? filteredPreds[0];
  const inspectedSensor = inspected ? sensorMap.get(inspected.tagId) : undefined;

  const exportCsv = () => {
    const header = 'TagId,State,RiskScore,CurrentValue,BaseAvg60,M60,M10,N10,Slope,Fcst10,Fcst20,Fcst30,TTL_min,TriggerPath\n';
    const body = filteredPreds
      .map((p) => [p.tagId, p.state, p.riskScore, p.currentValue, p.baseAvg60, p.m60, p.m10, p.n10, p.slope, p.forecast10, p.forecast20, p.forecast30, p.ttlMinutes ?? '', `"${(p.triggerPath ?? '').replace(/"/g, "'")}"`].join(','))
      .join('\n');
    const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pcw_predictions_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Build SVG coordinates for OLS 95% PI cone preview
  const renderForecastCone = () => {
    if (!inspected || !inspectedSensor) return null;
    const lim = inspectedSensor.engineeringLimits;
    const pts = [
      { x: 0, v: inspected.currentValue, band: 0, label: 'Now' },
      { x: 10, v: inspected.forecast10, band: inspected.band10, label: '+10m' },
      { x: 20, v: inspected.forecast20, band: inspected.band20, label: '+20m' },
      { x: 30, v: inspected.forecast30, band: inspected.band30, label: '+30m' },
    ];
    const allY = [
      lim.high,
      lim.low,
      ...pts.flatMap((d) => [d.v + d.band, d.v - d.band]),
    ];
    const minY = Math.min(...allY) - 0.05 * (lim.high - lim.low);
    const maxY = Math.max(...allY) + 0.05 * (lim.high - lim.low);
    const mapX = (m: number) => 40 + (m / 30) * 280;
    const mapY = (v: number) => 130 - ((v - minY) / Math.max(1e-6, maxY - minY)) * 110;

    const polyUpper = pts.map((d) => `${mapX(d.x)},${mapY(d.v + d.band)}`).join(' ');
    const polyLower = [...pts].reverse().map((d) => `${mapX(d.x)},${mapY(d.v - d.band)}`).join(' ');
    const linePath = pts.map((d) => `${mapX(d.x)},${mapY(d.v)}`).join(' ');

    return (
      <svg viewBox="0 0 340 155" style={{ width: '100%', background: 'var(--bg-subtle)', borderRadius: '6px', border: '1px solid var(--border-soft)' }}>
        <line x1="40" y1={mapY(lim.high)} x2="320" y2={mapY(lim.high)} stroke="#b91c1c" strokeDasharray="4 3" strokeWidth="1.5" />
        <text x="44" y={mapY(lim.high) - 3} fontSize="9" fontWeight="700" fill="#b91c1c">HI {lim.high}</text>
        <line x1="40" y1={mapY(lim.low)} x2="320" y2={mapY(lim.low)} stroke="#b45309" strokeDasharray="4 3" strokeWidth="1.5" />
        <text x="44" y={mapY(lim.low) + 10} fontSize="9" fontWeight="700" fill="#b45309">LO {lim.low}</text>
        <polygon points={`${polyUpper} ${polyLower}`} fill="rgba(3, 105, 161, 0.18)" />
        <polyline points={linePath} fill="none" stroke="#0369a1" strokeWidth="2.5" />
        {pts.map((d) => (
          <g key={d.label}>
            <circle cx={mapX(d.x)} cy={mapY(d.v)} r="3.5" fill="#0f172a" />
            <text x={mapX(d.x)} y="146" textAnchor="middle" fontSize="9" fill="#475569">{d.label}</text>
          </g>
        ))}
      </svg>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', height: '100%' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 className="panel-title">6. System Prediction & Pair Diagnostics Workbench</h2>
          <div className="panel-subtitle">Past-Only 70-min Window · Dual Density N10 · OLS 95% PI · L1–L7 Hardening · {sqliteStats?.totalRows?.toLocaleString() ?? 0} SQLite Logged Rows</div>
        </div>
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <button className={`btn ${tab === 'SENSOR' ? 'primary' : ''}`} onClick={() => setTab('SENSOR')}>Sensor Level ({predictions.length})</button>
          <button className={`btn ${tab === 'PAIR' ? 'primary' : ''}`} onClick={() => setTab('PAIR')}>Pair Level ({pairs.length})</button>
          <button className={`btn ${tab === 'AUDIT' ? 'primary' : ''}`} onClick={() => setTab('AUDIT')}>SQLite Execution Log</button>
          <label style={{ fontSize: '0.76rem', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '0.3rem', padding: '0 0.4rem' }}>
            <input type="checkbox" checked={predictionConfig?.global ?? true} onChange={(e) => updatePredictionConfig('global', 'global', e.target.checked)} />
            Engine ON
          </label>
          <button className="btn success" onClick={exportCsv}>Export CSV</button>
        </div>
      </div>

      {/* Filters */}
      <div className="card" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', padding: '0.55rem 0.9rem' }}>
        <input className="input mono" placeholder="Filter Tag ID..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ minWidth: '210px' }} />
        <select className="select" value={sysFilter} onChange={(e) => setSysFilter(e.target.value)}>
          <option value="">All Systems (PCW01–08)</option>
          {Array.from({ length: 8 }, (_, i) => `PCW0${i + 1}`).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="select" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
          <option value="">All States</option>
          <option value="EVENT">EVENT</option>
          <option value="T-10">T-10</option>
          <option value="T-20">T-20</option>
          <option value="T-30">T-30</option>
          <option value="NORMAL">NORMAL</option>
        </select>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: tab === 'SENSOR' && inspected ? '1fr 355px' : '1fr', gap: '0.85rem', flex: 1, minHeight: 0 }}>
        <div className="table-wrap" style={{ height: '100%' }}>
          {tab === 'SENSOR' && (
            <table>
              <thead>
                <tr>
                  <th>Canonical Tag</th>
                  <th>L / H</th>
                  <th>Live PV</th>
                  <th>Base60</th>
                  <th>M60/M10</th>
                  <th>N10 (θ={predictionConfig?.sensitivity ?? 2})</th>
                  <th>Slope/m</th>
                  <th>Fcst-30</th>
                  <th>Fcst-10</th>
                  <th>TTL</th>
                  <th>Risk</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {filteredPreds.map((p) => {
                  const s = sensorMap.get(p.tagId);
                  return (
                    <tr
                      key={p.tagId}
                      className={selectedTag === p.tagId ? 'selected-row' : ''}
                      style={{ cursor: 'pointer' }}
                      onClick={() => setSelectedTag(p.tagId)}
                      onDoubleClick={() => openTagDetail(p.tagId)}
                    >
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--brand-primary)' }}>{p.tagId}</td>
                      <td className="mono">{s ? `${s.engineeringLimits.low}/${s.engineeringLimits.high}` : '--'}</td>
                      <td className="mono" style={{ fontWeight: 800 }}>{p.currentValue.toFixed(3)}</td>
                      <td className="mono">{p.baseAvg60.toFixed(3)}</td>
                      <td className="mono">{p.m60}/{p.m10}</td>
                      <td className="mono" style={{ fontWeight: 700 }}>{p.n10 >= 999 ? 'SAT' : p.n10.toFixed(2)}</td>
                      <td className="mono">{p.slope.toFixed(4)}</td>
                      <td className="mono">{p.forecast30.toFixed(3)}</td>
                      <td className="mono">{p.forecast10.toFixed(3)}</td>
                      <td className="mono">{p.ttlMinutes !== null && p.ttlMinutes !== undefined ? `${p.ttlMinutes.toFixed(0)}m` : '--'}</td>
                      <td className="mono" style={{ fontWeight: 700 }}>{p.riskScore}</td>
                      <td><span className={`badge ${badgeForState(p.state)}`}>{p.state}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {tab === 'PAIR' && (
            <table>
              <thead>
                <tr>
                  <th>System / Submain</th>
                  <th>Supply PT (PTS)</th>
                  <th>Return PT (PTR)</th>
                  <th>Pair ΔP (bar)</th>
                  <th>Supply State</th>
                  <th>Return State</th>
                  <th>Pair State</th>
                  <th>Coupling Mode</th>
                  <th>Pair Risk</th>
                </tr>
              </thead>
              <tbody>
                {filteredPairs.map((pr) => (
                  <tr key={`${pr.systemId}.${pr.submainId}`}>
                    <td className="mono" style={{ fontWeight: 700 }}>{pr.systemId}.{pr.submainId}</td>
                    <td className="mono">{pr.supplyPressure.toFixed(3)}</td>
                    <td className="mono">{pr.returnPressure.toFixed(3)}</td>
                    <td className="mono">{pr.pairDeltaP.toFixed(3)}</td>
                    <td><span className={`badge ${badgeForState(pr.supplyState)}`}>{pr.supplyState}</span></td>
                    <td><span className={`badge ${badgeForState(pr.returnState)}`}>{pr.returnState}</span></td>
                    <td><span className={`badge ${badgeForState(pr.pairState)}`}>{pr.pairState}</span></td>
                    <td><span className={`badge ${pr.couplingMode === 'COUPLED_DRIFT' ? 't20' : pr.couplingMode === 'NORMAL' ? 'normal' : 'warning'}`}>{pr.couplingMode}</span></td>
                    <td className="mono" style={{ fontWeight: 700 }}>{pr.pairRiskScore}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {tab === 'AUDIT' && (
            <table>
              <thead>
                <tr>
                  <th>Eval Time</th>
                  <th>Tag ID</th>
                  <th>Scenario</th>
                  <th>PV</th>
                  <th>BaseAvg60</th>
                  <th>N10</th>
                  <th>Slope</th>
                  <th>Fcst30</th>
                  <th>State</th>
                  <th>Trigger Path</th>
                </tr>
              </thead>
              <tbody>
                {auditRows.map((r: any, idx: number) => (
                  <tr key={idx}>
                    <td className="mono">{new Date(r.evalTime ?? r.eval_time).toLocaleTimeString()}</td>
                    <td className="mono" style={{ fontWeight: 700 }}>{r.tagId ?? r.tag_id}</td>
                    <td>{r.scenario ?? 'NONE'}</td>
                    <td className="mono">{Number(r.currentValue ?? r.current_value).toFixed(3)}</td>
                    <td className="mono">{Number(r.baseAvg60 ?? r.base_avg_60).toFixed(3)}</td>
                    <td className="mono">{Number(r.n10).toFixed(2)}</td>
                    <td className="mono">{Number(r.slope).toFixed(4)}</td>
                    <td className="mono">{Number(r.fcst30 ?? r.forecast30).toFixed(3)}</td>
                    <td><span className={`badge ${badgeForState(r.state)}`}>{r.state}</span></td>
                    <td style={{ fontSize: '0.7rem' }}>{r.triggerPath ?? r.trigger_path}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {tab === 'SENSOR' && inspected && (
          <aside className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div className="kpi-label">Selected Forecast Cone</div>
                <strong className="mono" style={{ fontSize: '0.84rem', color: 'var(--brand-primary)' }}>{inspected.tagId}</strong>
              </div>
              <span className={`badge ${badgeForState(inspected.state)}`}>{inspected.state}</span>
            </div>

            {renderForecastCone()}

            <div className="mono" style={{ fontSize: '0.74rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem', background: 'var(--bg-subtle)', padding: '0.55rem', borderRadius: '6px' }}>
              <span>R² (OLS): <strong>{inspected.r2.toFixed(3)}</strong></span>
              <span>OLS Slope: <strong>{inspected.slopeOls.toFixed(4)}</strong></span>
              <span>95% PI ±10: <strong>±{inspected.band10.toFixed(3)}</strong></span>
              <span>95% PI ±30: <strong>±{inspected.band30.toFixed(3)}</strong></span>
              <span>Hold Count: <strong>{inspected.holdCount}</strong></span>
              <span>Valid Ratio: <strong>{(inspected.validRatio * 100).toFixed(0)}%</strong></span>
            </div>

            <div style={{ fontSize: '0.74rem', padding: '0.55rem', border: '1px solid var(--border-soft)', borderRadius: '6px' }}>
              <strong>L1–L7 Trigger Trace:</strong><br />
              {inspected.triggerPath}
            </div>

            <button className="btn primary" onClick={() => openTagDetail(inspected.tagId)}>Open Full Tag Drawer</button>
          </aside>
        )}
      </div>
    </div>
  );
};
