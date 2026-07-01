import type { Attachment, Email } from "./email";

export interface LogResponseBody {
  items: Log[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export type LogLevel =
  | "DEBUG"
  | "INFO"
  | "WARNING"
  | "ERROR"
  | "CRITICAL";

export interface Log {
  id: number;
  created_at: string;
  level: LogLevel;
  event_type: string;
  message?: string | null;
  step?: string | null;
  email_id?: number | null;
  attachment_id?: number | null;
  run_id?: number | null;
  workflow_id?: number | null;
  email?: Email | null;
  attachment?: Attachment | null;
}