import type { LogLevel } from './log';

export interface AlertRule {
  id: number;
  user_id: number;
  event_type: string | null;
  workflow_id: number | null;
  checkpoint_id: number | null;
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
export type AlertRuleBody = Partial<Pick<AlertRule, 'event_type' | 'workflow_id' | 'checkpoint_id' | 'min_level' | 'enabled'>>;
