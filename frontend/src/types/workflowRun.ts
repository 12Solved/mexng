export const RunState = {
  success: "success",
  failed: "failed",
  skipped: "skipped",
  re_run: "re_run",
  running: "running"
} as const;

export type RunState = typeof RunState[keyof typeof RunState];

export interface WorkflowRun {
  id: number;
  workflow_id: number;
  email_id: number;
  state: RunState;
  run_options: Record<string, unknown> | null;
  created_at: Date;
  parent_run_id: number | null;
  workflow_name: string;
}