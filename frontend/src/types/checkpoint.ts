export type CheckpointStatus = 'ok' | 'missed' | 'never_seen';

export interface Checkpoint {
  id: number;
  name: string;
  reference_timestamp: string;
  normal_interval_hours: number;
  late_interval_hours: number | null;
  next_expected_at: string;
  timezone: string;
  last_seen_at: string | null;
  last_successful: string | null;
  last_missed: string | null;
  status: CheckpointStatus;
  workflow_id: number | null;
  created_at: string;
  updated_at: string;
}
