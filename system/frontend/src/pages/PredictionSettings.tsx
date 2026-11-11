import React, { useState } from 'react';
import { useScadaStore } from '../store/scadaStore';

export const PredictionSettings = () => {
  const sensors = useScadaStore((s) => s.sensors);
  const predictionConfig = useScadaStore((s) => s.predictionConfig);
  const updateSensorSensitivity = useScadaStore((s) => s.updateSensorSensitivity);
  const tunePrediction = useScadaStore((s) => s.tunePrediction);

  const [filterSys, setFilterSys] = useState('');
  const [filterType, setFilterType] = useState('');

  const sensorShortType = (tagId: string) => {
    if (tagId.endsWith('.PTS') || tagId.endsWith('.PTR')) return 'PT';
    if (tagId.endsWith('.FT')) return 'FT';
    if (tagId.endsWith('.PDT')) return 'PDT';
    return '';
  };

  const filteredSensors = sensors.filter((s) => {
    if (filterSys && s.systemId !== filterSys) return false;
    if (filterType && sensorShortType(s.tagId) !== filterType) return false;
    return true;
  });

  const theta = predictionConfig?.sensitivity ?? 2;
  const gatePct = predictionConfig?.slopeGatePct ?? 5;
  const hold = predictionConfig?.releaseHold ?? 3;
  const rawOnset = predictionConfig?.rawOnset ?? 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', height: '100%' }}>
      <div className="card">
        <div className="panel-header" style={{ marginBottom: '0.4rem' }}>
          <div>
            <h2 className="panel-title">7. Prediction Engine Tuning & Ablation Controls</h2>
            <div className="panel-subtitle">Live tuning for Unified V1 Parameters (N10 Threshold θ, Span Gate g%, L6 Release Hold, Onset Confirmation)</div>
          </div>
          <span className="badge info">Active: θ={theta} · g={gatePct}% · Hold={hold} · Onset={rawOnset}</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(180px, 1fr))', gap: '0.75rem' }}>
          <div style={{ background: 'var(--bg-subtle)', padding: '0.65rem', borderRadius: '6px', border: '1px solid var(--border-soft)' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, marginBottom: '0.35rem' }}>Global N10 Threshold (θ)</label>
            <input
              type="number"
              className="input mono"
              min="1.0"
              max="10.0"
              step="0.5"
              value={theta}
              onChange={(e) => tunePrediction({ sensitivity: Number(e.target.value) })}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: '0.68rem', color: 'var(--ink-muted)', marginTop: '0.25rem' }}>Default: 2.0 (2.5 cuts spike FAR to 1.25%)</div>
          </div>

          <div style={{ background: 'var(--bg-subtle)', padding: '0.65rem', borderRadius: '6px', border: '1px solid var(--border-soft)' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, marginBottom: '0.35rem' }}>L2 Span Drift Gate (g%)</label>
            <input
              type="number"
              className="input mono"
              min="1.0"
              max="20.0"
              step="0.5"
              value={gatePct}
              onChange={(e) => tunePrediction({ slopeGatePct: Number(e.target.value) })}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: '0.68rem', color: 'var(--ink-muted)', marginTop: '0.25rem' }}>Excursion / level-shift gate % of (HI − LO)</div>
          </div>

          <div style={{ background: 'var(--bg-subtle)', padding: '0.65rem', borderRadius: '6px', border: '1px solid var(--border-soft)' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, marginBottom: '0.35rem' }}>L6 Release Hysteresis (K_hold)</label>
            <input
              type="number"
              className="input mono"
              min="0"
              max="10"
              step="1"
              value={hold}
              onChange={(e) => tunePrediction({ releaseHold: Number(e.target.value) })}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: '0.68rem', color: 'var(--ink-muted)', marginTop: '0.25rem' }}>Consecutive normal ticks to unlatch</div>
          </div>

          <div style={{ background: rawOnset >= 2 ? 'var(--success-bg)' : 'var(--bg-subtle)', padding: '0.65rem', borderRadius: '6px', border: '1px solid var(--border-strong)' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, marginBottom: '0.35rem' }}>Onset Confirmation (Spike Mitigation)</label>
            <select
              className="select mono"
              value={rawOnset}
              onChange={(e) => tunePrediction({ rawOnset: Number(e.target.value) })}
              style={{ width: '100%' }}
            >
              <option value={1}>raw_onset = 1 (Immediate Baseline)</option>
              <option value={2}>raw_onset = 2 (2-min Debounce · Recommended)</option>
            </select>
            <div style={{ fontSize: '0.68rem', color: 'var(--ink-secondary)', marginTop: '0.25rem' }}>Ablation: 2-min cuts spike FAR 25.62% → 6.88%</div>
          </div>
        </div>
      </div>

      {/* Per-sensor N10 overrides */}
      <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.65rem', overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ fontSize: '0.92rem', fontWeight: 900 }}>Per-Sensor N10 Threshold Overrides ({filteredSensors.length} tags)</h3>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select className="select" value={filterSys} onChange={(e) => setFilterSys(e.target.value)}>
              <option value="">All Systems (PCW01–08)</option>
              {Array.from({ length: 8 }, (_, i) => `PCW0${i + 1}`).map((sys) => <option key={sys} value={sys}>{sys}</option>)}
            </select>
            <select className="select" value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All Types (PT / FT / PDT)</option>
              <option value="PT">PT (160 Pressure)</option>
              <option value="FT">FT (80 Flow)</option>
              <option value="PDT">PDT (80 Differential Pressure)</option>
            </select>
          </div>
        </div>

        <div className="table-wrap" style={{ flex: 1 }}>
          <table>
            <thead>
              <tr>
                <th>Sensor Tag ID</th>
                <th>System / Submain</th>
                <th>Type</th>
                <th>Custom N10 (θ)</th>
                <th>Effective Threshold</th>
              </tr>
            </thead>
            <tbody>
              {filteredSensors.map((s) => {
                const customVal = predictionConfig?.sensorSensitivity?.[s.tagId];
                const effective = customVal ?? theta;
                return (
                  <tr key={s.tagId}>
                    <td className="mono" style={{ fontWeight: 700 }}>{s.tagId}</td>
                    <td>{s.systemId} / {s.submainId}</td>
                    <td>{sensorShortType(s.tagId)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        <input
                          type="number"
                          className="input mono"
                          min="0.5"
                          max="10"
                          step="0.5"
                          value={customVal ?? ''}
                          placeholder="Inherit"
                          onChange={(e) => updateSensorSensitivity(s.tagId, e.target.value ? Number(e.target.value) : null)}
                          style={{ width: '90px' }}
                        />
                        {customVal !== undefined && (
                          <button className="btn danger" style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }} onClick={() => updateSensorSensitivity(s.tagId, null)}>Clear</button>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${customVal !== undefined ? 'warning' : 'neutral'}`}>{effective}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
