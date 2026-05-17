"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RefreshCw, Users, ArrowRight } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Lead = {
  lead_id: string;
  company_name: string | null;
  domain: string | null;
  search_query: string;
  status: string;
  email: string | null;
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLeads = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${API_URL}/api/leads?limit=100`);
      const data = await res.json();
      setLeads(data.leads ?? []);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch leads.");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  return (
    <main className="shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">All Leads</p>
          <h1>Lead Directory</h1>
          <p className="hero-text">View and manage all extracted leads from your outreach pipeline.</p>
        </div>
        <div className="hero-meta">
          <button className="primary-button" onClick={fetchLeads} disabled={isRefreshing}>
            {isRefreshing ? <RefreshCw size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            Refresh
          </button>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="workspace">
        <div className="panel" style={{ gridColumn: '1 / -1' }}>
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
                  <ArrowRight size={14} />
                </div>
              </Link>
            ))}
            {leads.length === 0 && !isRefreshing && (
              <div className="empty-state">
                <Users size={32} />
                <p>No leads found. Start a run on the dashboard.</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
