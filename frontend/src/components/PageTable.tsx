import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { flexRender, type Table, type Row } from '@tanstack/react-table';
import Pagination from './Pagination';

interface PageTableProps<T> {
  table: Table<T>;
  emptyMessage?: ReactNode;
  onRowClick?: (row: Row<T>) => void;
  getRowHref?: (row: Row<T>) => string;
  unlinkedColumns?: string[];
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}

export function PageTable<T>({
  table,
  emptyMessage = 'No results found.',
  onRowClick,
  getRowHref,
  unlinkedColumns = [],
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
            rows.map(row => {
              const href = getRowHref?.(row);
              const rowClick = !href && onRowClick ? () => onRowClick(row) : undefined;
              return (
                <tr
                  key={row.id}
                  onClick={rowClick}
                  className={`border-b border-slate-50 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors${href || rowClick ? ' cursor-pointer' : ''}`}
                >
                  {row.getVisibleCells().map(cell => {
                    const content = flexRender(cell.column.columnDef.cell, cell.getContext());
                    if (!href || unlinkedColumns.includes(cell.column.id)) {
                      return <td key={cell.id} className="px-4 py-3">{content}</td>;
                    }
                    // Padding moves onto the link so the whole cell is clickable.
                    return (
                      <td key={cell.id} className="p-0">
                        <Link to={href} className="block px-4 py-3">{content}</Link>
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
      <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800">
        <Pagination page={page} pages={pages} onPageChange={onPageChange} />
      </div>
    </div>
  );
}
