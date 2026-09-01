import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["EMAIL_PROVIDER"] = "glob"
os.environ["GLOB_PATTERNS"] = ",".join(sys.argv[1:])
os.environ["CHECKPOINT_PATH"] = ""  # no checkpoint — always (re-)insert the given files
sys.argv = sys.argv[:1]  # consumed above as file patterns, not poller.main()'s own --loop/--interval flags
from mailextractor.app.poller.poller import main

main()
