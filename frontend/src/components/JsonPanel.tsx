import type { WorkflowJson } from '../types/workflowEditor';

interface JsonPanelProps {
  json: WorkflowJson | null;
  onClose: () => void;
}

const JsonPanel = ({ json, onClose }: JsonPanelProps) => {
  if (!json) return null;
  return (
    <div className="bg-gray-100 border-t border-gray-200 max-h-56 overflow-y-auto p-3 flex-shrink-0">
      <div className="flex justify-between items-center mb-1.5">
        <span className="font-semibold text-[13px] text-gray-800">Exported JSON</span>
        <button
          onClick={onClose}
          className="bg-transparent border-none cursor-pointer text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>
      </div>
      <pre className="text-[11px] m-0 bg-white p-2.5 rounded-md border border-gray-200 overflow-x-auto">
        {JSON.stringify(json, null, 2)}
      </pre>
    </div>
  );
};

export default JsonPanel;