import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { streamStats } from '../services/dashboardServices.ts'
import type { RecentRun, Stats, StatsPeriodPreset } from '../types/stats.ts'
import { RUN_STATE_BADGE } from '../lib/runState.ts'
import type { RunState } from '../types/workflowRun.ts'
import {
  EnvelopeIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'
import { WorkflowIcon } from '../assets/icons'

const PERIOD_TABS: { id: StatsPeriodPreset; label: string }[] = [
  { id: 'last_24h', label: 'Last 24H' },
  { id: 'last_7d', label: 'Last 7 days' },
  { id: 'last_28d', label: 'Last 28 days' },
  { id: 'all', label: 'All time' },
]
  
function formatPeriodRange(meta: Stats['period']): string {
  if (meta.preset === 'all' || !meta.starts_at || !meta.ends_at) return ''
  try {
    const opt: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' }
    const s = Date.parse(meta.starts_at)
    const e = Date.parse(meta.ends_at)
    if (Number.isNaN(s) || Number.isNaN(e)) return ''
    return `${new Date(s).toLocaleString(undefined, opt)} – ${new Date(e).toLocaleString(undefined, opt)}`
  } catch {
    return ''
  }
}

interface Snapshot {
  stats: Stats
  // Time the message arrived; "x ago" labels are computed against it.
  receivedAt: number
  // Keys of rows that are new or changed state since the previous message, so only they flash.
  // Empty on the first message and right after a filter switch: those rows are only newly listed.
  newRunKeys: Set<string>
}

// State is part of the key so a state change counts as new and replays the highlight.
const runKey = (run: RecentRun) => `${run.id}-${run.state}`

// Rows shown before "Show more"; the backend sends more than this.
const RECENT_RUNS_COLLAPSED = 5

const RUN_FILTERS: { id: RunState | null; label: string }[] = [
  { id: null, label: 'All' },
  { id: 'success', label: 'Success' },
  { id: 'failed', label: 'Failed' },
  { id: 're_run', label: 'Queued' },
  { id: 'skipped', label: 'Skipped' },
]

export default function DashboardPage() {
  const navigate = useNavigate()
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [period, setPeriod] = useState<StatsPeriodPreset>('last_24h')
  const [connectionLost, setConnectionLost] = useState(false)
  const [runsExpanded, setRunsExpanded] = useState(false)
  const [runsFilter, setRunsFilter] = useState<RunState | null>(null)

  useEffect(() => {
    let cancelled = false
    const cleanup = streamStats(
      period,
      runsFilter,
      (data) => {
        if (cancelled) return
        const receivedAt = Date.now()
        setSnapshot((prev) => {
          const sameList = prev !== null && prev.stats.recent_runs_state === data.recent_runs_state
          const prevKeys = new Set(prev?.stats.recent_runs.map(runKey))
          const newRunKeys = new Set(sameList ? data.recent_runs.map(runKey).filter((k) => !prevKeys.has(k)) : [])
          return { stats: data, receivedAt, newRunKeys }
        })
        setConnectionLost(false)
      },
      // EventSource keeps retrying on its own; the next message clears this flag.
      () => {
        if (cancelled) return
        setConnectionLost(true)
      },
    )
    return () => {
      cancelled = true
      cleanup()
    }
  }, [period, runsFilter])

  if (!snapshot) {
    return connectionLost ? (
      <div className="p-8 text-red-400 text-sm">Failed to load dashboard stats. Retrying…</div>
    ) : (
      <div className="p-8 text-[var(--muted-foreground)] text-sm">Loading dashboard…</div>
    )
  }

  const { stats, receivedAt, newRunKeys } = snapshot

  const rangeSubtitle = formatPeriodRange(stats.period)
  const staleness = stats.period.preset !== period
  const runsStaleness = stats.recent_runs_state !== runsFilter

  const renderRunRows = (runs: RecentRun[]) =>
    runs.map((run) => (
      <RecentRunRow
        key={runKey(run)}
        run={run}
        now={receivedAt}
        flash={newRunKeys.has(runKey(run))}
      />
    ))
  const emailsTitle = stats.period.preset === 'all' ? 'Total emails' : 'Emails in period'

  const runsSummaryTitle =
    stats.period.preset === 'all' ? 'All runs (totals)' : 'Runs in this period'

  return (
    <div className="max-w-screen-2xl mx-auto px-6 py-6 space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--foreground)]">
            Dashboard
            {connectionLost ? (
              <span className="ml-2 text-xs font-normal text-red-500 dark:text-red-400">Connection lost, retrying…</span>
            ) : staleness && (
              <span className="ml-2 text-xs font-normal text-amber-600 dark:text-amber-400">Updating…</span>
            )}
          </h1>
          {rangeSubtitle && (
            <p className="text-xs text-[var(--muted-foreground)] mt-1 tabular-nums">{rangeSubtitle}</p>
          )}
          {stats.period.preset === 'all' && (
            <p className="text-xs text-[var(--muted-foreground)] mt-1">Counts from the full history</p>
          )}
        </div>
        <div
          className="flex flex-wrap gap-1 p-1 rounded-lg bg-slate-200/80 dark:bg-slate-800/80 border border-slate-300/50 dark:border-slate-700/50"
          role="tablist"
          aria-label="Time range"
        >
          {PERIOD_TABS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={period === id}
              onClick={() => setPeriod(id)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                period === id
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div
        className={cn(
          'grid grid-cols-2 md:grid-cols-3 gap-4 transition-opacity',
          staleness && 'opacity-60',
        )}
      >
        <StatCard
          title={emailsTitle}
          value={stats.emails.in_period}
          icon={<EnvelopeIcon className="h-4 w-4 text-[var(--muted-foreground)]" />}
          subtitle={
            stats.period.preset !== 'all'
              ? `${stats.emails.total.toLocaleString()} all time`
              : undefined
          }
          onClick={() => navigate('/emails')}
        />
        <StatCard
          title="Successful runs"
          value={stats.runs.success}
          valueClassName="text-green-400"
          icon={<CheckCircleIcon className="h-4 w-4 text-green-400" />}
          onClick={() => navigate('/logs?run_state=success')}
        />
        <StatCard
          title="Failed runs"
          value={stats.runs.failed}
          valueClassName="text-red-400"
          icon={<XCircleIcon className="h-4 w-4 text-red-400" />}
          onClick={() => navigate('/logs?run_state=failed')}
        />
      </div>

      {/* Not period-scoped, so it only dims while a new run filter loads. */}
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-sm font-medium">Recent runs</CardTitle>
          <div className="flex flex-wrap gap-1" role="tablist" aria-label="Run state filter">
            {RUN_FILTERS.map(({ id, label }) => (
              <button
                key={label}
                type="button"
                role="tab"
                aria-selected={runsFilter === id}
                onClick={() => setRunsFilter(id)}
                className={cn(
                  'px-2 py-0.5 rounded text-[11px] font-medium transition-colors',
                  runsFilter === id
                    ? 'bg-slate-700 text-white dark:bg-slate-600'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800',
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className={cn('transition-opacity', runsStaleness && 'opacity-60')}>
          {stats.recent_runs.length === 0 ? (
            <p className="text-[var(--muted-foreground)] text-sm">
              {stats.recent_runs_state
                ? `No ${RUN_FILTERS.find((f) => f.id === stats.recent_runs_state)?.label.toLowerCase()} runs.`
                : 'No runs yet.'}
            </p>
          ) : (
            <>
              <ul className="divide-y divide-[var(--border)]">
                {renderRunRows(stats.recent_runs.slice(0, RECENT_RUNS_COLLAPSED))}
              </ul>
              {/* Overflow rows stay mounted while collapsed so the height can animate:
                  grid rows 0fr -> 1fr gives a height transition without measuring. */}
              <div
                className={cn(
                  'grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none',
                  runsExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
                )}
              >
                {/* Hidden rows shouldn't be tabbable or read out while collapsed. */}
                <div className="overflow-hidden" inert={!runsExpanded}>
                  <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
                    {renderRunRows(stats.recent_runs.slice(RECENT_RUNS_COLLAPSED))}
                  </ul>
                </div>
              </div>
              {stats.recent_runs.length > RECENT_RUNS_COLLAPSED && (
                <button
                  type="button"
                  onClick={() => setRunsExpanded((v) => !v)}
                  className="mt-2 w-full flex items-center justify-center gap-1 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  {runsExpanded ? 'Show less' : `Show more (${stats.recent_runs.length - RECENT_RUNS_COLLAPSED})`}
                  <ChevronDownIcon className={cn('h-3.5 w-3.5', runsExpanded && 'rotate-180')} />
                </button>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <div
        className={cn(
          'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 transition-opacity',
          staleness && 'opacity-60',
        )}
      >
        <Card className="cursor-pointer hover:ring-1 hover:ring-slate-400/50 transition-shadow" onClick={() => navigate('/workflow')}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              Workflows
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            <InfoRow label="Total" value={stats.workflows.total} />
            <InfoRow label="Enabled" value={stats.workflows.enabled} />
            <InfoRow label="Disabled" value={stats.workflows.total - stats.workflows.enabled} />
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:ring-1 hover:ring-slate-400/50 transition-shadow" onClick={() => navigate('/checkpoints')}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              Checkpoints
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            <InfoRow label="OK" value={stats.checkpoints.ok} />
            <InfoRow label="Missed" value={stats.checkpoints.missed} />
            <InfoRow label="Never Seen" value={stats.checkpoints.never_seen} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              {runsSummaryTitle}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {/* Success/failed already have their own cards above. Running is a live count, not limited to the period. */}
            <InfoRow label="Running now" value={stats.runs.running} />
            <InfoRow label="Skipped" value={stats.runs.skipped} />
            <InfoRow label="Re-run queued" value={stats.runs.re_run} />
          </CardContent>
        </Card>
      </div>

      <Card className={cn('transition-opacity', staleness && 'opacity-60')}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            {stats.period.preset === 'all' ? 'Recent errors' : 'Errors in this period'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stats.recent_errors.length === 0 ? (
            <p className="text-[var(--muted-foreground)] text-sm">No errors in this range.</p>
          ) : (
            <ul className="space-y-2">
              {stats.recent_errors.map((err) => (
                <ErrorRow key={err.id} err={err} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

interface StatCardProps {
  title: string
  value: number
  icon: ReactNode
  valueClassName?: string
  subtitle?: string
  onClick?: () => void
}

function StatCard({ title, value, icon, valueClassName, subtitle, onClick }: StatCardProps) {
  return (
    <Card
      className={cn('p-6', onClick && 'cursor-pointer hover:ring-1 hover:ring-slate-400/50 transition-shadow')}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <span className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wide leading-snug">{title}</span>
        <span className="shrink-0">{icon}</span>
      </div>
      <div className={cn('text-3xl font-bold tabular-nums', valueClassName ?? 'text-[var(--foreground)]')}>
        {value.toLocaleString()}
      </div>
      {subtitle ? (
        <p className="text-[11px] text-[var(--muted-foreground)] mt-2 leading-snug">{subtitle}</p>
      ) : null}
    </Card>
  )
}

function timeAgo(iso: string | null, now: number): string {
  if (!iso) return '—'
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return '—'
  const secs = Math.max(0, Math.round((now - t) / 1000))
  if (secs < 60) return `${secs}s ago`
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

interface RecentRunRowProps {
  run: RecentRun
  now: number
  flash: boolean
}

const ROW_ICON_LINK =
  'shrink-0 p-1 rounded text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-slate-200 dark:hover:bg-slate-700'

function RecentRunRow({ run, now, flash }: RecentRunRowProps) {
  return (
    <li
      className={cn(
        'flex items-center gap-3 py-2 px-2 -mx-2 rounded-md text-sm hover:bg-slate-100 dark:hover:bg-slate-800/60',
        flash && 'run-flash',
      )}
    >
      {/* A real link (not a click handler on the li) so it's keyboard-reachable; the icon links sit beside it. */}
      <Link
        to={`/logs?run_id=${run.id}`}
        className="flex-1 min-w-0 flex items-center gap-3 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
        title="View logs for this run"
      >
        <span
          className={cn(
            'shrink-0 w-16 text-center text-[11px] font-semibold px-2 py-0.5 rounded',
            RUN_STATE_BADGE[run.state],
          )}
        >
          {run.state === 're_run' ? 'queued' : run.state}
        </span>
        <span className="shrink-0 max-w-[40%] truncate font-medium text-[var(--foreground)]">{run.workflow_name}</span>
        <span className="flex-1 min-w-0 truncate text-[var(--muted-foreground)]">
          {run.email_subject ?? (run.email_id == null ? 'email deleted' : '(no subject)')}
        </span>
        <span
          className="shrink-0 text-xs tabular-nums text-[var(--muted-foreground)]"
          title={run.created_at ? `Created ${new Date(run.created_at).toLocaleString()}` : undefined}
        >
          {timeAgo(run.created_at, now)}
        </span>
      </Link>
      <span className="shrink-0 flex items-center">
        {run.email_id != null ? (
          <Link to={`/email/${run.email_id}`} className={ROW_ICON_LINK} title="Open email" aria-label="Open email">
            <EnvelopeIcon className="h-4 w-4" />
          </Link>
        ) : (
          // Keeps the workflow icon aligned across rows when the email was deleted.
          <span className="w-6" />
        )}
        <Link to={`/workflow/${run.workflow_id}`} className={ROW_ICON_LINK} title="Open workflow" aria-label="Open workflow">
          <WorkflowIcon size={16} />
        </Link>
      </span>
    </li>
  )
}

function InfoRow({ label, value }: { label: string; value: ReactNode | number }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-[var(--muted-foreground)]">{label}</span>
      <span className="font-semibold tabular-nums text-[var(--foreground)]">{value}</span>
    </div>
  )
}

function ErrorRow({ err }: { err: Stats['recent_errors'][number] }) {
  return (
    <li className="flex items-start gap-3 rounded-lg bg-slate-100 dark:bg-slate-800/60 p-3 text-sm border border-slate-300 dark:border-slate-700/50">
      <div className="flex-1 min-w-0">
        <p className="text-[var(--foreground)] truncate">{err.message ?? '—'}</p>
        <p className="text-[var(--muted-foreground)] text-xs mt-1">
          {err.step && <span className="font-mono mr-2">{err.step}</span>}
          {err.event_type && <span className="font-mono mr-2 text-red-400">{err.event_type}</span>}
          {err.created_at && new Date(err.created_at).toLocaleString()}
        </p>
      </div>
    </li>
  )
}
