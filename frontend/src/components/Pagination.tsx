interface Props {
  page: number
  pages: number
  onPageChange: (page: number) => void
}

const Pagination = ({ page, pages, onPageChange }: Props) => {
  if (pages <= 1) return null

  return (
    <div className="flex items-center justify-center gap-3 py-2">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-slate-500"
      >
        ← Prev
      </button>

      <span className="text-xs text-slate-400 dark:text-slate-500 tabular-nums">
        {page} / {pages}
      </span>

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === pages}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-slate-500"
      >
        Next →
      </button>
    </div>
  )
}

export default Pagination