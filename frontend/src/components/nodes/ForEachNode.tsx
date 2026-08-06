import { useContext } from 'react';
import { Handle, Position, NodeResizer, type NodeProps } from '@xyflow/react';
import { FALLBACK_COLORS, DropTargetContext } from '../../types/workflowEditor';
import type { ForeachFlowNode } from '../../types/workflowEditor';

const ForEachNode = ({ id, data, selected }: NodeProps<ForeachFlowNode>) => {
  const colors = data.meta?.colors ?? FALLBACK_COLORS;
  const config = data.config as { collection?: string; item?: string };
  const isDark = document.documentElement.classList.contains('dark');
  const isDropTarget = useContext(DropTargetContext) === id;

  return (
    <div
      className="rounded-xl w-full h-full box-border"
      style={{
        border: `2px dashed ${isDropTarget ? '#22c55e' : selected ? (isDark ? '#f1f5f9' : '#111827') : colors.border}`,
        background: isDropTarget
          ? (isDark ? 'rgba(34,197,94,0.18)' : 'rgba(34,197,94,0.10)')
          : (isDark ? 'rgba(139,92,246,0.08)' : 'rgba(139,92,246,0.04)'),
        boxShadow: isDropTarget ? '0 0 0 2px #22c55e' : selected ? `0 0 0 2px ${isDark ? '#f1f5f9' : '#111827'}` : undefined,
      }}
    >
      <NodeResizer
        minWidth={280}
        minHeight={160}
        isVisible={selected}
        lineStyle={{ border: '1.5px solid #8b5cf6' }}
        handleStyle={{ width: 8, height: 8, borderRadius: 2, background: '#8b5cf6' }}
      />
      <Handle type="target" position={Position.Top} />
      <div
        className="foreach-node flex items-center gap-2 px-3 py-1.5 rounded-t-[10px]"
        style={{
          '--step-border': colors.border,
          '--step-bg': colors.bg,
          '--step-text': colors.text,
          borderBottom: '1px dashed',
        } as React.CSSProperties}
      >
        <span className="font-semibold text-[13px]">For Each</span>
        {config.collection && (
          <span className="text-[11px] text-gray-400">
            {config.collection}
          </span>
        )}
        {data.user_comment && (
          <span className="text-[10px] italic text-gray-400 dark:text-slate-500 border-l border-gray-300 dark:border-slate-600 pl-1.5 ml-auto max-w-[120px] truncate">
            {String(data.user_comment)}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default ForEachNode;