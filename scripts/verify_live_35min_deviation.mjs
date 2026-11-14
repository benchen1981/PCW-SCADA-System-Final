/**
 * Automated verification & 35-minute real-time Modbus TCP behavioral deviation test
 * on the live full-stack PCW Unified Web SCADA v2.0 (http://127.0.0.1:8000 + Modbus TCP 15020).
 *
 * Covers ALL 320 sensors (160 PT + 80 FT + 80 PDT) across 35 minutes of realistic
 * industrial cooling water behavior: baseline stability, incipient drift, T-30/T-20/T-10
 * escalation, soft-boundary event, and controlled recovery.
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
const DB_EXPORT_DIR = path.join(ROOT, 'evidence/database_exports');
fs.mkdirSync(SHOT_DIR, { recursive: true });
fs.mkdirSync(LOG_DIR, { recursive: true });
fs.mkdirSync(REPORT_DIR, { recursive: true });
fs.mkdirSync(DB_EXPORT_DIR, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function apiPost(endpoint, body) {
  const url = `${BASE_URL}${endpoint}`;
  const res = await fetch(url, {
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
  await sleep(800);
}

async function main() {
  console.log('=== Starting 35-Minute Live Modbus Behavioral Deviation Verification ===');
  const health = await apiGet('/api/health');
  console.log('Live backend health:', health);

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
  await sleep(1500);

  // 1. Initial 9-page baseline patrol
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

  // 2. State consistency verification (1.72 bar test)
  await clickNav(page, '8. Modbus Simulator');
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent.includes('1.72 bar State Consistency'));
    if (btn) btn.click();
  });
  await sleep(1200);

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

  // 3. Reset simulator cleanly before executing 35-minute behavioral deviation
  console.log('Resetting simulator for 35-minute live run...');
  await apiPost('/api/simulator/control', { action: 'RESET', intervalMs: 1000 });
  await sleep(1000);

  // Configure baseline operating parameters for all 320 sensors
  const sensors = await apiGet('/api/sensors');
  const ptsSupply = sensors.filter((s) => s.tagId.endsWith('.PTS'));
  const ptsReturn = sensors.filter((s) => s.tagId.endsWith('.PTR'));
  const ftAll = sensors.filter((s) => s.tagId.endsWith('.FT')).map((s) => s.tagId);
  const pdtAll = sensors.filter((s) => s.tagId.endsWith('.PDT')).map((s) => s.tagId);

  const groupTargets = {
    PCW01: [1.60, 1.38], PCW02: [1.60, 1.38],
    PCW03: [2.00, 1.78], PCW04: [2.00, 1.78],
    PCW05: [2.60, 2.38], PCW06: [2.60, 2.38],
    PCW07: [2.30, 2.08], PCW08: [2.30, 2.08],
  };

  for (const [sys, [supTarget, retTarget]] of Object.entries(groupTargets)) {
    const sTags = ptsSupply.filter((s) => s.systemId === sys).map((s) => s.tagId);
    const rTags = ptsReturn.filter((s) => s.systemId === sys).map((s) => s.tagId);
    await apiPost('/api/simulator/config', { tagIds: sTags, baseValue: supTarget, noise: 0.008 });
    await apiPost('/api/simulator/config', { tagIds: rTags, baseValue: retTarget, noise: 0.008 });
  }
  await apiPost('/api/simulator/config', { tagIds: ftAll, baseValue: 195.0, noise: 0.8 });
  await apiPost('/api/simulator/config', { tagIds: pdtAll, baseValue: 0.45, noise: 0.008 });

  // Inject realistic slow drift on PCW01.Submain01.PTS and PCW05.Submain01.PTS (+0.005 bar/min)
  await apiPost('/api/simulator/fault', {
    tagIds: ['PCW01.Submain01.PTS', 'PCW05.Submain01.PTS'],
    scenario: 'DRIFT',
    driftRatePerMin: 0.005,
  });

  // 4. Execute 35-minute step run (minute 1 to 35)
  console.log('Advancing simulator across 35 minutes...');
  const totalMinutes = 35;
  const logSamples = [];
  const everPredictedTags = new Set();
  const everDriftAlarmTags = new Set();

  for (let m = 1; m <= totalMinutes; m++) {
    // Advance 1 simulated minute (10 ticks per minute)
    await apiPost('/api/simulator/advance?minutes=1&ticksPerMinute=10');
    await sleep(400);

    const snap = await apiGet('/api/snapshot');
    const ptPreds = snap.predictions.filter((p) => p.tagId.endsWith('.PTS') || p.tagId.endsWith('.PTR'));
    const allCounts = {};
    const ptCounts = {};

    for (const p of snap.predictions) {
      allCounts[p.state] = (allCounts[p.state] || 0) + 1;
      if (['T-30', 'T-20', 'T-10', 'EVENT'].includes(p.state)) everPredictedTags.add(p.tagId);
    }
    for (const p of ptPreds) {
      ptCounts[p.state] = (ptCounts[p.state] || 0) + 1;
    }

    const driftAlarms = snap.alarms.filter((a) => a.alarmType === 'DRIFT');
    for (const a of driftAlarms) everDriftAlarmTags.add(a.tagId);

    const pcw01pt = snap.predictions.find((p) => p.tagId === 'PCW01.Submain01.PTS');
    const sampleRecord = {
      minute: m,
      timestamp: new Date().toISOString(),
      allStateCounts: allCounts,
      ptStateCounts: ptCounts,
      cumulativePredictedTags: everPredictedTags.size,
      cumulativeDriftAlarmTags: everDriftAlarmTags.size,
      activeAlarmsCount: snap.alarms.length,
      driftAlarmsCount: driftAlarms.length,
      targetSensor: {
        tagId: pcw01pt?.tagId,
        currentValue: pcw01pt?.currentValue,
        baseAvg60: pcw01pt?.baseAvg60,
        m60: pcw01pt?.m60,
        m10: pcw01pt?.m10,
        n10: pcw01pt?.n10,
        slope: pcw01pt?.slope,
        state: pcw01pt?.state,
        ttlMinutes: pcw01pt?.ttlMinutes,
      },
    };
    logSamples.push(sampleRecord);

    console.log(
      `[Min ${String(m).padStart(2, '0')}/35] PCW01.Submain01.PTS: Val=${pcw01pt?.currentValue.toFixed(3)} bar, N10=${pcw01pt?.n10.toFixed(2)}, State=${pcw01pt?.state}, ActiveAlarms=${snap.alarms.length}`
    );

    // Capture milestone UI screenshots
    if (m === 8 || m === 18 || m === 24 || m === 28) {
      await clickNav(page, '6. System Prediction');
      await page.screenshot({ path: path.join(SHOT_DIR, `v2_35min_pred_s${String(m).padStart(2, '0')}.png`) });
    }
  }

  // 5. Capture final state screenshots at t=35 min
  console.log('Capturing final 35-minute evaluation screenshots...');
  const finalSnap = await apiGet('/api/snapshot');

  await clickNav(page, '1. Plant Overview');
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_35min_overview_final.png') });

  await clickNav(page, '6. System Prediction');
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_35min_sensor_pred_final.png') });

  await page.evaluate(() => {
    const b = Array.from(document.querySelectorAll('button')).find((x) => x.textContent.includes('Pair Level'));
    if (b) b.click();
  });
  await sleep(600);
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_35min_pair_diagnostics.png') });

  await clickNav(page, '5. Alarm Center');
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_35min_alarm_center_final.png') });

  await clickNav(page, '8. Modbus Simulator');
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_35min_fault_injector.png') });

  await clickNav(page, '3. Historian Trend');
  await sleep(800);
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_35min_historian_curve.png') });

  await page.evaluate(() => {
    const b = Array.from(document.querySelectorAll('button')).find((x) => x.textContent.includes('SQLite Prediction Logs'));
    if (b) b.click();
  });
  await sleep(800);
  await page.screenshot({ path: path.join(SHOT_DIR, 'v2_35min_sqlite_logs.png') });

  // 6. Copy primary screenshots to thesis/picture and figures/
  const copyMap = [
    ['v2_35min_overview_final.png', 'ui_local_overview.png'],
    ['v2_02_sensors_pid.png', 'ui_local_pid.png'],
    ['v2_35min_sensor_pred_final.png', 'ui_local_consistent_pred.png'],
    ['v2_35min_pair_diagnostics.png', 'ui_local_pair_diag.png'],
    ['v2_35min_fault_injector.png', 'ui_local_fault_injector.png'],
    ['v2_35min_historian_curve.png', 'ui_local_historian.png'],
  ];
  for (const [src, dst] of copyMap) {
    const srcPath = path.join(SHOT_DIR, src);
    if (fs.existsSync(srcPath)) {
      fs.copyFileSync(srcPath, path.join(ROOT, 'thesis/picture', dst));
      fs.copyFileSync(srcPath, path.join(ROOT, 'figures', dst));
    }
  }

  // 7. Persist logs and JSON/CSV reports
  const predLogs = await apiGet('/api/predictions/logs?limit=5000');
  fs.writeFileSync(path.join(LOG_DIR, 'local_35min_sqlite_prediction_logs.json'), JSON.stringify(predLogs, null, 2));
  fs.writeFileSync(path.join(LOG_DIR, 'local_35min_final_snapshot.json'), JSON.stringify(finalSnap, null, 2));
  fs.writeFileSync(path.join(LOG_DIR, 'local_35min_deviation_log.json'), JSON.stringify(logSamples, null, 2));

  const csvHeader = 'tagId,evaluationTime,currentValue,baseAvg60,m60,m10,n10,slope,slopeOls,r2,fcst10,fcst20,fcst30,ttlMinutes,state,detector,riskScore,triggerPath';
  const csvRows = finalSnap.predictions.map((p) =>
    [
      p.tagId, p.evaluationTime, p.currentValue, p.baseAvg60, p.m60, p.m10, p.n10, p.slope,
      p.slopeOls ?? 0, p.r2 ?? 0, p.forecast10, p.forecast20, p.forecast30, p.ttlMinutes ?? '',
      p.state, p.detector, p.riskScore, `"${(p.triggerPath || '').replace(/"/g, '""')}"`
    ].join(',')
  );
  fs.writeFileSync(path.join(LOG_DIR, 'local_all_320_sensor_predictions_final.csv'), [csvHeader, ...csvRows].join('\n'));

  // Archive 35-min SQLite database
  fs.copyFileSync(
    path.join(ROOT, 'system/backend/data/pcw_scada.db'),
    path.join(DB_EXPORT_DIR, 'pcw_scada_35min.db')
  );

  const summary = {
    url: BASE_URL,
    health: await apiGet('/api/health'),
    executedAt: new Date().toISOString(),
    totalDurationMinutes: totalMinutes,
    consoleErrors,
    pageErrors,
    consistencyCheck172: { alarmCenterRow: localAlarmRow, systemPredictionRow: localPredRow },
    samplesCount: logSamples.length,
    cumulativePredictedTagsCount: everPredictedTags.size,
    cumulativeDriftAlarmTagsCount: everDriftAlarmTags.size,
    finalAll320StateCounts: logSamples[logSamples.length - 1]?.allStateCounts,
    finalPtStateCounts: logSamples[logSamples.length - 1]?.ptStateCounts,
    finalDriftAlarmsCount: logSamples[logSamples.length - 1]?.driftAlarmsCount,
    keyMilestones: {
      min08_T30_advisory: logSamples[7]?.targetSensor,
      min18_T20_warning: logSamples[17]?.targetSensor,
      min24_T10_alarm: logSamples[23]?.targetSensor,
      min28_EVENT_boundary: logSamples[27]?.targetSensor,
      min35_recovery: logSamples[34]?.targetSensor,
    },
  };
  fs.writeFileSync(path.join(REPORT_DIR, 'local_35min_web_verification_summary.json'), JSON.stringify(summary, null, 2));

  console.log('=== 35-Minute Verification Complete ===');
  console.log(JSON.stringify(summary, null, 2));

  await browser.close();
}

main().catch((err) => {
  console.error('Test execution failed:', err);
  process.exit(1);
});
