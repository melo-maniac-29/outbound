"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Building2, Mail, RefreshCw, User } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Lead = {
  lead_id: string;
  company_name: string | null;
  domain: string | null;
  founder_name: string | null;
  email: string | null;
  status: string;
};

type RunDetail = {
  run_id: string;
  query: string;
  requested_companies: number;
  discovered_companies: number;
  processed_companies: number;
  source_type: string;
  status: string;
  error?: string | null;
  leads: Lead[];
};

export default function RunDetailPage(props: { params: Promise<{ runId: string }> }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const { runId } = await props.params;
      const res = await fetch(`${API_URL}/api/runs/${runId}`);
      const data = await res.json();
      setRun(data);
      setLoading(false);
    };
    void load();
  }, [props.params]);

  if (loading) {
    return <main className="shell"><div className="panel empty-state"><RefreshCw className="animate-spin" />Loading run...</div></main>;
  }

  if (!run) {
    return <main className="shell"><div className="panel empty-state">Run not found.</div></main>;
  }

  return (
    <main className="shell">
      <section className="panel route-panel">
        <Link href="/" className="back-link"><ArrowLeft size={16} />Back to dashboard</Link>
        <p className="eyebrow">Run Detail</p>
        <h1 className="route-title">{run.query}</h1>
        <div className="route-meta-grid">
          <div className="metric-box"><Building2 size={16} /><div><span>Requested</span><strong>{run.requested_companies}</strong></div></div>
          <div className="metric-box"><Building2 size={16} /><div><span>Discovered</span><strong>{run.discovered_companies}</strong></div></div>
          <div className="metric-box"><Mail size={16} /><div><span>Processed</span><strong>{run.processed_companies}</strong></div></div>
          <div className="metric-box"><User size={16} /><div><span>Status</span><strong>{run.status}</strong></div></div>
        </div>
        {run.error && <div className="error-banner">{run.error}</div>}
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Leads</p>
            <h2>Leads from this run</h2>
          </div>
        </div>
        <div className="lead-list">
          {run.leads.map((lead) => (
            <Link key={lead.lead_id} href={`/leads/${lead.lead_id}`} className="lead-item">
              <div className="lead-item-top">
                <strong>{lead.company_name || lead.domain}</strong>
                <span className={`status-badge status-${lead.status}`}>{lead.status.replaceAll("_", " ")}</span>
              </div>
              <p>{lead.domain}</p>
              <div className="lead-item-meta">
                <span>{lead.founder_name || "founder pending"}</span>
                <span>{lead.email || "email pending"}</span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
