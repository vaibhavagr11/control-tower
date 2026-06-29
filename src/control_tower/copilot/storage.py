"""SQLite-backed persistence for the copilot's memory.
ResolutionCopilot itself still keeps everything in plain dicts/lists at
runtime — this module is the durable layer underneath it. Load existing
state on startup, write through on every update, so a restart doesn't
wipe out what the copilot has learned.
"""
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "control_tower.db"

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def _init_db() -> None:
    """Create the tables if they don't already exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                gate_reason TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                agent_decision TEXT NOT NULL,
                agent_action TEXT NOT NULL,
                matched INTEGER NOT NULL,
                note TEXT NOT NULL
            )
        """)

def load_conversation_history() -> dict[str, list[BaseMessage]]:
    """Rebuild the per-ticket message lists from disk."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticket_id, role, content FROM conversation_history ORDER BY id"
        ).fetchall()
    history: dict[str, list[BaseMessage]]={}
    for ticket_id, role, content in rows:
        msg = HumanMessage(content=content) if role == "human" else AIMessage(content=content)
        history.setdefault(ticket_id, []).append(msg)
    return history

def load_customer_memory() -> dict[str, list[dict]]:
    """Rebuild the per-customer past-ticket records from disk."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT customer_id, ticket_id, issue_type, recommended_action, gate_reason "
            "FROM customer_memory ORDER BY id"
        ).fetchall()
    memory: dict[str, list[dict]] = {}
    for customer_id, ticket_id, issue_type, recommended_action, gate_reason in rows:
        memory.setdefault(customer_id, []).append({
            "ticket_id": ticket_id,
            "issue_type": issue_type,
            "recommended_action": recommended_action,
            "gate_reason": gate_reason,
        })
    return memory


def load_feedback_log() -> list[dict]:
    """Rebuild the flat feedback ledger from disk."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticket_id, recommended_action, agent_decision, agent_action, matched, note "
            "FROM feedback_log ORDER BY id"
        ).fetchall()
    return [
        {
            "ticket_id": r[0],
            "recommended_action": r[1],
            "agent_decision": r[2],
            "agent_action": r[3],
            "matched": bool(r[4]),
            "note": r[5],
        }
        for r in rows
    ]

def save_message(ticket_id: str, role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversation_history (ticket_id, role, content) VALUES (?, ?, ?)",
            (ticket_id, role, content),
        )

def save_customer_entry(customer_id: str, entry: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO customer_memory (customer_id, ticket_id, issue_type, recommended_action, gate_reason) "
            "VALUES (?, ?, ?, ?, ?)",
            (customer_id, entry["ticket_id"], entry["issue_type"], entry["recommended_action"], entry["gate_reason"]),
        )


def save_feedback_entry(entry: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO feedback_log (ticket_id, recommended_action, agent_decision, agent_action, matched, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                entry["ticket_id"],
                entry["recommended_action"],
                entry["agent_decision"],
                entry["agent_action"],
                int(entry["matched"]),
                entry["note"],
            ),
        )