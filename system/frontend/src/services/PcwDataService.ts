import { db } from '../repositories/MockDatabase';
import type { AuditEntry } from '../repositories/MockDatabase';
import { SimulatorEngine } from './SimulatorEngine';
import { API_CONFIG } from '../api/config';
import type { PcwSystem, PcwSubmain } from '../domain/pcwTypes';
import type { SensorTag, EngineeringLimits } from '../domain/sensorTypes';
import type { AlarmEvent } from '../domain/alarmTypes';
import type { HistorianRecord } from '../domain/historianTypes';
import type { PredictionResult, PredictionConfig } from '../domain/predictionTypes';
import type { SimulatorConfig, ModbusRegisterValue, ModbusRegisterDefinition, FaultScenario } from '../domain/modbusTypes';

export interface AlarmFilter {
  tagId?: string;
  startTime?: string;
  endTime?: string;
}

export function validateLimits(l: EngineeringLimits): string | null {
  const vals = [l.lowLow, l.low, l.high, l.highHigh];
  if (vals.some((v) => !Number.isFinite(v))) return 'All limits must be finite numbers';
  if (!(l.lowLow <= l.low)) return 'LL must be ≤ L';
  if (!(l.low < l.high)) return 'L must be < H';
  if (!(l.high <= l.highHigh)) return 'H must be ≤ HH';
  return null;
}

