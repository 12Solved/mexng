import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  MarkerType,
  type Edge,
  type NodeTypes,
  type Connection,
  type NodeMouseHandler,
} from '@xyflow/react';

import StepNode from './nodes/StepNode';
import ForEachNode from './nodes/ForEachNode';
import ConfigPanel from './ConfigPanel';
import Sidebar from './Sidebar';
import WorkflowInfoModal from './WorkflowInfoModal';
import TestRunModal from './TestRunModal';
import {
  uid,
  workflowJsonToFlow,
  flowToWorkflowJson,
  getWorkflowValidationErrors,
  relayoutForeachTree,
  FOREACH_WIDTH,
} from '../utils/workflowUtils';
import { DropTargetContext } from '../types/workflowEditor';
import type { AnyFlowNode, ContextVars, StepMeta, WorkflowJson } from '../types/workflowEditor';
import { createWorkflow, updateWorkflow } from '../services/workflowServices';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import type { Workflow } from '../types/workflow';
import { InfoIcon, UploadIcon } from '../assets/icons';

const nodeTypes: NodeTypes = { stepNode: StepNode, foreach: ForEachNode };

const EMPTY_WORKFLOW: WorkflowJson = { steps: [] };

/** Whether `nodeId` is nested (at any depth) inside `ancestorId`. */
const isDescendantOf = (nodeId: string, ancestorId: string, allNodes: AnyFlowNode[]): boolean => {
  let current = allNodes.find((n) => n.id === nodeId);
  while (current?.parentId) {
    if (current.parentId === ancestorId) return true;
    current = allNodes.find((n) => n.id === current!.parentId);
  }
  return false;
};

interface EditorInnerProps {
  stepsMeta: StepMeta[];
  contextVars: ContextVars;
  workflow: Workflow | null;
  onSaved: (saved: Workflow) => void;
}

