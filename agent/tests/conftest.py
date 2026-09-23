import os
import sys

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(AGENT_DIR, "scripts")
for path in (AGENT_DIR, TESTS_DIR, SCRIPTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.pop("JEV_API_KEY", None)
os.environ.pop("GROQ_API_KEY", None)
os.environ.pop("OPENROUTER_API_KEY", None)

import jev_client

jev_client._jev_dead = True
jev_client._client_failed = True