async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_CONFIG.REST_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export class PcwDataService {
  async getSnapshot(): Promise<any | null> {
    if (API_CONFIG.USE_MOCK) return null;
    return apiJson<any>('/snapshot');
  }

  async getAllSystems(): Promise<PcwSystem[]> {
    if (!API_CONFIG.USE_MOCK) return apiJson<PcwSystem[]>('/systems');
    return db.systems;
  }

  async getAllSubmains(systemId?: string): Promise<PcwSubmain[]> {
    if (!API_CONFIG.USE_MOCK) {
      const snap = await this.getSnapshot();
      const all = (snap?.submains ?? []) as PcwSubmain[];
      return systemId ? all.filter((sm) => sm.systemId === systemId) : all;
    }
    return systemId ? db.submains.filter((sm) => sm.systemId === systemId) : db.submains;
  }

  async getLatestSensorValues(tagIds?: string[]): Promise<SensorTag[]> {
    if (!API_CONFIG.USE_MOCK) {
      const all = await apiJson<SensorTag[]>('/sensors');
      return tagIds?.length ? all.filter((t) => tagIds.includes(t.tagId)) : all;
    }
    const result = tagIds?.length ? db.sensors.filter((t) => tagIds.includes(t.tagId)) : db.sensors;
    return result.map((s) => ({ ...s }));
  }

  async getSensorHistory(tagIds: string[], startTime: string, endTime: string): Promise<HistorianRecord[]> {
    if (!API_CONFIG.USE_MOCK) {
      const q = new URLSearchParams({ tags: tagIds.join(','), start: startTime, end: endTime });
      return apiJson<HistorianRecord[]>(`/historian?${q.toString()}`);
    }
    return db.historian.query(tagIds, startTime, endTime, 2000);
  }

  async getActiveAlarms(filters?: AlarmFilter): Promise<AlarmEvent[]> {
    if (!API_CONFIG.USE_MOCK) {
      const all = await apiJson<AlarmEvent[]>('/alarms?activeOnly=true');
      return filters?.tagId ? all.filter((a) => a.tagId === filters.tagId) : all;
    }
    let active = db.alarms.filter((a) => a.state.startsWith('ACTIVE') || a.state === 'CLEARED_UNACK' || a.state === 'SHELVED');
    if (filters?.tagId) active = active.filter((a) => a.tagId === filters.tagId);
    return active.map((a) => ({ ...a }));
  }

  async getAlarmHistory(filters?: AlarmFilter): Promise<AlarmEvent[]> {
    if (!API_CONFIG.USE_MOCK) {
      let history = await apiJson<AlarmEvent[]>('/alarms?activeOnly=false');
      if (filters?.startTime) history = history.filter((a) => new Date(a.activatedAt) >= new Date(filters.startTime!));
      if (filters?.endTime) history = history.filter((a) => new Date(a.activatedAt) <= new Date(filters.endTime!));
      if (filters?.tagId) history = history.filter((a) => a.tagId === filters.tagId);
      return history.sort((a, b) => b.activatedAt.localeCompare(a.activatedAt));
    }
    let history = [...db.alarms];
    if (filters?.startTime) history = history.filter((a) => new Date(a.activatedAt) >= new Date(filters.startTime!));
    if (filters?.endTime) history = history.filter((a) => new Date(a.activatedAt) <= new Date(filters.endTime!));
    if (filters?.tagId) history = history.filter((a) => a.tagId === filters.tagId);
    return history.sort((a, b) => b.activatedAt.localeCompare(a.activatedAt));
  }

  async acknowledgeAlarm(alarmId: string, user: string): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson(`/alarms/${encodeURIComponent(alarmId)}/ack?user=${encodeURIComponent(user)}`, { method: 'POST' });
      return;
    }
    const a = db.alarms.find((x) => x.alarmId === alarmId);
    if (a) {
      a.acknowledgedAt = new Date().toISOString();
      a.acknowledgedBy = user;
      if (a.state === 'ACTIVE_UNACK') a.state = 'ACTIVE_ACK';
      else if (a.state === 'CLEARED_UNACK') a.state = 'CLEARED_ACK';
      db.audit(user, 'ALARM_ACK', a.tagId, `${a.alarmType} ${a.alarmId}`);
      db.persist();
    }
  }

  async acknowledgeAllAlarms(user: string): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson(`/alarms/ack-all?user=${encodeURIComponent(user)}`, { method: 'POST' });
      return;
    }
    const now = new Date().toISOString();
    let n = 0;
    db.alarms.forEach((a) => {
      if (a.state === 'ACTIVE_UNACK' || a.state === 'CLEARED_UNACK') {
        a.acknowledgedAt = now;
        a.acknowledgedBy = user;
        if (a.state === 'ACTIVE_UNACK') a.state = 'ACTIVE_ACK';
        else if (a.state === 'CLEARED_UNACK') a.state = 'CLEARED_ACK';
        n++;
      }
    });
    if (n) {
      db.audit(user, 'ALARM_ACK_ALL', `${n} alarms`);
      db.persist();
    }
  }

  async shelveAlarm(alarmId: string, user = 'HMI_OPERATOR'): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson(`/alarms/${encodeURIComponent(alarmId)}/shelve?user=${encodeURIComponent(user)}`, { method: 'POST' });
      return;
    }
    const a = db.alarms.find((x) => x.alarmId === alarmId);
    if (a && a.state.startsWith('ACTIVE')) {
      a.state = 'SHELVED';
      if (!a.acknowledgedAt) {
        a.acknowledgedAt = new Date().toISOString();
        a.acknowledgedBy = user;
      }
      db.audit(user, 'ALARM_SHELVE', a.tagId, `${a.alarmType} ${a.alarmId}`);
      db.persist();
    }
  }

  async getAuditLog(): Promise<AuditEntry[]> {
    return [...db.auditLog].reverse();
  }

  async getPredictionResults(filters?: { tagId?: string }): Promise<PredictionResult[]> {
    if (!API_CONFIG.USE_MOCK) {
      const q = filters?.tagId ? `?tagId=${encodeURIComponent(filters.tagId)}` : '';
      return apiJson<PredictionResult[]>(`/predictions${q}`);
    }
    let res = [...db.predictions];
    if (filters?.tagId) res = res.filter((p) => p.tagId === filters.tagId);
    return res;
  }

  async getPredictionLogs(params?: { tagId?: string; state?: string; limit?: number }): Promise<any> {
    if (!API_CONFIG.USE_MOCK) {
      const q = new URLSearchParams();
      if (params?.tagId) q.set('tagId', params.tagId);
      if (params?.state) q.set('state', params.state);
      q.set('limit', String(params?.limit ?? 500));
      return apiJson<any>(`/predictions/logs?${q.toString()}`);
    }
    const rows = db.predictions.filter((p) => (!params?.tagId || p.tagId === params.tagId) && (!params?.state || p.state === params.state));
    return {
      summary: { total_rows: db.predictions.length, distinct_tags: db.predictions.length, non_normal_rows: db.predictions.filter((p) => p.state !== 'NORMAL').length },
      rows: rows.slice(0, params?.limit ?? 500),
    };
  }

  async tunePrediction(payload: {
    sensitivity?: number;
    slopeGatePct?: number;
    releaseHold?: number;
    rawOnset?: number;
    tagId?: string;
    sensorSensitivity?: number | null;
  }): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/prediction/tuning', { method: 'POST', body: JSON.stringify(payload) });
      return;
    }
    if (payload.sensitivity && payload.sensitivity > 0) db.predictionConfig.sensitivity = payload.sensitivity;
    if (payload.slopeGatePct !== undefined && payload.slopeGatePct >= 0) db.predictionConfig.slopeGatePct = payload.slopeGatePct;
    if (payload.releaseHold !== undefined && payload.releaseHold >= 0) db.predictionConfig.releaseHold = payload.releaseHold;
    if (payload.tagId) {
      if (!db.predictionConfig.sensorSensitivity) db.predictionConfig.sensorSensitivity = {};
      if (payload.sensorSensitivity === null) delete db.predictionConfig.sensorSensitivity[payload.tagId];
      else if (payload.sensorSensitivity && payload.sensorSensitivity > 0) db.predictionConfig.sensorSensitivity[payload.tagId] = payload.sensorSensitivity;
    }
    db.persistConfig();
    SimulatorEngine.evaluatePredictions(new Date().toISOString());
    db.persist();
  }

  async getPredictionConfig(): Promise<PredictionConfig> {
    if (!API_CONFIG.USE_MOCK) {
      const snap = await this.getSnapshot();
      return snap.predictionConfig;
    }
    return { ...db.predictionConfig };
  }

  async updatePredictionConfig(type: 'global' | 'system' | 'submain' | 'sensor', id: string, enabled: boolean): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/prediction/toggle', { method: 'POST', body: JSON.stringify({ type, id, enabled }) });
      return;
    }
    if (type === 'global') db.predictionConfig.global = enabled;
    else if (type === 'system') db.predictionConfig.systems[id] = enabled;
    else if (type === 'submain') db.predictionConfig.submains[id] = enabled;
    else if (type === 'sensor') db.predictionConfig.sensors[id] = enabled;
    db.persistConfig();
    SimulatorEngine.evaluatePredictions(new Date().toISOString());
    db.persist();
    db.audit('ENGINEER', 'PRED_ENABLE', `${type}:${id}`, String(enabled));
  }

  async updatePredictionSensitivity(val: number): Promise<void> {
    if (!Number.isFinite(val) || val <= 0) return;
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/prediction/tuning', { method: 'POST', body: JSON.stringify({ sensitivity: val }) });
      return;
    }
    db.predictionConfig.sensitivity = val;
    db.persistConfig();
    SimulatorEngine.evaluatePredictions(new Date().toISOString());
    db.persist();
    db.audit('ENGINEER', 'PRED_THETA', 'GLOBAL', String(val));
  }

  async updateSensorSensitivity(tagId: string, val: number | null): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/prediction/tuning', { method: 'POST', body: JSON.stringify({ tagId, sensorSensitivity: val }) });
      return;
    }
    if (!db.predictionConfig.sensorSensitivity) db.predictionConfig.sensorSensitivity = {};
    if (val === null) delete db.predictionConfig.sensorSensitivity[tagId];
    else if (Number.isFinite(val) && val > 0) db.predictionConfig.sensorSensitivity[tagId] = val;
    db.persistConfig();
    SimulatorEngine.evaluatePredictions(new Date().toISOString());
    db.persist();
    db.audit('ENGINEER', 'PRED_THETA', tagId, String(val));
  }

  async getSimulatorStatus(): Promise<{ isRunning: boolean; iteration: number; updateIntervalMs: number }> {
    if (!API_CONFIG.USE_MOCK) {
      const snap = await this.getSnapshot();
      return snap.simulatorStatus;
    }
    return { ...db.simulatorStatus };
  }

  async setSimulatorControl(action: 'START' | 'PAUSE' | 'RESET', interval?: number): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/simulator/control', { method: 'POST', body: JSON.stringify({ action, intervalMs: interval }) });
      return;
    }
    SimulatorEngine.setControl(action, interval);
  }

  async getSimulatorConfigs(): Promise<Record<string, SimulatorConfig>> {
    if (!API_CONFIG.USE_MOCK) {
      const snap = await this.getSnapshot();
      return snap.simulatorConfigs;
    }
    return { ...db.simulatorConfigs };
  }

  async updateSimulatorConfig(tagIds: string[], updates: Partial<SimulatorConfig>): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/simulator/config', {
        method: 'POST',
        body: JSON.stringify({ tagIds, baseValue: updates.baseValue, noise: updates.noise }),
      });
      return;
    }
    const nowIso = new Date().toISOString();
    tagIds.forEach((tag) => {
      if (db.simulatorConfigs[tag]) {
        db.simulatorConfigs[tag] = { ...db.simulatorConfigs[tag], ...updates };
        const s = db.sensors.find((x) => x.tagId === tag);
        if (s && updates.baseValue !== undefined) {
          s.value = updates.baseValue;
          s.timestamp = nowIso;
        }
      }
    });
    db.persistConfig();
    SimulatorEngine.evaluatePredictions(nowIso);
    db.persist();
  }

  async injectFault(tagIds: string[], scenario: FaultScenario, params: Partial<SimulatorConfig> = {}): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/simulator/fault', {
        method: 'POST',
        body: JSON.stringify({
          tagIds,
          scenario,
          driftRatePerMin: params.driftRatePerMin ?? 0,
          stepOffset: params.stepOffset ?? 0,
          spikeAmplitude: params.spikeAmplitude ?? 0,
          spikeProbability: params.spikeProbability ?? 0.05,
        }),
      });
      return;
    }
    SimulatorEngine.injectFault(tagIds, scenario, params);
  }

  async applySuggestedBaselines(systemId: string): Promise<void> {
    if (!API_CONFIG.USE_MOCK) {
      await apiJson(`/simulator/apply-baselines/${encodeURIComponent(systemId)}`, { method: 'POST' });
      return;
    }
    const targetTags = db.sensors.filter((s) => s.systemId === systemId);
    for (const t of targetTags) {
      const suggested = t.engineeringLimits.baseline ?? (t.engineeringLimits.high + t.engineeringLimits.low) / 2;
      await this.updateSimulatorConfig([t.tagId], {
        baseValue: suggested,
        noise: (t.engineeringLimits.high - t.engineeringLimits.low) * 0.02,
      });
    }
  }

  async updateSensorLimits(tagIds: string[], limits: Partial<EngineeringLimits>): Promise<string | null> {
    for (const tag of tagIds) {
      const sensor = db.sensors.find((s) => s.tagId === tag);
      if (!sensor) continue;
      const err = validateLimits({ ...sensor.engineeringLimits, ...limits });
      if (err) return `${tag}: ${err}`;
    }
    if (!API_CONFIG.USE_MOCK) {
      await apiJson('/limits', { method: 'POST', body: JSON.stringify({ tagIds, limits }) });
      return null;
    }
    tagIds.forEach((tag) => {
      const sensor = db.sensors.find((s) => s.tagId === tag);
      if (sensor) sensor.engineeringLimits = { ...sensor.engineeringLimits, ...limits };
    });
    db.persistConfig();
    SimulatorEngine.evaluatePredictions(new Date().toISOString());
    db.persist();
    db.audit('ENGINEER', 'LIMIT_CHANGE', tagIds.length === 1 ? tagIds[0] : `${tagIds.length} tags`, JSON.stringify(limits));
    return null;
  }

  async getModbusRegisters(): Promise<Record<number, ModbusRegisterValue>> {
    if (!API_CONFIG.USE_MOCK) {
      const snap = await this.getSnapshot();
      return snap.modbus;
    }
    return { ...db.modbusRegisters };
  }

  async getModbusMap(): Promise<ModbusRegisterDefinition[]> {
    if (!API_CONFIG.USE_MOCK) {
      const snap = await this.getSnapshot();
      return snap.modbusMap;
    }
    return db.modbusMap;
  }

  async getModbusWriteLog(): Promise<string[]> {
    if (!API_CONFIG.USE_MOCK) {
      const snap = await this.getSnapshot();
      return snap.modbusWriteLog;
    }
    return db.modbusWriteLog;
  }
}

export const pcwDataService = new PcwDataService();
