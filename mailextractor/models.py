import enum
from sqlalchemy import Column, Integer, Text, TIMESTAMP, Enum, ForeignKey, String, JSON, Boolean, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, BYTEA
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
Base = declarative_base()
import enum

class RunState(enum.Enum):
    success = "success"
    failed = "failed"
    skipped = "skipped"
    re_run = "re_run"
    running = "running"


class LogLevel(enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        Index('idx_email_message_id', 'message_id'),
    )

    id = Column(Integer, primary_key=True)
    message_id = Column(Text)
    subject = Column(Text)
    sender = Column(Text)
    recipient = Column(Text)
    date = Column(TIMESTAMP)
    body = Column(Text)
    html_body = Column(Text, nullable=True)
    raw_headers = Column(JSONB)
    created_at = Column(TIMESTAMP, server_default=func.now())
    attachments = relationship(
        "Attachment",
        back_populates="email",
        cascade="all, delete-orphan"
    )
    runs = relationship("WorkflowRun", back_populates="email")

    def __repr__(self):
        return (
            f"Email(id={self.id!r}, subject={self.subject!r}, "
            f"sender={self.sender!r}, date={self.date!r}, "
            f"attachments={len(self.attachments)})"
        )

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    filename = Column(Text, nullable=False)
    content_type = Column(Text)
    size = Column(Integer)
    content = Column(BYTEA)
    storage_path = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    email = relationship("Email", back_populates="attachments")

class WorkflowModel(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    workflow_json = Column(JSONB, nullable=False)
    enabled = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP, server_default=func.now())
    runs = relationship("WorkflowRun", back_populates="workflow", passive_deletes=True)

class WorkflowRun(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="SET NULL"), nullable=True)
    state = Column(Enum(RunState, name="run_state"), nullable=False)
    run_options = Column(JSONB, nullable=True, server_default="{}")
    created_at = Column(TIMESTAMP, server_default=func.now())
    parent_run_id = Column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)

    workflow = relationship("WorkflowModel", back_populates="runs")
    email = relationship("Email", back_populates="runs")
    parent_run = relationship("WorkflowRun", remote_side="WorkflowRun.id", foreign_keys="WorkflowRun.parent_run_id")

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    level = Column(Enum(LogLevel, name='log_level'), nullable=False)
    event_type = Column(Text, nullable=False)

    message = Column(Text)
    step = Column(Text)

    email_id = Column(Integer, ForeignKey("emails.id", ondelete="SET NULL"))
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="SET NULL"))
    attachment_id = Column(Integer, ForeignKey("attachments.id", ondelete="SET NULL"))
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    run = relationship("WorkflowRun")
    email = relationship("Email")
    attachment = relationship("Attachment")


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    __table_args__ = (
        CheckConstraint("status IN ('ok', 'missed', 'never_seen')", name='checkpoints_status_check'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    reference_timestamp = Column(TIMESTAMP, nullable=False)
    normal_interval_hours = Column(Integer, nullable=False)
    late_interval_hours = Column(Integer, nullable=True)
    next_expected_at = Column(TIMESTAMP, nullable=False)
    timezone = Column(Text, nullable=False, server_default="UTC")
    last_seen_at = Column(TIMESTAMP, nullable=True)
    last_successful = Column(TIMESTAMP, nullable=True)
    last_missed = Column(TIMESTAMP, nullable=True)
    status = Column(String, nullable=False, server_default="never_seen")
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
