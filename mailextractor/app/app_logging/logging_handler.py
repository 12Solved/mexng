import logging

from mailextractor.models import LogLevel

from .log_repository import LogRepository


class LoggingHandler(logging.Handler):
  def __init__(self, repo: LogRepository):
    super().__init__()
    self.repo = repo

  def emit(self, record):
    try:
      log_data = {
        "level": LogLevel(record.levelname),
        "event_type": getattr(record, "event_type", "UNKNOWN"),
        "message": record.getMessage(),
        "step": getattr(record, "step", None),
        "email_id": getattr(record, "email_id", None),
        "workflow_id": getattr(record, "workflow_id",None),
        "run_id": getattr(record, "run_id", None),
        "attachment_id": getattr(record, "attachment_id", None),
      }
      self.repo.add_log(log_data)

    except Exception as e:
      print("Handler error:", e)
