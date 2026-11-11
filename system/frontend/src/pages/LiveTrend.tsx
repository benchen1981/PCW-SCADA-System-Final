import React, { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useScadaStore } from '../store/scadaStore';

const COLORS = ['#0369a1', '#b91c1c', '#15803d', '#b45309', '#6d28d9'];

export const LiveTrend = () => {
  const sensors = useScadaStore((s) => s.sensors);
  const predictions = useScadaStore((s) => s.predictions);
  const [sysFilter, setSysFilter] = useState('PCW01');
  const [selectedTags, setSelectedTags] = useState<string[]>(['PCW01.Submain01.PTS', 'PCW01.Submain01.PTR']);
  const [buffer, setBuffer] = useState<any[]>([]);

  useEffect(() => {
    if (sensors.length === 0) return;
    const row: any = { time: new Date().toLocaleTimeString('en-GB', { hour12: false }) };
    selectedTags.forEach((tag) => {
      const found = sensors.find((s) => s.tagId === tag);
      if (found) row[tag] = Number(found.value.toFixed(4));
    });
    setBuffer((prev) => [...prev.slice(-119), row]);
  }, [sensors, selectedTags]);

  const toggleTag = (tagId: string) => {
    setSelectedTags((prev) =>
      prev.includes(tagId) ? prev.filter((t) => t !== tagId) : prev.length < 5 ? [...prev, tagId] : prev,
    );
  };

  const primaryTag = selectedTags[0] ? sensors.find((s) => s.tagId === selectedTags[0]) : undefined;
  const primaryPred = selectedTags[0] ? predictions.find((p) => p.tagId === selectedTags[0]) : undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', height: '100%' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 className="panel-title">4. Real-Time Oscilloscope & Live OLS Forecast Overlay</h2>
          <div className="panel-subtitle">1 Hz WebSocket telemetry ring buffer (up to 5 overlaid tags + engineering thresholds)</div>
        </div>
        <div style={{ display: 'flex', gap: '0.45rem', alignItems: 'center' }}>
          <select className="select" value={sysFilter} onChange={(e) => setSysFilter(e.target.value)}>
            {Array.from({ length: 8 }, (_, i) => `PCW0${i + 1}`).map((sys) => <option key={sys} value={sys}>{sys}</option>)}
          </select>
          <button
            className="btn brand"
            onClick={() => {
              setSelectedTags([`${sysFilter}.Submain01.PTS`, `${sysFilter}.Submain01.PTR`]);
              setBuffer([]);
            }}
          >
            Load {sysFilter} Submain01 Pair
          </button>
          <button className="btn" onClick={() => setBuffer([])}>Clear Buffer</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '0.85rem', flex: 1, minHeight: 0 }}>
        {/* Left Tag Picker */}
        <div className="card" style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div className="kpi-label" style={{ marginBottom: '0.25rem' }}>{sysFilter} Tags (Max 5 selected)</div>
          {sensors.filter((s) => s.systemId === sysFilter).map((s) => {
            const active = selectedTags.includes(s.tagId);
            return (
              <label key={s.tagId} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.3rem 0.45rem', borderRadius: '4px', cursor: 'pointer', background: active ? 'var(--brand-light)' : 'transparent', fontSize: '0.74rem' }}>
                <span>
                  <input type="checkbox" checked={active} onChange={() => toggleTag(s.tagId)} style={{ marginRight: '0.4rem' }} />
                  <span className="mono">{s.tagId.replace(`${sysFilter}.`, '')}</span>
                </span>
                <strong className="mono">{s.value.toFixed(3)}</strong>
              </label>
            );
          })}
        </div>

        {/* Right Oscilloscope + Live Projection */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', minWidth: 0 }}>
          <div className="card" style={{ flex: 1, minHeight: '280px', display: 'flex', flexDirection: 'column' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={buffer} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {primaryTag && (
                  <>
                    <ReferenceLine y={primaryTag.engineeringLimits.high} stroke="#b91c1c" strokeDasharray="4 4" label="HI" />
                    <ReferenceLine y={primaryTag.engineeringLimits.low} stroke="#b45309" strokeDasharray="4 4" label="LO" />
                  </>
                )}
                {selectedTags.map((tag, i) => (
                  <Line key={tag} type="monotone" dataKey={tag} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {primaryTag && primaryPred && (
            <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem', fontSize: '0.76rem' }}>
              <div><div className="kpi-label">Primary Tag</div><strong className="mono">{primaryTag.tagId}</strong></div>
              <div><div className="kpi-label">State / Risk</div><span className="badge info">{primaryPred.state} · {primaryPred.riskScore}</span></div>
              <div><div className="kpi-label">Slope / N10</div><strong className="mono">{primaryPred.slope.toFixed(4)} / {primaryPred.n10.toFixed(2)}</strong></div>
              <div><div className="kpi-label">Fcst +10 (±95% PI)</div><strong className="mono">{primaryPred.forecast10.toFixed(3)} ±{primaryPred.band10.toFixed(3)}</strong></div>
              <div><div className="kpi-label">Fcst +20 (±95% PI)</div><strong className="mono">{primaryPred.forecast20.toFixed(3)} ±{primaryPred.band20.toFixed(3)}</strong></div>
              <div><div className="kpi-label">Fcst +30 (±95% PI)</div><strong className="mono">{primaryPred.forecast30.toFixed(3)} ±{primaryPred.band30.toFixed(3)}</strong></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
