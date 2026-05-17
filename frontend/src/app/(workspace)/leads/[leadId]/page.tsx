"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Mail, RefreshCw, Trash2, User } from "lucide-react";

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
  company_profile?: {
    summary?: string;
    positioning?: string;
    audience?: string;
    key_services?: string[];
    credibility_signals?: string[];
    outreach_angle?: string;
  };
  status: string;
  run_id: string | null;
};

export default function LeadDetailPage() {
  const params = useParams<{ leadId: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`${API_URL}/api/leads/${params.leadId}`);
      const data = await res.json();
      setLead(data);
      setLoading(false);
    };
    void load();
  }, [params.leadId]);

  const deleteLead = async () => {
    setWorking(true);
    setMessage(null);
    const res = await fetch(`${API_URL}/api/leads/${params.leadId}`, { method: "DELETE" });
    if (res.ok) {
      router.push("/dashboard");
      router.refresh();
      return;
    }
    const data = await res.json().catch(() => null);
    setMessage(data?.detail ?? "Failed to delete lead.");
    setWorking(false);
  };

  if (loading) {
    return (
      <main className="shell">
        <div className="panel empty-state">
          <RefreshCw className="animate-spin" />
          Loading lead...
        </div>
      </main>
    );
  }

  if (!lead) {
    return (
      <main className="shell">
        <div className="panel empty-state">Lead not found.</div>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className="panel route-panel">
        <Link href="/dashboard" className="back-link">
          <ArrowLeft size={16} />
          Back to dashboard
        </Link>
        <p className="eyebrow">Lead Detail</p>
        <h1 className="route-title">{lead.company_name || lead.domain || lead.search_query}</h1>
        <p className="hero-text">{lead.domain || lead.search_query}</p>
        {lead.run_id && (
          <Link className="utility-link" href={`/runs/${lead.run_id}`}>
            Open parent run
          </Link>
        )}
        <div className="action-row">
          <button className="danger-button" type="button" onClick={deleteLead} disabled={working}>
            <Trash2 size={16} />
            Delete Lead
          </button>
        </div>
        {message && <div className="info-banner">{message}</div>}
      </section>

      <section className="workspace lower-workspace">
        <div className="panel">
          <div className="detail-metrics">
            <div className="metric-box">
              <User size={16} />
              <div>
                <span>Founder</span>
                <strong>{lead.founder_name || "Pending"}</strong>
                <small>{Math.round(lead.founder_confidence * 100)}% confidence</small>
              </div>
            </div>
            <div className="metric-box">
              <Mail size={16} />
              <div>
                <span>Email</span>
                <strong>{lead.email || "Pending"}</strong>
                <small>{Math.round(lead.email_confidence * 100)}% confidence</small>
              </div>
            </div>
            <div className="metric-box">
              <User size={16} />
              <div>
                <span>Status</span>
                <strong>{lead.status.replaceAll("_", " ")}</strong>
                <small>{lead.founder_linkedin || "no linkedin captured"}</small>
              </div>
            </div>
          </div>
          <div className="tag-group">
            {(lead.signals.length ? lead.signals : ["No personalization signals captured"]).map((signal) => (
              <span key={signal} className="signal-tag">
                {signal}
              </span>
            ))}
          </div>
          <div className="tag-group">
            {(lead.services.length ? lead.services : ["No services extracted"]).map((service) => (
              <span key={service} className="signal-tag">
                {service}
              </span>
            ))}
          </div>
        </div>
        <div className="panel">
          <h2>Company Profile</h2>
          <div className="detail-summary">
            <div className="detail-title-row">
              <div>
                <h3>{lead.company_profile?.summary || "Profile pending"}</h3>
                <p>{lead.company_profile?.positioning || "No positioning extracted yet."}</p>
              </div>
            </div>
            <div className="tag-group">
              {(lead.company_profile?.key_services?.length ? lead.company_profile.key_services : ["No key services yet"]).map((item) => (
                <span key={item} className="signal-tag">
                  {item}
                </span>
              ))}
            </div>
            <div className="tag-group">
              {(lead.company_profile?.credibility_signals?.length
                ? lead.company_profile.credibility_signals
                : ["No credibility signals yet"]).map((item) => (
                <span key={item} className="signal-tag">
                  {item}
                </span>
              ))}
            </div>
            <p className="supporting-text">
              {lead.company_profile?.outreach_angle || "No outreach angle was synthesized yet."}
            </p>
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
