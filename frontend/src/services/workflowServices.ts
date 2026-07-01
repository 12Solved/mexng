import api from '../api/api.ts'
import type { Workflow, WorkflowResponseBody } from '../types/workflow.ts'
import type { WorkflowJson } from '../types/workflowEditor'
import type { ContextVars, StepMeta } from '../types/workflowEditor'

export async function getWorkflows(page: number = 1, q?: string): Promise<WorkflowResponseBody> {
  const params = new URLSearchParams()
  params.set('page', String(page))
  if (q) params.set('q', q)
  const res = await api.get(`/workflows/?${params.toString()}`)
  return res.data
}

export async function getWorkflow(id: number): Promise<Workflow> {
  const res = await api.get(`/workflows/${id}`)
  return res.data
}

export async function createWorkflow(name: string, workflow_json: WorkflowJson, description?: string | null): Promise<Workflow> {
  const res = await api.post('/workflows/', { name, workflow_json, description: description || null })
  return res.data
}

export async function updateWorkflow(id: number, name: string, workflow_json: WorkflowJson, description?: string | null): Promise<Workflow> {
  const res = await api.put(`/workflows/${id}`, { name, workflow_json, description: description || null })
  return res.data
}

export async function deleteWorkflow(id: number): Promise<void> {
  await api.delete(`/workflows/${id}`)
}

export async function setWorkflowEnabled(id: number, enabled: boolean): Promise<Workflow> {
  const res = await api.patch(`/workflows/${id}/enabled`, { enabled })
  return res.data
}

export async function getSteps(): Promise<StepMeta[]> {
  const res = await api.get('/steps')
  return res.data
}

export async function getContextVars(): Promise<ContextVars> {
  const res = await api.get('/context-vars')
  return res.data
}

