"""SQLite queue. Claims and idempotent submissions are atomic."""

from datetime import datetime, timezone
import json
import sqlite3
import uuid

from qcompass.paths import project_root


def now():
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, root=None):
        self.root = root or project_root()
        folder = self.root / "artifacts"
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / "jobs.sqlite"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, token TEXT UNIQUE, config TEXT NOT NULL,
                    status TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL,
                    cancel_requested INTEGER DEFAULT 0, result TEXT, error TEXT);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                    time TEXT NOT NULL, message TEXT NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def submit(self, config, token=None):
        job_id = uuid.uuid4().hex
        token = token or job_id
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO jobs(id,token,config,status,created,updated) VALUES(?,?,?,'queued',?,?)",
                (job_id, token, json.dumps(config, sort_keys=True), now(), now()),
            )
            return db.execute("SELECT id FROM jobs WHERE token=?", (token,)).fetchone()[0]

    @staticmethod
    def decode(row):
        if row is None:
            return None
        value = dict(row)
        value["config"] = json.loads(value["config"])
        return value

    def get(self, job_id):
        with self.connect() as db:
            return self.decode(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def list(self):
        with self.connect() as db:
            return [self.decode(row) for row in db.execute("SELECT * FROM jobs ORDER BY created DESC")]

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():
                return None
            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE jobs SET status='running', updated=? WHERE id=?", (now(), row["id"]))
                result = self.decode(row)
                result["status"] = "running"
                return result
        return None

    def event(self, job_id, message):
        with self.connect() as db:
            db.execute("INSERT INTO events(job_id,time,message) VALUES(?,?,?)", (job_id, now(), str(message)))
            db.execute("UPDATE jobs SET updated=? WHERE id=?", (now(), job_id))

    def events(self, job_id):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM events WHERE job_id=? ORDER BY id", (job_id,))]

    def cancel(self, job_id):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET cancel_requested=1, status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END, updated=? WHERE id=?",
                (now(), job_id),
            )

    def cancelled(self, job_id):
        job = self.get(job_id)
        return bool(job and job["cancel_requested"])

    def finish(self, job_id, status, result=None, error=None):
        if status not in {"completed", "failed", "cancelled", "interrupted"}:
            raise ValueError("Invalid terminal status")
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status=?,result=?,error=?,updated=? WHERE id=?",
                (status, result, error, now(), job_id),
            )

    def recover_interrupted(self):
        # Called only by the exclusive worker-lock owner, never by a browser refresh.
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET status='interrupted', error='Worker exited before completion; restart explicitly',updated=? WHERE status='running'",
                (now(),),
            )
