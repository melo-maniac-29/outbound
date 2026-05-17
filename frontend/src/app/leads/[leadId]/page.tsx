"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Mail, RefreshCw, User } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Lead = {
  lead_id: string;
  company_name: string | null;
  domain: string | null;
  search_query: string;
  founder_name: string | null;
  founder_linkedin: string | null;
  founder_confidence: number;
  email: string | null;
  email_confidence: number;
  signals: string[];
  services: string[];
  email_sequence: string[];
  status: string;
  run_id: string | null;
};

export default function LeadDetailPage(props: { params: Promise<{ leadId: string }> }) {
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const { leadId } = await props.params;
      const res = await fetch(`${API_URL}/api/leads/${leadId}`);
      const data = await res.json();
      setLead(data);
      setLoading(false);
    };
    void load();
  }, [props.params]);

  if (loading) {
    return <main className="shell"><div className="panel empty-state"><RefreshCw className="animate-spin" />Loading lead...</div></main>;
  }

  if (!lead) {
    return <main className="shell"><div className="panel empty-state">Lead not found.</div></main>;
  }

  return (
    <main className="shell">
      <section className="panel route-panel">
        <Link href="/" className="back-link"><ArrowLeft size={16} />Back to dashboard</Link>
        <p className="eyebrow">Lead Detail</p>
        <h1 className="route-title">{lead.company_name || lead.domain || lead.search_query}</h1>
        <p className="hero-text">{lead.domain || lead.search_query}</p>
        {lead.run_id && <Link className="utility-link" href={`/runs/${lead.run_id}`}>Open parent run</Link>}
      </section>

      <section className="workspace lower-workspace">
        <div className="panel">
          <div className="detail-metrics">
            <div className="metric-box"><User size={16} /><div><span>Founder</span><strong>{lead.founder_name || "Pending"}</strong><small>{Math.round(lead.founder_confidence * 100)}% confidence</small></div></div>
            <div className="metric-box"><Mail size={16} /><div><span>Email</span><strong>{lead.email || "Pending"}</strong><small>{Math.round(lead.email_confidence * 100)}% confidence</small></div></div>
            <div className="metric-box"><User size={16} /><div><span>Status</span><strong>{lead.status.replaceAll("_", " ")}</strong><small>{lead.founder_linkedin || "no linkedin captured"}</small></div></div>
          </div>
          <div className="tag-group">
            {(lead.signals.length ? lead.signals : ["No personalization signals captured"]).map((signal) => (
              <span key={signal} className="signal-tag">{signal}</span>
            ))}
          </div>
          <div className="tag-group">
            {(lead.services.length ? lead.services : ["No services extracted"]).map((service) => (
              <span key={service} className="signal-tag">{service}</span>
            ))}
          </div>
        </div>
        <div className="panel">
          <h2>Email Drafts</h2>
          <div className="sequence-panel">
            {lead.email_sequence.length === 0 ? (
              <div className="empty-inline">No draft sequence generated yet.</div>
            ) : (
              lead.email_sequence.map((email, index) => (
                <article key={`${lead.lead_id}-${index}`} className="sequence-card">
                  <span className="sequence-step">Email {index + 1}</span>
                  <p>{email}</p>
                </article>
              ))
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
