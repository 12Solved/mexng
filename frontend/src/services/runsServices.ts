import api from '../api/api.ts'
import type { RunState, WorkflowRun } from '../types/workflowRun.ts'
import type { WorkflowJson } from '../types/workflowEditor.ts'

export async function getAllWorkflowRuns(email_id: string) {
  const res = await api.get(`/emails/${email_id}/runs/`);
  return res.data;
}

export async function rerunWorkflowRun(email_id: string, run_id: number, run_options?: Record<string, unknown>) {
  const res = await api.post(`/emails/${email_id}/runs/${run_id}/rerun`, run_options ? { run_options } : undefined);
  return res.data as { run: WorkflowRun; already_queued: boolean };
}

export async function rerunAllWorkflowRuns(email_id: string, run_options?: Record<string, unknown>) {
  const res = await api.post(`/emails/${email_id}/runs/rerun-all`, run_options ? { run_options } : undefined);
  return res.data as { queued: number; already_queued: number };
}

export async function runAllWorkflows(email_id: string, run_options?: Record<string, unknown>) {
  const res = await api.post(`/emails/${email_id}/runs/run-all-workflows`, run_options ? { run_options } : undefined);
  return res.data as { queued: number; already_queued: number };
}

export async function runNewWorkflows(email_id: string, run_options?: Record<string, unknown>) {
  const res = await api.post(`/emails/${email_id}/runs/run-new-workflows`, run_options ? { run_options } : undefined);
  return res.data as { queued: number; message: string };
}

export async function testRunWorkflow(workflowJson: WorkflowJson, email_id: number, workflow_id?: number) {
  const res = await api.post(`/workflows/test-run`, { workflow_json: workflowJson, email_id, workflow_id });
  return res.data as { run_id: number | null; state: RunState };
}