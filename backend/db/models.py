import json
import os
from datetime import datetime
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


DEFAULT_DRAFT_SYSTEM_PROMPT = """You are an expert sales representative writing cold outreach emails.
Your goal is to write a concise, peer-to-peer cold email based on extracted signals.

Constraints:
- Under 100 words.
- No generic openings (e.g., "Hope this finds you well").
- Tone: Peer-to-peer, confident, direct.
- Must reference the specific signal extracted.

Variables available:
- {first_name}: The founder's first name
- {company}: The target company name
- {signal}: The recent signal extracted from their site
- {product}: The product/service we are offering
- {sender}: The sender's name"""


def utcnow() -> datetime:
    return datetime.utcnow()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return database_url


_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(get_database_url(), min_size=2, max_size=20, kwargs={"row_factory": dict_row})
    return _pool


def get_connection():
    return get_pool().connection()


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS search_runs (
                    run_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    requested_companies INTEGER NOT NULL DEFAULT 5,
                    discovered_companies INTEGER NOT NULL DEFAULT 0,
                    processed_companies INTEGER NOT NULL DEFAULT 0,
                    source_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    stop_requested BOOLEAN NOT NULL DEFAULT FALSE,
                    stopped_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id TEXT PRIMARY KEY,
                    run_id TEXT REFERENCES search_runs(run_id) ON DELETE SET NULL,
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
                    company_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
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
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS run_id TEXT")
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS services JSONB NOT NULL DEFAULT '[]'::jsonb")
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS signals JSONB NOT NULL DEFAULT '[]'::jsonb")
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS company_profile JSONB NOT NULL DEFAULT '{}'::jsonb")
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_sequence JSONB NOT NULL DEFAULT '[]'::jsonb")
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0")
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS source_type TEXT")
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS extraction_timestamp TIMESTAMPTZ")
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'leads_run_id_fkey'
                    ) THEN
                        ALTER TABLE leads
                        ADD CONSTRAINT leads_run_id_fkey
                        FOREIGN KEY (run_id) REFERENCES search_runs(run_id) ON DELETE SET NULL;
                    END IF;
                END $$;
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
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS leads_run_id_idx
                ON leads (run_id)
                """
            )
            cursor.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('draft_system_prompt', %s::jsonb, NOW())
                ON CONFLICT (key) DO NOTHING
                """,
                (json.dumps({"text": DEFAULT_DRAFT_SYSTEM_PROMPT}),),
            )
            cursor.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('search_dedupe_across_db', %s::jsonb, NOW())
                ON CONFLICT (key) DO NOTHING
                """,
                (json.dumps({"text": "true"}),),
            )
            cursor.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('search_bucket_rounds', %s::jsonb, NOW())
                ON CONFLICT (key) DO NOTHING
                """,
                (json.dumps({"text": "6"}),),
            )
            cursor.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('search_variant_limit', %s::jsonb, NOW())
                ON CONFLICT (key) DO NOTHING
                """,
                (json.dumps({"text": "4"}),),
            )
            cursor.execute("ALTER TABLE search_runs ADD COLUMN IF NOT EXISTS stop_requested BOOLEAN NOT NULL DEFAULT FALSE")
            cursor.execute("ALTER TABLE search_runs ADD COLUMN IF NOT EXISTS stopped_at TIMESTAMPTZ")
        conn.commit()


def save_lead_to_db(state):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO leads (
                    lead_id, run_id, search_query, company_name, domain, founder_name,
                    founder_linkedin, founder_confidence, email, email_confidence,
                    services, signals, company_profile, source_url, source_type, extraction_timestamp,
                    email_sequence, retry_count, status, updated_at
                ) VALUES (
                    %(lead_id)s, %(run_id)s, %(search_query)s, %(company_name)s, %(domain)s, %(founder_name)s,
                    %(founder_linkedin)s, %(founder_confidence)s, %(email)s, %(email_confidence)s,
                    %(services)s::jsonb, %(signals)s::jsonb, %(company_profile)s::jsonb, %(source_url)s, %(source_type)s, %(extraction_timestamp)s,
                    %(email_sequence)s::jsonb, %(retry_count)s, %(status)s, %(updated_at)s
                )
                ON CONFLICT (lead_id) DO UPDATE SET
                    run_id = EXCLUDED.run_id,
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
                    company_profile = EXCLUDED.company_profile,
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
                    "run_id": state.run_id,
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
                    "company_profile": json.dumps(state.company_profile),
                    "source_url": state.source_url,
                    "source_type": state.source_type,
                    "extraction_timestamp": state.extraction_timestamp,
                    "email_sequence": json.dumps(state.email_sequence),
                    "retry_count": state.retry_count,
                    "status": state.status.value,
                    "updated_at": utcnow(),
                },
            )
        conn.commit()
    if state.run_id:
        touch_run(state.run_id)


def create_run(run_id: str, query: str, requested_companies: int, source_type: str) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "query": query,
        "requested_companies": requested_companies,
        "source_type": source_type,
        "status": "RUNNING",
    }
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO search_runs (
                    run_id, query, requested_companies, source_type, status, stop_requested, created_at, updated_at
                ) VALUES (
                    %(run_id)s, %(query)s, %(requested_companies)s, %(source_type)s, %(status)s, FALSE, NOW(), NOW()
                )
                RETURNING *
                """,
                payload,
            )
            row = cursor.fetchone()
        conn.commit()
    return row


