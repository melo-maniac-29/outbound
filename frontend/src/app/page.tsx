"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, Database, Radar, RefreshCw, Search, Settings, Sparkles } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Lead = {
  lead_id: string;
  company_name: string | null;
  domain: string | null;
  search_query: string;
  status: string;
  email: string | null;
};

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

type Summary = {
  total_leads: number;
  active_leads: number;
  ready_to_send: number;
  dead_leads: number;
  total_runs: number;
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [maxCompanies, setMaxCompanies] = useState(5);
  const [summary, setSummary] = useState<Summary>({
    total_leads: 0,
    active_leads: 0,
    ready_to_send: 0,
    dead_leads: 0,
    total_runs: 0,
  });
  const [leads, setLeads] = useState<Lead[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setIsRefreshing(true);
    try {
      const [summaryRes, leadsRes, runsRes] = await Promise.all([
        fetch(`${API_URL}/api/summary`),
        fetch(`${API_URL}/api/leads`),
        fetch(`${API_URL}/api/runs`),
      ]);
      const summaryData = await summaryRes.json();
      const leadsData = await leadsRes.json();
      const runsData = await runsRes.json();
      setSummary(summaryData);
      setLeads((leadsData.leads ?? []).slice(0, 8));
      setRuns((runsData.runs ?? []).slice(0, 8));
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
      const payload = isDomain ? { domain: trimmed, label: trimmed } : { query: trimmed, max_companies: maxCompanies };
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
          <p className="eyebrow">Outbound Operator</p>
          <h1>Search, build profiles, and draft outreach with review-first controls.</h1>
          <p className="hero-text">
            Runs are tracked separately, leads persist in PostgreSQL, and draft behavior can be changed in settings.
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
        <article className="stat-card"><span className="stat-label">Runs</span><strong>{summary.total_runs}</strong></article>
        <article className="stat-card"><span className="stat-label">Leads</span><strong>{summary.total_leads}</strong></article>
        <article className="stat-card"><span className="stat-label">Active</span><strong>{summary.active_leads}</strong></article>
        <article className="stat-card"><span className="stat-label">Draft Ready</span><strong>{summary.ready_to_send}</strong></article>
      </section>

      <section className="workspace">
        <div className="panel command-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Dispatch</p>
              <h2>Create a run</h2>
            </div>
          </div>
          <form className="command-form" onSubmit={handleSubmit}>
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
          {error && <div className="error-banner">{error}</div>}
        </div>

        <div className="panel pipeline-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Behavior</p>
              <h2>What this does now</h2>
            </div>
          </div>
          <div className="info-grid single-column">
            <div className="info-card"><Radar size={18} /><div><strong>Iterative discovery</strong><p>Search retries across query variants until your company target is met or attempts are exhausted.</p></div></div>
            <div className="info-card"><Sparkles size={18} /><div><strong>Draft-only completion</strong><p>Runs stop at `READY_TO_SEND` for review. No mock send step is used anymore.</p></div></div>
          </div>
        </div>
      </section>

      <section className="workspace lower-workspace">
        <div className="panel lead-list-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Recent Runs</p>
              <h2>Inspectable job history</h2>
            </div>
          </div>
          <div className="lead-list">
            {runs.map((run) => (
              <Link key={run.run_id} href={`/runs/${run.run_id}`} className="lead-item">
                <div className="lead-item-top">
                  <strong>{run.query}</strong>
                  <span className={`status-badge status-${run.status}`}>{run.status}</span>
                </div>
                <p>{run.source_type}</p>
                <div className="lead-item-meta">
                  <span>{run.discovered_companies}/{run.requested_companies} discovered</span>
                  <span>{run.processed_companies} processed</span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="panel detail-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Recent Leads</p>
              <h2>Open a lead profile</h2>
            </div>
          </div>
          <div className="lead-list">
            {leads.map((lead) => (
              <Link key={lead.lead_id} href={`/leads/${lead.lead_id}`} className="lead-item">
                <div className="lead-item-top">
                  <strong>{lead.company_name || lead.domain || lead.search_query}</strong>
                  <span className={`status-badge status-${lead.status}`}>{lead.status.replaceAll("_", " ")}</span>
                </div>
                <p>{lead.domain || lead.search_query}</p>
                <div className="lead-item-meta">
                  <span>{lead.email || "email pending"}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
