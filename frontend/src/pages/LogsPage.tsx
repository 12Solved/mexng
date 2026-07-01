import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner';
import type { Log, LogLevel } from '../types/log';
import { getAllLogFilters, getAllLogs } from '../services/logServices';
import Pagination from '../components/Pagination';
import { Link, useSearchParams } from 'react-router-dom';

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

const LEVEL_BORDER: Record<LogLevel, string> = {
  DEBUG:    'border-l-slate-400',
  INFO:     'border-l-blue-400',
  WARNING:  'border-l-amber-400',
  ERROR:    'border-l-red-400',
  CRITICAL: 'border-l-red-600',
};

const LEVEL_BADGE: Record<LogLevel, string> = {
  DEBUG:    'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300',
  INFO:     'bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400',
  WARNING:  'bg-amber-50 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400',
  ERROR:    'bg-red-50 dark:bg-red-900/40 text-red-600 dark:text-red-400',
  CRITICAL: 'bg-red-500 text-white',
};

const LEVEL_ROW_BG: Partial<Record<LogLevel, string>> = {
  CRITICAL: 'bg-red-50/50 dark:bg-red-900/10',
};

function fmt(val: string) {
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

function LinkIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 2H2a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1V7" />
      <path d="M8 1h3v3" />
      <path d="M11 1L6 6" />
    </svg>
  );
}

function LogIdChip({ label, val, qContext }: { label: string; val: number; qContext: string }) {
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

function LogRow({ log, qContext }: { log: Log; qContext: string }) {
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

const LOG_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

const SEARCH_DEBOUNCE_MS = 380

const LogsPage = () => {
  const [logs, setLogs] = useState<Log[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [logFilters, setLogFilters] = useState<string[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('');
  const [selectedLevel, setSelectedLevel] = useState<string>('INFO');
  const [searchParams, setSearchParams] = useSearchParams();
  const committedQ = searchParams.get('q')?.trim() ?? '';
  const runState = searchParams.get('run_state') ?? undefined;

  const [draftQ, setDraftQ] = useState(committedQ);
  const skipNextDraftSync = useRef(false);

  useEffect(() => {
    const email = searchParams.get('email_id');
    const wf = searchParams.get('workflow_id');
    const run = searchParams.get('run_id');
    const att = searchParams.get('attachment_id');
    const legacyTags: string[] = [];
    if (email != null && email !== '') legacyTags.push(`email:${email}`);
    if (wf != null && wf !== '') legacyTags.push(`workflow:${wf}`);
    if (run != null && run !== '') legacyTags.push(`run:${run}`);
    if (att != null && att !== '') legacyTags.push(`attachment:${att}`);
    if (legacyTags.length === 0) return;

    skipNextDraftSync.current = true;
    let merged = searchParams.get('q')?.trim() ?? '';
    for (const tag of legacyTags) {
      merged = mergeLogsSearchQuery(merged || undefined, tag);
    }

    const next = new URLSearchParams(searchParams);
    next.delete('email_id');
    next.delete('workflow_id');
    next.delete('run_id');
    next.delete('attachment_id');
    if (merged.trim() === '') next.delete('q');
    else next.set('q', merged.trim());

    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (skipNextDraftSync.current) {
      skipNextDraftSync.current = false;
      setDraftQ(searchParams.get('q')?.trim() ?? '');
      return;
    }
    setDraftQ(committedQ);
  }, [committedQ, searchParams]);

  useEffect(() => {
    if (draftQ.trim() === committedQ) return;
    const t = window.setTimeout(() => {
      setSearchParams((prev) => {
        const n = new URLSearchParams(prev);
        const d = draftQ.trim();
        if (d === '') n.delete('q');
        else n.set('q', d);
        return n;
      }, { replace: true });
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(t);
  }, [draftQ, committedQ, setSearchParams]);

  useEffect(() => {
    setCurrentPage(1)
  }, [committedQ, selectedFilter, selectedLevel, runState]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await getAllLogs(currentPage, selectedFilter, {
          level: selectedLevel || undefined,
          q: committedQ || undefined,
          run_state: runState,
        });
        setLogs(data.items);
        setCurrentPage(data.page);
        setTotalPages(data.pages);
        if (data.pages < data.page) setCurrentPage(1);
      } catch (error) {
        toast.error('Failed to load logs.');
      }
    };
    fetchLogs();
  }, [currentPage, selectedFilter, selectedLevel, committedQ, runState]);

  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const data = await getAllLogFilters();
        setLogFilters(data);
      } catch (error) {
        toast.error('Failed to load log filters.');
      }
    };
    fetchFilters();
  }, []);

  return (
    <div className="mx-auto px-6 py-6">
      {runState && (
        <div className="mb-4 flex items-center gap-3 px-4 py-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg text-sm text-blue-800 dark:text-blue-300">
          <span>Showing logs for <strong>{runState}</strong> runs</span>
          <button
            onClick={() => setSearchParams(p => { const n = new URLSearchParams(p); n.delete('run_state'); return n; })}
            className="ml-auto text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 underline"
          >
            Clear filter
          </button>
        </div>
      )}
      <div className="mb-4 flex flex-col gap-2">
        <label className="text-xs font-medium text-slate-500 dark:text-slate-400" htmlFor="logs-search-q">
          Search logs
        </label>
        <div className="flex flex-col sm:flex-row gap-2 sm:items-start">
          <input
            id="logs-search-q"
            type="text"
            value={draftQ}
            onChange={e => setDraftQ(e.target.value)}
            placeholder='e.g. workflow:4 attachment_saved or event:FILE step:SaveAttachment'
            spellCheck={false}
            autoComplete="off"
            className="flex-1 min-w-0 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2 flex-wrap">
        <select
          className="border border-slate-200 dark:border-slate-700 rounded-md px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
          onChange={e => { setSelectedFilter(e.target.value); setCurrentPage(1); }}
          value={selectedFilter}
        >
          <option value="">All event types</option>
          {logFilters.map(event_type => (
            <option key={event_type} value={event_type}>{event_type}</option>
          ))}
        </select>

        <div className="flex items-center gap-1">
          {(() => {
            const minIdx = selectedLevel ? LOG_LEVELS.indexOf(selectedLevel as LogLevel) : -1;
            return LOG_LEVELS.map((level, idx) => {
              const isActive = minIdx === -1 || idx >= minIdx;
              const isSelected = level === selectedLevel;
              return (
                <button
                  key={level}
                  type="button"
                  onClick={() => { setSelectedLevel(level); setCurrentPage(1); }}
                  title={`Show ${level} and above`}
                  className={`text-[11px] font-semibold font-mono px-2.5 py-1 rounded transition-colors cursor-pointer ${
                    isActive
                      ? LEVEL_BADGE[level]
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600'
                  } ring-2 ring-offset-1 ${isSelected ? 'ring-current' : 'ring-transparent'} dark:ring-offset-slate-900`}
                >
                  {level}
                </button>
              );
            });
          })()}
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl overflow-hidden">
        {logs.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-slate-400 dark:text-slate-600">
            No logs found.
          </div>
        ) : (
          logs.map(log => <LogRow key={log.id} log={log} qContext={committedQ || draftQ} />)
        )}
        <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800">
          <Pagination page={currentPage} pages={totalPages} onPageChange={setCurrentPage} />
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