def update_run_counts(run_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE search_runs r
                SET
                    discovered_companies = COALESCE(sub.count_all, 0),
                    processed_companies = COALESCE(sub.count_processed, 0),
                    updated_at = NOW()
                FROM (
                    SELECT
                        COUNT(*) AS count_all,
                        COUNT(*) FILTER (
                            WHERE status IN ('READY_TO_SEND', 'DEAD_LEAD', 'RETRY_PENDING')
                        ) AS count_processed
                    FROM leads
                    WHERE run_id = %s
                ) sub
                WHERE r.run_id = %s
                """,
                (run_id, run_id),
            )
        conn.commit()


def finalize_run(run_id: str, status: str, error: str | None = None):
    update_run_counts(run_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if status == "STOPPED":
                cursor.execute(
                    """
                    UPDATE search_runs
                    SET status = %s, error = %s, stop_requested = TRUE, stopped_at = COALESCE(stopped_at, NOW()), updated_at = NOW()
                    WHERE run_id = %s
                    """,
                    (status, error, run_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE search_runs
                    SET status = %s, error = %s, updated_at = NOW()
                    WHERE run_id = %s
                    """,
                    (status, error, run_id),
                )
        conn.commit()


def touch_run(run_id: str):
    update_run_counts(run_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE search_runs
                SET updated_at = NOW()
                WHERE run_id = %s
                """,
                (run_id,),
            )
        conn.commit()


def request_run_stop(run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE search_runs
                SET stop_requested = TRUE, status = 'STOPPED', stopped_at = COALESCE(stopped_at, NOW()), updated_at = NOW()
                WHERE run_id = %s
                RETURNING *
                """,
                (run_id,),
            )
            row = cursor.fetchone()
        conn.commit()
    return row


def delete_run(run_id: str, purge_leads: bool = True) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if purge_leads:
                cursor.execute("DELETE FROM leads WHERE run_id = %s", (run_id,))
            cursor.execute("DELETE FROM search_runs WHERE run_id = %s", (run_id,))
            deleted = cursor.rowcount > 0
        conn.commit()
    return deleted


def delete_lead(lead_id: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT run_id FROM leads WHERE lead_id = %s", (lead_id,))
            row = cursor.fetchone()
            run_id = row["run_id"] if row else None
            cursor.execute("DELETE FROM leads WHERE lead_id = %s", (lead_id,))
            deleted = cursor.rowcount > 0
        conn.commit()
    if deleted and run_id:
        touch_run(run_id)
    return deleted


def fetch_all_leads(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM leads ORDER BY updated_at DESC LIMIT %s OFFSET %s", (limit, offset))
            rows = cursor.fetchall()
    return [normalize_lead(row) for row in rows]


def fetch_lead(lead_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM leads WHERE lead_id = %s", (lead_id,))
            row = cursor.fetchone()
    return normalize_lead(row) if row else None


def fetch_runs(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM search_runs ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
            return cursor.fetchall()


def fetch_run(run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM search_runs WHERE run_id = %s", (run_id,))
            run = cursor.fetchone()
            if not run:
                return None
            cursor.execute("SELECT * FROM leads WHERE run_id = %s ORDER BY updated_at DESC", (run_id,))
            leads = cursor.fetchall()
    return {
        **run,
        "leads": [normalize_lead(lead) for lead in leads],
    }


def fetch_summary() -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_leads,
                    COUNT(*) FILTER (WHERE status = 'SENT') AS sent_leads,
                    COUNT(*) FILTER (WHERE status = 'READY_TO_SEND') AS ready_to_send,
                    COUNT(*) FILTER (WHERE status = 'DEAD_LEAD') AS dead_leads,
                    COUNT(*) FILTER (
                        WHERE status IN ('SEARCHED', 'CRAWLED', 'EXTRACTED', 'ENRICHED', 'VALIDATED', 'PERSONALIZED')
                    ) AS active_leads
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
            cursor.execute("SELECT COUNT(*) AS total_runs FROM search_runs")
            runs = cursor.fetchone() or {"total_runs": 0}
    return {
        **stats,
        **runs,
        "status_counts": status_counts,
    }


def find_existing_lead(domain: str | None) -> dict[str, Any] | None:
    if not domain:
        return None
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM leads WHERE domain = %s ORDER BY updated_at DESC LIMIT 1",
                (domain,),
            )
            row = cursor.fetchone()
    return normalize_lead(row) if row else None


def get_settings() -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT key, value, updated_at FROM app_settings ORDER BY key ASC")
            rows = cursor.fetchall()
    return {
        row["key"]: row["value"]["text"] if isinstance(row["value"], dict) and "text" in row["value"] else row["value"]
        for row in rows
    }


def update_setting(key: str, text_value: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = NOW()
                """,
                (key, json.dumps({"text": text_value})),
            )
        conn.commit()


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
            row = cursor.fetchone()
    if not row:
        return default
    value = row["value"]
    if isinstance(value, dict) and "text" in value:
        return value["text"]
    return default


def get_bool_setting(key: str, default: bool = False) -> bool:
    raw_value = get_setting(key)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_int_setting(key: str, default: int) -> int:
    raw_value = get_setting(key)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def normalize_lead(row: dict[str, Any]) -> dict[str, Any]:
    lead = dict(row)
    lead["services"] = lead.get("services") or []
    lead["signals"] = lead.get("signals") or []
    lead["company_profile"] = lead.get("company_profile") or {}
    lead["email_sequence"] = lead.get("email_sequence") or []
    return lead
