import { useEffect, useRef } from 'react'
import type { Workflow, WorkflowRunStats } from '../types/workflow'

interface WorkflowInfoModalProps {
  workflow: Workflow | null;
  mode: 'view' | 'edit';
  name?: string;
  description?: string;
  onNameChange?: (v: string) => void;
  onDescriptionChange?: (v: string) => void;
  onClose: () => void;
}

const STAT_CONFIG: { key: keyof WorkflowRunStats; label: string; cls: string }[] = [
  { key: 'success', label: 'success', cls: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  { key: 'failed',  label: 'failed',  cls: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400' },
  { key: 'skipped', label: 'skipped', cls: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400' },
  { key: 're_run',  label: 're-run',  cls: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' },
]

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const WorkflowInfoModal = ({
  workflow,
  mode,
  name,
  description,
  onNameChange,
  onDescriptionChange,
  onClose,
}: WorkflowInfoModalProps) => {
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const stats = workflow?.run_stats
  const totalRuns = stats ? stats.success + stats.failed + stats.skipped + stats.re_run : 0

  const displayName = mode === 'edit' ? (name ?? '') : (workflow?.name ?? '')
  const displayDesc = mode === 'edit' ? (description ?? '') : (workflow?.description ?? '')

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={e => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-md mx-4 flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400 dark:text-slate-500">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <span className="text-sm font-semibold text-gray-900 dark:text-slate-100">Workflow info</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 text-xl leading-none bg-transparent border-none cursor-pointer p-1"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 flex flex-col gap-4 overflow-y-auto" style={{ maxHeight: '60vh' }}>

          {/* Name */}
          <div>
            <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-1.5">Name</div>
            {mode === 'edit' ? (
              <input
                value={displayName}
                onChange={e => onNameChange?.(e.target.value)}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-slate-700 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 box-border transition-all"
              />
            ) : (
              <p className="text-sm text-gray-800 dark:text-slate-200 font-medium">{displayName || '—'}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-1.5">Description</div>
            {mode === 'edit' ? (
              <textarea
                value={displayDesc}
                onChange={e => onDescriptionChange?.(e.target.value)}
                placeholder="Describe what this workflow does…"
                rows={4}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-slate-700 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 resize-none bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 placeholder-gray-300 dark:placeholder-slate-600 box-border transition-all"
              />
            ) : (
              <div className="h-28 overflow-y-auto text-sm text-gray-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed pr-1">
                {displayDesc || <span className="text-gray-300 dark:text-slate-600 italic">No description</span>}
              </div>
            )}
          </div>

          {/* Meta row */}
          <div className="flex items-center gap-6 pt-1 border-t border-gray-100 dark:border-slate-800">
            {workflow?.id && (
              <div>
                <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-0.5">ID</div>
                <span className="text-xs font-mono text-gray-500 dark:text-slate-400">#{workflow.id}</span>
              </div>
            )}
            {workflow?.created_at && (
              <div>
                <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-0.5">Created</div>
                <span className="text-xs text-gray-500 dark:text-slate-400">{formatDate(workflow.created_at)}</span>
              </div>
            )}
            {workflow && (
              <div>
                <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-0.5">Status</div>
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${workflow.enabled ? 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'}`}>
                  {workflow.enabled ? 'enabled' : 'disabled'}
                </span>
              </div>
            )}
          </div>

          {/* Run stats */}
          {stats && totalRuns > 0 && (
            <div className="pt-1 border-t border-gray-100 dark:border-slate-800">
              <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-2">Run stats</div>
              <div className="flex items-center gap-1.5 flex-wrap">
                {STAT_CONFIG.map(({ key, label, cls }) =>
                  (stats as WorkflowRunStats)[key] > 0 ? (
                    <span key={key} className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${cls}`}>
                      {(stats as WorkflowRunStats)[key]} {label}
                    </span>
                  ) : null
                )}
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-100 dark:border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700 rounded-md hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
          >
            {mode === 'edit' ? 'Done' : 'Close'}
          </button>
        </div>

      </div>
    </div>
  )
}

export default WorkflowInfoModal
