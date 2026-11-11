import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useScadaStore } from '../store/scadaStore';

const badgeForPred = (state: string) => {
  if (state === 'NORMAL') return 'normal';
  if (state === 'T-30') return 't30';
  if (state === 'T-20') return 't20';
  if (state === 'T-10' || state === 'EVENT') return 'event';
  return 'neutral';
};

export const SystemOverview = () => {
  const systems = useScadaStore((s) => s.systems);
  const pairs = useScadaStore((s) => s.pairs);
  const alarms = useScadaStore((s) => s.alarms);
  const sensors = useScadaStore((s) => s.sensors);
  const predictions = useScadaStore((s) => s.predictions);
  const sqliteStats = useScadaStore((s) => s.sqliteStats);
  const predictionConfig = useScadaStore((s) => s.predictionConfig);
  const openTagDetail = useScadaStore((s) => s.openTagDetail);
  const navigate = useNavigate();

  const ptCount = sensors.filter((s) => s.measurementType === 'PRESSURE').length;
  const ftCount = sensors.filter((s) => s.measurementType === 'FLOW').length;
  const pdtCount = sensors.filter((s) => s.measurementType === 'DP' || s.measurementType === 'DIFFERENTIAL_PRESSURE').length;
  const activeAlarms = alarms.filter((a) => a.state.startsWith('ACTIVE'));
  const unackAlarms = alarms.filter((a) => a.state.includes('UNACK'));
  const warningPreds = predictions.filter((p) => ['T-30', 'T-20', 'T-10'].includes(p.state));
  const eventPreds = predictions.filter((p) => p.state === 'EVENT');
  const coupledPairs = pairs.filter((p) => p.couplingMode === 'COUPLED_DRIFT').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      {/* Top Telemetry KPI Strip */}
      <section className="kpi-strip">
        <div className="kpi-card">
          <span className="kpi-label">Plant Topology</span>
          <span className="kpi-value">{sensors.length || 320} Tags</span>
          <span className="kpi-sub">{ptCount} PT · {ftCount} FT · {pdtCount} PDT (80 Pairs)</span>
        </div>
        <div className="kpi-card" style={{ borderColor: activeAlarms.length ? 'var(--danger)' : undefined }}>
          <span className="kpi-label">Active ISA-18.2 Alarms</span>
          <span className="kpi-value" style={{ color: activeAlarms.length ? 'var(--danger)' : 'var(--success)' }}>
            {activeAlarms.length}
          </span>
          <span className="kpi-sub">Unacknowledged: {unackAlarms.length}</span>
        </div>
        <div className="kpi-card" style={{ borderColor: warningPreds.length ? 'var(--warning)' : undefined }}>
          <span className="kpi-label">Early Drift Warnings</span>
          <span className="kpi-value" style={{ color: warningPreds.length ? 'var(--warning)' : 'var(--success)' }}>
            {warningPreds.length}
          </span>
          <span className="kpi-sub">Events: {eventPreds.length} · Coupled Pairs: {coupledPairs}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Engine Parameters</span>
          <span className="kpi-value">θ={predictionConfig?.sensitivity ?? 2}</span>
          <span className="kpi-sub">Gate {predictionConfig?.slopeGatePct ?? 5}% · Hold {predictionConfig?.releaseHold ?? 3} · Onset {predictionConfig?.rawOnset ?? 1}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">SQLite Prediction Logs</span>
          <span className="kpi-value">{(sqliteStats?.totalRows ?? 0).toLocaleString()}</span>
          <span className="kpi-sub">Tags Logged: {sqliteStats?.uniqueTags ?? 0} · Non-Normal: {(sqliteStats?.nonNormalRows ?? 0).toLocaleString()}</span>
        </div>
      </section>

      {/* 8-Loop Factory Grid */}
      <section className="card">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">ALL LOOP SYSTEM STATUS (PCW01 ~ PCW08)</h2>
            <div className="panel-subtitle">Real-time Supply/Return loop telemetry, submain drift distribution & alarm health</div>
          </div>
          <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
            <span className="badge normal">NORMAL</span>
            <span className="badge t30">EARLY WARNING (T-30/T-20/T-10)</span>
            <span className="badge alarm">ALARM / EVENT</span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(220px, 1fr))', gap: '0.75rem' }}>
          {systems.map((sys) => {
            const sysSensors = sensors.filter((s) => s.systemId === sys.systemId);
            const ptsList = sysSensors.filter((s) => s.tagId.endsWith('.PTS'));
            const ftList = sysSensors.filter((s) => s.tagId.endsWith('.FT'));
            const pdtList = sysSensors.filter((s) => s.tagId.endsWith('.PDT'));
            const avgPts = ptsList.length ? ptsList.reduce((a, b) => a + b.value, 0) / ptsList.length : sys.supplyPressure ?? 0;
            const avgFt = ftList.length ? ftList.reduce((a, b) => a + b.value, 0) / ftList.length : sys.flowRate ?? 0;
            const avgPdt = pdtList.length ? pdtList.reduce((a, b) => a + b.value, 0) / pdtList.length : 0.3;

            const sysPreds = predictions.filter((p) => p.tagId.startsWith(sys.systemId));
            const driftCount = sysPreds.filter((p) => p.state !== 'NORMAL' && p.state !== 'INSUFFICIENT_DATA' && p.state !== 'DISABLED').length;
            const sysAlarms = alarms.filter((a) => a.systemId === sys.systemId && a.state.startsWith('ACTIVE'));
            const topRisk = [...sysPreds].sort((a, b) => b.riskScore - a.riskScore)[0];
            const overallState = sysAlarms.length > 0 ? 'ALARM' : driftCount > 0 ? 'WARNING' : 'NORMAL';

            const borderStyle =
              overallState === 'ALARM'
                ? { border: '2px solid var(--danger)', borderTop: '5px solid var(--danger)' }
                : overallState === 'WARNING'
                ? { border: '2px dashed var(--warning)', borderTop: '5px solid var(--warning)' }
                : { border: '1.5px solid var(--border-strong)', borderTop: '5px solid var(--success)' };

            return (
              <div
                key={sys.systemId}
                className="card"
                style={{ ...borderStyle, cursor: 'pointer', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}
                onClick={() => navigate(`/sensors?systemId=${sys.systemId}`)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong style={{ fontSize: '1.05rem', fontWeight: 900 }}>{sys.systemId}</strong>
                    <div style={{ fontSize: '0.68rem', color: 'var(--ink-muted)' }}>{sys.description}</div>
                  </div>
                  <span className={`badge ${overallState === 'ALARM' ? 'alarm' : overallState === 'WARNING' ? 'warning' : 'normal'}`}>
                    {overallState}
                  </span>
                </div>

                {/* Live Physical Telemetry Summary */}
                <div className="mono" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.35rem', background: 'var(--bg-subtle)', padding: '0.4rem', borderRadius: '6px', fontSize: '0.72rem' }}>
                  <div><div style={{ color: 'var(--ink-muted)', fontSize: '0.64rem' }}>PTS Mean</div><strong>{avgPts.toFixed(2)}</strong></div>
                  <div><div style={{ color: 'var(--ink-muted)', fontSize: '0.64rem' }}>FT Mean</div><strong>{avgFt.toFixed(0)}</strong></div>
                  <div><div style={{ color: 'var(--ink-muted)', fontSize: '0.64rem' }}>ΔP Mean</div><strong>{avgPdt.toFixed(2)}</strong></div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                  <span>Active Alarms: <strong>{sysAlarms.length}</strong></span>
                  <span>Drift Tags: <strong>{driftCount} / {sysSensors.length}</strong></span>
                </div>

                {topRisk && topRisk.riskScore > 0 && (
                  <div
                    onClick={(e) => { e.stopPropagation(); openTagDetail(topRisk.tagId); }}
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', borderTop: '1px solid var(--border-soft)', paddingTop: '0.35rem' }}
                  >
                    <span className="mono" style={{ color: 'var(--brand-primary)', fontWeight: 700 }}>{topRisk.tagId.replace(`${sys.systemId}.`, '')}</span>
                    <span className={`badge ${badgeForPred(topRisk.state)}`}>{topRisk.state} ({topRisk.riskScore})</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
