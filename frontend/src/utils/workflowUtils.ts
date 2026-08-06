import { getOutgoers, MarkerType, type Edge } from '@xyflow/react';
import type { AnyFlowNode, ForeachStep, StepMeta, WorkflowJson, WorkflowStep } from '../types/workflowEditor';

/** @deprecated Use Edge from '@xyflow/react' directly. */
export type WorkflowFlowEdge = Edge;

let _idCounter = 1;
export const uid = (): string => `node-${_idCounter++}`;

export const FOREACH_HEADER_H = 45;
export const FOREACH_PADDING_B = 30;
export const FOREACH_WIDTH = 340;
const FOREACH_TOP_PAD = 16;
const FOREACH_CHILD_MARGIN_X = 20;
const FOREACH_CHILD_GAP_Y = 20;
const DEFAULT_STEP_WIDTH = 260;
const DEFAULT_STEP_HEIGHT = 80;
const TOP_LEVEL_GAP_Y = 40;
const Y_STEP = 130;

interface FlowGraph {
  nodes: AnyFlowNode[];
  edges: WorkflowFlowEdge[];
}

/**
 * Sizes every for-each container to fit its children and stacks those children into a clean
 * vertical column, recursing depth-first so a nested for-each's own size is finalized before
 * its ancestor sizes itself around it. Order within a container is taken from each child's
 * current position.y, so dropping a step at a given height reorders it there. Finally re-stacks
 * the top-level chain so a for-each that grew or shrank doesn't overlap whatever comes after it.
 */
export const relayoutForeachTree = (allNodes: AnyFlowNode[]): AnyFlowNode[] => {
  const byId = new Map(allNodes.map((n) => [n.id, { ...n }]));
  const childrenOf = new Map<string, string[]>();
  allNodes.forEach((n) => {
    if (n.parentId) {
      const arr = childrenOf.get(n.parentId) ?? [];
      arr.push(n.id);
      childrenOf.set(n.parentId, arr);
    }
  });

  const layoutForeach = (id: string): void => {
    const node = byId.get(id);
    if (!node || node.type !== 'foreach') return;

    const childIds = [...(childrenOf.get(id) ?? [])].sort(
      (a, b) => byId.get(a)!.position.y - byId.get(b)!.position.y,
    );
    childIds.forEach(layoutForeach); // nested for-each children finalize their size first

    let y = FOREACH_HEADER_H + FOREACH_TOP_PAD;
    let maxChildWidth = 0;
    childIds.forEach((cid) => {
      const child = byId.get(cid)!;
      // A nested for-each's width/height was just computed above (this same pass) — that's
      // authoritative and must win over `.measured`, which is react-flow's DOM measurement
      // from the *previous* render and would otherwise make the parent size itself around a
      // stale, one-cycle-behind value, so growth only crept up a single level at a time.
      // Plain step nodes aren't sized by us at all, so their real rendered `.measured` size
      // (once available) is the best estimate for them.
      const w = child.type === 'foreach'
        ? (child.width ?? (child.style?.width as number | undefined) ?? DEFAULT_STEP_WIDTH)
        : (child.measured?.width ?? child.width ?? (child.style?.width as number | undefined) ?? DEFAULT_STEP_WIDTH);
      const h = child.type === 'foreach'
        ? (child.height ?? (child.style?.height as number | undefined) ?? DEFAULT_STEP_HEIGHT)
        : (child.measured?.height ?? child.height ?? (child.style?.height as number | undefined) ?? DEFAULT_STEP_HEIGHT);
      byId.set(cid, { ...child, position: { x: FOREACH_CHILD_MARGIN_X, y } });
      y += h + FOREACH_CHILD_GAP_Y;
      maxChildWidth = Math.max(maxChildWidth, w);
    });

    const height = childIds.length
      ? y - FOREACH_CHILD_GAP_Y + FOREACH_PADDING_B
      : FOREACH_HEADER_H + DEFAULT_STEP_HEIGHT + FOREACH_PADDING_B;
    const width = Math.max(FOREACH_WIDTH, maxChildWidth + FOREACH_CHILD_MARGIN_X * 2);

    byId.set(id, { ...node, height, width, style: { ...node.style, height, width } });
  };

  allNodes.forEach((n) => layoutForeach(n.id));

  const topLevelIds = allNodes
    .filter((n) => !n.parentId)
    .map((n) => n.id)
    .sort((a, b) => byId.get(a)!.position.y - byId.get(b)!.position.y);

  let y = topLevelIds.length ? byId.get(topLevelIds[0])!.position.y : 0;
  topLevelIds.forEach((id) => {
    const node = byId.get(id)!;
    byId.set(id, { ...node, position: { ...node.position, y } });
    // Same staleness concern as above: a top-level for-each's height was just finalized in
    // this pass and must win over its stale pre-pass `.measured` value.
    const h = node.type === 'foreach'
      ? (node.height ?? (node.style?.height as number | undefined) ?? DEFAULT_STEP_HEIGHT)
      : (node.measured?.height ?? node.height ?? (node.style?.height as number | undefined) ?? DEFAULT_STEP_HEIGHT);
    y += h + TOP_LEVEL_GAP_Y;
  });

  return allNodes.map((n) => byId.get(n.id)!);
};

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
        ...(parentId ? { parentId } : {}),
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
        // Rough placeholder just to space this pass's siblings — relayoutForeachTree below
        // sizes every for-each to its actual (possibly nested) contents afterward.
        const roughHeight =
          FOREACH_HEADER_H + FOREACH_TOP_PAD +
          Math.max(childSteps.length, 1) * (DEFAULT_STEP_HEIGHT + FOREACH_CHILD_GAP_Y) +
          FOREACH_PADDING_B;
        node.width  = FOREACH_WIDTH;
        node.height = roughHeight;
        node.style  = { width: FOREACH_WIDTH, height: roughHeight };
        node.data   = { ...node.data, config: { collection: foreachStep.over ?? '' } };
        if (childSteps.length) processSteps(childSteps, id, FOREACH_HEADER_H + FOREACH_TOP_PAD, FOREACH_CHILD_MARGIN_X);
      }

      localY += isForeach ? ((node.height ?? 200) + 40) : Y_STEP;
    });
  };

  processSteps(workflowJson.steps, null, 60, 300);
  return { nodes: relayoutForeachTree(nodes), edges };
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