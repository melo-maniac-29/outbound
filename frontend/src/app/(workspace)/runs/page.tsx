"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Run = { run_id: string; query: string; requested_companies: number; discovered_companies: number; processed_companies: number; ready_to_send_count?: number; source_type: string; status: string; };

function statusBadge(s: string) {
  const m: Record<string, string> = { RUNNING: "badge-running", COMPLETED: "badge-completed", EXHAUSTED: "badge-failed", STOPPED: "badge-default", FAILED: "badge-failed" };
  return `badge ${m[s] || "badge-default"}`;
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await fetch(`${API_URL}/api/runs?limit=50`);
      if (!res.ok) throw new Error();
      const d = await res.json();
      setRuns(d.runs ?? []); setError(null);
    } catch { setError("Failed to fetch runs."); } finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  return (
    <main className="shell">
      <div className="page-header">
        <p className="eyebrow">All Runs</p>
        <h1>Job History</h1>
        <p>Every search and domain processing run.</p>
        <div className="meta-row">
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="callout callout-error">{error}</div>}

      <div className="data-list">
        {runs.map(run => (
          <Link key={run.run_id} href={`/runs/${run.run_id}`} className="data-row">
            <span className="primary">{run.query}</span>
            <span className="mono">{run.ready_to_send_count ?? 0}/{run.requested_companies} ready</span>
            <span className="secondary">{run.discovered_companies} attempted</span>
            <span className="secondary">{run.processed_companies} done</span>
            <span className={statusBadge(run.status)}>{run.status}</span>
          </Link>
        ))}
        {runs.length === 0 && !loading && <div className="empty"><p>No runs found.</p></div>}
      </div>
    </main>
  );
}
