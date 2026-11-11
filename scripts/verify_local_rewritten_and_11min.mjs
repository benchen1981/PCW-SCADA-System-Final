/**
 * Automated verification & 11.2-minute real-time Modbus TCP behavioral deviation test
 * on the live rewritten full-stack PCW Unified Web SCADA v2.0 (http://127.0.0.1:8000 + Modbus TCP 15020).
 *
 * Covers ALL 320 sensors (160 PT + 80 FT + 80 PDT) and persists full SQLite + CSV + Chrome evidence.
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const puppeteer = require('/Users/benchen1981/Downloads/Web SCADA Final 20261111/Existing/Code/pcw-poc-v1_merged/node_modules/puppeteer');

const BASE_URL = 'http://127.0.0.1:8000';
const ROOT = '/Users/benchen1981/Downloads/Web SCADA Final 20261111/PCW_SCADA_Final_Project';
const SHOT_DIR = path.join(ROOT, 'evidence/browser_screenshots/local_v2');
const LOG_DIR = path.join(ROOT, 'evidence/inference_logs');
const REPORT_DIR = path.join(ROOT, 'evidence/test_reports');
fs.mkdirSync(SHOT_DIR, { recursive: true });
fs.mkdirSync(LOG_DIR, { recursive: true });
fs.mkdirSync(REPORT_DIR, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function apiPost(endpoint, body) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${endpoint} -> ${res.status}`);
  return res.json();
}

async function apiGet(endpoint) {
  const res = await fetch(`${BASE_URL}${endpoint}`);
  if (!res.ok) throw new Error(`GET ${endpoint} -> ${res.status}`);
  return res.json();
}

async function clickNav(page, labelPart) {
  await page.evaluate((part) => {
    const links = Array.from(document.querySelectorAll('.top-nav-item'));
    const target = links.find((a) => a.textContent && a.textContent.includes(part));
    if (!target) throw new Error('Nav not found: ' + part);
    target.click();
  }, labelPart);
  await sleep(900);
}

async function main() {
  const health = await apiGet('/api/health');
  console.log('Live v2.0 backend health:', health);

  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--window-size=1440,900'],
    defaultViewport: { width: 1440, height: 900 },
  });
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => pageErrors.push(e.message));

  await page.goto(BASE_URL, { waitUntil: 'networkidle2', timeout: 30000 });
  await sleep(1600);

  const streamBadge = await page.evaluate(() => document.querySelector('.top-nav-logo')?.innerText || '');
  console.log('Header transport badge:', streamBadge.replace(/\s+/g, ' '));

  // 1. Clean-state patrol of all 9 pages
  const pagesToVisit = [
    ['1. Plant Overview', 'v2_01_overview_clean.png'],
    ['2. Live Sensor Data', 'v2_02_sensors_pid.png'],
    ['3. Historian Trend', 'v2_03_historian_clean.png'],
    ['4. Live Trend', 'v2_04_live_trend.png'],
    ['5. Alarm Center', 'v2_05_alarms_clean.png'],
    ['6. System Prediction', 'v2_06_prediction_clean.png'],
    ['7. Prediction Tuning', 'v2_07_tuning.png'],
    ['8. Modbus Simulator', 'v2_08_modbus_simulator.png'],
    ['9. Prediction Model Info', 'v2_09_model_info.png'],
  ];
  for (const [nav, shot] of pagesToVisit) {
    await clickNav(page, nav);
    await page.screenshot({ path: path.join(SHOT_DIR, shot) });
  }

  // 2. Verify state consistency fix via UI button: 1.72 bar on PCW01.Submain01.PTS
  await clickNav(page, '8. Modbus Simulator');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent.includes('1.72 bar State Consistency'));
    if (!btn) throw new Error('Missing 1.72 bar preset button');
    btn.click();
  });
  await sleep(1400);

  await clickNav(page, '5. Alarm Center');
  const localAlarmRow = await page.evaluate(() => {
    const tr = Array.from(document.querySelectorAll('tbody tr')).find((r) => r.textContent.includes('PCW01.Submain01.PTS'));
    return tr ? tr.innerText.replace(/\s+/g, ' ').trim() : 'NONE';
  });
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_10a_consistent_alarm.png') });

  await clickNav(page, '6. System Prediction');
  const localPredRow = await page.evaluate(() => {
    const tr = Array.from(document.querySelectorAll('tbody tr')).find((r) => r.textContent.includes('PCW01.Submain01.PTS'));
    return tr ? tr.innerText.replace(/\s+/g, ' ').trim() : 'NONE';
  });
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_10_consistent_pred_cone.png') });

  // Reset back to clean baseline before 11.2-minute behavioral deviation test across ALL 320 sensors
  await apiPost('/api/simulator/control', { action: 'RESET', intervalMs: 1000 });
  await sleep(1200);

  // 3. Inject behavioral deviations across ALL 320 sensors (160 PT + 80 FT + 80 PDT) within engineering limits
  const sensors = await apiGet('/api/sensors');
  const ptsSupply = sensors.filter((s) => s.tagId.endsWith('.PTS'));
  const ptsReturn = sensors.filter((s) => s.tagId.endsWith('.PTR'));
  const ftAll = sensors.filter((s) => s.tagId.endsWith('.FT')).map((s) => s.tagId);
  const pdtAll = sensors.filter((s) => s.tagId.endsWith('.PDT')).map((s) => s.tagId);

  const groupTargets = {
    PCW01: [1.62, 1.38], PCW02: [1.62, 1.38],
    PCW03: [2.02, 1.78], PCW04: [2.02, 1.78],
    PCW05: [2.62, 2.38], PCW06: [2.62, 2.38],
    PCW07: [2.32, 2.08], PCW08: [2.32, 2.08],
  };

  for (const [sys, [supTarget, retTarget]] of Object.entries(groupTargets)) {
    const sTags = ptsSupply.filter((s) => s.systemId === sys).map((s) => s.tagId);
    const rTags = ptsReturn.filter((s) => s.systemId === sys).map((s) => s.tagId);
    await apiPost('/api/simulator/config', { tagIds: sTags, baseValue: supTarget, noise: 0.008 });
    await apiPost('/api/simulator/config', { tagIds: rTags, baseValue: retTarget, noise: 0.008 });
  }
  await apiPost('/api/simulator/config', { tagIds: ftAll, baseValue: 195.0, noise: 0.8 });
  await apiPost('/api/simulator/config', { tagIds: pdtAll, baseValue: 0.45, noise: 0.008 });

  // Also inject realistic slow positive drift (+0.008 bar/min) on PCW01.Submain01.PTS & PCW05.Submain01.PTS
  await apiPost('/api/simulator/fault', {
    tagIds: ['PCW01.Submain01.PTS', 'PCW05.Submain01.PTS'],
    scenario: 'DRIFT',
    driftRatePerMin: 0.008,
  });

  // 4. Real-time >10 minute continuous run (11.2 minutes)
  const totalDurationMs = 11.2 * 60 * 1000;
  const sampleIntervalMs = 30 * 1000;
  const startMs = Date.now();
  const logSamples = [];
  const everPredictedTags = new Set();
  const everDriftAlarmTags = new Set();
  let idx = 0;

  while (true) {
    const elapsedMs = Date.now() - startMs;
    const elapsedMin = Number((elapsedMs / 60000).toFixed(2));
    const snap = await apiGet('/api/snapshot');
    const ptPreds = snap.predictions.filter((p) => p.tagId.endsWith('.PTS') || p.tagId.endsWith('.PTR'));
    const allCounts = {};
    const ptCounts = {};

    for (const p of snap.predictions) {
      allCounts[p.state] = (allCounts[p.state] || 0) + 1;
      if (['T-30', 'T-20', 'T-10', 'EVENT'].includes(p.state)) everPredictedTags.add(p.tagId);
    }
    for (const p of ptPreds) ptCounts[p.state] = (ptCounts[p.state] || 0) + 1;

    const driftAlarms = snap.alarms.filter((a) => a.alarmType === 'DRIFT');
    for (const a of driftAlarms) everDriftAlarmTags.add(a.tagId);

    logSamples.push({
      sampleIdx: idx,
      timestamp: new Date().toISOString(),
      elapsedMin,
      allStateCounts: allCounts,
      ptStateCounts: ptCounts,
      cumulativePredictedTags: everPredictedTags.size,
      cumulativeDriftAlarmTags: everDriftAlarmTags.size,
      activeAlarmsCount: snap.alarms.length,
      driftAlarmsCount: driftAlarms.length,
      representative: snap.predictions.filter((p) => p.tagId.includes('Submain01.')),
    });

    if (idx === 0 || idx === 10 || idx === 20) {
      await clickNav(page, '6. System Prediction');
      await page.screenshot({ path: path.join(SHOT_DIR, `v2_11min_pred_s${String(idx).padStart(2, '0')}.png`) });
    }

    if (elapsedMs + sampleIntervalMs > totalDurationMs) {
      // Wait the remaining fraction if still slightly below 11.2 min, or break once past 11.2 min
      if (elapsedMs < totalDurationMs) {
        await sleep(totalDurationMs - elapsedMs + 1000);
      }
      // Capture final v2.0 UI screenshots across key views at >= 11.2 min
      const finalSnap = await apiGet('/api/snapshot');
      const finalCounts = {};
      const finalPtCounts = {};
      for (const p of finalSnap.predictions) {
        finalCounts[p.state] = (finalCounts[p.state] || 0) + 1;
        if (['T-30', 'T-20', 'T-10', 'EVENT'].includes(p.state)) everPredictedTags.add(p.tagId);
      }
      for (const p of finalSnap.predictions.filter((p) => p.tagId.endsWith('.PTS') || p.tagId.endsWith('.PTR'))) {
        finalPtCounts[p.state] = (finalPtCounts[p.state] || 0) + 1;
      }
      const finalDrift = finalSnap.alarms.filter((a) => a.alarmType === 'DRIFT');
      for (const a of finalDrift) everDriftAlarmTags.add(a.tagId);

      logSamples.push({
        sampleIdx: idx + 1,
        timestamp: new Date().toISOString(),
        elapsedMin: Number(((Date.now() - startMs) / 60000).toFixed(2)),
        allStateCounts: finalCounts,
        ptStateCounts: finalPtCounts,
        cumulativePredictedTags: everPredictedTags.size,
        cumulativeDriftAlarmTags: everDriftAlarmTags.size,
        activeAlarmsCount: finalSnap.alarms.length,
        driftAlarmsCount: finalDrift.length,
        representative: finalSnap.predictions.filter((p) => p.tagId.includes('Submain01.')),
      });

      await clickNav(page, '1. Plant Overview');
      await page.screenshot({ path: path.join(SHOT_DIR, 'v2_11min_overview_final.png') });

      await clickNav(page, '6. System Prediction');
      await page.screenshot({ path: path.join(SHOT_DIR, 'v2_11min_sensor_pred_final.png') });
      await page.evaluate(() => {
        const b = Array.from(document.querySelectorAll('button')).find((x) => x.textContent.includes('Pair Level'));
        if (b) b.click();
      });
      await sleep(600);
      await page.screenshot({ path: path.join(SHOT_DIR, 'v2_11min_pair_diagnostics.png') });

      await clickNav(page, '5. Alarm Center');
      await page.screenshot({ path: path.join(SHOT_DIR, 'v2_11min_alarm_center_final.png') });

      await clickNav(page, '8. Modbus Simulator');
      await page.screenshot({ path: path.join(SHOT_DIR, 'v2_11min_fault_injector.png') });

      await clickNav(page, '3. Historian Trend');
      await sleep(900);
      await page.screenshot({ path: path.join(SHOT_DIR, 'v2_11min_historian_curve.png') });
      await page.evaluate(() => {
        const b = Array.from(document.querySelectorAll('button')).find((x) => x.textContent.includes('SQLite Prediction Logs'));
        if (b) b.click();
      });
      await sleep(900);
      await page.screenshot({ path: path.join(SHOT_DIR, 'v2_11min_sqlite_logs.png') });

      // Export full SQLite prediction logs & final 320 sensor snapshots
      const predLogs = await apiGet('/api/predictions/logs?limit=5000');
      fs.writeFileSync(path.join(LOG_DIR, 'local_11min_sqlite_prediction_logs.json'), JSON.stringify(predLogs, null, 2));
      fs.writeFileSync(path.join(LOG_DIR, 'local_11min_final_snapshot.json'), JSON.stringify(finalSnap, null, 2));

      const csvHeader = 'tagId,evaluationTime,currentValue,baseAvg60,m60,m10,n10,slope,slopeOls,r2,fcst10,fcst20,fcst30,ttlMinutes,state,detector,riskScore,triggerPath';
      const csvRows = finalSnap.predictions.map((p) =>
        [
          p.tagId, p.evaluationTime, p.currentValue, p.baseAvg60, p.m60, p.m10, p.n10, p.slope,
          p.slopeOls ?? 0, p.r2 ?? 0, p.forecast10, p.forecast20, p.forecast30, p.ttlMinutes ?? '',
          p.state, p.detector, p.riskScore, `"${(p.triggerPath || '').replace(/"/g, '""')}"`
        ].join(',')
      );
      fs.writeFileSync(path.join(LOG_DIR, 'local_all_320_sensor_predictions_final.csv'), [csvHeader, ...csvRows].join('\n'));
      break;
    }

    idx += 1;
    await sleep(sampleIntervalMs);
  }

  // Archive live SQLite DB after 11.2m run and reset simulator cleanly for user UI
  fs.copyFileSync(path.join(ROOT, 'system/backend/data/pcw_scada.db'), path.join(ROOT, 'evidence/database_exports/pcw_scada_11min.db'));

  const summary = {
    url: BASE_URL,
    health: await apiGet('/api/health'),
    executedAt: new Date().toISOString(),
    durationMinutes: Number(((Date.now() - startMs) / 60000).toFixed(2)),
    consoleErrors,
    pageErrors,
    consistencyCheck172: { alarmCenterRow: localAlarmRow, systemPredictionRow: localPredRow },
    samplesCount: logSamples.length,
    cumulativePredictedTagsCount: everPredictedTags.size,
    cumulativeDriftAlarmTagsCount: everDriftAlarmTags.size,
    finalAll320StateCounts: logSamples[logSamples.length - 1]?.allStateCounts,
    finalPtStateCounts: logSamples[logSamples.length - 1]?.ptStateCounts,
    finalDriftAlarmsCount: logSamples[logSamples.length - 1]?.driftAlarmsCount,
  };
  fs.writeFileSync(path.join(LOG_DIR, 'local_11min_deviation_log.json'), JSON.stringify(logSamples, null, 2));
  fs.writeFileSync(path.join(REPORT_DIR, 'local_web_verification_summary.json'), JSON.stringify(summary, null, 2));

  console.log(JSON.stringify(summary, null, 2));
  await browser.close();
  if (consoleErrors.length || pageErrors.length) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
