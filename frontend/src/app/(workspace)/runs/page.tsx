"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RefreshCw, Activity, ArrowRight } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Run = {
  run_id: string;
  query: string;
  requested_companies: number;
  discovered_companies: number;
  processed_companies: number;
  source_type: string;
  status: string;
  created_at: string;
};

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${API_URL}/api/runs?limit=50`);
      const data = await res.json();
      setRuns(data.runs ?? []);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch runs.");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  return (
    <main className="shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">All Runs</p>
          <h1>Job History</h1>
          <p className="hero-text">View and manage all your automated search and discovery runs.</p>
        </div>
        <div className="hero-meta">
          <button className="primary-button" onClick={fetchRuns} disabled={isRefreshing}>
            {isRefreshing ? <RefreshCw size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            Refresh
          </button>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="workspace">
        <div className="panel" style={{ gridColumn: '1 / -1' }}>
          <div className="lead-list">
            {runs.map((run) => (
              <Link key={run.run_id} href={`/runs/${run.run_id}`} className="lead-item">
                <div className="lead-item-top">
                  <strong>{run.query}</strong>
                  <span className={`status-badge status-${run.status}`}>{run.status}</span>
                </div>
                <p>{run.source_type}</p>
                <div className="lead-item-meta">
                  <span>
                    {run.discovered_companies}/{run.requested_companies} discovered
                  </span>
                  <span>{run.processed_companies} processed</span>
                  <ArrowRight size={14} />
                </div>
              </Link>
            ))}
            {runs.length === 0 && !isRefreshing && (
              <div className="empty-state">
                <Activity size={32} />
                <p>No runs found. Start a run on the dashboard.</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
