import { FALLBACK_COLORS } from '../types/workflowEditor';
import type { StepMeta } from '../types/workflowEditor';

interface SidebarProps {
  stepsMeta: StepMeta[];
  loading?: boolean;
}

const Sidebar = ({ stepsMeta, loading }: SidebarProps) => {
  const grouped = stepsMeta.reduce<Record<string, StepMeta[]>>((acc, s) => {
    const cat = s.category || 'general';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(s);
    return acc;
  }, {});

  const orderedCategories = stepsMeta.reduce<string[]>((acc, s) => {
    const cat = s.category || 'general';
    if (!acc.includes(cat)) acc.push(cat);
    return acc;
  }, []);

  const onDragStart = (e: React.DragEvent<HTMLDivElement>, step: StepMeta): void => {
    e.dataTransfer.setData('application/reactflow-step', JSON.stringify(step));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="w-[220px] bg-gray-50 dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 overflow-y-auto flex-shrink-0">
      <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-800 font-semibold text-[13px] text-gray-800 dark:text-slate-100">
        Steps
      </div>
      {loading && <div className="p-4 text-xs text-gray-400 dark:text-slate-500">Loading…</div>}
      {orderedCategories.map(category => {
        const steps = grouped[category];
        const colors = steps[0]?.colors ?? FALLBACK_COLORS;
        return (
          <div key={category}>
            <div className="px-4 pt-2 pb-1 text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider">
              {category}
            </div>
            {steps.map(step => (
              <div
                key={step.type}
                draggable
                onDragStart={e => onDragStart(e, step)}
                className="mx-2.5 my-1 px-2.5 py-2 rounded-md cursor-grab text-xs font-medium select-none hover:opacity-80 transition-opacity"
                style={{ border: `1.5px solid ${colors.border}`, background: colors.bg, color: colors.text }}
              >
                {step.label}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};

export default Sidebar;
