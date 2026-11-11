import { create } from 'zustand';
import { pcwDataService } from '../services/PcwDataService';
import { API_CONFIG } from '../api/config';
import type { PcwSystem, PcwSubmain } from '../domain/pcwTypes';
import type { SensorTag } from '../domain/sensorTypes';
import type { AlarmEvent } from '../domain/alarmTypes';
import type { PredictionResult } from '../domain/predictionTypes';
import type { ModbusRegisterValue, SimulatorConfig, ModbusRegisterDefinition, FaultScenario } from '../domain/modbusTypes';

export interface PairSummary {
  systemId: string;
  submainId: string;
  supplyTag: string;
  returnTag: string;
  supplyPressure: number;
  returnPressure: number;
  pairDeltaP: number;
  supplyState: string;
  returnState: string;
  pairState: string;
  couplingMode: string;
  pairRiskScore: number;
}

export interface SqliteStats {
  totalRows: number;
  uniqueTags: number;
  nonNormalRows: number;
}

interface ScadaState {
  systems: PcwSystem[];
  submains: PcwSubmain[];
  pairs: PairSummary[];
  sensors: SensorTag[];
  alarms: AlarmEvent[];
  predictions: PredictionResult[];
  predictionConfig: any;
  modbus: Record<number, ModbusRegisterValue>;
  modbusMap: ModbusRegisterDefinition[];
  simulatorConfigs: Record<string, SimulatorConfig>;
  simulatorStatus: any;
  modbusWriteLog: string[];
  sqliteStats: SqliteStats;
  historyData: any[];
  lastFetch: string;
  connectionMode: 'WS_LIVE' | 'REST_POLL' | 'LOCAL_MOCK';
  isFetching: boolean;
  selectedGlobalTag: string | null;

  openTagDetail: (tagId: string) => void;
  closeTagDetail: () => void;
  applySnapshot: (snap: any, mode?: 'WS_LIVE' | 'REST_POLL') => void;
  fetchAllData: () => Promise<void>;
  fetchSensorHistory: (tags: string[], start: string, end: string) => Promise<void>;
  startPolling: (intervalMs?: number) => void;
  stopPolling: () => void;
  acknowledgeAlarm: (alarmId: string, user: string) => Promise<void>;
  acknowledgeAllAlarms: (user: string) => Promise<void>;
  shelveAlarm: (alarmId: string) => Promise<void>;
  setSimulatorControl: (action: 'START' | 'PAUSE' | 'RESET', interval?: number) => Promise<void>;
  updateSimulatorConfig: (tagIds: string[], updates: Partial<SimulatorConfig>) => Promise<void>;
  injectFault: (tagIds: string[], scenario: FaultScenario, params?: Partial<SimulatorConfig>) => Promise<void>;
  applySuggestedBaselines: (systemId: string) => Promise<void>;
  updateSensorLimits: (tagIds: string[], limits: Partial<any>) => Promise<void>;
  updatePredictionConfig: (type: 'global' | 'system' | 'submain' | 'sensor', id: string, enabled: boolean) => Promise<void>;
  updatePredictionSensitivity: (val: number) => Promise<void>;
  updateSensorSensitivity: (tagId: string, val: number | null) => Promise<void>;
  tunePrediction: (payload: { sensitivity?: number; slopeGatePct?: number; releaseHold?: number; rawOnset?: number }) => Promise<void>;
}

let pollingTimer: ReturnType<typeof setInterval> | null = null;
let sseSource: EventSource | null = null;
let sseReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let shouldStream = false;

