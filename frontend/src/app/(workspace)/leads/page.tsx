"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { RefreshCw, Wifi, WifiOff } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CACHE_KEY = "outbound_leads_cache";

type Lead = { lead_id: string; company_name: string | null; domain: string | null; search_query: string; status: string; email: string | null; founder_name: string | null; };

function statusBadge(s: string) {
  const m: Record<string, string> = { READY_TO_SEND: "badge-ready", DEAD_LEAD: "badge-dead", SENT: "badge-completed", RUNNING: "badge-running" };
  return `badge ${m[s] || "badge-default"}`;
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const load = async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/leads?limit=100`, { signal: ac.signal });
      if (!res.ok) throw new Error();
      const d = await res.json();
      const data = d.leads ?? [];
      setLeads(data);
      setError(null);
      // Save to localStorage so next visit is instant
      try { localStorage.setItem(CACHE_KEY, JSON.stringify(data)); } catch {}
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      setError("Failed to fetch leads.");
    } finally { setLoading(false); }
  };

  // Mount: load cache instantly, then fetch fresh
  useEffect(() => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) { setLeads(JSON.parse(cached)); setLoading(false); }
    } catch {}
    void load();
    return () => abortRef.current?.abort();
  }, []);

  // SSE: re-fetch only when pipeline state actually changes
  useEffect(() => {
    let retryTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      esRef.current?.close();
      const es = new EventSource(`${API_URL}/api/stream/summary`);
      esRef.current = es;
      es.onopen = () => setConnected(true);
      es.onmessage = () => void load();
      es.onerror = () => {
        setConnected(false);
        es.close();
        retryTimer = setTimeout(connect, 5000);
      };
    };

    connect();
    return () => { clearTimeout(retryTimer); esRef.current?.close(); };
  }, []);

  const readyCount = leads.filter(l => l.status === "READY_TO_SEND").length;
  const activeCount = leads.filter(l => !["READY_TO_SEND", "DEAD_LEAD", "SENT"].includes(l.status)).length;

  return (
    <main className="shell">
      <div className="page-header">
        <p className="eyebrow">All Leads</p>
        <h1>Lead Directory</h1>
        <p>Every company discovered and processed by the pipeline.</p>
        <div className="meta-row" style={{ marginTop: 12 }}>
          {readyCount > 0 && <span className="badge badge-ready">{readyCount} ready to send</span>}
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
          <span style={{ fontSize: "0.78rem", display: "flex", alignItems: "center", gap: 5, color: connected ? "var(--teal)" : "var(--muted)" }}>
            {connected
              ? <><Wifi size={12} /> Live{activeCount > 0 && <RefreshCw size={11} className="animate-spin" style={{ marginLeft: 4 }} />}</>
              : <><WifiOff size={12} /> Reconnecting…</>}
          </span>
        </div>
      </div>

      {error && <div className="callout callout-error">{error}</div>}

      <div className="data-list">
        {loading && leads.length === 0 && (
          <div className="empty"><RefreshCw size={14} className="animate-spin" style={{ marginRight: 8 }} /> Loading…</div>
        )}
        {leads.map(lead => (
          <Link key={lead.lead_id} href={`/leads/${lead.lead_id}`} className="data-row data-row-3col">
            <div>
              <span className="primary">{lead.company_name || lead.domain || lead.search_query}</span>
              <div className="secondary" style={{ marginTop: 2 }}>{lead.founder_name || lead.domain || lead.search_query}</div>
            </div>
            <span className="mono">{lead.email || "—"}</span>
            <span className={statusBadge(lead.status)}>{lead.status.replaceAll("_", " ")}</span>
          </Link>
        ))}
        {leads.length === 0 && !loading && <div className="empty"><p>No leads yet. Start a run on the dashboard.</p></div>}
      </div>
    </main>
  );
}
