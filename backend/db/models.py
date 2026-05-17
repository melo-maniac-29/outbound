import sqlite3
import json
from datetime import datetime

DB_PATH = "outbound_leads.db"

def init_db():
    """Initialize the SQLite database for storing structured lead records."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                lead_id TEXT PRIMARY KEY,
                search_query TEXT,
                company_name TEXT,
                domain TEXT,
                founder_name TEXT,
                founder_linkedin TEXT,
                founder_confidence REAL,
                email TEXT,
                email_confidence REAL,
                services TEXT, -- Stored as JSON
                signals TEXT, -- Stored as JSON
                source_url TEXT,
                source_type TEXT,
                extraction_timestamp TEXT,
                email_sequence TEXT, -- Stored as JSON
                retry_count INTEGER,
                status TEXT,
                updated_at TEXT
            )
        ''')
        conn.commit()

def save_lead_to_db(state):
    """Upsert a LeadState Pydantic model into the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (
                lead_id, search_query, company_name, domain, founder_name,
                founder_linkedin, founder_confidence, email, email_confidence,
                services, signals, source_url, source_type, extraction_timestamp,
                email_sequence, retry_count, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lead_id) DO UPDATE SET
                search_query=excluded.search_query,
                company_name=excluded.company_name,
                domain=excluded.domain,
                founder_name=excluded.founder_name,
                founder_linkedin=excluded.founder_linkedin,
                founder_confidence=excluded.founder_confidence,
                email=excluded.email,
                email_confidence=excluded.email_confidence,
                services=excluded.services,
                signals=excluded.signals,
                source_url=excluded.source_url,
                source_type=excluded.source_type,
                extraction_timestamp=excluded.extraction_timestamp,
                email_sequence=excluded.email_sequence,
                retry_count=excluded.retry_count,
                status=excluded.status,
                updated_at=excluded.updated_at
        ''', (
            state.lead_id,
            state.search_query,
            state.company_name,
            state.domain,
            state.founder_name,
            state.founder_linkedin,
            state.founder_confidence,
            state.email,
            state.email_confidence,
            json.dumps(state.services),
            json.dumps(state.signals),
            state.source_url,
            state.source_type,
            state.extraction_timestamp.isoformat() if state.extraction_timestamp else None,
            json.dumps(state.email_sequence),
            state.retry_count,
            state.status.value,
            datetime.now().isoformat()
        ))
        conn.commit()
