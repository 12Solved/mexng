export interface EmailResponseBody {
  items: Email[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface Email {
  id: number;
  message_id: string;
  subject: string;
  body: string;
  html_body: string | null;
  sender: string;
  recipient: string;
  date: Date;
  created_at: Date;
  raw_headers: EmailHeaders;
  attachments: Attachment[];
  run_summary: RunSummary
}

export interface RunSummary {
  success: number,
  failed: number,
  skipped: number,
  re_run: number,
}

export interface EmailHeaders {
  [key: string]: string;
}

export interface Attachment {
  id: number;
  email_id: number;
  filename: string;
  content_type: string | null;
  size: number | null;
  content: string | null;
  storage_path?: string | null;
  created_at: string;
  email: Email;
}