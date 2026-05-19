"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Building2, ExternalLink, Globe, Mail, RefreshCw, Sparkles, Trash2, User } from "lucide-react";

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
  source_url: string | null;
};

export default function LeadDetailPage() {
  const params = useParams<{ leadId: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${API_URL}/api/leads/${params.leadId}`);
        if (!res.ok) {
          const data = await res.json().catch(() => null);
          throw new Error(data?.detail ?? `Lead request failed with ${res.status}`);
        }
        const data = await res.json();
        setLead(data);
        setLoadError(null);
      } catch (err) {
        console.error(err);
        setLead(null);
        setLoadError(err instanceof Error ? err.message : "Failed to load lead.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [params.leadId]);

  const deleteLead = async () => {
    setWorking(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/leads/${params.leadId}`, { method: "DELETE" });
      if (res.ok) {
        router.push("/leads");
        router.refresh();
        return;
      }
      const data = await res.json().catch(() => null);
      setMessage(data?.detail ?? "Failed to delete lead.");
    } catch (err) {
      console.error(err);
      setMessage("Failed to delete lead.");
    } finally {
      setWorking(false);
    }
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
        <div className="panel empty-state">{loadError ?? "Lead not found."}</div>
      </main>
    );
  }

  const profile = lead.company_profile || {};
  const hasProfile = !!(profile.summary || profile.positioning || profile.audience);
  const emailLabels = ["Day 0 — Initial Reach", "Day 3 — Follow Up", "Day 10 — Close the Loop"];

  return (
    <main className="shell">
      {/* Header */}
      <section className="panel route-panel">
        <Link href="/leads" className="back-link">
          <ArrowLeft size={16} />
          Back to leads
        </Link>
        <p className="eyebrow">Lead Detail</p>
        <h1 className="route-title">{lead.company_name || lead.domain || lead.search_query}</h1>
        <p className="hero-text">{lead.domain || lead.search_query}</p>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "14px" }}>
          <span className={`status-badge status-${lead.status}`}>{lead.status.replaceAll("_", " ")}</span>
          {lead.run_id && (
            <Link className="utility-link" href={`/runs/${lead.run_id}`}>
              Open parent run
            </Link>
          )}
          {lead.domain && (
            <a className="utility-link" href={`https://${lead.domain}`} target="_blank" rel="noreferrer">
              <Globe size={14} />
              Visit website
            </a>
          )}
        </div>
        <div className="action-row">
          <button className="danger-button ghost" type="button" onClick={deleteLead} disabled={working}>
            <Trash2 size={16} />
            Delete Lead
          </button>
        </div>
        {message && <div className="info-banner">{message}</div>}
      </section>

      {/* Key Metrics */}
      <section className="route-meta-grid" style={{ marginTop: "18px" }}>
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
          <ExternalLink size={16} />
          <div>
            <span>LinkedIn</span>
            {lead.founder_linkedin ? (
              <a href={lead.founder_linkedin} target="_blank" rel="noreferrer" style={{ fontWeight: 700 }}>
                View Profile
              </a>
            ) : (
              <strong style={{ color: "var(--muted)" }}>Not found</strong>
            )}
          </div>
        </div>
        <div className="metric-box">
          <Building2 size={16} />
          <div>
            <span>Services</span>
            <strong>{lead.services.length || "0"} extracted</strong>
          </div>
        </div>
        <div className="metric-box">
          <Sparkles size={16} />
          <div>
            <span>Signals</span>
            <strong>{lead.signals.length || "0"} captured</strong>
          </div>
        </div>
      </section>

      <section className="workspace lower-workspace" style={{ marginTop: "18px" }}>
        {/* Company Profile */}
        <div className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Company Profile</p>
              <h2>About {lead.company_name || lead.domain}</h2>
            </div>
          </div>

          {hasProfile ? (
            <div className="detail-layout">
              {/* Summary */}
              {profile.summary && (
                <div className="detail-summary">
                  <p style={{ margin: 0, lineHeight: 1.7, fontFamily: "'Segoe UI', sans-serif" }}>
                    {profile.summary}
                  </p>
                </div>
              )}

              {/* Positioning & Audience */}
              <div className="info-grid">
                {profile.positioning && (
                  <div className="info-card">
                    <div>
                      <strong>Positioning</strong>
                      <p>{profile.positioning}</p>
                    </div>
                  </div>
                )}
                {profile.audience && (
                  <div className="info-card">
                    <div>
                      <strong>Target Audience</strong>
                      <p>{profile.audience}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Outreach Angle */}
              {profile.outreach_angle && (
                <div style={{
                  padding: "16px",
                  borderRadius: "18px",
                  background: "rgba(29, 107, 98, 0.08)",
                  border: "1px solid rgba(29, 107, 98, 0.2)",
                }}>
                  <span style={{
                    display: "block",
                    marginBottom: "8px",
                    fontFamily: "'Segoe UI', sans-serif",
                    fontSize: "0.78rem",
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase" as const,
                    color: "var(--teal)",
                  }}>
                    Outreach Angle
                  </span>
                  <p style={{ margin: 0, fontFamily: "'Segoe UI', sans-serif", lineHeight: 1.6 }}>
                    {profile.outreach_angle}
                  </p>
                </div>
              )}

              {/* Key Services */}
              {(profile.key_services?.length ?? 0) > 0 && (
                <div>
                  <span className="sequence-step">Key Services</span>
                  <div className="tag-group" style={{ marginTop: "8px" }}>
                    {profile.key_services!.map((service) => (
                      <span key={service} className="signal-tag">{service}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Credibility Signals */}
              {(profile.credibility_signals?.length ?? 0) > 0 && (
                <div>
                  <span className="sequence-step">Credibility Signals</span>
                  <div className="tag-group" style={{ marginTop: "8px" }}>
                    {profile.credibility_signals!.map((signal) => (
                      <span key={signal} className="signal-tag">{signal}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-inline">No company profile synthesized yet.</div>
          )}
        </div>

        {/* Extracted Data */}
        <div className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Extracted Data</p>
              <h2>Signals & Services</h2>
            </div>
          </div>

          <div className="detail-layout">
            <div>
              <span className="sequence-step">Personalization Signals</span>
              {lead.signals.length > 0 ? (
                <div className="tag-group" style={{ marginTop: "8px" }}>
                  {lead.signals.map((signal) => (
                    <span key={signal} className="signal-tag">{signal}</span>
                  ))}
                </div>
              ) : (
                <div className="empty-inline" style={{ marginTop: "8px" }}>No signals captured yet.</div>
              )}
            </div>

            <div>
              <span className="sequence-step">Services Offered</span>
              {lead.services.length > 0 ? (
                <div className="tag-group" style={{ marginTop: "8px" }}>
                  {lead.services.map((service) => (
                    <span key={service} className="signal-tag">{service}</span>
                  ))}
                </div>
              ) : (
                <div className="empty-inline" style={{ marginTop: "8px" }}>No services extracted yet.</div>
              )}
            </div>
          </div>
        </div>

        {/* Email Drafts — full width */}
        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <div className="panel-head">
            <div>
              <p className="eyebrow">Outreach Sequence</p>
              <h2>Email Drafts</h2>
            </div>
            {lead.email_sequence.length > 0 && (
              <span className="status-badge status-READY_TO_SEND">{lead.email_sequence.length} emails drafted</span>
            )}
          </div>

          {lead.email_sequence.length === 0 ? (
            <div className="empty-state">
              <Mail size={24} />
              <p>No draft sequence generated yet.</p>
            </div>
          ) : (
            <div className="detail-layout">
              {lead.email_sequence.map((email, index) => (
                <article key={`${lead.lead_id}-email-${index}`} className="sequence-card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                    <span className="sequence-step">{emailLabels[index] || `Email ${index + 1}`}</span>
                  </div>
                  <p>{email}</p>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
