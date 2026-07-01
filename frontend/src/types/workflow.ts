import type { WorkflowJson } from '../types/workflowEditor'

export interface WorkflowRunStats {
  success: number
  failed: number
  skipped: number
  re_run: number
}

export interface Workflow {
  id: number
  name: string
  description?: string | null
  workflow_json: WorkflowJson
  enabled: boolean
  created_at?: string | null
  run_stats?: WorkflowRunStats | null
}


export interface WorkflowResponseBody {
  items: Workflow[];
  total: number;
  page: number;
  size: number;
  pages: number;
}