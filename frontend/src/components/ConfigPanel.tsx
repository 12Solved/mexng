import { useState } from 'react';
import { FALLBACK_COLORS } from '../types/workflowEditor';
import { getCollectionsAtNode, getContextAtNode } from '../utils/workflowUtils';
import DelimitedListEditor from './DelimitedListEditor';
import type { AnyFlowNode, ContextVars, StepMeta, ConfigSchemaField } from '../types/workflowEditor';
import type { Edge } from '@xyflow/react';

type DurationUnit = 'hours' | 'days' | 'weeks';
const DURATION_MULTIPLIERS: Record<DurationUnit, number> = { hours: 1, days: 24, weeks: 168 };

function hoursToDisplay(h: number): { value: number; unit: DurationUnit } {
  if (h >= 168 && h % 168 === 0) return { value: h / 168, unit: 'weeks' };
  if (h >= 24 && h % 24 === 0) return { value: h / 24, unit: 'days' };
  return { value: h, unit: 'hours' };
}

interface ConfigPanelProps {
  node: AnyFlowNode;
  stepsMeta: StepMeta[];
  nodes: AnyFlowNode[];
  edges: Edge[];
  contextVars: ContextVars;
  onChange: (nodeId: string, config: Record<string, string>) => void;
  onCommentChange: (nodeId: string, comment: string) => void;
  onClose: () => void;
  onDelete: (nodeId: string) => void;
}

