"""Main loop: poll -> process -> checkpoint check, every --interval seconds."""
import argparse
import logging
import signal
from datetime import datetime
import sys
import os

from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mailextractor.app.config import config
from mailextractor.app.poller.poller import poll
from mailextractor.app.processor.processor import process
from scripts.check_checkpoints import check_once

logger = logging.getLogger(__name__)

def cycle():
    poll(config)
    process(config)
    check_once()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=300, help="Seconds between cycles")
    args = parser.parse_args()

    scheduler = BlockingScheduler()
    scheduler.add_job(cycle, "interval", seconds=args.interval, max_instances=1, coalesce=True, next_run_time=datetime.now())

    def shutdown(signum, frame):
        logger.info("Shutting down main loop", extra={"event_type": "MAIN_LOOP_SHUTDOWN"})
        scheduler.shutdown(wait=True)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    logger.info(f"Main loop started (interval: {args.interval}s)", extra={"event_type": "MAIN_LOOP_STARTED"})

    scheduler.start()
    
if __name__ == "__main__":
    main()