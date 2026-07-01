import { Handle, Position, type NodeProps } from '@xyflow/react';
import { FALLBACK_COLORS } from '../../types/workflowEditor';
import type { StepFlowNode } from '../../types/workflowEditor';

const StepNode = ({ data, selected }: NodeProps<StepFlowNode>) => {
  const colors = data.meta?.colors ?? FALLBACK_COLORS;
  return (
    <div
      className="rounded-lg min-w-[180px]"
      style={{
        border: `2px solid ${selected ? '#111827' : colors.border}`,
        background: colors.bg,
        boxShadow: selected ? '0 0 0 2px #111827' : '0 2px 6px rgba(0,0,0,0.1)',
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="px-3 py-2">
        <div className="font-semibold text-[13px]" style={{ color: colors.text }}>
          {data.meta?.label ?? data.stepType}
        </div>
        {data.meta?.docstring && (
          <div className="text-[11px] text-gray-400 mt-0.5 max-w-[200px]">
            {data.meta.docstring.split('\n')[0]}
          </div>
        )}
        {data.config && Object.entries(data.config).map(([k, v]) => (
          <div key={k} className="text-[10px] mt-1 text-gray-600 dark:text-slate-400">
            <span className="font-medium">{k}:</span>{' '}
            <span className="text-gray-400 dark:text-slate-500">
              {String(v).slice(0, 30)}{String(v).length > 30 ? '…' : ''}
            </span>
          </div>
        ))}
        {data.user_comment && (
          <div className="text-[10px] mt-1.5 italic text-gray-400 dark:text-slate-500 border-l-2 border-gray-200 dark:border-slate-700 pl-1.5 max-w-[200px] leading-snug">
            {String(data.user_comment).slice(0, 80)}{String(data.user_comment).length > 80 ? '…' : ''}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default StepNode;