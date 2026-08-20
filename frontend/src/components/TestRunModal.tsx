import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import type { RuleGroupType } from 'react-querybuilder'
import { getAllEmails } from '../services/emailServices'
import { testRunWorkflow } from '../services/runsServices'
import { getAllLogs, getAllLogFilters } from '../services/logServices'
import { LogRow, LOG_LEVELS, LEVEL_BADGE, mergeLogsSearchQuery } from './LogRow'
import type { Email } from '../types/email'
import type { WorkflowJson } from '../types/workflowEditor'
import type { RunState } from '../types/workflowRun'
import type { Log, LogLevel } from '../types/log'

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

  const [search, setSearch] = useState('')
  const [emails, setEmails] = useState<Email[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Email | null>(null)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{ runId: number | null; state: RunState } | null>(null)
  const [logs, setLogs] = useState<Log[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsError, setLogsError] = useState(false)
  const [logsTotal, setLogsTotal] = useState<{ shown: number; total: number } | null>(null)
  const [logSearch, setLogSearch] = useState('')
  const [logLevel, setLogLevel] = useState('')
  const [logEventType, setLogEventType] = useState('')
  const [logEventTypes, setLogEventTypes] = useState<string[]>([])

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

  useEffect(() => {
    if (result?.runId == null) return
    let cancelled = false
    getAllLogFilters(String(result.runId))
      .then(data => { if (!cancelled) setLogEventTypes(data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [result?.runId])

  useEffect(() => {
    if (result?.runId == null) return
    let cancelled = false
    const timer = setTimeout(() => {
      setLogsLoading(true)
      setLogsError(false)
      getAllLogs(1, logEventType, {
        runId: String(result.runId),
        q: logSearch.trim() || undefined,
        level: logLevel || undefined,
      })
        .then(data => {
          if (cancelled) return
          setLogs(data.items)
          setLogsTotal({ shown: data.items.length, total: data.total })
        })
        .catch(() => {
          if (cancelled) return
          setLogsError(true)
        })
        .finally(() => {
          if (cancelled) return
          setLogsLoading(false)
        })
    }, 300)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [result?.runId, logSearch, logLevel, logEventType])

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
    setLogs([])
    setLogsTotal(null)
    setLogsError(false)
    setLogSearch('')
    setLogLevel('')
    setLogEventType('')
    setLogEventTypes([])
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={e => { if (e.target === overlayRef.current) onClose() }}
    >
      <div className={`bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full mx-4 flex flex-col overflow-hidden ${result ? 'max-w-2xl' : 'max-w-lg'}`}>

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
            <div className="flex flex-col gap-3 py-4">
              <div className="flex flex-col items-center text-center gap-3">
                {result.runId == null && (
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATE_BADGE[result.state]}`}>
                    {result.state}
                  </span>
                )}
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Dry run against &ldquo;{selected?.subject}&rdquo; — no attachments saved, no other side effects.
                  {result.runId == null && ' Save the workflow first to keep a trace.'}
                </p>
              </div>

              {result.runId != null && (() => {
                let openInLogsQ = `run:${result.runId}`
                if (logEventType) openInLogsQ = mergeLogsSearchQuery(openInLogsQ, `event:${logEventType}`)
                if (logSearch.trim()) openInLogsQ = mergeLogsSearchQuery(openInLogsQ, logSearch.trim())

                return (
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Trace</span>
                    <Link
                      to={`/logs?q=${encodeURIComponent(openInLogsQ)}`}
                      onClick={onClose}
                      className="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Open in Logs page
                    </Link>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      value={logSearch}
                      onChange={e => setLogSearch(e.target.value)}
                      placeholder="Search trace (event:X step:Y)…"
                      className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 dark:border-slate-700 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200"
                    />
                    <select
                      value={logEventType}
                      onChange={e => setLogEventType(e.target.value)}
                      className="px-1.5 py-1 text-xs border border-gray-200 dark:border-slate-700 rounded-md bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200"
                    >
                      <option value="">All events</option>
                      {logEventTypes.map(et => (
                        <option key={et} value={et}>{et}</option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-1">
                    {(() => {
                      const minIdx = logLevel ? LOG_LEVELS.indexOf(logLevel as LogLevel) : -1
                      return LOG_LEVELS.map(level => {
                        const idx = LOG_LEVELS.indexOf(level)
                        const isActive = minIdx === -1 || idx >= minIdx
                        const isSelected = level === logLevel
                        return (
                          <button
                            key={level}
                            type="button"
                            onClick={() => setLogLevel(level)}
                            title={`Show ${level} and above`}
                            className={`text-[10px] font-semibold font-mono px-2 py-0.5 rounded transition-colors cursor-pointer ${
                              isActive
                                ? LEVEL_BADGE[level]
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600'
                            } ring-2 ring-offset-1 ${isSelected ? 'ring-current' : 'ring-transparent'} dark:ring-offset-slate-900`}
                          >
                            {level}
                          </button>
                        )
                      })
                    })()}
                    {logLevel && (
                      <button
                        type="button"
                        onClick={() => setLogLevel('')}
                        className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 ml-0.5"
                      >
                        clear
                      </button>
                    )}
                    <span className={`ml-auto text-xs font-medium px-2.5 py-1 rounded-full ${STATE_BADGE[result.state]}`}>
                      run #{result.runId} · {result.state}
                    </span>
                  </div>

                  <div className="border border-gray-100 dark:border-slate-800 rounded-lg overflow-y-auto" style={{ maxHeight: '40vh' }}>
                    {logsLoading ? (
                      <p className="text-sm text-slate-400 px-3 py-4">Loading…</p>
                    ) : logsError ? (
                      <p className="text-sm text-slate-400 px-3 py-4">Failed to load logs.</p>
                    ) : logs.length === 0 ? (
                      <p className="text-sm text-slate-400 px-3 py-4">No log entries.</p>
                    ) : (
                      logs.map(log => <LogRow key={log.id} log={log} qContext="" />)
                    )}
                  </div>
                  {logsTotal && logsTotal.total > logsTotal.shown && (
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      Showing first {logsTotal.shown} of {logsTotal.total} — see the full trace in the Logs page above.
                    </span>
                  )}
                </div>
                )
              })()}

              <div className="flex gap-2 justify-center mt-1">
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
