import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { streamStats } from '../services/dashboardServices.ts'
import type { Stats, StatsPeriodPreset } from '../types/stats.ts'
import {
  EnvelopeIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

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

export default function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<Stats | null>(null)
  const [period, setPeriod] = useState<StatsPeriodPreset>('last_24h')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const cleanup = streamStats(period, (data) => {
      if (cancelled) return
      setStats(data)
      setLoading(false)
    })
    return () => {
      cancelled = true
      cleanup()
    }
  }, [period])

  if (loading) {
    return (
      <div className="p-8 text-[var(--muted-foreground)] text-sm">Loading dashboard…</div>
    )
  }

  if (!stats) {
    return (
      <div className="p-8 text-red-400 text-sm">Failed to load dashboard stats.</div>
    )
  }

  const rangeSubtitle = formatPeriodRange(stats.period)
  const staleness = stats.period.preset !== period
  const emailsTitle = stats.period.preset === 'all' ? 'Total emails' : 'Emails in period'

  const runsSummaryTitle =
    stats.period.preset === 'all' ? 'All runs (totals)' : 'Runs in this period'

  return (
    <div className="max-w-screen-2xl mx-auto px-6 py-6 space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--foreground)]">
            Dashboard
            {staleness && (
              <span className="ml-2 text-xs font-normal text-amber-600 dark:text-amber-400">Updating…</span>
            )}
          </h1>
          {rangeSubtitle && (
            <>
              <p className="text-xs text-[var(--muted-foreground)] mt-1 tabular-nums">{rangeSubtitle}</p>
              <p className="text-[10px] text-[var(--muted-foreground)]/80 mt-0.5">Times are UTC.</p>
            </>
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
            <InfoRow label="Success" value={stats.runs.success} />
            <InfoRow label="Failed" value={stats.runs.failed} />
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
