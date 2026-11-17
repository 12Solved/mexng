import type { LogLevel } from './log';

export interface AlertRule {
  id: number;
  user_id: number;
  event_type: string | null;
  workflow_id: number | null;
  checkpoint_id: number | null;
  // Regex alternatives to the exact filters above; a rule sets one or the other per filter.
  event_type_pattern: string | null;
  workflow_name_pattern: string | null;
  checkpoint_name_pattern: string | null;
  patterns_case_sensitive: boolean;
  min_level: LogLevel;
  enabled: boolean;
  created_at: string;
}

export interface AlertRuleResponseBody {
  items: AlertRule[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// null filters mean "any". On update, omitted fields are left unchanged.
export type AlertRuleBody = Partial<Pick<AlertRule,
  | 'event_type' | 'workflow_id' | 'checkpoint_id'
  | 'event_type_pattern' | 'workflow_name_pattern' | 'checkpoint_name_pattern' | 'patterns_case_sensitive'
  | 'min_level' | 'enabled'>>;
