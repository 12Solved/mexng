import type { RunState } from '../types/workflowRun.ts'

export const RUN_STATE_BADGE: Record<RunState, string> = {
  success: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  skipped: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  re_run: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
  running: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
}
