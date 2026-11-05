import api from '../api/api.ts';
import type { AlertRule, AlertRuleBody, AlertRuleResponseBody } from '../types/alertRule.ts';

export async function getAlertRules(page = 1): Promise<AlertRuleResponseBody> {
  const res = await api.get(`/alert-rules/?page=${page}`);
  return res.data;
}

export async function createAlertRule(body: AlertRuleBody): Promise<AlertRule> {
  const res = await api.post('/alert-rules/', body);
  return res.data;
}

export async function updateAlertRule(id: number, body: AlertRuleBody): Promise<AlertRule> {
  const res = await api.patch(`/alert-rules/${id}`, body);
  return res.data;
}

export async function deleteAlertRule(id: number) {
  const res = await api.delete(`/alert-rules/${id}`);
  return res.data;
}
