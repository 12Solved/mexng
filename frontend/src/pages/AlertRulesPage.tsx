import { useState, useEffect, useCallback, useMemo } from 'react';
import { toast } from 'sonner';
import { getAlertRules, updateAlertRule, deleteAlertRule } from '../services/alertRuleServices';
import { getWorkflows } from '../services/workflowServices';
import { getCheckpoints } from '../services/checkpointServices';
import { getAllLogFilters } from '../services/logServices';
import type { AlertRule } from '../types/alertRule';
import type { Checkpoint } from '../types/checkpoint';
import type { LogLevel } from '../types/log';
import { PageTable } from '../components/PageTable';
import { LEVEL_BADGE } from '../components/LogRow';
import AlertRuleModal, { type CheckpointOption, type WorkflowOption } from '../components/AlertRuleModal';
import { useReactTable, getCoreRowModel, type ColumnDef } from '@tanstack/react-table';
import { useUser } from '../context/UserContext';

// check_logs never alerts on its own events, so don't suggest them.
const SELF_EVENT_PREFIX = 'CHECK_LOGS_';

// Rules only store IDs, and both lists are paginated, so walk every page.
async function loadAll<T>(fetchPage: (p: number) => Promise<{ items: T[]; pages: number }>): Promise<T[]> {
  const items: T[] = [];
  let page = 1;
  let pages = 1;
  do {
    const data = await fetchPage(page);
    items.push(...data.items);
    pages = data.pages;
    page++;
  } while (page <= pages);
  return items;
}

function toNameMap(items: { id: number; name: string }[]): Map<number, string> {
  return new Map(items.map(item => [item.id, item.name]));
}

function AnyLabel() {
  return <span className="text-xs text-slate-400">Any</span>;
}

