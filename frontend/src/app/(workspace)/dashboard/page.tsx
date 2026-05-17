"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, Database, RefreshCw, Search, Settings } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Summary = {
  total_leads: number;
  active_leads: number;
  ready_to_send: number;
  dead_leads: number;
  total_runs: number;
};

export default function DashboardPage() {
  const [query, setQuery] = useState("");
  const [maxCompanies, setMaxCompanies] = useState(5);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [summary, setSummary] = useState<Summary>({
    total_leads: 0,
    active_leads: 0,
    ready_to_send: 0,
    dead_leads: 0,
    total_runs: 0,
  });
  const [isSearching, setIsSearching] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${API_URL}/api/summary`);
      const summaryData = await res.json();
      setSummary(summaryData);
      
      const runsRes = await fetch(`${API_URL}/api/runs?limit=3`);
      const runsData = await runsRes.json();
      setRecentRuns(runsData.runs ?? []);
      
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to refresh dashboard.");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    const initialLoad = setTimeout(() => {
      void fetchDashboard();
    }, 0);
    const interval = setInterval(fetchDashboard, 3500);
    return () => {
      clearTimeout(initialLoad);
      clearInterval(interval);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    try {
      const trimmed = query.trim();
      const isDomain = !trimmed.includes(" ") && trimmed.includes(".");
      const endpoint = isDomain ? "/api/process-domain" : "/api/search";
      const payload = isDomain
        ? { domain: trimmed, label: trimmed }
        : { query: trimmed, max_companies: maxCompanies };
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Request failed with ${res.status}`);
      setQuery("");
      await fetchDashboard();
    } catch (err) {
      console.error(err);
      setError("Failed to start the run.");
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <main className="shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Workspace Dashboard</p>
          <h1>Dispatch Center</h1>
          <p className="hero-text">
            Start new discovery runs and view high-level metrics. Navigate to Runs or Leads for detailed records.
          </p>
        </div>
        <div className="hero-meta">
          <div className="status-chip">
            {isRefreshing ? <RefreshCw size={14} className="animate-spin" /> : <Activity size={14} />}
            Live sync
          </div>
          <div className="hero-links">
            <Link className="utility-link" href="/settings">
              <Settings size={16} />
              Prompt Settings
            </Link>
            <a className="utility-link" href="http://localhost:8081" target="_blank" rel="noreferrer">
              <Database size={16} />
              Open Adminer
            </a>
          </div>
        </div>
      </section>

      <section className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">Runs</span>
          <strong>{summary.total_runs}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">Leads</span>
          <strong>{summary.total_leads}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">Active Processing</span>
          <strong>{summary.active_leads}</strong>
        </article>
        <article className="stat-card">
          <span className="stat-label">Draft Ready</span>
          <strong>{summary.ready_to_send}</strong>
        </article>
      </section>

      <section className="workspace">
        <div className="panel command-panel" style={{ gridColumn: '1 / -1' }}>
          <div className="panel-head">
            <div>
              <p className="eyebrow">Dispatch</p>
              <h2>Create a new pipeline run</h2>
            </div>
          </div>
          <form className="command-form" onSubmit={handleSubmit} style={{ maxWidth: '600px' }}>
            <label className="field">
              <span>Query or direct domain</span>
              <input
                className="text-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="boutique lifecycle marketing agency founder or retention.com"
              />
            </label>
            <div className="control-row">
              <label className="field compact-field">
                <span>Company limit</span>
                <input
                  className="text-input"
                  type="number"
                  min={1}
                  max={25}
                  value={maxCompanies}
                  onChange={(e) => setMaxCompanies(Number(e.target.value) || 1)}
                />
              </label>
              <button className="primary-button" type="submit" disabled={isSearching}>
                {isSearching ? <RefreshCw size={18} className="animate-spin" /> : <Search size={18} />}
                Start Run
              </button>
            </div>
          </form>
          {error && <div className="error-banner" style={{ marginTop: '1rem' }}>{error}</div>}
        </div>

        <div className="panel" style={{ gridColumn: '1 / -1' }}>
          <div className="panel-head">
            <div>
              <p className="eyebrow">Activity</p>
              <h2>Recent Runs</h2>
            </div>
            <Link href="/runs" className="utility-link">View All</Link>
          </div>
          <div className="lead-list" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', display: 'grid' }}>
            {recentRuns.map((run) => (
              <Link key={run.run_id} href={`/runs/${run.run_id}`} className="lead-item">
                <div className="lead-item-top">
                  <strong>{run.query}</strong>
                  <span className={`status-badge status-${run.status}`}>{run.status}</span>
                </div>
                <div className="lead-item-meta" style={{ marginTop: '12px' }}>
                  <span>
                    {run.discovered_companies}/{run.requested_companies} discovered
                  </span>
                  <span>{run.processed_companies} processed</span>
                </div>
              </Link>
            ))}
            {recentRuns.length === 0 && !isRefreshing && (
              <div className="empty-state">
                <p>No recent runs found.</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
