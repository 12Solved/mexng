import { getOutgoers, MarkerType, type Edge } from '@xyflow/react';
import type { AnyFlowNode, ForeachStep, StepMeta, WorkflowJson, WorkflowStep } from '../types/workflowEditor';

/** @deprecated Use Edge from '@xyflow/react' directly. */
export type WorkflowFlowEdge = Edge;

let _idCounter = 1;
export const uid = (): string => `node-${_idCounter++}`;

export const FOREACH_HEADER_H = 45;
export const FOREACH_CHILD_GAP = 110;
export const FOREACH_PADDING_B = 30;
export const FOREACH_WIDTH = 340;
const Y_STEP = 130;

interface FlowGraph {
  nodes: AnyFlowNode[];
  edges: WorkflowFlowEdge[];
}

export const workflowJsonToFlow = (
  workflowJson: WorkflowJson | null | undefined,
  stepsMeta: StepMeta[],
): FlowGraph => {
  const nodes: AnyFlowNode[] = [];
  const edges: WorkflowFlowEdge[] = [];
  if (!workflowJson?.steps) return { nodes, edges };

  const metaByType = Object.fromEntries(stepsMeta.map(s => [s.type, s]));

  const processSteps = (
    steps: WorkflowStep[],
    parentId: string | null = null,
    startY = 60,
    startX = 300,
  ): void => {
    let localY  = startY;
    let prevId: string | null = null;

    steps.forEach((step) => {
      const id        = uid();
      const meta      = metaByType[step.type] as StepMeta | undefined;
      const isForeach = step.type === 'foreach';

      const node: AnyFlowNode = {
        id,
        type: isForeach ? 'foreach' : 'stepNode',
        position: { x: parentId ? 30 : startX, y: localY },
        data: {
          stepType: step.type,
          config: { ...(step.config as Record<string, string> || {}) },
          meta,
          user_comment: step.user_comment ?? '',
        },
        ...(parentId ? { parentId, extent: 'parent' as const } : {}),
      };

      nodes.push(node);

      if (prevId) {
        edges.push({
          id: `e-${prevId}-${id}`,
          source: prevId,
          target: id,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });
      }
      prevId = id;

      if (isForeach) {
        const foreachStep = step as ForeachStep;
        const childSteps = foreachStep.steps ?? [];
        const containerHeight =
          FOREACH_HEADER_H + (childSteps.length || 1) * FOREACH_CHILD_GAP + FOREACH_PADDING_B;
        node.width  = FOREACH_WIDTH;
        node.height = containerHeight;
        node.style  = { width: FOREACH_WIDTH, height: containerHeight };
        node.data   = { ...node.data, config: { collection: foreachStep.over ?? '' } };
        if (childSteps.length) processSteps(childSteps, id, FOREACH_HEADER_H + 16, 20);
      }

      localY += isForeach ? ((node.height ?? 200) + 40) : Y_STEP;
    });
  };

  processSteps(workflowJson.steps, null, 60, 300);
  return { nodes, edges };
};

export const getContextAtNode = (
  nodeId: string,
  nodes: AnyFlowNode[],
  edges: WorkflowFlowEdge[],
): Record<string, string> => {
  const context: Record<string, string> = {};
  const visited = new Set<string>();

  const walk = (id: string) => {
    if (visited.has(id)) return;
    visited.add(id);

    edges.filter(e => e.target === id).forEach(e => walk(e.source));

    const node = nodes.find(n => n.id === id);
    const argsOut = node?.data.meta?.args_out ?? {};
    Object.assign(context, argsOut);
  };

  edges.filter(e => e.target === nodeId).forEach(e => walk(e.source));

  return context;
};

export const getCollectionsAtNode = (
  nodeId: string,
  nodes: AnyFlowNode[],
  edges: WorkflowFlowEdge[],
): string[] => {
  const context = getContextAtNode(nodeId, nodes, edges);
  return Object.entries(context)
    .filter(([, type]) => type.endsWith('[]'))
    .map(([key]) => key);
};

