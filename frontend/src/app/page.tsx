"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  Building2,
  Database,
  Globe,
  Loader2,
  Mail,
  Radar,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Lead = {
  lead_id: string;
  search_query: string;
  company_name: string | null;
  domain: string | null;
  founder_name: string | null;
  founder_linkedin: string | null;
  founder_confidence: number;
  email: string | null;
  email_confidence: number;
  services: string[];
  signals: string[];
  email_sequence: string[];
  status: string;
  source_type: string | null;
  updated_at?: string;
};

type Summary = {
  total_leads: number;
  sent_leads: number;
  ready_to_send: number;
  dead_leads: number;
  active_leads: number;
  status_counts: Array<{ status: string; count: number }>;
};

const EMPTY_SUMMARY: Summary = {
  total_leads: 0,
  sent_leads: 0,
  ready_to_send: 0,
  dead_leads: 0,
  active_leads: 0,
  status_counts: [],
};

function formatStatus(status: string) {
  return status.replaceAll("_", " ");
}

function inferMode(value: string) {
  const trimmed = value.trim();
  return !trimmed.includes(" ") && trimmed.includes(".") ? "domain" : "search";
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [maxCompanies, setMaxCompanies] = useState(5);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [summary, setSummary] = useState<Summary>(EMPTY_SUMMARY);
  const [isSearching, setIsSearching] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setIsRefreshing(true);
    try {
      const [leadsRes, summaryRes] = await Promise.all([
        fetch(`${API_URL}/api/leads`),
        fetch(`${API_URL}/api/summary`),
      ]);

      if (!leadsRes.ok) {
        throw new Error(`Lead fetch failed with status ${leadsRes.status}`);
      }

      const leadsData = await leadsRes.json();
      const summaryData = summaryRes.ok ? await summaryRes.json() : EMPTY_SUMMARY;
      const nextLeads = (leadsData.leads ?? []) as Lead[];

      setLeads(nextLeads);
      setSummary({
        ...EMPTY_SUMMARY,
        ...summaryData,
      });
      setSelectedLeadId((current) => current ?? nextLeads[0]?.lead_id ?? null);
      setError(null);
    } catch (err) {
      console.error("Dashboard refresh failed", err);
      setError("Backend unavailable or dashboard refresh failed.");
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
      const isDirectDomain = inferMode(trimmed) === "domain";
      const endpoint = isDirectDomain ? "/api/process-domain" : "/api/search";
      const payload = isDirectDomain
        ? { domain: trimmed, label: trimmed }
        : { query: trimmed, max_companies: maxCompanies };

      const res = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Pipeline trigger failed with status ${res.status}`);
      }

      setQuery("");
      setError(null);
      void fetchDashboard();
    } catch (err) {
      console.error("Pipeline trigger failed", err);
      setError("Pipeline trigger failed. Check backend logs and API credentials.");
    } finally {
      setIsSearching(false);
    }
  };

  const selectedLead =
    leads.find((lead) => lead.lead_id === selectedLeadId) ?? leads[0] ?? null;
  const mode = inferMode(query);

  return (
    <main className="shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Outbound Operator Console</p>
          <h1>Run discovery, inspect the pipeline, and review send-ready sequences.</h1>
          <p className="hero-text">
            Search can now be capped to a specific number of target companies, duplicates are blocked at the
            domain level, and PostgreSQL is the source of truth behind the dashboard.
          </p>
        </div>

        <div className="hero-meta">
          <div className="status-chip">
            {isRefreshing ? <RefreshCw size={14} className="animate-spin" /> : <Activity size={14} />}
            Live sync
          </div>
          <a className="utility-link" href="http://localhost:8081" target="_blank" rel="noreferrer">
            <Database size={16} />
            Open Adminer
          </a>
        </div>
      </section>

      <section className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">Total Leads</span>
          <strong>{summary.total_leads}</strong>
          <p>Persisted in PostgreSQL</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Active</span>
          <strong>{summary.active_leads}</strong>
          <p>Still moving through the graph</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Ready / Sent</span>
          <strong>{summary.ready_to_send + summary.sent_leads}</strong>
          <p>Validated outreach candidates</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Dead Leads</span>
          <strong>{summary.dead_leads}</strong>
          <p>Failed validation or extraction</p>
        </article>
      </section>

      <section className="workspace">
        <div className="panel command-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Dispatch</p>
              <h2>Queue a new run</h2>
            </div>
            <div className={`mode-pill mode-${mode}`}>
              {mode === "domain" ? <Globe size={14} /> : <Radar size={14} />}
              {mode === "domain" ? "Direct Domain" : "Search Discovery"}
            </div>
          </div>

          <form className="command-form" onSubmit={handleSubmit}>
            <label className="field">
              <span>Search phrase or company domain</span>
              <input
                className="text-input"
                placeholder="retention.com or boutique retention marketing agency founder"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isSearching}
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
                  disabled={isSearching || mode === "domain"}
                />
              </label>

              <button className="primary-button" type="submit" disabled={isSearching}>
                {isSearching ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
                {mode === "domain" ? "Run Direct Domain" : "Search and Queue"}
              </button>
            </div>
          </form>

          <div className="info-grid">
            <div className="info-card">
              <ShieldCheck size={18} />
              <div>
                <strong>No repetition</strong>
                <p>Domains are deduplicated before a new lead enters the graph.</p>
              </div>
            </div>
            <div className="info-card">
              <Building2 size={18} />
              <div>
                <strong>Explicit limits</strong>
                <p>Search runs now use your chosen company cap instead of an implicit fixed result count.</p>
              </div>
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}
        </div>

        <div className="panel pipeline-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Pipeline Health</p>
              <h2>Status distribution</h2>
            </div>
          </div>

          <div className="status-stack">
            {summary.status_counts.length === 0 ? (
              <div className="empty-inline">No persisted leads yet.</div>
            ) : (
              summary.status_counts.map((entry) => (
                <div key={entry.status} className="status-row">
                  <span className={`status-badge status-${entry.status}`}>{formatStatus(entry.status)}</span>
                  <span className="status-count">{entry.count}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="workspace lower-workspace">
        <div className="panel lead-list-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Queue</p>
              <h2>Lead stream</h2>
            </div>
            <span className="mini-note">{leads.length} visible</span>
          </div>

          <div className="lead-list">
            {leads.length === 0 ? (
              <div className="empty-state">
                <Sparkles size={28} />
                <p>No leads yet. Run a search or direct domain above.</p>
              </div>
            ) : (
              leads.map((lead) => (
                <button
                  key={lead.lead_id}
                  type="button"
                  className={`lead-item ${selectedLead?.lead_id === lead.lead_id ? "lead-item-active" : ""}`}
                  onClick={() => setSelectedLeadId(lead.lead_id)}
                >
                  <div className="lead-item-top">
                    <strong>{lead.company_name || lead.domain || lead.search_query}</strong>
                    <span className={`status-badge status-${lead.status}`}>{formatStatus(lead.status)}</span>
                  </div>
                  <p>{lead.domain || lead.search_query}</p>
                  <div className="lead-item-meta">
                    <span>{lead.source_type || "unknown source"}</span>
                    <ArrowRight size={14} />
                    <span>{lead.email || "email pending"}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="panel detail-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Inspection</p>
              <h2>Lead detail</h2>
            </div>
          </div>

          {!selectedLead ? (
            <div className="empty-state">
              <Mail size={28} />
              <p>Select a lead to inspect enrichment, confidence, and generated copy.</p>
            </div>
          ) : (
            <div className="detail-layout">
              <div className="detail-summary">
                <div className="detail-title-row">
                  <div>
                    <h3>{selectedLead.company_name || selectedLead.domain || selectedLead.search_query}</h3>
                    <p>{selectedLead.domain || selectedLead.search_query}</p>
                  </div>
                  <span className={`status-badge status-${selectedLead.status}`}>
                    {formatStatus(selectedLead.status)}
                  </span>
                </div>

                <div className="detail-metrics">
                  <div className="metric-box">
                    <User size={16} />
                    <div>
                      <span>Founder</span>
                      <strong>{selectedLead.founder_name || "Pending"}</strong>
                      <small>{Math.round(selectedLead.founder_confidence * 100)}% confidence</small>
                    </div>
                  </div>
                  <div className="metric-box">
                    <Mail size={16} />
                    <div>
                      <span>Email</span>
                      <strong>{selectedLead.email || "Pending"}</strong>
                      <small>{Math.round(selectedLead.email_confidence * 100)}% confidence</small>
                    </div>
                  </div>
                  <div className="metric-box">
                    <Send size={16} />
                    <div>
                      <span>Sequence</span>
                      <strong>{selectedLead.email_sequence.length} drafts</strong>
                      <small>{selectedLead.source_type || "manual or search sourced"}</small>
                    </div>
                  </div>
                </div>

                <div className="tag-group">
                  {(selectedLead.signals.length ? selectedLead.signals : ["No signals captured yet"]).map((signal) => (
                    <span key={signal} className="signal-tag">
                      {signal}
                    </span>
                  ))}
                </div>
              </div>

              <div className="sequence-panel">
                <h4>Email sequence preview</h4>
                {selectedLead.email_sequence.length === 0 ? (
                  <div className="empty-inline">Sequence not generated yet.</div>
                ) : (
                  selectedLead.email_sequence.map((email, index) => (
                    <article key={`${selectedLead.lead_id}-${index}`} className="sequence-card">
                      <span className="sequence-step">Email {index + 1}</span>
                      <p>{email}</p>
                    </article>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
