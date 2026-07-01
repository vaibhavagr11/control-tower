import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

# Register our custom Pydantic types so LangGraph can safely deserialize
# them from msgpack checkpoints. Without this, LangGraph will block
# deserialization of unregistered types in a future version.
os.environ.setdefault(
    "LANGGRAPH_ALLOW_MSGPACK_MODULES",
    "control_tower.schemas",
)

# Shared checkpointer instance — persists graph state to the same SQLite
# database used by the rest of the app. check_same_thread=False is required
# for use outside of a context manager in a multi-call application.
_conn = sqlite3.connect("data/control_tower.db", check_same_thread=False)
checkpointer = SqliteSaver(_conn)