export const flowToWorkflowJson = (nodes: AnyFlowNode[], edges: WorkflowFlowEdge[]): WorkflowJson => {
  const childrenByParent: Record<string, AnyFlowNode[]> = {};
  nodes.filter(n => n.parentId).forEach(n => {
    const pid = n.parentId!;
    if (!childrenByParent[pid]) childrenByParent[pid] = [];
    childrenByParent[pid].push(n);
  });
  Object.values(childrenByParent).forEach(arr =>
    arr.sort((a, b) => a.position.y - b.position.y),
  );

  const nodeToStep = (node: AnyFlowNode): WorkflowStep | ForeachStep => {
    if (node.type === 'foreach') {
      const foreachStep: ForeachStep = {
        type: 'foreach',
        over: (node.data.config as Record<string, string>)['collection'] ?? '',
        steps: (childrenByParent[node.id] ?? []).map(nodeToStep) as WorkflowStep[],
        ...(node.data.user_comment ? { user_comment: node.data.user_comment } : {}),
      };
      return foreachStep;
    }
    const step: WorkflowStep = { type: node.data.stepType };
    const config: Record<string, unknown> = { ...(node.data.config || {}) };
    if (Object.keys(config).length > 0) step.config = config;
    if (node.data.user_comment) step.user_comment = node.data.user_comment;
    return step;
  };

  const visited = new Set<string>();
  const steps: WorkflowStep[] = [];

  const walk = (node: AnyFlowNode): void => {
    if (visited.has(node.id) || node.parentId) return;
    visited.add(node.id);
    steps.push(nodeToStep(node));
    getOutgoers(node, nodes, edges).forEach(walk);
  };

  const topLevel = nodes.filter(n => !n.parentId);
  const hasIncoming = new Set(edges.map(e => e.target));
  topLevel.filter(n => !hasIncoming.has(n.id)).forEach(walk);

  return { steps };
};

const isProvidedConfigValue = (value: unknown): boolean =>
  String(value ?? '').trim().length > 0;


const collectTopLevelConnectivityErrors = (nodes: AnyFlowNode[], edges: WorkflowFlowEdge[]): string[] => {
  const errs: string[] = [];
  const topLevel = nodes.filter(n => !n.parentId);
  if (topLevel.length === 0) return errs;

  const hasIncoming = new Set(edges.map(e => String(e.target)));
  const roots = topLevel.filter(n => !hasIncoming.has(n.id));

  if (roots.length === 0) {
    errs.push(
      'No workflow start — every step has an incoming connection (cycle or missing head). Break the cycle or remove an incoming link on the step that should run first.',
    );
    return errs;
  }

  if (roots.length > 1) {
    errs.push(
      'Disconnected flows — only one step may start without an incoming link. Reconnect your steps into a single linear flow.',
    );
    return errs;
  }

  const rootId = roots[0].id;
  const reachable = new Set<string>();
  const stack = [rootId];
  while (stack.length) {
    const id = stack.pop()!;
    if (reachable.has(id)) continue;
    reachable.add(id);
    edges.forEach(e => {
      if (String(e.source) === id) stack.push(String(e.target));
    });
  }

  const unreachableTop = topLevel.filter(n => !reachable.has(n.id));
  if (unreachableTop.length > 0) {
    errs.push(
      'Some steps are not reachable from the start — restore missing connections or remove unused blocks.',
    );
  }

  return errs;
};

/**
 * Validation before save/export: graph connectivity, foreach bodies, required config fields.
 */
export const getWorkflowValidationErrors = (
  nodes: AnyFlowNode[],
  edges: WorkflowFlowEdge[],
  stepsMeta: StepMeta[],
): string[] => {
  const errors: string[] = [];
  const metaByType = Object.fromEntries(stepsMeta.map(s => [s.type, s]));

  if (nodes.length === 0) {
    errors.push('Add at least one step to the workflow.');
    return errors;
  }

  const connectivityErrs = collectTopLevelConnectivityErrors(nodes, edges);
  errors.push(...connectivityErrs);

  const json = flowToWorkflowJson(nodes, edges);
  if (json.steps.length === 0 && connectivityErrs.length === 0) {
    errors.push('Serialized workflow is empty — check connections and try again.');
  }

  nodes.forEach((n: AnyFlowNode) => {
    if (n.type !== 'foreach') return;
    const inner = nodes.filter(c => c.parentId === n.id);
    if (inner.length === 0) {
      errors.push('Each “For each” block must contain at least one step.');
    }
  });

  nodes.forEach((n: AnyFlowNode) => {
    const meta = metaByType[n.data.stepType];
    if (!meta) return;
    const schema = meta.config_schema ?? {};
    const config = n.data.config ?? {};
    const stepTitle = meta.label ?? n.data.stepType;
    Object.entries(schema).forEach(([key, field]) => {
      if (!field.required) return;
      const raw = config[key] ?? field.default;
      if (!isProvidedConfigValue(raw)) {
        errors.push(`${stepTitle}: “${field.label}” is required.`);
      }
    });
  });

  return errors;
};