import React, { useEffect, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useScadaStore } from '../store/scadaStore';
import { pcwDataService } from '../services/PcwDataService';

export const HistorianTrend = () => {
  const sensors = useScadaStore((s) => s.sensors);
  const historyData = useScadaStore((s) => s.historyData);
  const fetchSensorHistory = useScadaStore((s) => s.fetchSensorHistory);

  const [subTab, setSubTab] = useState<'SERIES' | 'SQLITE_LOGS'>('SERIES');
  const [baseTag, setBaseTag] = useState('PCW01.Submain01.PTS');
  const [includeFeatures, setIncludeFeatures] = useState(true);
  const [hoursBack, setHoursBack] = useState(2);

  // SQLite Prediction Logs state
  const [logTagFilter, setLogTagFilter] = useState('');
  const [logStateFilter, setLogStateFilter] = useState('');
  const [logData, setLogData] = useState<{ summary: any; rows: any[] }>({ summary: {}, rows: [] });

  const runHistoryQuery = () => {
    const end = new Date();
    const start = new Date(end.getTime() - hoursBack * 3600 * 1000);
    const tags = includeFeatures
      ? [baseTag, `${baseTag}_BaseAvg60`, `${baseTag}_Fcst10`, `${baseTag}_Fcst30`]
      : [baseTag];
    fetchSensorHistory(tags, start.toISOString(), end.toISOString());
  };

  const runLogsQuery = () => {
    pcwDataService.getPredictionLogs({ tagId: logTagFilter || undefined, state: logStateFilter || undefined, limit: 300 }).then(setLogData);
  };

  useEffect(() => {
    runHistoryQuery();
  }, [baseTag, hoursBack, includeFeatures]);

  useEffect(() => {
    if (subTab === 'SQLITE_LOGS') runLogsQuery();
  }, [subTab]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', height: '100%' }}>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 className="panel-title">3. Historian Time Series & SQLite Prediction Audit</h2>
          <div className="panel-subtitle">1-minute aggregated GOOD history + persisted prediction_logs SQLite table</div>
        </div>
        <div style={{ display: 'flex', gap: '0.45rem' }}>
          <button className={`btn ${subTab === 'SERIES' ? 'primary' : ''}`} onClick={() => setSubTab('SERIES')}>Historian Curve</button>
          <button className={`btn ${subTab === 'SQLITE_LOGS' ? 'primary' : ''}`} onClick={() => setSubTab('SQLITE_LOGS')}>SQLite Prediction Logs</button>
        </div>
      </div>

      {subTab === 'SERIES' ? (
        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontSize: '0.78rem', fontWeight: 700 }}>Target Sensor:</label>
            <select className="select mono" value={baseTag} onChange={(e) => setBaseTag(e.target.value)}>
              {sensors.map((s) => <option key={s.tagId} value={s.tagId}>{s.tagId}</option>)}
            </select>
            <select className="select" value={hoursBack} onChange={(e) => setHoursBack(Number(e.target.value))}>
              <option value={1}>Last 1 Hour</option>
              <option value={2}>Last 2 Hours</option>
              <option value={6}>Last 6 Hours</option>
              <option value={12}>Last 12 Hours</option>
            </select>
            <label style={{ fontSize: '0.78rem', fontWeight: 600 }}>
              <input type="checkbox" checked={includeFeatures} onChange={(e) => setIncludeFeatures(e.target.checked)} style={{ marginRight: '0.35rem' }} />
              Overlay BaseAvg60 & Fcst10/30
            </label>
            <button className="btn primary" onClick={runHistoryQuery}>Query Historian</button>
          </div>

          <div style={{ flex: 1, minHeight: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
                <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey={baseTag} name={`${baseTag} (PV)`} stroke="#0f172a" strokeWidth={2.2} dot={false} />
                {includeFeatures && (
                  <>
                    <Line type="monotone" dataKey={`${baseTag}_BaseAvg60`} name="BaseAvg60" stroke="#15803d" strokeDasharray="4 4" strokeWidth={1.8} dot={false} />
                    <Line type="monotone" dataKey={`${baseTag}_Fcst10`} name="Fcst+10" stroke="#0369a1" strokeWidth={1.5} dot={false} />
                    <Line type="monotone" dataKey={`${baseTag}_Fcst30`} name="Fcst+30" stroke="#b91c1c" strokeWidth={1.5} dot={false} />
                  </>
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.65rem', overflow: 'hidden' }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <input className="input mono" placeholder="Exact Tag ID (optional)" value={logTagFilter} onChange={(e) => setLogTagFilter(e.target.value)} style={{ minWidth: '210px' }} />
            <select className="select" value={logStateFilter} onChange={(e) => setLogStateFilter(e.target.value)}>
              <option value="">All States</option>
              <option value="EVENT">EVENT</option>
              <option value="T-10">T-10</option>
              <option value="T-20">T-20</option>
              <option value="T-30">T-30</option>
              <option value="NORMAL">NORMAL</option>
            </select>
            <button className="btn primary" onClick={runLogsQuery}>Query SQLite DB</button>
            <span className="badge info">Total DB Rows: {(logData.summary?.totalRows ?? 0).toLocaleString()}</span>
            <span className="badge warning">Non-Normal: {(logData.summary?.nonNormalRows ?? 0).toLocaleString()}</span>
          </div>

          <div className="table-wrap" style={{ flex: 1 }}>
            <table>
              <thead>
                <tr>
                  <th>Eval Time</th>
                  <th>Tag ID</th>
                  <th>Scenario</th>
                  <th>PV</th>
                  <th>BaseAvg60</th>
                  <th>M60 / M10 / N10</th>
                  <th>Slope</th>
                  <th>Fcst30</th>
                  <th>State</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {(logData.rows ?? []).map((r: any, idx: number) => (
                  <tr key={idx}>
                    <td className="mono">{new Date(r.evalTime ?? r.eval_time).toLocaleTimeString()}</td>
                    <td className="mono" style={{ fontWeight: 700 }}>{r.tagId ?? r.tag_id}</td>
                    <td>{r.scenario ?? 'NONE'}</td>
                    <td className="mono">{Number(r.currentValue ?? r.current_value).toFixed(3)}</td>
                    <td className="mono">{Number(r.baseAvg60 ?? r.base_avg_60).toFixed(3)}</td>
                    <td className="mono">{r.m60} / {r.m10} / {Number(r.n10).toFixed(2)}</td>
                    <td className="mono">{Number(r.slope).toFixed(4)}</td>
                    <td className="mono">{Number(r.fcst30 ?? r.forecast30).toFixed(3)}</td>
                    <td><span className={`badge ${r.state === 'NORMAL' ? 'normal' : r.state === 'EVENT' ? 'event' : 't30'}`}>{r.state}</span></td>
                    <td className="mono">{r.riskScore ?? r.risk_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
