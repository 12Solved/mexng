import { useState } from 'react';
import type { ConfigSchemaField, DelimitedListColumn } from '../types/workflowEditor';

interface DelimitedListEditorProps {
  field: ConfigSchemaField;
  value: string;
  onChange: (value: string) => void;
}

const defaultColumns: DelimitedListColumn[] = [{ key: 'value', label: 'Value' }];

const parseRows = (value: string, field: ConfigSchemaField): string[][] => {
  const itemDelimiter = field.item_delimiter ?? ',';
  const pairDelimiter = field.pair_delimiter;
  const columns = field.columns ?? defaultColumns;

  const items = (value ?? '').split(itemDelimiter).map(s => s.trim()).filter(s => s.length > 0);
  if (items.length === 0) return [columns.map(() => '')];

  return items.map(item => {
    const parts = pairDelimiter ? item.split(pairDelimiter) : [item];
    if (parts.length > columns.length) {
      const head = parts.slice(0, columns.length - 1);
      const tail = parts.slice(columns.length - 1).join(pairDelimiter as string);
      return [...head, tail].map(p => p.trim());
    }
    while (parts.length < columns.length) parts.push('');
    return parts.map(p => p.trim());
  });
};

const serializeRows = (rows: string[][], field: ConfigSchemaField): string => {
  const itemDelimiter = field.item_delimiter ?? ',';
  const pairDelimiter = field.pair_delimiter;
  return rows
    .filter(row => row.some(cell => cell.trim().length > 0))
    .map(row => (pairDelimiter ? row.join(pairDelimiter) : row[0] ?? ''))
    .join(itemDelimiter);
};

const inputClass =
  'flex-1 min-w-0 px-2.5 py-1.5 text-xs border rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 box-border transition-all bg-white dark:bg-slate-800 dark:text-slate-200 dark:placeholder-slate-500';

const DelimitedListEditor = ({ field, value, onChange }: DelimitedListEditorProps) => {
  const columns = field.columns ?? defaultColumns;
  // Rows are local state, seeded once from `value`, rather than re-derived from it on every
  // render — serialization drops fully-blank rows (so they don't pollute the saved config),
  // which would otherwise make a freshly-added blank row vanish the instant it's added.
  const [rows, setRows] = useState<string[][]>(() => parseRows(value, field));

  const commit = (next: string[][]): void => {
    setRows(next);
    onChange(serializeRows(next, field));
  };

  const updateCell = (rowIdx: number, colIdx: number, cellValue: string): void => {
    const next = rows.map(r => [...r]);
    next[rowIdx][colIdx] = cellValue;
    commit(next);
  };

  const removeRow = (rowIdx: number): void => {
    const next = rows.filter((_, i) => i !== rowIdx);
    commit(next.length > 0 ? next : [columns.map(() => '')]);
  };

  const addRow = (): void => {
    commit([...rows, columns.map(() => '')]);
  };

  return (
    <div className="flex flex-col gap-1.5">
      {columns.length > 1 && (
        <div className="flex gap-1.5">
          {columns.map(col => (
            <div key={col.key} className="flex-1 min-w-0 text-[10px] text-gray-400 dark:text-slate-500">
              {col.label}
            </div>
          ))}
          <div className="w-5 flex-shrink-0" />
        </div>
      )}
      {rows.map((row, rowIdx) => (
        <div key={rowIdx} className="flex gap-1.5 items-center">
          {columns.map((col, colIdx) => {
            const isFlaggedEmpty = colIdx === 0 && columns.length > 1 && row[colIdx].trim().length === 0;
            return (
              <input
                key={col.key}
                type={col.mask ? 'password' : 'text'}
                value={row[colIdx] ?? ''}
                placeholder={col.placeholder ?? (columns.length === 1 ? col.label : '')}
                onChange={e => updateCell(rowIdx, colIdx, e.target.value)}
                className={`${inputClass} ${
                  isFlaggedEmpty ? 'border-red-400 dark:border-red-500' : 'border-gray-300 dark:border-slate-700'
                }`}
              />
            );
          })}
          <button
            type="button"
            onClick={() => removeRow(rowIdx)}
            className="w-5 h-5 flex-shrink-0 flex items-center justify-center text-gray-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 bg-transparent border-none cursor-pointer text-sm leading-none"
            aria-label="Remove row"
          >
            ×
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addRow}
        className="self-start text-[11px] text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 bg-transparent border-none cursor-pointer px-0 py-1"
      >
        + Add row
      </button>
    </div>
  );
};

export default DelimitedListEditor;
