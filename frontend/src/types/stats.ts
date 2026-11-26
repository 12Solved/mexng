import type { RunState } from './workflowRun.ts'

export interface RunStats {
  success: number
  failed: number
  running: number
  skipped: number
  re_run: number
}

export type StatsPeriodPreset = 'last_24h' | 'last_7d' | 'last_28d' | 'all'

export interface StatsPeriodMeta {
  preset: StatsPeriodPreset
  starts_at: string | null
  ends_at: string | null
}

export interface RecentError {
  id: number
  message: string | null
  step: string | null
  event_type: string
  created_at: string | null
  email_id: number | null
  workflow_id: number | null
  run_id: number | null
}

export interface RecentRun {
  id: number
  state: RunState
  workflow_id: number
  workflow_name: string
  email_id: number | null
  email_subject: string | null
  created_at: string | null
}

export interface Stats {
  period: StatsPeriodMeta
  emails: { total: number; in_period: number }
  runs: RunStats
  workflows: { total: number; enabled: number }
  checkpoints: { ok: number; missed: number; never_seen: number }
  recent_errors: RecentError[]
  // The run state filter recent_runs was built with; null means all states.
  recent_runs_state: RunState | null
  recent_runs: RecentRun[]
}
