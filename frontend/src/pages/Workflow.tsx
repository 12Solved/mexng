import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import EditorInner from '../components/EditorInner';
import type { ContextVars, StepMeta } from '../types/workflowEditor';
import { getWorkflow, getSteps, getContextVars } from '../services/workflowServices';
import type { Workflow } from '../types/workflow';

const WorkflowEditor = () => {
  const { id } = useParams<{ id: string }>()
  const [stepsMeta, setStepsMeta] = useState<StepMeta[]>([]);
  const [contextVars, setContextVars] = useState<ContextVars>({ global: {}, foreach: {} });
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getSteps(),
      getContextVars(),
      id && id !== 'new' ? getWorkflow(Number(id)) : Promise.resolve(null),
    ])
      .then(([steps, vars, wf]) => {
        setStepsMeta(steps)
        setContextVars(vars)
        setWorkflow(wf)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id]);

  if (loading) return (
    <div className="flex items-center justify-center h-[calc(100vh-56px)] text-sm text-gray-400">
      Loading…
    </div>
  );

  if (error) return (
    <div className="flex items-center justify-center h-[calc(100vh-56px)] text-sm text-red-500">
      Failed to load: {error}
    </div>
  );

  return (
    <ReactFlowProvider>
      <EditorInner stepsMeta={stepsMeta} contextVars={contextVars} workflow={workflow} />
    </ReactFlowProvider>
  );
};

export default WorkflowEditor;
