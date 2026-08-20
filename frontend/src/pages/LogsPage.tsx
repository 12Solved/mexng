import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner';
import type { Log, LogLevel } from '../types/log';
import { getAllLogFilters, getAllLogs } from '../services/logServices';
import Pagination from '../components/Pagination';
import { useSearchParams } from 'react-router-dom';
import { LogRow, mergeLogsSearchQuery, LEVEL_BADGE, LOG_LEVELS } from '../components/LogRow';

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
