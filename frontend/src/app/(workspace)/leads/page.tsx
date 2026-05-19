"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Lead = { lead_id: string; company_name: string | null; domain: string | null; search_query: string; status: string; email: string | null; };

function statusBadge(s: string) {
  const m: Record<string, string> = { READY_TO_SEND: "badge-ready", DEAD_LEAD: "badge-dead", SENT: "badge-completed" };
  return `badge ${m[s] || "badge-default"}`;
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await fetch(`${API_URL}/api/leads?limit=100`);
      if (!res.ok) throw new Error();
      const d = await res.json();
      setLeads(d.leads ?? []); setError(null);
    } catch { setError("Failed to fetch leads."); } finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  return (
    <main className="shell">
      <div className="page-header">
        <p className="eyebrow">All Leads</p>
        <h1>Lead Directory</h1>
        <p>Every company discovered and processed by the pipeline.</p>
        <div className="meta-row">
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="callout callout-error">{error}</div>}

      <div className="data-list">
        {leads.map(lead => (
          <Link key={lead.lead_id} href={`/leads/${lead.lead_id}`} className="data-row data-row-3col">
            <div>
              <span className="primary">{lead.company_name || lead.domain || lead.search_query}</span>
              <div className="secondary" style={{ marginTop: 2 }}>{lead.domain || lead.search_query}</div>
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
