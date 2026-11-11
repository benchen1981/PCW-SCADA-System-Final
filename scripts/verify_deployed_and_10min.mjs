/**
 * Automated verification & 11.5-minute real-time Modbus behavioral deviation test
 * on the deployed Vercel Web SCADA system: https://pcw-scada-system.vercel.app/
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const puppeteer = require('/Users/benchen1981/Downloads/Web SCADA Final 20261111/Existing/Code/pcw-poc-v1_merged/node_modules/puppeteer');

const BASE_URL = 'https://pcw-scada-system.vercel.app';
const ROOT = '/Users/benchen1981/Downloads/Web SCADA Final 20261111/PCW_SCADA_Final_Project';
const SHOT_DIR = path.join(ROOT, 'evidence/browser_screenshots/deployed');
const LOG_DIR = path.join(ROOT, 'evidence/inference_logs');
const REPORT_DIR = path.join(ROOT, 'evidence/test_reports');
fs.mkdirSync(SHOT_DIR, { recursive: true });
fs.mkdirSync(LOG_DIR, { recursive: true });
fs.mkdirSync(REPORT_DIR, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function clickNav(page, labelPart) {
  await page.evaluate((part) => {
    const links = Array.from(document.querySelectorAll('.top-nav-item'));
    const target = links.find((a) => a.textContent && a.textContent.includes(part));
    if (!target) throw new Error('Nav not found: ' + part);
    target.click();
  }, labelPart);
  await sleep(700);
}

async function clickButtonByText(page, textPart) {
  const ok = await page.evaluate((part) => {
    const btns = Array.from(document.querySelectorAll('button'));
    const b = btns.find((x) => x.textContent && x.textContent.includes(part));
    if (!b) return false;
    b.click();
    return true;
  }, textPart);
  return ok;
}

async function setControlledInput(page, selectorIndex, value) {
  await page.evaluate((idx, val) => {
    const inputs = Array.from(document.querySelectorAll('input[type="number"]'));
    const el = inputs[idx];
    if (!el) throw new Error('Input index missing: ' + idx);
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, String(val));
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, selectorIndex, value);
}

async function setSelectValue(page, selectIndex, value) {
  await page.evaluate((idx, val) => {
    const sels = Array.from(document.querySelectorAll('select'));
    const el = sels[idx];
    if (!el) throw new Error('Select index missing: ' + idx);
    const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
    setter.call(el, val);
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, selectIndex, value);
  await sleep(300);
}

async function main() {
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
  await sleep(2000);

  // 1. Patrol all 9 pages
  const pagesToVisit = [
    ['1. Plant Overview', 'deployed_01_overview.png'],
    ['2. Live Sensor Data', 'deployed_02_sensors.png'],
    ['3. Historian Trend', 'deployed_03_historian.png'],
    ['4. Live Trend', 'deployed_04_live_trend.png'],
    ['5. Alarm Center', 'deployed_05_alarms.png'],
    ['6. System Prediction', 'deployed_06_prediction.png'],
    ['7. Prediction Tuning', 'deployed_07_tuning.png'],
    ['8. Modbus Simulator', 'deployed_08_modbus_monitor.png'],
    ['9. Prediction Model Info', 'deployed_09_model_info.png'],
  ];
  const patrolResults = [];
  for (const [navName, shot] of pagesToVisit) {
    await clickNav(page, navName);
    const bodyLen = await page.evaluate(() => document.body.innerText.trim().length);
    await page.screenshot({ path: path.join(SHOT_DIR, shot), fullPage: false });
    patrolResults.push({ navName, bodyLen, shot });
  }

  // 2. Consistency defect check: PCW01.Submain01.PTS -> 1.72 bar (HI = 1.70)
  await clickNav(page, '8. Modbus Simulator');
  await clickButtonByText(page, 'Sensor Simulator');
  await sleep(400);
  await page.screenshot({ path: path.join(SHOT_DIR, 'deployed_10_simulator.png') });

  // Apply suggested baselines for PCW01..PCW08 first
  for (let i = 1; i <= 8; i++) {
    await setSelectValue(page, 0, `PCW0${i}`);
    await clickButtonByText(page, 'Apply Suggested Baselines');
    await sleep(150);
  }

  // Test 1.72 bar on PCW01.Submain01.PTS
  await page.evaluate(() => {
    const inp = document.querySelector('input[placeholder="Search canonical tag"]');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, 'PCW01.Submain01.PTS');
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    inp.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await sleep(300);
  await clickButtonByText(page, 'Select All Displayed');
  await sleep(200);
  await setControlledInput(page, 1, 1.72); // Base Value input
  await clickButtonByText(page, 'Apply to Selected Tags');
  await sleep(3500); // > 3 ticks for AlarmEngine onDelay=3

  await clickNav(page, '5. Alarm Center');
  await sleep(500);
  const alarmCheckText = await page.evaluate(() => {
    const tr = Array.from(document.querySelectorAll('tbody tr')).find((r) => r.textContent.includes('PCW01.Submain01.PTS'));
    return tr ? tr.innerText.replace(/\s+/g, ' ').trim() : 'NONE';
  });
  await page.screenshot({ path: path.join(SHOT_DIR, 'deployed_11_defect_alarm.png') });

  await clickNav(page, '6. System Prediction');
  await sleep(500);
  const predCheckText = await page.evaluate(() => {
    const tr = Array.from(document.querySelectorAll('tbody tr')).find((r) => r.textContent.includes('PCW01.Submain01.PTS'));
    return tr ? tr.innerText.replace(/\s+/g, ' ').trim() : 'NONE';
  });
  await page.screenshot({ path: path.join(SHOT_DIR, 'deployed_12_defect_prediction.png') });

  // 3. Test all 160 PT sensors across PCW01..PCW08 (apply group baselines + read Modbus + Prediction + Sensor state)
  await clickNav(page, '8. Modbus Simulator');
  await clickButtonByText(page, 'Sensor Simulator');
  await sleep(300);
  // Reset search filter
  await page.evaluate(() => {
    const inp = document.querySelector('input[placeholder="Search canonical tag"]');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, '');
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    inp.dispatchEvent(new Event('change', { bubbles: true }));
  });
  // Restore PCW01 suggested baseline and set 500ms interval
  await setSelectValue(page, 0, 'PCW01');
  await clickButtonByText(page, 'Apply Suggested Baselines');
  await setControlledInput(page, 0, 500);
  await clickButtonByText(page, 'Pause');
  await sleep(200);
  await clickButtonByText(page, 'Start');
  await sleep(1000);

  // Inject behavioral deviation (within engineering limits!) across 8 representative PT sensors (one per PCW loop)
  // Plus inject a batch deviation across ALL 160 PT sensors in PCW01..PCW08 via Modbus Simulator!
  // Let's shift ALL 160 PT sensors in two rounds or shift 160 PT sensors by +0.11 bar above baseline so every PT executes prediction/deviation!
  const groupShifts = {
    PCW01: 1.63, PCW02: 1.63, // baseline 1.50, H=1.70
    PCW03: 2.03, PCW04: 2.03, // baseline 1.90, H=2.10
    PCW05: 2.63, PCW06: 2.63, // baseline 2.50, H=2.70
    PCW07: 2.33, PCW08: 2.33, // baseline 2.20, H=2.40
  };

  for (const [sys, targetBase] of Object.entries(groupShifts)) {
    // Deselect first if any selected
    await setSelectValue(page, 1, sys); // simSysFilter
    await setSelectValue(page, 2, ''); // simSubFilter
    await setSelectValue(page, 3, 'PRESSURE'); // simTypeFilter
    await sleep(200);
    // Ensure fresh select-all
    const btnTxt = await page.evaluate(() => {
      const b = Array.from(document.querySelectorAll('button')).find((x) => x.textContent.includes('Select All Displayed') || x.textContent.includes('Deselect All'));
      return b ? b.textContent : '';
    });
    if (btnTxt.includes('Deselect All')) {
      await clickButtonByText(page, 'Deselect All');
      await sleep(150);
    }
    await clickButtonByText(page, 'Select All Displayed');
    await sleep(150);
    await setControlledInput(page, 1, targetBase);
    await setControlledInput(page, 2, 0.008);
    await clickButtonByText(page, 'Apply to Selected Tags');
    await sleep(200);
    await clickButtonByText(page, 'Deselect All');
    await sleep(150);
  }

  // 4. Real-time >10 minute observation (11.5 minutes = 690 seconds, sampling every 30s)
  const totalDurationMs = 11.5 * 60 * 1000;
  const sampleIntervalMs = 30 * 1000;
  const startMs = Date.now();
  const timeSeriesLog = [];
  let sampleIdx = 0;

  while (Date.now() - startMs <= totalDurationMs) {
    const elapsedMin = ((Date.now() - startMs) / 60000).toFixed(2);
    await clickNav(page, '6. System Prediction');
    await setSelectValue(page, 2, 'PT');
    await sleep(400);
    const predRows = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('tbody tr')).map((tr) => {
        const tds = Array.from(tr.querySelectorAll('td')).map((td) => td.innerText.trim());
        return {
          tagId: tds[0],
          limits: tds[1],
          currentValue: tds[2],
          baseAvg60: tds[3],
          m60_m10: tds[4],
          n10: tds[5],
          slope: tds[6],
          fcst30: tds[7],
          fcst20: tds[8],
          fcst10: tds[9],
          state: tds[10],
          triggerPath: tds[11],
        };
      });
    });

    const nonNormal = predRows.filter((r) => r.state && r.state !== 'NORMAL');
    timeSeriesLog.push({
      sampleIdx,
      timestamp: new Date().toISOString(),
      elapsedMin: Number(elapsedMin),
      totalPtRows: predRows.length,
      nonNormalCount: nonNormal.length,
      sampleTags: predRows.filter((r) => r.tagId && r.tagId.includes('Submain01.PTS')),
    });

    if (sampleIdx === 0 || sampleIdx === 10 || sampleIdx === 20 || Date.now() - startMs + sampleIntervalMs > totalDurationMs) {
      await page.screenshot({ path: path.join(SHOT_DIR, `deployed_11min_pred_s${String(sampleIdx).padStart(2, '0')}.png`) });
    }

    // Also snapshot Alarm Center & full 160 PT state on final sample
    if (Date.now() - startMs + sampleIntervalMs > totalDurationMs) {
      fs.writeFileSync(
        path.join(LOG_DIR, 'deployed_160pt_final_predictions.json'),
        JSON.stringify(predRows, null, 2),
      );
      const csvHeader = 'tagId,limits,currentValue,baseAvg60,m60_m10,n10,slope,fcst30,fcst20,fcst10,state,triggerPath';
      const csvLines = predRows.map((r) =>
        [r.tagId, r.limits, r.currentValue, r.baseAvg60, r.m60_m10, r.n10, r.slope, r.fcst30, r.fcst20, r.fcst10, r.state, `"${(r.triggerPath || '').replace(/"/g, '""')}"`].join(',')
      );
      fs.writeFileSync(path.join(LOG_DIR, 'deployed_160pt_final_predictions.csv'), [csvHeader, ...csvLines].join('\n'));

      await clickNav(page, '5. Alarm Center');
      await sleep(400);
      await page.screenshot({ path: path.join(SHOT_DIR, 'deployed_11min_alarms_final.png') });
      const alarmRows = await page.evaluate(() =>
        Array.from(document.querySelectorAll('tbody tr')).map((tr) => tr.innerText.replace(/\s+/g, ' ').trim())
      );
      fs.writeFileSync(path.join(LOG_DIR, 'deployed_11min_alarms.json'), JSON.stringify(alarmRows, null, 2));
      break;
    }

    sampleIdx += 1;
    await sleep(sampleIntervalMs);
  }

  // Restore baselines on deployed browser session
  await clickNav(page, '8. Modbus Simulator');
  await clickButtonByText(page, 'Sensor Simulator');
  for (let i = 1; i <= 8; i++) {
    await setSelectValue(page, 0, `PCW0${i}`);
    await clickButtonByText(page, 'Apply Suggested Baselines');
    await sleep(100);
  }

  const summary = {
    url: BASE_URL,
    executedAt: new Date().toISOString(),
    durationMinutes: Number(((Date.now() - startMs) / 60000).toFixed(2)),
    patrolResults,
    consoleErrors,
    pageErrors,
    consistencyCheck172: { alarmCenterRow: alarmCheckText, systemPredictionRow: predCheckText },
    samplesCount: timeSeriesLog.length,
  };
  fs.writeFileSync(path.join(LOG_DIR, 'deployed_11min_deviation_log.json'), JSON.stringify(timeSeriesLog, null, 2));
  fs.writeFileSync(path.join(REPORT_DIR, 'deployed_web_verification_summary.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

