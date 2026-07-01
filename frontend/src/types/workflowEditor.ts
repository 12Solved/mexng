import type { Node, Edge } from '@xyflow/react';

export interface CategoryColors {
  border: string;
  bg: string;
  text: string;
}

export const FALLBACK_COLORS: CategoryColors = { border: '#6b7280', bg: '#f9fafb', text: '#374151' };

export interface ConfigSchemaField {
  type: string;
  required?: boolean;
  label: string;
  placeholder?: string;
  description?: string;
  default?: string;
  options?: string[];
  template_vars?: Record<string, string>;
}

export interface StepMeta {
  type: string;
  label: string;
  docstring?: string;
  category: string;
  colors: CategoryColors;
  args_in: Record<string, string>;
  args_out: Record<string, string>;
  config_schema: Record<string, ConfigSchemaField>;
}

export interface WorkflowStep {
  type: string;
  config?: Record<string, unknown>;
  user_comment?: string;
}

export interface ForeachStep {
  type: 'foreach';
  over: string;
  steps: WorkflowStep[];
  config?: Record<string, unknown>;
  user_comment?: string;
}

export interface WorkflowJson {
  steps: (WorkflowStep | ForeachStep)[];
}

export interface StepNodeData extends Record<string, unknown> {
  stepType: string;
  config: Record<string, string>;
  meta?: StepMeta;
  user_comment?: string;
}

export type StepFlowNode = Node<StepNodeData, 'stepNode'>;
export type ForeachFlowNode = Node<StepNodeData, 'foreach'>;
export type AnyFlowNode = StepFlowNode | ForeachFlowNode;
export type AnyFlowEdge = Edge;

export interface ContextVars {
  global: Record<string, string>;
  foreach: Record<string, string>;
}
