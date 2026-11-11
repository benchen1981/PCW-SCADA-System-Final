import React, { useState } from 'react';
import { useScadaStore } from '../store/scadaStore';
import type { FaultScenario } from '../domain/modbusTypes';

export const ModbusMonitor = () => {
  const sensors = useScadaStore((s) => s.sensors);
  const modbus = useScadaStore((s) => s.modbus);
  const modbusMap = useScadaStore((s) => s.modbusMap);
  const simulatorConfigs = useScadaStore((s) => s.simulatorConfigs);
  const simulatorStatus = useScadaStore((s) => s.simulatorStatus);
  const modbusWriteLog = useScadaStore((s) => s.modbusWriteLog);
  const setSimulatorControl = useScadaStore((s) => s.setSimulatorControl);
  const updateSimulatorConfig = useScadaStore((s) => s.updateSimulatorConfig);
  const injectFault = useScadaStore((s) => s.injectFault);
  const applySuggestedBaselines = useScadaStore((s) => s.applySuggestedBaselines);

  const [tab, setTab] = useState<'SIMULATOR' | 'MODBUS'>('SIMULATOR');
  const [sysFilter, setSysFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>(['PCW01.Submain01.PTS']);

  // Injection controls
  const [baseVal, setBaseVal] = useState('1.62');
  const [noiseVal, setNoiseVal] = useState('0.008');
  const [scenario, setScenario] = useState<FaultScenario>('DRIFT');
  const [driftRate, setDriftRate] = useState('0.008');
  const [stepOffset, setStepOffset] = useState('0.14');
  const [spikeAmp, setSpikeAmp] = useState('0.12');

  const filteredSensors = sensors.filter((s) => {
    if (sysFilter && s.systemId !== sysFilter) return false;
    if (typeFilter === 'PT' && !(s.tagId.endsWith('.PTS') || s.tagId.endsWith('.PTR'))) return false;
    if (typeFilter === 'FT' && !s.tagId.endsWith('.FT')) return false;
    if (typeFilter === 'PDT' && !s.tagId.endsWith('.PDT')) return false;
    if (search && !s.tagId.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const toggleTag = (tagId: string) => {
    setSelectedTags((prev) => (prev.includes(tagId) ? prev.filter((t) => t !== tagId) : [...prev, tagId]));
  };

  // One-click preset scenarios aligned with thesis validation
  const runPresetConsistencyProbe = async () => {
    await updateSimulatorConfig(['PCW01.Submain01.PTS'], { baseValue: 1.72, noise: 0.0 });
  };

  const runPreset160PtDeviation = async () => {
    const groups: Record<string, [number, number]> = {
      PCW01: [1.62, 1.38], PCW02: [1.62, 1.38],
      PCW03: [2.02, 1.78], PCW04: [2.02, 1.78],
      PCW05: [2.62, 2.38], PCW06: [2.62, 2.38],
      PCW07: [2.32, 2.08], PCW08: [2.32, 2.08],
    };
    for (const [sys, [sup, ret]] of Object.entries(groups)) {
      const sTags = sensors.filter((x) => x.systemId === sys && x.tagId.endsWith('.PTS')).map((x) => x.tagId);
      const rTags = sensors.filter((x) => x.systemId === sys && x.tagId.endsWith('.PTR')).map((x) => x.tagId);
      await updateSimulatorConfig(sTags, { baseValue: sup, noise: 0.008 });
      await updateSimulatorConfig(rTags, { baseValue: ret, noise: 0.008 });
    }
    await injectFault(['PCW01.Submain01.PTS', 'PCW05.Submain01.PTS'], 'DRIFT', { driftRatePerMin: 0.008 });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', height: '100%' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 className="panel-title">8. Modbus/TCP Server (Port 15020) & Behavioral Deviation Simulator</h2>
          <div className="panel-subtitle mono">
            Status: {simulatorStatus?.isRunning ? 'RUNNING' : 'PAUSED'} · Iteration #{simulatorStatus?.iteration ?? 0} · Encoding: IEEE-754 FLOAT32 CDAB (40001..40639)
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
          <button className={`btn ${tab === 'SIMULATOR' ? 'primary' : ''}`} onClick={() => setTab('SIMULATOR')}>Sensor Simulator</button>
          <button className={`btn ${tab === 'MODBUS' ? 'primary' : ''}`} onClick={() => setTab('MODBUS')}>Modbus Register Monitor ({modbusMap.length} Tags)</button>
          <button className="btn success" onClick={() => setSimulatorControl('START', 1000)}>Start</button>
          <button className="btn" onClick={() => setSimulatorControl('PAUSE')}>Pause</button>
          <button className="btn danger" onClick={() => setSimulatorControl('RESET', 1000)}>Reset Baseline</button>
        </div>
      </div>

      {tab === 'SIMULATOR' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '0.85rem', flex: 1, minHeight: 0 }}>
          {/* Left Injection Workbench */}
          <div className="card" style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <div className="kpi-label" style={{ marginBottom: '0.35rem' }}>Quick Research Validation Presets</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <button className="btn brand" onClick={runPresetConsistencyProbe}>1.72 bar State Consistency Probe (SM01.PTS)</button>
                <button className="btn primary" onClick={runPreset160PtDeviation}>&gt;10-min Behavioral Deviation (All 160 PT)</button>
                <button className="btn" onClick={() => applySuggestedBaselines(sysFilter || 'PCW01')}>Apply Suggested Baselines ({sysFilter || 'PCW01'})</button>
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border-soft)', paddingTop: '0.65rem' }}>
              <div className="kpi-label" style={{ marginBottom: '0.35rem' }}>Custom Manual Baseline & Noise ({selectedTags.length} selected)</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginBottom: '0.4rem' }}>
                <div>
                  <label style={{ fontSize: '0.7rem', fontWeight: 700 }}>Base Value</label>
                  <input className="input mono" style={{ width: '100%' }} value={baseVal} onChange={(e) => setBaseVal(e.target.value)} />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', fontWeight: 700 }}>Noise (±)</label>
                  <input className="input mono" style={{ width: '100%' }} value={noiseVal} onChange={(e) => setNoiseVal(e.target.value)} />
                </div>
              </div>
              <button
                className="btn primary"
                style={{ width: '100%' }}
                onClick={() => updateSimulatorConfig(selectedTags, { baseValue: Number(baseVal), noise: Number(noiseVal) })}
              >
                Update Base Value / Noise
              </button>
            </div>

            <div style={{ borderTop: '1px solid var(--border-soft)', paddingTop: '0.65rem' }}>
              <div className="kpi-label" style={{ marginBottom: '0.35rem' }}>Behavioral Deviation Scenario Injection</div>
              <select className="select" style={{ width: '100%', marginBottom: '0.4rem' }} value={scenario} onChange={(e) => setScenario(e.target.value as FaultScenario)}>
                <option value="NONE">NONE (Clean Nominal)</option>
                <option value="DRIFT">DRIFT (Slow Linear Ramp)</option>
                <option value="STEP">STEP (Immediate Offset Jump)</option>
                <option value="SPIKE">SPIKE (Transient Impulse)</option>
                <option value="BAD_QUALITY">BAD_QUALITY (Sensor Fault)</option>
                <option value="COMM_LOSS">COMM_LOSS (Freeze Last Value)</option>
              </select>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.35rem', marginBottom: '0.45rem' }}>
                <div><label style={{ fontSize: '0.66rem', fontWeight: 700 }}>Drift/m</label><input className="input mono" style={{ width: '100%' }} value={driftRate} onChange={(e) => setDriftRate(e.target.value)} /></div>
                <div><label style={{ fontSize: '0.66rem', fontWeight: 700 }}>Step Δ</label><input className="input mono" style={{ width: '100%' }} value={stepOffset} onChange={(e) => setStepOffset(e.target.value)} /></div>
                <div><label style={{ fontSize: '0.66rem', fontWeight: 700 }}>Spike</label><input className="input mono" style={{ width: '100%' }} value={spikeAmp} onChange={(e) => setSpikeAmp(e.target.value)} /></div>
              </div>
              <button
                className="btn danger"
                style={{ width: '100%' }}
                onClick={() =>
                  injectFault(selectedTags, scenario, {
                    driftRatePerMin: Number(driftRate),
                    stepOffset: Number(stepOffset),
                    spikeAmplitude: Number(spikeAmp),
                    spikeProbability: 0.1,
                  })
                }
              >
                Inject Scenario on Selected Tags
              </button>
            </div>
          </div>

          {/* Right Sensor Matrix */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', overflow: 'hidden' }}>
            <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
              <input className="input mono" placeholder="Search Tag..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ minWidth: '180px' }} />
              <select className="select" value={sysFilter} onChange={(e) => setSysFilter(e.target.value)}>
                <option value="">All Systems</option>
                {Array.from({ length: 8 }, (_, i) => `PCW0${i + 1}`).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                <option value="">All Types</option>
                <option value="PT">PT (160)</option>
                <option value="FT">FT (80)</option>
                <option value="PDT">PDT (80)</option>
              </select>
              <button className="btn" onClick={() => setSelectedTags(filteredSensors.map((s) => s.tagId))}>Select Displayed ({filteredSensors.length})</button>
              <button className="btn" onClick={() => setSelectedTags([])}>Clear Selection</button>
            </div>

            <div className="table-wrap" style={{ flex: 1 }}>
              <table>
                <thead>
                  <tr>
                    <th>Sel</th>
                    <th>Tag ID</th>
                    <th>Live Value</th>
                    <th>Base Setpoint</th>
                    <th>Scenario</th>
                    <th>Noise</th>
                    <th>Limits (HH / H / L / LL)</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSensors.map((s) => {
                    const cfg = simulatorConfigs[s.tagId];
                    const checked = selectedTags.includes(s.tagId);
                    return (
                      <tr key={s.tagId} className={checked ? 'selected-row' : ''} onClick={() => toggleTag(s.tagId)} style={{ cursor: 'pointer' }}>
                        <td><input type="checkbox" checked={checked} onChange={() => {}} /></td>
                        <td className="mono" style={{ fontWeight: 700 }}>{s.tagId}</td>
                        <td className="mono" style={{ fontWeight: 800 }}>{s.value.toFixed(3)} {s.unit}</td>
                        <td className="mono">{cfg?.baseValue?.toFixed(3) ?? '--'}</td>
                        <td><span className={`badge ${cfg?.scenario && cfg.scenario !== 'NONE' ? 'warning' : 'normal'}`}>{cfg?.scenario ?? 'NONE'}</span></td>
                        <td className="mono">{cfg?.noise?.toFixed(3) ?? '--'}</td>
                        <td className="mono">{s.engineeringLimits.highHigh} / {s.engineeringLimits.high} / {s.engineeringLimits.low} / {s.engineeringLimits.lowLow}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '0.85rem', flex: 1, minHeight: 0 }}>
          <div className="table-wrap" style={{ height: '100%' }}>
            <table>
              <thead>
                <tr>
                  <th>Reg Addr (Base 40001)</th>
                  <th>Canonical Tag</th>
                  <th>Word 1 (CD) Hex</th>
                  <th>Word 2 (AB) Hex</th>
                  <th>Engineering Float32</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {modbusMap.map((m) => {
                  const rv = modbus[m.registerAddress];
                  const r1 = rv?.reg1 ?? 0;
                  const r2 = rv?.reg2 ?? 0;
                  return (
                    <tr key={m.tagId}>
                      <td className="mono" style={{ fontWeight: 700 }}>{m.registerAddress}–{m.registerAddress + 1}</td>
                      <td className="mono">{m.tagId}</td>
                      <td className="mono">0x{r1.toString(16).padStart(4, '0').toUpperCase()} ({r1})</td>
                      <td className="mono">0x{r2.toString(16).padStart(4, '0').toUpperCase()} ({r2})</td>
                      <td className="mono" style={{ fontWeight: 800 }}>{rv?.engineeringValue !== undefined ? rv.engineeringValue.toFixed(4) : '--'} {m.unit}</td>
                      <td><span className={`badge ${rv?.quality === 'GOOD' ? 'normal' : 'alarm'}`}>{rv?.quality ?? 'GOOD'}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div className="kpi-label" style={{ marginBottom: '0.5rem' }}>Modbus TCP Write Audit Log (:15020)</div>
            <div className="mono" style={{ flex: 1, overflowY: 'auto', fontSize: '0.72rem', background: 'var(--bg-subtle)', padding: '0.5rem', borderRadius: '6px' }}>
              {modbusWriteLog.length === 0 ? 'Waiting for external FC06/FC16 writes...' : [...modbusWriteLog].reverse().map((line, i) => <div key={i} style={{ marginBottom: '0.25rem' }}>{line}</div>)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
