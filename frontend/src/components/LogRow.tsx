import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Log, LogLevel } from '../types/log'
import { LinkIcon } from '../assets/icons'

export function mergeLogsSearchQuery(existing: string | null | undefined, tag: string): string {
  const t = tag.trim()
  const base = (existing ?? '').trim()
  if (!t) return base
  return base ? `${base} ${t}` : t
}

function logsPathWithQ(nextQ: string): string {
  const p = new URLSearchParams()
  const qt = nextQ.trim()
  if (qt) p.set('q', qt)
  const s = p.toString()
  return s ? `/logs?${s}` : '/logs'
}

export const LOG_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

export const LEVEL_BORDER: Record<LogLevel, string> = {
  DEBUG:    'border-l-slate-400',
  INFO:     'border-l-blue-400',
  WARNING:  'border-l-amber-400',
  ERROR:    'border-l-red-400',
  CRITICAL: 'border-l-red-600',
};

export const LEVEL_BADGE: Record<LogLevel, string> = {
  DEBUG:    'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300',
  INFO:     'bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400',
  WARNING:  'bg-amber-50 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400',
  ERROR:    'bg-red-50 dark:bg-red-900/40 text-red-600 dark:text-red-400',
  CRITICAL: 'bg-red-500 text-white',
};

export const LEVEL_ROW_BG: Partial<Record<LogLevel, string>> = {
  CRITICAL: 'bg-red-50/50 dark:bg-red-900/10',
};

export function fmt(val: string) {
  return new Date(val).toISOString().replace('T', ' ').slice(0, 23);
}

const CHIP_STATIC =
  'text-xs font-mono px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300';
const CHIP_LINK =
  `${CHIP_STATIC} hover:bg-blue-100 dark:hover:bg-blue-900/40 hover:text-blue-800 dark:hover:text-blue-200 ` +
  'cursor-pointer underline-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ' +
  'focus-visible:ring-offset-1 dark:focus-visible:ring-offset-slate-900';

const CHIP_SPLIT_WRAPPER =
  'inline-flex items-center rounded overflow-hidden bg-slate-200 dark:bg-slate-700';
const CHIP_SPLIT_LEFT =
  'text-xs font-mono px-2 py-0.5 text-slate-600 dark:text-slate-300 ' +
  'hover:bg-blue-100 dark:hover:bg-blue-900/40 hover:text-blue-800 dark:hover:text-blue-200 ' +
  'cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-inset';
const CHIP_SPLIT_ICON =
  'px-1 py-0.5 flex items-center text-slate-400 dark:text-slate-500 ' +
  'hover:bg-blue-100 dark:hover:bg-blue-900/40 hover:text-blue-600 dark:hover:text-blue-300 ' +
  'border-l border-slate-300 dark:border-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-inset';

export function LogIdChip({ label, val, qContext }: { label: string; val: number; qContext: string }) {
  const text = `${label}:#${val}`;
  if (label === 'email') {
    return (
      <span className={CHIP_SPLIT_WRAPPER}>
        <Link
          to={logsPathWithQ(mergeLogsSearchQuery(qContext, `email:${val}`))}
          className={CHIP_SPLIT_LEFT}
          title="Add email filter to search"
        >
          {text}
        </Link>
        <Link to={`/email/${val}`} className={CHIP_SPLIT_ICON} title="Open email">
          <LinkIcon />
        </Link>
      </span>
    );
  }
  if (label === 'workflow') {
    return (
      <span className={CHIP_SPLIT_WRAPPER}>
        <Link
          to={logsPathWithQ(mergeLogsSearchQuery(qContext, `workflow:${val}`))}
          className={CHIP_SPLIT_LEFT}
          title="Add workflow filter to search"
        >
          {text}
        </Link>
        <Link to={`/workflow/${val}`} className={CHIP_SPLIT_ICON} title="Open workflow editor">
          <LinkIcon />
        </Link>
      </span>
    );
  }
  if (label === 'run') {
    return (
      <Link
        to={logsPathWithQ(mergeLogsSearchQuery(qContext, `run:${val}`))}
        className={CHIP_LINK}
        title="Add run filter to search"
      >
        {text}
      </Link>
    );
  }
  if (label === 'attachment') {
    return (
      <Link
        to={logsPathWithQ(mergeLogsSearchQuery(qContext, `attachment:${val}`))}
        className={CHIP_LINK}
        title="Add attachment filter to search"
      >
        {text}
      </Link>
    );
  }
  return <span className={CHIP_STATIC}>{text}</span>;
}

export function LogRow({ log, qContext }: { log: Log; qContext: string }) {
  const [expanded, setExpanded] = useState(false);
  const hasLongMessage = (log.message?.length ?? 0) > 80;
  const displayMessage = expanded || !hasLongMessage
    ? (log.message ?? null)
    : log.message!.slice(0, 80) + '…';

  const ids = [
    log.email_id != null    && { label: 'email',    val: log.email_id },
    log.run_id != null      && { label: 'run',      val: log.run_id },
    log.workflow_id != null && { label: 'workflow', val: log.workflow_id },
    log.attachment_id != null && { label: 'attachment', val: log.attachment_id },
  ].filter(Boolean) as { label: string; val: number }[];

  return (
    <div
      className={`border-l-4 ${LEVEL_BORDER[log.level]} ${LEVEL_ROW_BG[log.level] ?? ''} px-4 py-2.5 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors`}
    >
      <div className="flex items-start gap-3 min-w-0">
        <span className={`inline-block shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded font-mono tracking-wide ${LEVEL_BADGE[log.level]}`}>
          {log.level}
        </span>
        <span className="shrink-0 text-[11px] font-mono text-slate-400 dark:text-slate-500 pt-px whitespace-nowrap">
          {fmt(log.created_at)}
        </span>
        <span className="shrink-0 text-xs font-mono font-medium text-slate-600 dark:text-slate-300 pt-px">
          {log.event_type}
        </span>
        {displayMessage && (
          <span className="text-xs text-slate-500 dark:text-slate-400 pt-px min-w-0 break-words">
            {displayMessage}
            {hasLongMessage && (
              <button
                type="button"
                onClick={() => setExpanded(e => !e)}
                className="ml-1.5 text-[10px] text-blue-400 hover:text-blue-600 dark:hover:text-blue-300 font-medium"
              >
                {expanded ? 'less' : 'more'}
              </button>
            )}
          </span>
        )}
      </div>

      {(ids.length > 0 || log.step) && (
        <div className="flex items-center gap-1.5 mt-1.5 ml-[calc(theme(spacing.3)+theme(spacing.4)+3rem)]">
          {log.step && (
            <span className={CHIP_STATIC}>step:{log.step}</span>
          )}
          {ids.map(({ label, val }) => (
            <LogIdChip key={`${label}-${val}`} label={label} val={val} qContext={qContext} />
          ))}
        </div>
      )}
    </div>
  );
}
