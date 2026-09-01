import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner';
import { getAllEmails } from '../services/emailServices';
import type { EmailResponseBody, Email } from '../types/email';
import { EmailActionsMenu } from '../components/EmailActionsMenu';
import { PageTable } from '../components/PageTable';
import { QueryBuilder, defaultOperators, type RuleGroupType } from 'react-querybuilder';
import 'react-querybuilder/dist/query-builder.css';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  useReactTable,
  getCoreRowModel,
  type ColumnDef,
} from '@tanstack/react-table';

const stringOperators = [
  ...defaultOperators.filter(op =>
    ['contains', 'doesNotContain', 'beginsWith', 'endsWith', '=', '!='].includes(op.name)
  ),
  { name: 'matches', label: 'matches' },
];
const dateOperators = defaultOperators.filter(op =>
  ['=', '<', '>', '<=', '>='].includes(op.name)
);
const fields = [
  { name: 'subject',   label: 'Subject',   operators: stringOperators },
  { name: 'sender',    label: 'Sender',    operators: stringOperators },
  { name: 'recipient', label: 'Recipient', operators: stringOperators },
  { name: 'body',      label: 'Body',      operators: stringOperators },
  { name: 'date',      label: 'Date',      inputType: 'date', operators: dateOperators },
];

const QB_CONTROL =
  'border border-slate-200 dark:border-slate-600 rounded-md px-2 py-1.5 text-sm ' +
  'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 ' +
  'focus:outline-none focus:ring-2 focus:ring-blue-400 dark:focus:ring-blue-500';

function RunSummaryCell({ summary }: { summary?: { success: number; failed: number; skipped: number, re_run: number } | null }) {
  if (!summary) return <span className="text-slate-400 dark:text-slate-600">—</span>;
  return (
    <span className="flex items-center gap-2 text-xs font-mono">
      <span className="inline-flex items-center gap-0.5 text-green-600 leading-none">
        <span aria-hidden="true">✓</span>
        <span>{summary.success}</span>
      </span>
      <span className="inline-flex items-center gap-0.5 text-red-500 leading-none">
        <span aria-hidden="true">✗</span>
        <span>{summary.failed}</span>
      </span>
      <span className="inline-flex items-center gap-0.5 text-gray-400 leading-none">
        <span aria-hidden="true">-</span>
        <span>{summary.skipped}</span>
      </span>
      <span className="inline-flex items-center gap-0.5 text-blue-500 leading-none">
        <span aria-hidden="true">↺</span>
        <span>{summary.re_run}</span>
      </span>
    </span>
  );
}

const STATE_LABELS: Record<string, string> = {
  success: 'successful',
  failed: 'failed',
  skipped: 'skipped',
  re_run: 're-run',
}

