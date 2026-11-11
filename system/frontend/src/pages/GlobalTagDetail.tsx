import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useScadaStore } from '../store/scadaStore';

const stateBadgeClass = (st?: string) => {
  if (!st || st === 'NORMAL') return 'normal';
  if (st === 'T-30') return 't30';
  if (st === 'T-20') return 't20';
  if (st === 'T-10' || st === 'EVENT') return 'event';
  return 'neutral';
};

export const GlobalTagDetail: React.FC = () => {
  const selectedGlobalTag = useScadaStore((s) => s.selectedGlobalTag);
  const closeTagDetail = useScadaStore((s) => s.closeTagDetail);
  const sensors = useScadaStore((s) => s.sensors);
  const alarms = useScadaStore((s) => s.alarms);
  const predictions = useScadaStore((s) => s.predictions);
  const modbusMap = useScadaStore((s) => s.modbusMap);
  const modbus = useScadaStore((s) => s.modbus);
  const navigate = useNavigate();

  if (!selectedGlobalTag) return null;

  const tag = sensors.find((s) => s.tagId === selectedGlobalTag);
  const pred = predictions.find((p) => p.tagId === selectedGlobalTag);
  const regDef = modbusMap.find((m) => m.tagId === selectedGlobalTag);
  const regVal = regDef ? modbus[regDef.registerAddress] : undefined;
  const activeAlarms = alarms.filter((a) => a.tagId === selectedGlobalTag && a.state.startsWith('ACTIVE'));

  const lim = tag?.engineeringLimits;
  const pctInSpan =
    tag && lim && lim.highHigh > lim.lowLow
      ? Math.max(0, Math.min(100, ((tag.value - lim.lowLow) / (lim.highHigh - lim.lowLow)) * 100))
      : 50;

  return (
    <aside
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '430px',
        background: 'var(--bg-surface)',
        borderLeft: '2px solid var(--border-strong)',
        boxShadow: '-8px 0 24px rgba(15, 23, 42, 0.14)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div className="panel-header" style={{ padding: '0.85rem 1rem', marginBottom: 0, background: 'var(--bg-subtle)' }}>
        <div>
          <div className="panel-title">Tag Telemetry Inspector</div>
          <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--brand-primary)', fontWeight: 700 }}>{selectedGlobalTag}</div>
        </div>
        <button className="btn" onClick={closeTagDetail}>Close</button>
      </div>

      {!tag ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--ink-muted)' }}>Tag not found in topology</div>
      ) : (
        <div style={{ padding: '1rem', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {/* Live Value + Limit Gauge */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span className="kpi-label">Live Process Value ({tag.measurementType})</span>
              <span className={`badge ${tag.quality === 'GOOD' ? 'normal' : 'alarm'}`}>{tag.quality}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.45rem', marginTop: '0.35rem' }}>
              <span className="mono" style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--ink-primary)' }}>
                {tag.value.toFixed(3)}
              </span>
              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--ink-secondary)' }}>{tag.unit}</span>
            </div>
            {lim && (
              <div style={{ marginTop: '0.65rem' }}>
                <div style={{ height: '10px', background: '#e2e8f0', borderRadius: '999px', position: 'relative', overflow: 'hidden', border: '1px solid var(--border-strong)' }}>
                  <div style={{ position: 'absolute', left: '16.7%', right: '16.7%', top: 0, bottom: 0, background: '#dcfce7' }} />
                  <div style={{ position: 'absolute', left: `calc(${pctInSpan}% - 4px)`, top: '-1px', width: '8px', height: '10px', background: 'var(--ink-primary)', borderRadius: '2px' }} />
                </div>
                <div className="mono" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--ink-muted)', marginTop: '0.25rem' }}>
                  <span>LL {lim.lowLow}</span>
                  <span>L {lim.low}</span>
                  <span>Base {lim.baseline}</span>
                  <span>H {lim.high}</span>
                  <span>HH {lim.highHigh}</span>
                </div>
              </div>
            )}
          </div>

          {/* Prediction & L1-L7 Trace */}
          {pred && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span className="kpi-label">Unified V1 Inference</span>
                <span className={`badge ${stateBadgeClass(pred.state)}`}>{pred.state} · Risk {pred.riskScore}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', fontSize: '0.78rem' }}>
                <div>BaseAvg60: <strong className="mono">{pred.baseAvg60.toFixed(3)}</strong></div>
                <div>M60 / M10: <strong className="mono">{pred.m60} / {pred.m10}</strong></div>
                <div>N10 Ratio: <strong className="mono">{pred.n10 >= 999 ? 'SAT (999)' : pred.n10.toFixed(2)}</strong></div>
                <div>Slope/min: <strong className="mono">{pred.slope.toFixed(4)}</strong></div>
                <div>Fcst +10/20/30: <strong className="mono">{pred.forecast10.toFixed(3)} / {pred.forecast20.toFixed(3)} / {pred.forecast30.toFixed(3)}</strong></div>
                <div>TTL: <strong className="mono">{pred.ttlMinutes !== null ? `${pred.ttlMinutes.toFixed(1)}m (${pred.ttlLimit})` : 'N/A'}</strong></div>
                <div>OLS Slope / R²: <strong className="mono">{pred.slopeOls.toFixed(4)} / {pred.r2.toFixed(2)}</strong></div>
                <div>95% PI (±δ30): <strong className="mono">±{pred.band30.toFixed(3)}</strong></div>
              </div>
              <div style={{ marginTop: '0.55rem', padding: '0.45rem', background: 'var(--bg-subtle)', borderRadius: '4px', fontSize: '0.74rem', border: '1px solid var(--border-soft)' }}>
                <strong>Decision Trace:</strong> {pred.triggerPath}
              </div>
            </div>
          )}

          {/* Modbus CDAB Register */}
          {regDef && (
            <div className="card">
              <div className="kpi-label" style={{ marginBottom: '0.4rem' }}>Modbus/TCP Holding Register (CDAB FLOAT32)</div>
              <div className="mono" style={{ fontSize: '0.78rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem' }}>
                <span>Address: <strong>{regDef.registerAddress}</strong></span>
                <span>Type: <strong>FLOAT32</strong></span>
                <span>Word C/D: <strong>{regVal?.reg1 ?? '--'}</strong></span>
                <span>Word A/B: <strong>{regVal?.reg2 ?? '--'}</strong></span>
              </div>
            </div>
          )}

          {activeAlarms.length > 0 && (
            <div className="card" style={{ borderColor: 'var(--danger)', background: 'var(--danger-bg)' }}>
              <div className="kpi-label" style={{ color: 'var(--danger)' }}>Active Alarms ({activeAlarms.length})</div>
              {activeAlarms.map((a) => (
                <div key={a.alarmId} style={{ fontSize: '0.78rem', marginTop: '0.35rem', fontWeight: 700 }}>
                  [{a.state}] {a.alarmType}: {a.message} ({a.value.toFixed(3)})
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto' }}>
            <button className="btn primary" style={{ flex: 1 }} onClick={() => { closeTagDetail(); navigate('/t30'); }}>Open Prediction Workbench</button>
            <button className="btn" style={{ flex: 1 }} onClick={() => { closeTagDetail(); navigate('/historian'); }}>Historian & Logs</button>
          </div>
        </div>
      )}
    </aside>
  );
};
