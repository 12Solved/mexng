import { Handle, Position, type NodeProps } from '@xyflow/react';
import { FALLBACK_COLORS } from '../../types/workflowEditor';
import type { StepFlowNode } from '../../types/workflowEditor';

const StepNode = ({ data, selected }: NodeProps<StepFlowNode>) => {
  const colors = data.meta?.colors ?? FALLBACK_COLORS;
  return (
    <div
      className="step-node px-3 py-2 rounded-lg min-w-[150px] cursor-pointer"
      style={{
        '--step-border': colors.border,
        '--step-bg': colors.bg,
        '--step-text': colors.text,
        border: `2px solid ${selected ? '#111827' : ''}`,
        borderColor: selected ? (document.documentElement.classList.contains('dark') ? '#f1f5f9' : '#111827') : undefined,
      } as React.CSSProperties}
    >
      <Handle type="target" position={Position.Top} />
        <div className="font-semibold text-[13px]">
          {data.meta?.label ?? data.stepType}
        </div>
        {data.meta?.docstring && (
          <div className="text-[11px] text-gray-400 mt-0.5 max-w-[200px]">
            {data.meta.docstring.split('\n')[0]}
          </div>
        )}
        {data.config && Object.entries(data.config).map(([k, v]) => {
          const isMasked = data.meta?.config_schema?.[k]?.columns?.some(c => c.mask);
          return (
            <div key={k} className="text-[10px] mt-1 text-gray-600 dark:text-slate-400">
              <span className="font-medium">{k}:</span>{' '}
              <span className="text-gray-400 dark:text-slate-500">
                {isMasked
                  ? (String(v).trim() ? '••••••••' : '')
                  : `${String(v).slice(0, 30)}${String(v).length > 30 ? '…' : ''}`}
              </span>
            </div>
          );
        })}
        {data.user_comment && (
          <div className="text-[10px] mt-1.5 italic text-gray-400 dark:text-slate-500 border-l-2 border-gray-200 dark:border-slate-700 pl-1.5 max-w-[200px] leading-snug">
            {String(data.user_comment).slice(0, 80)}{String(data.user_comment).length > 80 ? '…' : ''}
          </div>
        )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default StepNode;