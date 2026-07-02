import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { getWorkflows, deleteWorkflow, setWorkflowEnabled } from '../services/workflowServices'
import { PageTable } from '../components/PageTable'
import type { Workflow, WorkflowRunStats } from '../types/workflow'
import { useReactTable, getCoreRowModel, type ColumnDef } from '@tanstack/react-table'
import WorkflowInfoModal from '../components/WorkflowInfoModal'
import { InfoIcon } from '../assets/icons'

const STAT_CONFIG = [
  { key: 'success' as const, label: 'success', cls: 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/40 hover:cursor-pointer' },
  { key: 'failed'  as const, label: 'failed',  cls: 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 hover:cursor-pointer' },
  { key: 'skipped' as const, label: 'skipped', cls: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 hover:cursor-pointer' },
  { key: 're_run'  as const, label: 're-run',  cls: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 hover:cursor-pointer' },
]

function RunStatsBadges({ wf, onStatClick }: { wf: Workflow; onStatClick: (wfId: number, wfName: string, state: string) => void }) {
  const stats = wf.run_stats
  if (!stats) return <span className="text-slate-300 text-xs">—</span>
  const total = stats.success + stats.failed + stats.skipped + stats.re_run
  if (total === 0) return <span className="text-slate-300 text-xs">no runs</span>
  return (
    <span className="flex items-center gap-1 flex-wrap">
      {STAT_CONFIG.map(({ key, label, cls }) =>
        (stats as WorkflowRunStats)[key] > 0 ? (
          <button
            key={key}
            onClick={e => { e.stopPropagation(); onStatClick(wf.id, wf.name, key) }}
            className={`text-[11px] font-medium px-2 py-0.5 rounded-full transition-colors ${cls}`}
          >
            {(stats as WorkflowRunStats)[key]} {label}
          </button>
        ) : null
      )}
    </span>
  )
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [hasWorkflows, setHasWorkflows] = useState(false)
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [togglingId, setTogglingId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [activeSearch, setActiveSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [workflowPendingDelete, setWorkflowPendingDelete] = useState<Workflow | null>(null)
  const [viewingWorkflow, setViewingWorkflow] = useState<Workflow | null>(null)
  const navigate = useNavigate()
  const isFirstRender = useRef(true)

  const openDeleteModal = useCallback((wf: Workflow) => {
    setWorkflowPendingDelete(wf)
  }, [])

  const closeDeleteModal = useCallback(() => {
    setWorkflowPendingDelete(null)
  }, [])

  useEffect(() => {
    if (!workflowPendingDelete) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDeleteModal()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [workflowPendingDelete, closeDeleteModal])

  const fetchWorkflows = async (p: number, name: string) => {
    setLoading(true)
    try {
      const data = await getWorkflows(p, name || undefined)
      setWorkflows(data.items)
      setPage(data.page)
      setTotalPages(data.pages)
      if (!name && data.total > 0) setHasWorkflows(true)
    } catch (e) {
      toast.error('Failed to load workflows.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      fetchWorkflows(1, '')
      return
    }
    const timer = setTimeout(() => {
      setActiveSearch(search)
      setPage(1)
      fetchWorkflows(1, search)
    }, 400)
    return () => clearTimeout(timer)
  }, [search])

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    fetchWorkflows(newPage, search)
  }

  const handleStatClick = (wfId: number, wfName: string, state: string) => {
    navigate(`/emails?workflow_id=${wfId}&run_state=${state}&workflow_name=${encodeURIComponent(wfName)}`)
  }

  const handleToggleEnabled = async (wf: Workflow) => {
    setTogglingId(wf.id)
    try {
      await setWorkflowEnabled(wf.id, !wf.enabled)
      toast.success(`Workflow "${wf.name}" ${wf.enabled ? 'disabled' : 'enabled'}.`)
      fetchWorkflows(page, search)
    } catch (e) {
      toast.error('Failed to update workflow.')
    } finally {
      setTogglingId(null)
    }
  }

  const confirmDeleteWorkflow = async () => {
    const wf = workflowPendingDelete
    if (!wf) return
    closeDeleteModal()
    setDeletingId(wf.id)
    try {
      await deleteWorkflow(wf.id)
      toast.success(`Workflow "${wf.name}" deleted.`)
      fetchWorkflows(page, search)
    } catch (e) {
      toast.error('Failed to delete workflow.')
    } finally {
      setDeletingId(null)
    }
  }

  const columns = useMemo<ColumnDef<Workflow>[]>(() => [
    {
      header: 'ID',
      accessorKey: 'id',
      cell: ({ getValue }) => (
        <span className="text-xs text-slate-400 font-mono">#{getValue<number>()}</span>
      ),
    },
    {
      header: 'Name',
      accessorKey: 'name',
      cell: ({ getValue }) => (
        <span className="font-medium text-slate-800 dark:text-slate-100">{getValue<string>()}</span>
      ),
    },
    {
      header: 'Status',
      accessorKey: 'enabled',
      cell: ({ getValue }) => {
        const enabled = getValue<boolean>()
        return (
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${enabled ? 'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'}`}>
            {enabled ? 'enabled' : 'disabled'}
          </span>
        )
      },
    },
    {
      header: 'Runs',
      accessorKey: 'run_stats',
      cell: ({ row }) => (
        <RunStatsBadges wf={row.original} onStatClick={handleStatClick} />
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={e => { e.stopPropagation(); setViewingWorkflow(row.original) }}
            title="Workflow info"
            className="flex items-center justify-center w-7 h-7 rounded-md text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors border-none bg-transparent cursor-pointer"
          >
            <InfoIcon size={14} />
          </button>
          <button
            onClick={e => { e.stopPropagation(); navigate(`/workflow/${row.original.id}`) }}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            Edit
          </button>
          <button
            onClick={e => { e.stopPropagation(); handleToggleEnabled(row.original) }}
            disabled={togglingId === row.original.id}
            className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors disabled:opacity-50 ${
              row.original.enabled
                ? 'border-amber-200 text-amber-600 hover:bg-amber-50 dark:border-amber-800 dark:text-amber-400 dark:hover:bg-amber-900/20'
                : 'border-green-200 text-green-600 hover:bg-green-50 dark:border-green-800 dark:text-green-400 dark:hover:bg-green-900/20'
            }`}
          >
            {togglingId === row.original.id ? '…' : row.original.enabled ? 'Disable' : 'Enable'}
          </button>
          <button
            onClick={e => { e.stopPropagation(); openDeleteModal(row.original) }}
            disabled={deletingId === row.original.id}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-red-100 text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            {deletingId === row.original.id ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      ),
    },
  ], [deletingId, togglingId, handleStatClick, handleToggleEnabled, openDeleteModal, navigate])

  const table = useReactTable({
    data: workflows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div>

      <div className="bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-white px-4 py-2.5 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
        <span className="font-bold text-[15px]">Workflows</span>
        <button
          onClick={() => navigate('/workflow/new')}
          className="px-3.5 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-[13px] cursor-pointer border-none transition-colors"
        >
          + New Workflow
        </button>
      </div>

      <div className="w-full px-6 py-6">

        {(hasWorkflows || search) && (
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search workflows…"
            className="w-64 mb-4 px-3 py-1.5 text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
          />
        )}

        {loading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : workflows.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 text-center py-12">
            <p className="text-slate-400 text-sm">
              {activeSearch ? 'No workflows match your search.' : 'No workflows yet.'}
            </p>
            {!activeSearch && (
              <button
                onClick={() => navigate('/workflow/new')}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-md transition-colors"
              >
                Create your first workflow
              </button>
            )}
          </div>
        ) : (
          <PageTable
            table={table}
            page={page}
            pages={totalPages}
            onPageChange={handlePageChange}
          />
        )}
      </div>

      {workflowPendingDelete && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          onClick={closeDeleteModal}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-workflow-title"
            className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-md p-6 flex flex-col gap-4 border border-slate-200 dark:border-slate-800"
            onClick={e => e.stopPropagation()}
          >
            <h2 id="delete-workflow-title" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Delete workflow?
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              This cannot be undone. Delete workflow{' '}
              <span className="font-medium text-slate-800 dark:text-slate-200">
                &ldquo;{workflowPendingDelete.name}&rdquo;
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
                onClick={confirmDeleteWorkflow}
                className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {viewingWorkflow && (
        <WorkflowInfoModal
          workflow={viewingWorkflow}
          mode="view"
          onClose={() => setViewingWorkflow(null)}
        />
      )}
    </div>
  )
}