const ConfigPanel = ({ node, stepsMeta, nodes, edges, contextVars, onChange, onCommentChange, onClose, onDelete }: ConfigPanelProps) => {
  const meta = stepsMeta.find(s => s.type === node.data.stepType);
  const schema = meta?.config_schema ?? {};
  const config = node.data.config ?? {};
  const colors = meta?.colors ?? FALLBACK_COLORS;
  const hasConfig = Object.keys(schema).length > 0;
  const isForeach = node.data.stepType === 'foreach';
  const isInsideForeach = !!node.parentId;
  const availableCollections = isForeach ? getCollectionsAtNode(node.id, nodes, edges) : [];
  const graphContext = Object.entries(getContextAtNode(node.id, nodes, edges));

  const isRequiredEmpty = (key: string, field: ConfigSchemaField): boolean => {
    if (!field.required) return false;
    const v = config[key] ?? field.default ?? '';
    return String(v ?? '').trim().length === 0;
  };

  const guaranteedVars = {
    ...contextVars.global,
    ...(isInsideForeach ? contextVars.foreach : {}),
  };

  const hasAnyContext = Object.keys(guaranteedVars).length > 0 || graphContext.length > 0;
  const [contextOpen, setContextOpen] = useState(true);

  const handleChange = (key: string, value: string): void =>
    onChange(node.id, { ...config, [key]: value });

  return (
    <div className="absolute top-0 right-0 bottom-0 w-72 bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-800 z-10 flex flex-col shadow-xl">

      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <div
            className="step-indicator w-2 h-2 rounded-full flex-shrink-0"
            style={{ '--step-border': colors.border } as React.CSSProperties}
          />
          <div>
            <div className="font-semibold text-sm text-gray-900 dark:text-slate-100">{meta?.label ?? node.data.stepType}</div>
            <div className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-wider mt-0.5">{meta?.category}</div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 text-lg leading-none bg-transparent border-none cursor-pointer p-1"
        >
          ×
        </button>
      </div>

      {meta?.docstring && (
        <div className="px-4 py-2.5 text-[11px] text-gray-500 dark:text-slate-400 border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 italic leading-relaxed">
          {meta.docstring}
        </div>
      )}

      <div className="px-4 py-3 overflow-y-auto flex-1 space-y-1">

        <div className="mb-3">
          <label className="block text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-1.5">Notes</label>
          <textarea
            value={node.data.user_comment ?? ''}
            onChange={e => onCommentChange(node.id, e.target.value)}
            placeholder="Describe what this step does in this workflow…"
            rows={3}
            className="w-full px-2.5 py-1.5 text-xs border border-gray-300 dark:border-slate-700 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 resize-none bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 placeholder-gray-300 dark:placeholder-slate-500 box-border transition-all"
          />
        </div>

        {hasConfig && (
          <div className="mb-2">
            <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-2">Configuration</div>
            {Object.entries(schema).map(([key, field]) => {
              const stored = parseInt(config[key] ?? '', 10);
              const { value: durDispVal, unit: durDispUnit } =
                isNaN(stored) || stored <= 0 ? { value: 1, unit: 'hours' as DurationUnit } : hoursToDisplay(stored);
              return (
              <div key={key} className="mb-3">
                <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-0.5">*</span>}
                </label>

                {isForeach && key === 'collection' ? (
                  availableCollections.length > 0 ? (
                    <select
                      value={config[key] ?? ''}
                      onChange={e => handleChange(key, e.target.value)}
                      className={`w-full px-2.5 py-1.5 text-xs border rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 box-border transition-all bg-white dark:bg-slate-800 dark:text-slate-200 ${
                        isRequiredEmpty(key, field)
                          ? 'border-red-400 dark:border-red-500'
                          : 'border-gray-300 dark:border-slate-700'
                      }`}
                    >
                      <option value="" disabled>Select a collection…</option>
                      {availableCollections.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  ) : (
                    <div className="w-full px-2.5 py-1.5 text-xs border border-dashed border-gray-300 dark:border-slate-700 rounded-md text-gray-400 dark:text-slate-500 bg-gray-50 dark:bg-slate-800/50">
                      No collections in context yet — connect a step that outputs a list first.
                    </div>
                  )
                ) : field.options ? (
                  <select
                    value={config[key] ?? field.default ?? ''}
                    onChange={e => handleChange(key, e.target.value)}
                    className={`w-full px-2.5 py-1.5 text-xs border rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 box-border transition-all bg-white dark:bg-slate-800 dark:text-slate-200 ${
                      isRequiredEmpty(key, field)
                        ? 'border-red-400 dark:border-red-500'
                        : 'border-gray-300 dark:border-slate-700'
                    }`}
                  >
                    {field.default == null && <option value="" disabled>Select…</option>}
                    {field.options.map(opt => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : field.type === 'datetime' ? (
                  <div className="flex flex-col gap-0.5">
                    <input
                      type="datetime-local"
                      value={(config[key] ?? '').replace('Z', '').slice(0, 16)}
                      onChange={e => handleChange(key, e.target.value ? `${e.target.value}:00Z` : '')}
                      className={`w-full px-2.5 py-1.5 text-xs border rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 box-border transition-all bg-white dark:bg-slate-800 dark:text-slate-200 ${
                        isRequiredEmpty(key, field)
                          ? 'border-red-400 dark:border-red-500'
                          : 'border-gray-300 dark:border-slate-700'
                      }`}
                    />
                    <div className="text-[10px] text-gray-400 dark:text-slate-500">Interpreted as UTC</div>
                  </div>
                ) : field.type === 'json_list' ? (
                  <DelimitedListEditor
                    key={`${node.id}:${key}`}
                    field={field}
                    value={config[key] ?? field.default ?? ''}
                    onChange={v => handleChange(key, v)}
                  />
                ) : field.type === 'duration' ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      inputMode="numeric"
                      value={durDispVal}
                      onChange={e => {
                        const n = parseInt(e.target.value, 10);
                        if (n > 0) handleChange(key, String(n * DURATION_MULTIPLIERS[durDispUnit]));
                      }}
                      className={`w-20 px-2.5 py-1.5 text-xs border rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 box-border transition-all bg-white dark:bg-slate-800 dark:text-slate-200 ${
                        isRequiredEmpty(key, field)
                          ? 'border-red-400 dark:border-red-500'
                          : 'border-gray-300 dark:border-slate-700'
                      }`}
                    />
                    <select
                      value={durDispUnit}
                      onChange={e => {
                        const u = e.target.value as DurationUnit;
                        handleChange(key, String(durDispVal * DURATION_MULTIPLIERS[u]));
                      }}
                      className="flex-1 px-2.5 py-1.5 text-xs border border-gray-300 dark:border-slate-700 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 box-border transition-all bg-white dark:bg-slate-800 dark:text-slate-200"
                    >
                      <option value="hours">Hours</option>
                      <option value="days">Days</option>
                      <option value="weeks">Weeks</option>
                    </select>
                  </div>
                ) : (
                  <input
                    type="text"
                    value={config[key] ?? field.default ?? ''}
                    placeholder={field.placeholder ?? ''}
                    onChange={e => handleChange(key, e.target.value)}
                    className={`w-full px-2.5 py-1.5 text-xs border rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 box-border transition-all bg-white dark:bg-slate-800 dark:text-slate-200 dark:placeholder-slate-500 ${
                      isRequiredEmpty(key, field)
                        ? 'border-red-400 dark:border-red-500'
                        : 'border-gray-300 dark:border-slate-700'
                    }`}
                  />
                )}

                {field.description && (
                  <div className="text-[10px] text-gray-400 dark:text-slate-500 mt-1">{field.description}</div>
                )}
              </div>
              );
            })}
          </div>
        )}

        {!hasConfig && (
          <div className="flex items-center gap-2 py-3 text-xs text-gray-400 dark:text-slate-500">
            <span>✓</span>
            <span>No configuration needed</span>
          </div>
        )}

        {meta?.args_in && Object.keys(meta.args_in).length > 0 && (
          <div className="pt-2 border-t border-gray-100 dark:border-slate-800">
            <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-2">Reads from context</div>
            {Object.entries(meta.args_in).map(([k, t]) => (
              <div key={k} className="flex items-center justify-between py-1 text-[11px]">
                <span className="text-gray-700 dark:text-slate-300 font-medium">{k}</span>
                <span className="text-gray-400 dark:text-slate-500 font-mono bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">{t}</span>
              </div>
            ))}
          </div>
        )}

        {meta?.args_out && Object.keys(meta.args_out).length > 0 && (
          <div className="pt-2 border-t border-gray-100 dark:border-slate-800">
            <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider mb-2">Writes to context</div>
            {Object.entries(meta.args_out).map(([k, t]) => (
              <div key={k} className="flex items-center justify-between py-1 text-[11px]">
                <span className="text-gray-700 dark:text-slate-300 font-medium">{k}</span>
                <span className="text-gray-400 dark:text-slate-500 font-mono bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">{t}</span>
              </div>
            ))}
          </div>
        )}

        {hasAnyContext && (
          <div className="pt-2 border-t border-gray-100 dark:border-slate-800">
            <button
              onClick={() => setContextOpen(o => !o)}
              className="flex items-center justify-between w-full bg-transparent border-none cursor-pointer p-0 mb-2 group"
            >
              <div className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider">
                Available context
              </div>
              <span className="text-gray-300 dark:text-slate-600 group-hover:text-gray-400 dark:group-hover:text-slate-400 text-[10px] transition-colors">
                {contextOpen ? '▲' : '▼'}
              </span>
            </button>

            {contextOpen && (
              <div className="flex flex-col gap-2">
                {Object.keys(guaranteedVars).length > 0 && (
                  <div>
                    <div className="text-[9px] font-semibold text-gray-300 dark:text-slate-600 uppercase tracking-wider mb-1">Guaranteed</div>
                    <div className="flex flex-col gap-0.5">
                      {Object.entries(guaranteedVars).map(([k, t]) => (
                        <div key={k} className="flex items-center justify-between px-2 py-1 rounded text-[11px] bg-gray-50 dark:bg-slate-800">
                          <span className="font-mono font-medium text-gray-600 dark:text-slate-300">${`{${k}}`}</span>
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-400">{t}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {graphContext.length > 0 && (
                  <div>
                    <div className="text-[9px] font-semibold text-gray-300 dark:text-slate-600 uppercase tracking-wider mb-1">From workflow</div>
                    <div className="flex flex-col gap-0.5">
                      {graphContext.map(([k, t]) => (
                        <div key={k} className="flex items-center justify-between px-2 py-1 rounded text-[11px] bg-gray-50 dark:bg-slate-800">
                          <span className="font-mono font-medium text-gray-600 dark:text-slate-300">${`{${k}}`}</span>
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-400">{t}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="px-4 py-3 border-t border-gray-100 dark:border-slate-800">
        <button
          onClick={() => { onDelete(node.id); onClose(); }}
          className="w-full py-1.5 text-xs text-red-500 border border-red-200 dark:border-red-900 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 cursor-pointer bg-transparent transition-colors"
        >
          Delete step
        </button>
      </div>
    </div>
  );
};

export default ConfigPanel;