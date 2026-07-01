import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mailextractor.models import Log


class LogRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def add_log(self, log_data: dict):
        session = self.session_factory()
        try:
            log = Log(**log_data)
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            print("Logging failed:", e)
        finally:
            session.close()
