import type { ReactNode } from 'react';
import { flexRender, type Table, type Row } from '@tanstack/react-table';
import Pagination from './Pagination';

interface PageTableProps<T> {
  table: Table<T>;
  emptyMessage?: ReactNode;
  onRowClick?: (row: Row<T>) => void;
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}

export function PageTable<T>({
  table,
  emptyMessage = 'No results found.',
  onRowClick,
  page,
  pages,
  onPageChange,
}: PageTableProps<T>) {
  const rows = table.getRowModel().rows;
  const colCount = table.getAllColumns().length;

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id} className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
              {hg.headers.map(h => (
                <th key={h.id} className="px-4 py-3 text-left text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={colCount} className="px-4 py-12 text-center text-sm text-slate-300 dark:text-slate-600">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map(row => (
              <tr
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`border-b border-slate-50 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors${onRowClick ? ' cursor-pointer' : ''}`}
              >
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-4 py-3">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
      <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800">
        <Pagination page={page} pages={pages} onPageChange={onPageChange} />
      </div>
    </div>
  );
}
