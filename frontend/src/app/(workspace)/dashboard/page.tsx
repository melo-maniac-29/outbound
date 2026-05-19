"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, RefreshCw, Search, Wifi, WifiOff } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CACHE_SUMMARY = "outbound_summary_cache";
const CACHE_RUNS = "outbound_runs_cache";

type RunSummary = { run_id: string; query: string; requested_companies: number; discovered_companies: number; processed_companies: number; ready_to_send_count?: number; source_type: string; status: string; };
type Summary = { total_leads: number; active_leads: number; ready_to_send: number; dead_leads: number; total_runs: number; };

function statusBadge(status: string) {
  const map: Record<string, string> = { RUNNING: "badge-running", COMPLETED: "badge-completed", EXHAUSTED: "badge-failed", STOPPED: "badge-default", FAILED: "badge-failed" };
  return `badge ${map[status] || "badge-default"}`;
}

export default function DashboardPage() {
  const [query, setQuery] = useState("");
  const [maxCompanies, setMaxCompanies] = useState(5);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [summary, setSummary] = useState<Summary>({ total_leads: 0, active_leads: 0, ready_to_send: 0, dead_leads: 0, total_runs: 0 });
  const [isSearching, setIsSearching] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let retryTimer: ReturnType<typeof setTimeout>;

    // Restore from cache instantly
    try {
      const cs = localStorage.getItem(CACHE_SUMMARY);
      const cr = localStorage.getItem(CACHE_RUNS);
      if (cs) setSummary(JSON.parse(cs));
      if (cr) setRuns(JSON.parse(cr));
    } catch {}

    const connect = () => {
      esRef.current?.close();
      const es = new EventSource(`${API_URL}/api/stream/summary`);
      esRef.current = es;

      es.onopen = () => { setConnected(true); setError(null); };

      es.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.summary) {
            setSummary(data.summary);
            try { localStorage.setItem(CACHE_SUMMARY, JSON.stringify(data.summary)); } catch {}
          }
          if (Array.isArray(data.runs)) {
            setRuns(data.runs);
            try { localStorage.setItem(CACHE_RUNS, JSON.stringify(data.runs)); } catch {}
          }
        } catch { /* ignore malformed */ }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        retryTimer = setTimeout(connect, 5000);
      };
    };

    connect();

    return () => {
      clearTimeout(retryTimer);
      esRef.current?.close();
    };
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    setError(null);
    try {
      const t = query.trim();
      const isDomain = !t.includes(" ") && t.includes(".");
      const ep = isDomain ? "/api/process-domain" : "/api/search";
      const body = isDomain ? { domain: t, label: t } : { query: t, max_companies: maxCompanies };
      const res = await fetch(`${API_URL}${ep}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "Failed to start run.");
      setQuery("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start run.");
    } finally {
      setIsSearching(false);
    }
  };

  const hasActiveRun = runs.some(r => r.status === "RUNNING");

  return (
    <main className="shell">
      <div className="page-header">
        <p className="eyebrow">Dashboard</p>
        <h1>Dispatch Center</h1>
        <p>Start discovery runs and monitor pipeline progress.</p>
        <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8, fontSize: "0.78rem" }}>
          {connected ? (
            <span style={{ color: "var(--teal)", display: "flex", alignItems: "center", gap: 5 }}>
              <Wifi size={12} /> Live
              {hasActiveRun && <><RefreshCw size={11} className="animate-spin" style={{ marginLeft: 4 }} /> Pipeline running</>}
            </span>
          ) : (
            <span style={{ color: "var(--muted)", display: "flex", alignItems: "center", gap: 5 }}>
              <WifiOff size={12} /> Reconnecting…
            </span>
          )}
        </div>
      </div>

      <div className="stats-row">
        <div className="stat-block"><div className="stat-value">{summary.total_runs}</div><div className="stat-label">Runs</div></div>
        <div className="stat-block"><div className="stat-value">{summary.total_leads}</div><div className="stat-label">Leads</div></div>
        <div className="stat-block"><div className="stat-value">{summary.active_leads}</div><div className="stat-label">Processing</div></div>
        <div className="stat-block"><div className="stat-value">{summary.ready_to_send}</div><div className="stat-label">Draft Ready</div></div>
      </div>

      <div className="section">
        <div className="section-head">
          <h2 className="section-title">New Run</h2>
        </div>
        <form onSubmit={submit} style={{ maxWidth: 560 }}>
          <div className="form-group" style={{ marginBottom: 14 }}>
            <label className="form-label">Query or direct domain</label>
            <input className="form-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="boutique lifecycle marketing agency founder" />
          </div>
          <div className="form-row">
            <div className="form-group" style={{ width: 140 }}>
              <label className="form-label">Target count</label>
              <input className="form-input" type="number" min={1} max={25} value={maxCompanies} onChange={e => setMaxCompanies(Number(e.target.value) || 1)} />
            </div>
            <button className="btn btn-primary" type="submit" disabled={isSearching}>
              {isSearching ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />} Start Run
            </button>
          </div>
          <p className="form-hint" style={{ marginTop: 10 }}>Multi-wave search continues until this many leads reach draft-ready.</p>
        </form>
        {error && <div className="callout callout-error" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      <div className="section">
        <div className="section-head">
          <h2 className="section-title">Recent Runs</h2>
          <Link href="/runs" className="btn-link">View all <ArrowRight size={14} /></Link>
        </div>
        <div className="data-list">
          {runs.map(run => (
            <Link key={run.run_id} href={`/runs/${run.run_id}`} className="data-row">
              <span className="primary">{run.query}</span>
              <span className="mono">{run.ready_to_send_count ?? 0}/{run.requested_companies} ready</span>
              <span className="secondary">{run.discovered_companies} attempted</span>
              <span className="secondary">{run.processed_companies} finished</span>
              <span className={statusBadge(run.status)}>{run.status}</span>
            </Link>
          ))}
          {runs.length === 0 && !connected && <div className="empty"><p>Connecting…</p></div>}
          {runs.length === 0 && connected && <div className="empty"><p>No runs yet. Start one above.</p></div>}
        </div>
      </div>
    </main>
  );
}
