import { useState, useEffect, useCallback, useMemo } from 'react';
import { toast } from 'sonner';
import { getCheckpoints, deleteCheckpoint } from '../services/checkpointServices';
import type { Checkpoint, CheckpointStatus } from '../types/checkpoint';
import { PageTable } from '../components/PageTable';
import { useReactTable, getCoreRowModel, type ColumnDef } from '@tanstack/react-table';

const STATUS_STYLES: Record<CheckpointStatus, string> = {
  ok: 'bg-green-50 text-green-700 ring-green-600/20',
  missed: 'bg-red-50 text-red-700 ring-red-600/20',
  never_seen: 'bg-slate-100 text-slate-500 ring-slate-400/20',
};

const STATUS_LABELS: Record<CheckpointStatus, string> = {
  ok: 'OK',
  missed: 'Missed',
  never_seen: 'Never seen',
};

function fmt(val: string | null) {
  if (!val) return '—';
  return new Date(val + 'Z').toISOString().replace('T', ' ').slice(0, 19);
}

const CheckpointsPage = () => {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [checkpointPendingDelete, setCheckpointPendingDelete] = useState<Checkpoint | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const fetchCheckpoints = useCallback(async (p: number) => {
    try {
      const data = await getCheckpoints(p);
      setCheckpoints(data.items);
      setPage(data.page);
      setTotalPages(data.pages);
    } catch (err) {
      toast.error('Failed to load checkpoints.');
    }
  }, []);

  useEffect(() => { fetchCheckpoints(page); }, [page, fetchCheckpoints]);

  const openDeleteModal = useCallback((cp: Checkpoint) => {
    setCheckpointPendingDelete(cp);
  }, []);

  const closeDeleteModal = useCallback(() => {
    setCheckpointPendingDelete(null);
  }, []);

  useEffect(() => {
    if (!checkpointPendingDelete) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDeleteModal();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [checkpointPendingDelete, closeDeleteModal]);

  const confirmDeleteCheckpoint = async () => {
    const cp = checkpointPendingDelete;
    if (!cp) return;
    closeDeleteModal();
    setDeletingId(cp.id);
    try {
      await deleteCheckpoint(cp.id);
      toast.success('Checkpoint deleted.');
      fetchCheckpoints(page);
    } catch (err) {
      toast.error('Failed to delete checkpoint.');
    } finally {
      setDeletingId(null);
    }
  };

  const columns = useMemo<ColumnDef<Checkpoint>[]>(() => [
    {
      header: 'Name',
      accessorKey: 'name',
      cell: ({ getValue }) => (
        <span className="font-medium text-slate-800 dark:text-slate-100">{getValue<string>()}</span>
      ),
    },
    {
      header: 'Next expected',
      accessorKey: 'next_expected_at',
      cell: ({ getValue }) => (
        <span className="font-mono text-xs text-slate-500">{fmt(getValue<string>())}</span>
      ),
    },
    {
      header: 'Timezone',
      accessorKey: 'timezone',
      cell: ({ getValue }) => (
        <span className="text-xs text-slate-500">{getValue<string>()}</span>
      ),
    },
    {
      header: 'Last seen',
      accessorKey: 'last_seen_at',
      cell: ({ getValue }) => (
        <span className="text-xs text-slate-400">{fmt(getValue<string | null>())}</span>
      ),
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: ({ getValue }) => {
        const s = getValue<CheckpointStatus>();
        return (
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[s]}`}>
            {STATUS_LABELS[s]}
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
            onClick={e => { e.stopPropagation(); openDeleteModal(row.original); }}
            disabled={deletingId === row.original.id}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-red-100 dark:border-red-900/40 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deletingId === row.original.id ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      ),
    },
  ], [deletingId, openDeleteModal]);

  const table = useReactTable({
    data: checkpoints,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="max-w-screen-2xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Checkpoints</h1>
      </div>

      <PageTable
        table={table}
        emptyMessage={
          <>No checkpoints yet. Add a <span className="font-mono">timeout</span> step to a workflow to create one.</>
        }
        page={page}
        pages={totalPages}
        onPageChange={setPage}
      />

      {checkpointPendingDelete && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          onClick={closeDeleteModal}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-checkpoint-title"
            className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-md p-6 flex flex-col gap-4 border border-slate-200 dark:border-slate-800"
            onClick={e => e.stopPropagation()}
          >
            <h2 id="delete-checkpoint-title" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Delete checkpoint?
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              This cannot be undone. Delete checkpoint{' '}
              <span className="font-medium text-slate-800 dark:text-slate-200">
                &ldquo;{checkpointPendingDelete.name}&rdquo;
              </span>
              ?
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={closeDeleteModal}
                className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDeleteCheckpoint}
                className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors"
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

export default CheckpointsPage;