const EditorInner = ({ stepsMeta, contextVars, workflow, onSaved }: EditorInnerProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<AnyFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<AnyFlowNode | null>(null);
  const [workflowName, setWorkflowName] = useState(workflow?.name ?? '');
  const [workflowDescription, setWorkflowDescription] = useState(workflow?.description ?? '');
  const [infoOpen, setInfoOpen] = useState(false);
  const [testRunOpen, setTestRunOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importJson, setImportJson] = useState('');
  const [exportOpen, setExportOpen] = useState(false);
  const [exportJson, setExportJson] = useState('');
  const [isDroppingJson, setIsDroppingJson] = useState(false);
  const [dropTargetId, setDropTargetId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition, getInternalNode } = useReactFlow();
  const navigate = useNavigate();

  useEffect(() => {
    if (!stepsMeta.length) return;
    const json = workflow?.workflow_json ?? EMPTY_WORKFLOW;
    const { nodes: n, edges: e } = workflowJsonToFlow(json, stepsMeta);
    setNodes(n);
    setEdges(e);
  }, [stepsMeta, workflow]);

  const onConnect = useCallback(
    (params: Connection) => {
      const outgoingCount: Record<string, number> = {};
      edges.forEach((e: { source: string | number; }) => { outgoingCount[e.source] = (outgoingCount[e.source] ?? 0) + 1; });

      const sourceAlreadyBranches = (outgoingCount[params.source] ?? 0) >= 1;

      if (sourceAlreadyBranches) {
        toast.error('Each step can only connect to one next step.');
        return;
      }

      setEdges((eds: Edge[]) => addEdge({ ...params, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed } }, eds));
    },
    [edges, setEdges],
  );

  const onNodeClick: NodeMouseHandler<AnyFlowNode> = useCallback(
    (_: React.MouseEvent, node: AnyFlowNode) => setSelectedNode(node),
    [],
  );
  const onPaneClick = useCallback(() => setSelectedNode(null), []);

  const onConfigChange = useCallback((nodeId: string, newConfig: Record<string, string>): void => {
    setNodes((nds: AnyFlowNode[]) => nds.map((n: AnyFlowNode) =>
      n.id === nodeId ? { ...n, data: { ...n.data, config: newConfig } } : n,
    ));
    setSelectedNode((prev: AnyFlowNode | null) =>
      prev?.id === nodeId ? { ...prev, data: { ...prev.data, config: newConfig } } : prev,
    );
  }, [setNodes]);

  const onCommentChange = useCallback((nodeId: string, comment: string): void => {
    setNodes((nds: AnyFlowNode[]) => nds.map((n: AnyFlowNode) =>
      n.id === nodeId ? { ...n, data: { ...n.data, user_comment: comment } } : n,
    ));
    setSelectedNode((prev: AnyFlowNode | null) =>
      prev?.id === nodeId ? { ...prev, data: { ...prev.data, user_comment: comment } } : prev,
    );
  }, [setNodes]);

  // Deletes a node along with every step nested inside it, at any depth.
  const onDeleteNode = useCallback((nodeId: string): void => {
    const toRemove = new Set<string>([nodeId]);
    let grew = true;
    while (grew) {
      grew = false;
      nodes.forEach((n: AnyFlowNode) => {
        if (n.parentId && toRemove.has(n.parentId) && !toRemove.has(n.id)) {
          toRemove.add(n.id);
          grew = true;
        }
      });
    }
    setNodes((nds: AnyFlowNode[]) => relayoutForeachTree(nds.filter((n: AnyFlowNode) => !toRemove.has(n.id))));
    setEdges((eds: Edge[]) => eds.filter((e: Edge) => !toRemove.has(String(e.source)) && !toRemove.has(String(e.target))));
  }, [nodes, setNodes, setEdges]);

  // Absolute (canvas-space) bounding box of a node, correct regardless of nesting depth.
  const getAbsBounds = useCallback((n: AnyFlowNode) => {
    const abs = getInternalNode(n.id)?.internals.positionAbsolute ?? n.position;
    const w = n.width ?? n.measured?.width ?? (n.style?.width as number | undefined) ?? FOREACH_WIDTH;
    const h = n.height ?? n.measured?.height ?? (n.style?.height as number | undefined) ?? 280;
    return { x: abs.x, y: abs.y, w, h };
  }, [getInternalNode]);

  // Among several for-each containers whose bounds all contain the drop point (nested
  // containers overlap by definition), the innermost one — always the smallest by area,
  // since a container is sized to fit around its children — is the intended target.
  const smallestByArea = useCallback((candidates: AnyFlowNode[]): AnyFlowNode | undefined =>
    candidates.reduce<AnyFlowNode | undefined>((best, n) => {
      if (!best) return n;
      const b = getAbsBounds(best);
      const c = getAbsBounds(n);
      return c.w * c.h < b.w * b.h ? n : best;
    }, undefined),
  [getAbsBounds]);

  // Finds the for-each container (if any) whose bounds contain a canvas point — used while
  // dragging a brand-new step in from the sidebar.
  const findForeachAtPoint = useCallback((point: { x: number; y: number }): AnyFlowNode | undefined =>
    smallestByArea(nodes.filter((n: AnyFlowNode) => {
      if (n.type !== 'foreach') return false;
      const { x, y, w, h } = getAbsBounds(n);
      return point.x >= x && point.x <= x + w && point.y >= y && point.y <= y + h;
    })),
  [nodes, getAbsBounds, smallestByArea]);

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const flowPos = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    setDropTargetId(findForeachAtPoint(flowPos)?.id ?? null);
  }, [screenToFlowPosition, findForeachAtPoint]);

  const onDragLeave = useCallback((): void => setDropTargetId(null), []);

  // Finds the for-each container (if any) whose bounds contain the dragged node's center.
  // A for-each may itself be dropped into another for-each, but never into itself or one of
  // its own descendants (that would create a cycle).
  const findForeachDropTarget = useCallback((draggedNode: AnyFlowNode): AnyFlowNode | undefined => {
    const { x: dx, y: dy, w: dw, h: dh } = getAbsBounds(draggedNode);
    const centerX = dx + dw / 2;
    const centerY = dy + dh / 2;

    return smallestByArea(nodes.filter((n: AnyFlowNode) => {
      if (n.type !== 'foreach' || n.id === draggedNode.id) return false;
      if (draggedNode.type === 'foreach' && isDescendantOf(n.id, draggedNode.id, nodes)) return false;
      const { x, y, w, h } = getAbsBounds(n);
      return centerX >= x && centerX <= x + w && centerY >= y && centerY <= y + h;
    }));
  }, [nodes, getAbsBounds, smallestByArea]);

  // Highlights the for-each container the dragged node currently hovers over.
  const onNodeDrag: NodeMouseHandler<AnyFlowNode> = useCallback((_, draggedNode) => {
    setDropTargetId(findForeachDropTarget(draggedNode)?.id ?? null);
  }, [findForeachDropTarget]);

  // Reparents a step into (or out of) a for-each container when it's dropped there on the canvas,
  // and re-stacks a container's children whenever one is dropped at a new position within it.
  const onNodeDragStop: NodeMouseHandler<AnyFlowNode> = useCallback((_, draggedNode) => {
    setDropTargetId(null);

    const target = findForeachDropTarget(draggedNode);
    const prevParentId = draggedNode.parentId ?? null;

    if ((target?.id ?? null) === prevParentId) {
      if (!target) return; // freely repositioned at top level — nothing to relayout
      setNodes((nds: AnyFlowNode[]) => relayoutForeachTree(nds));
      return;
    }

    const draggedAbs = getInternalNode(draggedNode.id)?.internals.positionAbsolute ?? draggedNode.position;
    const targetAbs = target ? getAbsBounds(target) : null;

    setNodes((nds: AnyFlowNode[]) => {
      const next = nds.map((n: AnyFlowNode) => {
        if (n.id !== draggedNode.id) return n;
        if (target && targetAbs) {
          return {
            ...n,
            parentId: target.id,
            position: { x: draggedAbs.x - targetAbs.x, y: draggedAbs.y - targetAbs.y },
          };
        }
        const { parentId: _parentId, ...rest } = n;
        return { ...rest, position: draggedAbs };
      });

      return relayoutForeachTree(next);
    });

    // The node's old "next step" edges (from import, or a prior reorder) no longer mean
    // anything once it's crossed into a different container — drop them so a promoted-to-
    // top-level node doesn't look like it still has an incoming link from its old sibling
    // and get silently excluded (along with everything nested inside it) from export.
    setEdges((eds: Edge[]) => eds.filter((e: Edge) => e.source !== draggedNode.id && e.target !== draggedNode.id));
  }, [findForeachDropTarget, getAbsBounds, getInternalNode, setNodes, setEdges]);

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    setDropTargetId(null);
    const raw = e.dataTransfer.getData('application/reactflow-step');
    if (!raw) return;
    const step = JSON.parse(raw) as StepMeta;

    const flowPos   = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    const isForeach = step.type === 'foreach';

    // A brand-new step (including a fresh for-each) can be dropped into an existing for-each —
    // it has no children of its own yet, so nesting it can never create a cycle.
    const foreachParent = findForeachAtPoint(flowPos);
    const parentAbs = foreachParent ? getAbsBounds(foreachParent) : null;

    const position = foreachParent && parentAbs
      ? { x: flowPos.x - parentAbs.x, y: flowPos.y - parentAbs.y }
      : flowPos;

    const newNode: AnyFlowNode = {
      id: uid(),
      type: isForeach ? 'foreach' : 'stepNode',
      position,
      data: { stepType: step.type, config: {}, meta: step },
      ...(foreachParent ? { parentId: foreachParent.id } : {}),
      ...(isForeach ? { width: 340, height: 280, style: { width: 340, height: 280 } } : {}),
    };

    setNodes((nds: AnyFlowNode[]) => {
      const next = [...nds, newNode];
      return foreachParent ? relayoutForeachTree(next) : next;
    });
  }, [screenToFlowPosition, setNodes, findForeachAtPoint, getAbsBounds]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => setImportJson(ev.target?.result as string);
    reader.readAsText(file);
  };

  const handleImport = () => {
    setImportError(null);
    let parsed: unknown;
    try { parsed = JSON.parse(importJson); } catch { setImportError('Invalid JSON.'); return; }
    const { nodes: n, edges: eg } = workflowJsonToFlow(parsed as WorkflowJson, stepsMeta);
    setNodes(n);
    setEdges(eg);
    setImportOpen(false);
    setImportJson('');
  };

  const isJsonFile = (e: React.DragEvent) =>
    Array.from(e.dataTransfer.items).some(i => i.kind === 'file' && (i.type === 'application/json' || i.type === ''));

  const onEditorDragEnter = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    if (isJsonFile(e)) { e.preventDefault(); setIsDroppingJson(true); }
  }, []);

  const onEditorDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDroppingJson(false);
  }, []);

  const onEditorDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    if (isDroppingJson) e.preventDefault();
  }, [isDroppingJson]);

  const onEditorDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    if (!isDroppingJson) return;
    e.preventDefault();
    setIsDroppingJson(false);
    const file = Array.from(e.dataTransfer.files).find(f => f.name.endsWith('.json') || f.type === 'application/json');
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const json = JSON.parse(ev.target?.result as string) as WorkflowJson;
        const { nodes: n, edges: eg } = workflowJsonToFlow(json, stepsMeta);
        setNodes(n);
        setEdges(eg);
      } catch {
        toast.error('Invalid JSON file.');
      }
    };
    reader.readAsText(file);
  }, [isDroppingJson, stepsMeta, setNodes, setEdges]);

  const validationErrors = useMemo(
    () => getWorkflowValidationErrors(nodes, edges, stepsMeta),
    [nodes, edges, stepsMeta],
  );

  const handleSave = async () => {
    if (!workflowName.trim()) {
      toast.error('Please enter a workflow name.');
      return;
    }
    if (validationErrors.length > 0) {
      toast.error(
        validationErrors.length === 1
          ? validationErrors[0]
          : 'Workflow cannot be saved yet.',
        {
          description:
            validationErrors.length === 1 ? undefined : validationErrors.join('\n'),
          duration: validationErrors.length > 3 ? 12_000 : 6_000,
        },
      );
      return;
    }
    const isUpdate = Boolean(workflow?.id);
    setSaving(true);
    try {
      const json = flowToWorkflowJson(nodes, edges);
      const saved = isUpdate
        ? await updateWorkflow(workflow!.id, workflowName, json, workflowDescription)
        : await createWorkflow(workflowName, json, workflowDescription);
      onSaved(saved);
      toast.success(isUpdate ? 'Workflow saved.' : 'Workflow created.');
    } catch (e) {
      console.error('Save failed', e);
      toast.error('Save failed. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const exportWorkflow = (): void => {
    const json = flowToWorkflowJson(nodes, edges);
    setExportJson(JSON.stringify(json, null, 2));
    setExportOpen(true);
  };

  const handleDownloadJson = (): void => {
    const blob = new Blob([exportJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName || 'workflow'}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 100);
  };

  return (
    <>
    <div className="flex flex-col h-[calc(100vh-56px)] w-full">

      <div className="bg-slate-100 dark:bg-gray-900 text-slate-800 dark:text-white border-b border-slate-200 dark:border-slate-800 px-4 py-2.5 flex items-center gap-3 flex-shrink-0">
        <button
          onClick={() => navigate('/workflow')}
          className="text-slate-400 dark:text-gray-400 hover:text-slate-700 dark:hover:text-white text-sm transition-colors"
        >
          ← Back
        </button>
        <input
          value={workflowName}
          onChange={e => setWorkflowName(e.target.value)}
          placeholder="Workflow name…"
          aria-invalid={workflowName.trim() === ''}
          className={`flex-1 bg-white dark:bg-gray-800 text-slate-800 dark:text-white text-sm px-3 py-1.5 rounded-md border outline-none focus:border-blue-500 placeholder:text-slate-400 dark:placeholder:text-gray-500 max-w-xs transition-colors ${
            workflowName.trim() === ''
              ? 'border-rose-300 dark:border-rose-700'
              : 'border-slate-200 dark:border-gray-700'
          }`}
        />
        <button
          onClick={() => setInfoOpen(true)}
          title="Workflow info"
          className="flex items-center justify-center w-8 h-8 rounded-md text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors border-none bg-transparent cursor-pointer flex-shrink-0"
        >
          <InfoIcon />
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <button
            onClick={() => { setImportJson(''); setImportError(null); setImportOpen(true); }}
            className="px-3.5 py-1.5 bg-slate-200 dark:bg-gray-700 hover:bg-slate-300 dark:hover:bg-gray-600 text-slate-700 dark:text-white rounded-md text-[13px] cursor-pointer border-none transition-colors"
          >
            Import JSON
          </button>
          <button
            onClick={exportWorkflow}
            className="px-3.5 py-1.5 bg-slate-200 dark:bg-gray-700 hover:bg-slate-300 dark:hover:bg-gray-600 text-slate-700 dark:text-white rounded-md text-[13px] cursor-pointer border-none transition-colors"
          >
            Export JSON
          </button>
          <button
            onClick={() => setTestRunOpen(true)}
            className="px-3.5 py-1.5 bg-slate-200 dark:bg-gray-700 hover:bg-slate-300 dark:hover:bg-gray-600 text-slate-700 dark:text-white rounded-md text-[13px] cursor-pointer border-none transition-colors"
          >
            Test run
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-3.5 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md text-[13px] cursor-pointer border-none transition-colors"
          >
            {saving ? 'Saving…' : workflow?.id ? 'Save' : 'Create'}
          </button>
        </div>
      </div>

      {importOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-2xl mx-4 p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Import Workflow JSON</h2>
              <button onClick={() => setImportOpen(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => fileRef.current?.click()}
                className="w-full py-2 text-xs font-medium border border-dashed border-gray-300 dark:border-slate-700 rounded-md text-gray-500 dark:text-slate-400 hover:border-gray-400 dark:hover:border-slate-500 hover:text-gray-700 dark:hover:text-slate-300 transition-colors"
              >
                {importJson ? '✓ File loaded — click to replace' : 'Click to upload a .json file'}
              </button>
              <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={handleFileChange} />
              <textarea
                value={importJson}
                onChange={e => setImportJson(e.target.value)}
                placeholder="Or paste JSON here…"
                rows={16}
                className="px-3 py-2 text-xs font-mono border border-gray-200 dark:border-slate-700 rounded-md outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 resize-none bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 dark:placeholder-slate-500"
              />
            </div>
            {importError && <p className="text-xs text-red-500">{importError}</p>}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setImportOpen(false)} className="px-4 py-2 text-sm text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700 rounded-md hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                Cancel
              </button>
              <button onClick={handleImport} className="px-4 py-2 text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors">
                Load into editor
              </button>
            </div>
          </div>
        </div>
      )}

      {exportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-2xl mx-4 p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100">Export Workflow JSON</h2>
              <button onClick={() => setExportOpen(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 text-lg leading-none">×</button>
            </div>
            <div className="flex flex-col gap-2">
              <textarea
                value={exportJson}
                readOnly
                rows={20}
                className="px-3 py-2 text-xs font-mono border border-gray-200 dark:border-slate-700 rounded-md outline-none resize-none bg-slate-50 dark:bg-slate-800 text-gray-800 dark:text-slate-200"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setExportOpen(false)} className="px-4 py-2 text-sm text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700 rounded-md hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                Close
              </button>
              <button onClick={handleDownloadJson} className="px-4 py-2 text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors">
                Download JSON
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden relative"
        onDragEnter={onEditorDragEnter}
        onDragLeave={onEditorDragLeave}
        onDragOver={onEditorDragOver}
        onDrop={onEditorDrop}
      >
        <Sidebar stepsMeta={stepsMeta} />

        <div ref={reactFlowWrapper} className="flex-1 relative bg-slate-50 dark:bg-slate-950">
          <DropTargetContext.Provider value={dropTargetId}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onNodeDrag={onNodeDrag}
              onNodeDragStop={onNodeDragStop}
              onPaneClick={onPaneClick}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              nodeTypes={nodeTypes}
              defaultEdgeOptions={{ markerEnd: { type: MarkerType.ArrowClosed } }}
              fitView
            >
              <Controls />
              <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
            </ReactFlow>
          </DropTargetContext.Provider>

          {isDroppingJson && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-blue-500/10 border-2 border-dashed border-blue-400 rounded-lg m-2 pointer-events-none">
              <UploadIcon />
              <p className="mt-3 text-sm font-medium text-blue-500">Drop JSON to load workflow</p>
            </div>
          )}

        </div>

        {selectedNode && (
          <ConfigPanel
            node={selectedNode}
            stepsMeta={stepsMeta}
            nodes={nodes}
            edges={edges}
            contextVars={contextVars}
            onChange={onConfigChange}
            onCommentChange={onCommentChange}
            onDelete={onDeleteNode}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>

    </div>

    {infoOpen && (
      <WorkflowInfoModal
        workflow={workflow}
        mode="edit"
        name={workflowName}
        description={workflowDescription}
        onNameChange={setWorkflowName}
        onDescriptionChange={setWorkflowDescription}
        onClose={() => setInfoOpen(false)}
      />
    )}

    {testRunOpen && (
      <TestRunModal
        workflowJson={flowToWorkflowJson(nodes, edges)}
        workflowId={workflow?.id}
        workflowName={workflowName}
        onClose={() => setTestRunOpen(false)}
      />
    )}
    </>
  );
};

export default EditorInner;