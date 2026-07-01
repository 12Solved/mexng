import logging

from sqlalchemy.orm import sessionmaker

from .log_repository import LogRepository
from .logging_handler import LoggingHandler


def setup_logging(engine):
  SessionLocal = sessionmaker(bind=engine)
  repo = LogRepository(SessionLocal)

  db_handler = LoggingHandler(repo)

  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)

  formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
  )

  if not any(isinstance(h, LoggingHandler) for h in logger.handlers):
    logger.addHandler(db_handler)

  if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

  if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    file_handler = logging.FileHandler("app.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

  return logger
