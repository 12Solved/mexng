import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["EMAIL_PROVIDER"] = "glob"
os.environ["GLOB_PATTERNS"] = ",".join(sys.argv[1:])
os.environ["CHECKPOINT_PATH"] = "read_email_checkpoint.txt"
from mailextractor.app.poller.poller import main

main()
