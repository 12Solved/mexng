import api from '../api/api.ts'

export async function getAllLogs(
  currentPage: number,
  eventType: string,
  filters: {
    emailId?: string
    workflowId?: string
    runId?: string
    attachmentId?: string
    level?: string
    q?: string
    run_state?: string
  } = {},
) {
  const params = new URLSearchParams();
  params.set('page', String(currentPage));
  if (eventType) params.set('event_type', eventType);
  if (filters.emailId != null) params.append('email_id', String(filters.emailId));
  if (filters.workflowId != null) params.append('workflow_id', String(filters.workflowId));
  if (filters.runId != null) params.append('run_id', String(filters.runId));
  if (filters.attachmentId != null) params.append('attachment_id', String(filters.attachmentId));
  if (filters.level) params.set('level', filters.level);
  const qt = filters.q?.trim();
  if (qt) params.set('q', qt);
  if (filters.run_state) params.set('run_state', filters.run_state);
  const res = await api.get(`/logs/?${params.toString()}`);
  return res.data;
}

export async function getAllLogFilters(runId?: string) {
  const params = new URLSearchParams();
  if (runId != null) params.set('run_id', runId);
  const qs = params.toString();
  const res = await api.get(`/logs/filters${qs ? `?${qs}` : ''}`)
  return res.data;
}
