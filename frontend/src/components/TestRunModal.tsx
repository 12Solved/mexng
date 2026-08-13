import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import type { RuleGroupType } from 'react-querybuilder'
import { getAllEmails } from '../services/emailServices'
import { testRunWorkflow } from '../services/runsServices'
import type { Email } from '../types/email'
import type { WorkflowJson } from '../types/workflowEditor'
import type { RunState } from '../types/workflowRun'

interface TestRunModalProps {
  workflowJson: WorkflowJson
  workflowId?: number
  workflowName: string
  onClose: () => void
}

const STATE_BADGE: Record<RunState, string> = {
  success: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  skipped: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  re_run: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
  running: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
}

function TestRunModal({ workflowJson, workflowId, workflowName, onClose }: TestRunModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const [search, setSearch] = useState('')
  const [emails, setEmails] = useState<Email[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Email | null>(null)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{ runId: number | null; state: RunState } | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const trimmed = search.trim()
        const query: RuleGroupType | undefined = trimmed
          ? { combinator: 'or', rules: [
              { field: 'subject', operator: 'contains', value: trimmed },
              { field: 'sender', operator: 'contains', value: trimmed },
            ] }
          : undefined
        const data = await getAllEmails(1, query)
        setEmails(data.items)
      } catch {
        toast.error('Failed to load emails.')
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const handleRun = async () => {
    if (!selected) return
    setRunning(true)
    try {
      const run = await testRunWorkflow(workflowJson, selected.id, workflowId)
      setResult({ runId: run.run_id, state: run.state })
      if (run.state === 'failed') {
        toast.error('Test run failed.')
      } else {
        toast.success(`Test run finished: ${run.state}.`)
      }
    } catch {
      toast.error('Failed to start test run.')
    } finally {
      setRunning(false)
    }
  }

  const handleRunAnother = () => {
    setResult(null)
    setSelected(null)
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={e => { if (e.target === overlayRef.current) onClose() }}
    >
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-lg mx-4 flex flex-col overflow-hidden">

        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-slate-800">
          <span className="text-sm font-semibold text-gray-900 dark:text-slate-100">
            Test run &ldquo;{workflowName || 'Untitled workflow'}&rdquo;
          </span>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 text-xl leading-none bg-transparent border-none cursor-pointer p-1"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4 flex flex-col gap-3">
          {result ? (
            <div className="flex flex-col gap-3 py-4 items-center text-center">
              <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATE_BADGE[result.state]}`}>
                {result.runId != null ? `run #${result.runId} · ` : ''}{result.state}
              </span>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Ran in dry-run mode against &ldquo;{selected?.subject}&rdquo; — no attachments were saved and no other side effects were performed by steps that honor dry-run.
                {result.runId == null && ' This workflow isn’t saved yet, so no run record or trace was kept — save it first if you need one.'}
              </p>
              <div className="flex gap-2 mt-1">
                {result.runId != null && (
                  <button
                    onClick={() => { onClose(); navigate(`/logs?run_id=${result.runId}`) }}
                    className="px-3.5 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-[13px] cursor-pointer border-none transition-colors"
                  >
                    View trace in Logs
                  </button>
                )}
                <button
                  onClick={handleRunAnother}
                  className="px-3.5 py-1.5 text-[13px] text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700 rounded-md hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
                >
                  Test another email
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Pick a stored email to run the workflow currently on the canvas against, in dry-run mode — including any unsaved changes. Side effects are skipped only for steps that opt out during dry-run (currently just attachment saving).
              </p>
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search by subject or sender…"
                autoFocus
                className="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-slate-700 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 box-border transition-all"
              />

              <div className="border border-gray-100 dark:border-slate-800 rounded-lg overflow-y-auto" style={{ maxHeight: '40vh' }}>
                {loading ? (
                  <p className="text-sm text-slate-400 px-3 py-4">Loading…</p>
                ) : emails.length === 0 ? (
                  <p className="text-sm text-slate-400 px-3 py-4">No emails found.</p>
                ) : (
                  emails.map(email => (
                    <button
                      key={email.id}
                      onClick={() => setSelected(email)}
                      className={`w-full text-left px-3 py-2 border-b last:border-b-0 border-gray-50 dark:border-slate-800 transition-colors cursor-pointer ${
                        selected?.id === email.id
                          ? 'bg-blue-50 dark:bg-blue-900/20'
                          : 'bg-transparent hover:bg-gray-50 dark:hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{email.subject || '(no subject)'}</div>
                      <div className="text-xs text-gray-400 dark:text-slate-500 truncate">{email.sender} · {new Date(email.date).toLocaleString()}</div>
                    </button>
                  ))
                )}
              </div>
            </>
          )}
        </div>

        {!result && (
          <div className="px-5 py-3 border-t border-gray-100 dark:border-slate-800 flex justify-end gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-sm text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700 rounded-md hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleRun}
              disabled={!selected || running}
              className="px-4 py-1.5 text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors disabled:opacity-50"
            >
              {running ? 'Running…' : 'Run dry-run test'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default TestRunModal
