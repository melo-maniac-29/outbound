"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, RefreshCw, Search } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setIsRefreshing(true);
    try {
      const [sRes, rRes] = await Promise.all([fetch(`${API_URL}/api/summary`), fetch(`${API_URL}/api/runs?limit=5`)]);
      if (sRes.ok) setSummary(await sRes.json());
      if (rRes.ok) { const d = await rRes.json(); setRuns(d.runs ?? []); }
      setError(null);
    } catch { setError("Backend unreachable."); } finally { setIsRefreshing(false); }
  };

  useEffect(() => { void refresh(); const id = setInterval(refresh, 3500); return () => clearInterval(id); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    try {
      const t = query.trim();
      const isDomain = !t.includes(" ") && t.includes(".");
      const ep = isDomain ? "/api/process-domain" : "/api/search";
      const body = isDomain ? { domain: t, label: t } : { query: t, max_companies: maxCompanies };
      const res = await fetch(`${API_URL}${ep}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!res.ok) throw new Error();
      setQuery(""); await refresh();
    } catch { setError("Failed to start run."); } finally { setIsSearching(false); }
  };

  return (
    <main className="shell">
      <div className="page-header">
        <p className="eyebrow">Dashboard</p>
        <h1>Dispatch Center</h1>
        <p>Start discovery runs and monitor pipeline progress.</p>
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
        {error && <div className="callout callout-error">{error}</div>}
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
          {runs.length === 0 && !isRefreshing && <div className="empty"><p>No runs yet. Start one above.</p></div>}
        </div>
      </div>
    </main>
  );
}