function computeLocalPairs(sensors: SensorTag[], predictions: PredictionResult[]): PairSummary[] {
  const predMap = new Map(predictions.map((p) => [p.tagId, p]));
  const sensorMap = new Map(sensors.map((s) => [s.tagId, s]));
  const sev: Record<string, number> = { DISABLED: -2, INSUFFICIENT_DATA: -1, NORMAL: 0, 'T-30': 1, 'T-20': 2, 'T-10': 3, EVENT: 4 };
  const out: PairSummary[] = [];
  for (let i = 1; i <= 8; i++) {
    const sys = `PCW0${i}`;
    for (let j = 1; j <= 10; j++) {
      const sub = `Submain${String(j).padStart(2, '0')}`;
      const ptsTag = `${sys}.${sub}.PTS`;
      const ptrTag = `${sys}.${sub}.PTR`;
      const pts = predMap.get(ptsTag);
      const ptr = predMap.get(ptrTag);
      const ss = sensorMap.get(ptsTag);
      const sr = sensorMap.get(ptrTag);
      if (!ss || !sr) continue;
      const stS = pts?.state ?? 'NORMAL';
      const stR = ptr?.state ?? 'NORMAL';
      const wS = (sev[stS] ?? 0) >= 1;
      const wR = (sev[stR] ?? 0) >= 1;
      const pairState = (sev[stS] ?? 0) >= (sev[stR] ?? 0) ? stS : stR;
      const couplingMode = wS && wR ? 'COUPLED_DRIFT' : wS ? 'SUPPLY_ONLY' : wR ? 'RETURN_ONLY' : 'NORMAL';
      out.push({
        systemId: sys,
        submainId: sub,
        supplyTag: ptsTag,
        returnTag: ptrTag,
        supplyPressure: ss.value,
        returnPressure: sr.value,
        pairDeltaP: ss.value - sr.value,
        supplyState: stS,
        returnState: stR,
        pairState,
        couplingMode,
        pairRiskScore: Math.max(pts?.riskScore ?? 0, ptr?.riskScore ?? 0),
      });
    }
  }
  return out;
}