const AlertRulesPage = () => {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [checkpoints, setCheckpoints] = useState<CheckpointOption[]>([]);
  const [eventTypes, setEventTypes] = useState<string[]>([]);
  // undefined = modal closed, null = creating, AlertRule = editing
  const [ruleInModal, setRuleInModal] = useState<AlertRule | null | undefined>(undefined);
  const [rulePendingDelete, setRulePendingDelete] = useState<AlertRule | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const fetchRules = useCallback(async (p: number) => {
    try {
      const data = await getAlertRules(p);
      setRules(data.items);
      setPage(data.page);
      setTotalPages(data.pages);
    } catch {
      toast.error('Failed to load alert rules.');
    }
  }, []);

  useEffect(() => { fetchRules(page); }, [page, fetchRules]);

  const { user, loading: userLoading } = useUser();
  useEffect(() => {
    if (userLoading || !user || user.email) return;
    toast.warning('No email is configured for your user, so alert rules will not send anything.', { id: 'no-alert-email' });
  }, [user, userLoading]);

  useEffect(() => {
    loadAll(getWorkflows)
      .then(items => setWorkflows(items.map(({ id, name }) => ({ id, name }))))
      .catch(() => toast.error('Failed to load workflows.'));
    loadAll<Checkpoint>(getCheckpoints)
      .then(items => setCheckpoints(items.map(({ id, name, workflow_id }) => ({ id, name, workflow_id }))))
      .catch(() => toast.error('Failed to load checkpoints.'));
    getAllLogFilters()
      .then((types: string[]) => setEventTypes(types.filter(t => !t.startsWith(SELF_EVENT_PREFIX)).sort()))
      .catch(() => toast.error('Failed to load event types.'));
  }, []);

  const workflowNames = useMemo(() => toNameMap(workflows), [workflows]);
  const checkpointNames = useMemo(() => toNameMap(checkpoints), [checkpoints]);

  const closeRuleModal = useCallback(() => setRuleInModal(undefined), []);

  const handleRuleSaved = () => {
    toast.success(ruleInModal ? 'Alert rule updated.' : 'Alert rule created.');
    closeRuleModal();
    fetchRules(page);
  };

  const handleToggleEnabled = useCallback(async (rule: AlertRule) => {
    setTogglingId(rule.id);
    try {
      await updateAlertRule(rule.id, { enabled: !rule.enabled });
      toast.success(`Alert rule ${rule.enabled ? 'disabled' : 'enabled'}.`);
      fetchRules(page);
    } catch {
      toast.error('Failed to update alert rule.');
    } finally {
      setTogglingId(null);
    }
  }, [fetchRules, page]);

  const openDeleteModal = useCallback((rule: AlertRule) => {
    setRulePendingDelete(rule);
  }, []);

  const closeDeleteModal = useCallback(() => {
    setRulePendingDelete(null);
  }, []);

  useEffect(() => {
    if (!rulePendingDelete) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDeleteModal();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [rulePendingDelete, closeDeleteModal]);

  const confirmDeleteRule = async () => {
    const rule = rulePendingDelete;
    if (!rule) return;
    closeDeleteModal();
    setDeletingId(rule.id);
    try {
      await deleteAlertRule(rule.id);
      toast.success('Alert rule deleted.');
      fetchRules(page);
    } catch {
      toast.error('Failed to delete alert rule.');
    } finally {
      setDeletingId(null);
    }
  };

  const columns = useMemo<ColumnDef<AlertRule>[]>(() => [
    {
      header: 'Event type',
      accessorKey: 'event_type',
      cell: ({ getValue }) => {
        const v = getValue<string | null>();
        return v
          ? <span className="font-mono text-xs text-slate-800 dark:text-slate-100">{v}</span>
          : <AnyLabel />;
      },
    },
    {
      header: 'Workflow',
      accessorKey: 'workflow_id',
      cell: ({ getValue }) => {
        const id = getValue<number | null>();
        if (id === null) return <AnyLabel />;
        return <span className="text-sm text-slate-700 dark:text-slate-200">{workflowNames.get(id) ?? `#${id}`}</span>;
      },
    },
    {
      header: 'Checkpoint',
      accessorKey: 'checkpoint_id',
      cell: ({ getValue }) => {
        const id = getValue<number | null>();
        if (id === null) return <AnyLabel />;
        return <span className="text-sm text-slate-700 dark:text-slate-200">{checkpointNames.get(id) ?? `#${id}`}</span>;
      },
    },
    {
      header: 'Min level',
      accessorKey: 'min_level',
      cell: ({ getValue }) => {
        const level = getValue<LogLevel>();
        return (
          <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded font-mono tracking-wide ${LEVEL_BADGE[level]}`}>
            {level}
          </span>
        );
      },
    },
    {
      header: 'Status',
      accessorKey: 'enabled',
      cell: ({ getValue }) => {
        const enabled = getValue<boolean>();
        return (
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${enabled ? 'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'}`}>
            {enabled ? 'enabled' : 'disabled'}
          </span>
        );
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={e => { e.stopPropagation(); setRuleInModal(row.original); }}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={e => { e.stopPropagation(); handleToggleEnabled(row.original); }}
            disabled={togglingId === row.original.id}
            className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
              row.original.enabled
                ? 'border-amber-200 text-amber-600 hover:bg-amber-50 dark:border-amber-800 dark:text-amber-400 dark:hover:bg-amber-900/20'
                : 'border-green-200 text-green-600 hover:bg-green-50 dark:border-green-800 dark:text-green-400 dark:hover:bg-green-900/20'
            }`}
          >
            {togglingId === row.original.id ? '…' : row.original.enabled ? 'Disable' : 'Enable'}
          </button>
          <button
            type="button"
            onClick={e => { e.stopPropagation(); openDeleteModal(row.original); }}
            disabled={deletingId === row.original.id}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-red-100 dark:border-red-900/40 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deletingId === row.original.id ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      ),
    },
  ], [workflowNames, checkpointNames, deletingId, togglingId, handleToggleEnabled, openDeleteModal]);

  const table = useReactTable({
    data: rules,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="max-w-screen-2xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Alerts</h1>
        <button
          type="button"
          onClick={() => setRuleInModal(null)}
          className="px-3.5 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-[13px] cursor-pointer border-none transition-colors"
        >
          + New Rule
        </button>
      </div>

      <PageTable
        table={table}
        emptyMessage="No alert rules yet."
        page={page}
        pages={totalPages}
        onPageChange={setPage}
      />

      {ruleInModal !== undefined && (
        <AlertRuleModal
          // Remount per rule so the form starts from that rule's values.
          key={ruleInModal?.id ?? 'new'}
          rule={ruleInModal}
          workflows={workflows}
          checkpoints={checkpoints}
          eventTypes={eventTypes}
          onClose={closeRuleModal}
          onSaved={handleRuleSaved}
        />
      )}

      {rulePendingDelete && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          onClick={closeDeleteModal}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-alert-rule-title"
            className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-md p-6 flex flex-col gap-4 border border-slate-200 dark:border-slate-800"
            onClick={e => e.stopPropagation()}
          >
            <h2 id="delete-alert-rule-title" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Delete alert rule?
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              This cannot be undone. Alerts this rule has already queued will still be sent in the next digest.
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={closeDeleteModal}
                className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDeleteRule}
                className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors cursor-pointer"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AlertRulesPage;