const EmailsPage = () => {
  const initialQuery: RuleGroupType = { combinator: 'and', rules: [] };
  const [query, setQuery] = useState<RuleGroupType>(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState<RuleGroupType>(initialQuery);
  const [emails, setEmails] = useState<Email[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const workflowId = searchParams.get('workflow_id') ? Number(searchParams.get('workflow_id')) : undefined;
  const runState = searchParams.get('run_state') ?? undefined;
  const workflowName = searchParams.get('workflow_name') ?? undefined;

  const fetchEmails = useCallback(async (page: number, q: RuleGroupType, silent = false) => {
    try {
      const data: EmailResponseBody = await getAllEmails(page, q, workflowId, runState);
      setEmails(data.items);
      setCurrentPage(data.page);
      setTotalPages(data.pages);
    } catch (err) {
      if (silent) {
        console.error('Silent email fetch failed:', err);
      } else {
        toast.error('Failed to load emails.');
      }
    }
  }, [workflowId, runState]);

  // Debounce query edits so an in-progress value (e.g. a half-typed regex) doesn't
  // trigger a fetch, and mid-typing errors (like an unbalanced regex) stay silent.
  useEffect(() => {
    const handle = setTimeout(() => setDebouncedQuery(query), 400);
    return () => clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    void fetchEmails(currentPage, debouncedQuery, true);
  }, [currentPage, workflowId, runState, debouncedQuery, fetchEmails]);

  const handleSearch = () => {
    setCurrentPage(1);
    setDebouncedQuery(query);
    fetchEmails(1, query);
  };


  const columns: ColumnDef<Email>[] = [
    {
      id: 'email_id_col',
      header: 'ID',
      accessorKey: 'id',
      cell: ({ getValue }) => (
        <span className="text-xs text-gray-400 font-mono">#{getValue<number>()}</span>
      ),
    },
    {
      header: 'Subject',
      accessorKey: 'subject',
      cell: ({ getValue }) => {
        const subject = getValue<string>();
        return (
          <span 
            title={subject}
            className="font-medium text-slate-800 dark:text-slate-100 truncate block max-w-[320px]"
          >
            {subject}
          </span>
        );
      }
    },
    {
      header: 'From',
      accessorKey: 'sender',
      cell: ({ getValue }) => {
        const sender = getValue<string>();
        return (
          <span title={sender} className="text-sm text-slate-500 truncate block max-w-[200px]">
            {sender}
          </span>
        );
      },
    },
    {
      header: 'To',
      accessorKey: 'recipient',
      cell: ({ getValue }) => {
        const recipient = getValue<string>();
        return (
          <span title={recipient} className="text-sm text-slate-500 truncate block max-w-[180px]">
            {recipient}
          </span>
        );
      },
    },
    {
      header: 'Received',
      accessorKey: 'date',
      cell: ({ getValue }) => (
        <span className="text-xs text-gray-400 whitespace-nowrap">
          {new Date(getValue<string>()).toISOString().replace('T', ' ').slice(0, 19)}
        </span>
      ),
    },
    {
      header: 'Runs',
      accessorKey: 'run_summary',
      cell: ({ getValue }) => <RunSummaryCell summary={getValue<Email['run_summary']>()} />,
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => <EmailActionsMenu email={row.original} />,
    },
  ];

  // TanStack Table's hook API is intentionally incompatible with React Compiler memoization.
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table
  const table = useReactTable({
    data: emails,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="w-full px-6 py-6">

      {workflowId && runState && (
        <div className="mb-4 flex items-center gap-3 px-4 py-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg text-sm text-blue-800 dark:text-blue-300">
          <span>
            Showing <strong>{STATE_LABELS[runState] ?? runState}</strong> runs for workflow <strong>{workflowName ?? `#${workflowId}`}</strong>
          </span>
          <button
            onClick={() => navigate('/emails')}
            className="ml-auto text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 underline"
          >
            Clear filter
          </button>
        </div>
      )}

      <div className="mb-4 flex items-end gap-3">
        <QueryBuilder
          fields={fields}
          query={query}
          onQueryChange={setQuery}
          controlClassnames={{
            queryBuilder: 'queryBuilder-branches text-slate-900 dark:text-slate-100',
            addRule: 'px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm font-medium',
            addGroup: 'px-3 py-1.5 bg-slate-500 text-white rounded hover:bg-slate-600 text-sm font-medium',
            removeRule: 'px-2 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 text-sm',
            removeGroup: 'px-2 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 text-sm',
            combinators: QB_CONTROL,
            fields: QB_CONTROL,
            operators: QB_CONTROL,
            value: QB_CONTROL,
          }}
        />
        <button
          onClick={handleSearch}
          className="px-4 py-1.5 mb-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 whitespace-nowrap"
        >
          Search
        </button>
      </div>

      <PageTable
        table={table}
        emptyMessage="No emails found."
        onRowClick={row => navigate(`/email/${row.original.id}`)}
        page={currentPage}
        pages={totalPages}
        onPageChange={setCurrentPage}
      />
    </div>
  );
};

export default EmailsPage;