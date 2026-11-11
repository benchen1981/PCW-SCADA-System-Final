import React from 'react';
import { useScadaStore } from '../store/scadaStore';

export const PredictionModelInfo: React.FC = () => {
  const predictionConfig = useScadaStore((s) => s.predictionConfig);
  const sqliteStats = useScadaStore((s) => s.sqliteStats);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      <div className="card">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">9. Unified V1 Statistical Early-Warning Engine Specification</h2>
            <div className="panel-subtitle">Past-Only 70-min Window · Python / TypeScript Numerical Parity (&lt; 1e-9) · Excel PT-1 Parity (480 / 480)</div>
          </div>
          <span className="badge info">Active Config: θ={predictionConfig?.sensitivity ?? 2} · g={predictionConfig?.slopeGatePct ?? 5}% · Hold={predictionConfig?.releaseHold ?? 3} · Onset={predictionConfig?.rawOnset ?? 1}</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
          <div style={{ background: 'var(--bg-subtle)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-soft)' }}>
            <div className="kpi-label">1. Past-Only Causal Window (70 min)</div>
            <p style={{ fontSize: '0.78rem', marginTop: '0.35rem', lineHeight: 1.5 }}>
              Base <strong>B = [t-70, t-10)</strong> (60 pts), Pre-local <strong>P = [t-10, t-5)</strong> (5 pts), Recent <strong>R = [t-5, t)</strong> (5 pts). Strictly causal with zero future leakage and &ge;80% GOOD sample gate (L1).
            </p>
          </div>
          <div style={{ background: 'var(--bg-subtle)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-soft)' }}>
            <div className="kpi-label">2. Fixed N10 Reachability & L2 Sustained Shift</div>
            <p style={{ fontSize: '0.78rem', marginTop: '0.35rem', lineHeight: 1.5 }}>
              Corrected <code>N10 &ge; &theta;</code> removes the unreachable blind spot under symmetric noise (<em>M60 &ge; 30</em>). L2 level-shift gate <code>|&Delta;&mu;10| &ge; g%*(H-L)</code> preserves warnings when bias lasts &gt;10 min and local slope approaches zero.
            </p>
          </div>
          <div style={{ background: 'var(--bg-subtle)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-soft)' }}>
            <div className="kpi-label">3. OLS 95% PI, TTL & L5–L7 Hardening</div>
            <p style={{ fontSize: '0.78rem', marginTop: '0.35rem', lineHeight: 1.5 }}>
              Extrapolates <code>Fcst+10/20/30</code> with Student-t (<em>df=8, 2.306</em>) 95% intervals &amp; closed-form TTL, separates <code>EVENT</code> beyond HI/LO (L5), applies L6 hysteresis, and logs every cycle to SQLite (<strong>{(sqliteStats?.totalRows ?? 0).toLocaleString()}</strong> rows).
            </p>
          </div>
        </div>
      </div>

      {/* Verification Benchmarks Card */}
      <div className="card">
        <h3 style={{ fontSize: '0.92rem', fontWeight: 900, marginBottom: '0.6rem' }}>Verified System Benchmarks & Hardware Limits</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Group / Metric</th>
                <th>Scope / Loops</th>
                <th>Baseline / Benchmark Result</th>
                <th>Engineering Limits (LL / LO / HI / HIHI) or Details</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Group 1 PT (40 tags)</td><td>PCW01 – PCW02</td><td className="mono">1.50 bar</td><td className="mono">1.20 / 1.30 / 1.70 / 1.80 bar</td></tr>
              <tr><td>Group 2 PT (40 tags)</td><td>PCW03 – PCW04</td><td className="mono">1.90 bar</td><td className="mono">1.60 / 1.70 / 2.10 / 2.20 bar</td></tr>
              <tr><td>Group 3 PT (40 tags)</td><td>PCW05 – PCW06</td><td className="mono">2.50 bar</td><td className="mono">2.20 / 2.30 / 2.70 / 2.80 bar</td></tr>
              <tr><td>Group 4 PT (40 tags)</td><td>PCW07 – PCW08</td><td className="mono">2.20 bar (Code-Aligned)</td><td className="mono">1.90 / 2.00 / 2.40 / 2.50 bar</td></tr>
              <tr><td>Flow FT (80 tags)</td><td>PCW01 – PCW08</td><td className="mono">180.0 L/min</td><td className="mono">150.0 / 160.0 / 200.0 / 220.0 L/min</td></tr>
              <tr><td>Differential PDT (80 tags)</td><td>PCW01 – PCW08</td><td className="mono">0.30 bar</td><td className="mono">0.00 / 0.10 / 0.50 / 0.60 bar</td></tr>
              <tr><td>Excel PT-1 Replay Parity</td><td>480 rows</td><td className="mono">480 / 480 Exact Match</td><td>Max absolute error 0.0 (Tolerance 1e-9)</td></tr>
              <tr><td>320-Tag Benchmark (3,840 trials)</td><td>160 PT Subset / Full 320</td><td className="mono">Recall 100%, F1 0.9405</td><td>Onset=2 Ablation: FAR drops 25.62% &rarr; 1.25%–6.88%</td></tr>
              <tr><td>Apple M5 Execution Latency</td><td>Single / Batch / DB / Modbus</td><td className="mono">14.5 µs / 4.68 ms</td><td>320+SQLite: 20.54 ms · Modbus FC03 (20 regs): 271.4 µs</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
