import json
import os
from datetime import datetime
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return database_url


def get_connection():
    return connect(get_database_url(), row_factory=dict_row)


def init_db():
    """Initialize PostgreSQL tables for lead storage."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id TEXT PRIMARY KEY,
                    search_query TEXT NOT NULL,
                    company_name TEXT,
                    domain TEXT,
                    founder_name TEXT,
                    founder_linkedin TEXT,
                    founder_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
                    email TEXT,
                    email_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
                    services JSONB NOT NULL DEFAULT '[]'::jsonb,
                    signals JSONB NOT NULL DEFAULT '[]'::jsonb,
                    source_url TEXT,
                    source_type TEXT,
                    extraction_timestamp TIMESTAMPTZ,
                    email_sequence JSONB NOT NULL DEFAULT '[]'::jsonb,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute("DROP INDEX IF EXISTS leads_source_type_domain_unique")
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS leads_domain_unique
                ON leads (domain)
                WHERE domain IS NOT NULL
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS leads_updated_at_idx
                ON leads (updated_at DESC)
                """
            )
        conn.commit()


def save_lead_to_db(state):
    """Upsert a LeadState model into PostgreSQL."""
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO leads (
                    lead_id, search_query, company_name, domain, founder_name,
                    founder_linkedin, founder_confidence, email, email_confidence,
                    services, signals, source_url, source_type, extraction_timestamp,
                    email_sequence, retry_count, status, updated_at
                ) VALUES (
                    %(lead_id)s, %(search_query)s, %(company_name)s, %(domain)s, %(founder_name)s,
                    %(founder_linkedin)s, %(founder_confidence)s, %(email)s, %(email_confidence)s,
                    %(services)s::jsonb, %(signals)s::jsonb, %(source_url)s, %(source_type)s, %(extraction_timestamp)s,
                    %(email_sequence)s::jsonb, %(retry_count)s, %(status)s, %(updated_at)s
                )
                ON CONFLICT (lead_id) DO UPDATE SET
                    search_query = EXCLUDED.search_query,
                    company_name = EXCLUDED.company_name,
                    domain = EXCLUDED.domain,
                    founder_name = EXCLUDED.founder_name,
                    founder_linkedin = EXCLUDED.founder_linkedin,
                    founder_confidence = EXCLUDED.founder_confidence,
                    email = EXCLUDED.email,
                    email_confidence = EXCLUDED.email_confidence,
                    services = EXCLUDED.services,
                    signals = EXCLUDED.signals,
                    source_url = EXCLUDED.source_url,
                    source_type = EXCLUDED.source_type,
                    extraction_timestamp = EXCLUDED.extraction_timestamp,
                    email_sequence = EXCLUDED.email_sequence,
                    retry_count = EXCLUDED.retry_count,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
                """,
                {
                    "lead_id": state.lead_id,
                    "search_query": state.search_query,
                    "company_name": state.company_name,
                    "domain": state.domain,
                    "founder_name": state.founder_name,
                    "founder_linkedin": state.founder_linkedin,
                    "founder_confidence": state.founder_confidence,
                    "email": state.email,
                    "email_confidence": state.email_confidence,
                    "services": json.dumps(state.services),
                    "signals": json.dumps(state.signals),
                    "source_url": state.source_url,
                    "source_type": state.source_type,
                    "extraction_timestamp": state.extraction_timestamp,
                    "email_sequence": json.dumps(state.email_sequence),
                    "retry_count": state.retry_count,
                    "status": state.status.value,
                    "updated_at": datetime.utcnow(),
                },
            )
        conn.commit()


def fetch_all_leads() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM leads ORDER BY updated_at DESC")
            rows = cursor.fetchall()

    leads: list[dict[str, Any]] = []
    for row in rows:
        lead = dict(row)
        lead["services"] = lead.get("services") or []
        lead["signals"] = lead.get("signals") or []
        lead["email_sequence"] = lead.get("email_sequence") or []
        leads.append(lead)
    return leads


def fetch_summary() -> dict[str, Any]:
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_leads,
                    COUNT(*) FILTER (WHERE status = 'SENT') AS sent_leads,
                    COUNT(*) FILTER (WHERE status = 'READY_TO_SEND') AS ready_to_send,
                    COUNT(*) FILTER (WHERE status = 'DEAD_LEAD') AS dead_leads,
                    COUNT(*) FILTER (WHERE status IN ('SEARCHED', 'CRAWLED', 'EXTRACTED', 'ENRICHED', 'VALIDATED', 'PERSONALIZED')) AS active_leads
                FROM leads
                """
            )
            stats = cursor.fetchone() or {}
            cursor.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM leads
                GROUP BY status
                ORDER BY count DESC, status ASC
                """
            )
            status_counts = cursor.fetchall()
    return {
        **stats,
        "status_counts": status_counts,
    }


def find_existing_lead(domain: str | None) -> dict[str, Any] | None:
    if not domain:
        return None
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM leads
                WHERE domain = %s
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (domain,),
            )
            return cursor.fetchone()
