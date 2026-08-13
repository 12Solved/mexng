from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class LogLevel(str, Enum):
  DEBUG = "DEBUG"
  INFO = "INFO"
  WARNING = "WARNING"
  ERROR = "ERROR"
  CRITICAL = "CRITICAL"

class RunState(str, Enum):
  success = "success"
  failed = "failed"
  skipped = "skipped"
  re_run = "re_run"
  running = "running"

class Attachment(BaseModel):
  id: int
  email_id: int
  filename: str
  content_type: str | None
  size: int | None
  storage_path: str | None
  created_at: datetime

  class Config:
    from_attributes = True

class WorkflowRunSummary(BaseModel):
  success: int
  failed: int
  skipped: int
  re_run: int

class Email(BaseModel):
  id: int
  message_id: str | None
  subject: str | None
  sender: str | None
  recipient: str | None
  date: datetime | None
  body: str | None
  html_body: str | None
  raw_headers: dict | None
  created_at: datetime
  run_summary: WorkflowRunSummary | None = None
  attachments: list[Attachment] = []

  class Config:
    from_attributes = True

class Log(BaseModel):
  id: int
  created_at: datetime

  level: LogLevel
  event_type: str

  message: str | None
  step: str | None

  email_id: int | None
  attachment_id: int | None
  run_id: int | None
  workflow_id: int | None

  class Config:
    from_attributes = True

class WorkflowRun(BaseModel):
  id: int
  workflow_id: int | None
  email_id: int | None
  state: RunState
  run_options: dict | None = None
  created_at: datetime
  parent_run_id: int | None = None
  workflow_name: str | None = None

  class Config:
    from_attributes = True

class RunOptions(BaseModel):
  run_options: dict = {}

class TestRunBody(BaseModel):
  email_id: int
  workflow_json: dict
  workflow_id: int | None = None

class TestRunResult(BaseModel):
  run_id: int | None
  state: RunState

class EmailSearchBody(BaseModel):
  query: dict | None = None
  workflow_id: int | None = None
  run_state: str | None = None

class WorkflowSchema(BaseModel):
  id: int
  name: str
  description: str | None = None
  workflow_json: dict
  enabled: bool
  created_at: datetime | None = None
  run_stats: WorkflowRunSummary | None = None

  class Config:
    from_attributes = True

class WorkflowCreateBody(BaseModel):
  name: str
  description: str | None = None
  workflow_json: dict

class WorkflowSearchBody(BaseModel):
  name: str | None = None



class CheckpointSchema(BaseModel):
  id: int
  name: str
  reference_timestamp: datetime
  normal_interval_hours: int
  late_interval_hours: int | None
  next_expected_at: datetime
  timezone: str
  last_seen_at: datetime | None
  last_successful: datetime | None
  last_missed: datetime | None
  status: str
  workflow_id: int | None
  created_at: datetime
  updated_at: datetime

  class Config:
    from_attributes = True

class RerunResponse(BaseModel):
    run: WorkflowRun
    already_queued: bool