export const useScadaStore = create<ScadaState>((set, get) => ({
  systems: [],
  submains: [],
  pairs: [],
  sensors: [],
  alarms: [],
  predictions: [],
  predictionConfig: { global: true, systems: {}, submains: {}, sensors: {}, sensitivity: 2, slopeGatePct: 5, releaseHold: 3, rawOnset: 1 },
  modbus: {},
  modbusMap: [],
  simulatorConfigs: {},
  simulatorStatus: { isRunning: false, iteration: 0, updateIntervalMs: 1000 },
  modbusWriteLog: [],
  sqliteStats: { totalRows: 0, uniqueTags: 0, nonNormalRows: 0 },
  historyData: [],
  lastFetch: '',
  connectionMode: API_CONFIG.USE_MOCK ? 'LOCAL_MOCK' : 'REST_POLL',
  isFetching: false,
  selectedGlobalTag: null,

  openTagDetail: (tagId: string) => set({ selectedGlobalTag: tagId }),
  closeTagDetail: () => set({ selectedGlobalTag: null }),

  applySnapshot: (snap: any, mode: 'WS_LIVE' | 'REST_POLL' = 'REST_POLL') => {
    set({
      systems: snap.systems ?? [],
      submains: snap.submains ?? [],
      pairs: snap.pairs ?? [],
      sensors: snap.sensors ?? [],
      alarms: snap.alarms ?? [],
      predictions: snap.predictions ?? [],
      modbus: snap.modbus ?? {},
      modbusMap: snap.modbusMap ?? [],
      simulatorConfigs: snap.simulatorConfigs ?? {},
      simulatorStatus: snap.simulatorStatus ?? { isRunning: false, iteration: 0, updateIntervalMs: 1000 },
      modbusWriteLog: snap.modbusWriteLog ?? [],
      predictionConfig: snap.predictionConfig ?? {},
      sqliteStats: snap.sqliteStats ?? get().sqliteStats,
      lastFetch: new Date().toISOString(),
      connectionMode: mode,
      isFetching: false,
    });
  },

  fetchAllData: async () => {
    set({ isFetching: true });
    try {
      const snap = await pcwDataService.getSnapshot();
      if (snap) {
        get().applySnapshot(snap, sseSource && sseSource.readyState === EventSource.OPEN ? 'WS_LIVE' : 'REST_POLL');
        return;
      }
      const [systems, submains, sensors, alarms, predictions, modbus, modbusMap, simulatorConfigs, simulatorStatus, modbusWriteLog, predictionConfig] = await Promise.all([
        pcwDataService.getAllSystems(),
        pcwDataService.getAllSubmains(),
        pcwDataService.getLatestSensorValues(),
        pcwDataService.getActiveAlarms(),
        pcwDataService.getPredictionResults(),
        pcwDataService.getModbusRegisters(),
        pcwDataService.getModbusMap(),
        pcwDataService.getSimulatorConfigs(),
        pcwDataService.getSimulatorStatus(),
        pcwDataService.getModbusWriteLog(),
        pcwDataService.getPredictionConfig(),
      ]);
      set({
        systems,
        submains,
        pairs: computeLocalPairs(sensors, predictions),
        sensors,
        alarms,
        predictions,
        modbus,
        modbusMap,
        simulatorConfigs,
        simulatorStatus,
        modbusWriteLog,
        predictionConfig,
        connectionMode: 'LOCAL_MOCK',
        lastFetch: new Date().toISOString(),
        isFetching: false,
      });
    } catch (error) {
      console.error('Failed to fetch SCADA data', error);
      set({ isFetching: false });
    }
  },

  fetchSensorHistory: async (tags: string[], start: string, end: string) => {
    try {
      const records = await pcwDataService.getSensorHistory(tags, start, end);
      const pivot: Record<string, any> = {};
      records.forEach((r) => {
        const iso = new Date(r.timestamp).toISOString();
        if (!pivot[iso]) pivot[iso] = { isoTime: iso, timestamp: new Date(r.timestamp).toLocaleTimeString() };
        pivot[iso][r.tagId] = r.value;
      });
      const chartData = Object.values(pivot).sort((a, b) => a.isoTime.localeCompare(b.isoTime));
      set({ historyData: chartData });
    } catch (e) {
      console.error('Failed to fetch history', e);
      set({ historyData: [] });
    }
  },

  startPolling: (intervalMs = 1000) => {
    const { fetchAllData, applySnapshot, stopPolling } = get();
    stopPolling();
    shouldStream = true;
    fetchAllData();

    if (API_CONFIG.USE_MOCK) {
      pollingTimer = setInterval(fetchAllData, intervalMs);
      return;
    }

    const connectSse = () => {
      if (!shouldStream || typeof EventSource === 'undefined') return;
      try {
        const es = new EventSource(`${API_CONFIG.REST_URL}/stream`);
        sseSource = es;
        es.onopen = () => {
          set({ connectionMode: 'WS_LIVE' });
          if (pollingTimer) {
            clearInterval(pollingTimer);
            pollingTimer = null;
          }
        };
        es.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            if (msg && msg.type === 'SNAPSHOT_PUSH') {
              applySnapshot(msg, 'WS_LIVE');
            }
          } catch {
            // ignore malformed frame
          }
        };
        es.onerror = () => {
          es.close();
          sseSource = null;
          set({ connectionMode: 'REST_POLL' });
          if (shouldStream) {
            if (!pollingTimer) pollingTimer = setInterval(fetchAllData, Math.max(1500, intervalMs));
            sseReconnectTimer = setTimeout(connectSse, 3000);
          }
        };
      } catch {
        if (!pollingTimer) pollingTimer = setInterval(fetchAllData, Math.max(1500, intervalMs));
      }
    };
    connectSse();
  },

  stopPolling: () => {
    shouldStream = false;
    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
    if (sseReconnectTimer) {
      clearTimeout(sseReconnectTimer);
      sseReconnectTimer = null;
    }
    if (sseSource) {
      sseSource.close();
      sseSource = null;
    }
  },

  acknowledgeAlarm: async (alarmId: string, user: string) => {
    await pcwDataService.acknowledgeAlarm(alarmId, user);
    await get().fetchAllData();
  },

  acknowledgeAllAlarms: async (user: string) => {
    await pcwDataService.acknowledgeAllAlarms(user);
    await get().fetchAllData();
  },

  shelveAlarm: async (alarmId: string) => {
    await pcwDataService.shelveAlarm(alarmId);
    await get().fetchAllData();
  },

  setSimulatorControl: async (action, interval) => {
    await pcwDataService.setSimulatorControl(action, interval);
    await get().fetchAllData();
  },

  updateSimulatorConfig: async (tagIds, updates) => {
    await pcwDataService.updateSimulatorConfig(tagIds, updates);
    await get().fetchAllData();
  },

  injectFault: async (tagIds, scenario, params) => {
    await pcwDataService.injectFault(tagIds, scenario, params);
    await get().fetchAllData();
  },

  applySuggestedBaselines: async (systemId) => {
    await pcwDataService.applySuggestedBaselines(systemId);
    await get().fetchAllData();
  },

  updateSensorLimits: async (tagIds, limits) => {
    await pcwDataService.updateSensorLimits(tagIds, limits);
    await get().fetchAllData();
  },

  updatePredictionConfig: async (type, id, enabled) => {
    await pcwDataService.updatePredictionConfig(type, id, enabled);
    await get().fetchAllData();
  },

  updatePredictionSensitivity: async (val: number) => {
    await pcwDataService.updatePredictionSensitivity(val);
    await get().fetchAllData();
  },

  updateSensorSensitivity: async (tagId: string, val: number | null) => {
    await pcwDataService.updateSensorSensitivity(tagId, val);
    await get().fetchAllData();
  },

  tunePrediction: async (payload) => {
    await pcwDataService.tunePrediction(payload);
    await get().fetchAllData();
  },
}));
