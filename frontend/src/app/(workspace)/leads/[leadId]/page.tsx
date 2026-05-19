"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Copy, ExternalLink, RefreshCw, Trash2 } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Lead = {
  lead_id: string; company_name: string | null; domain: string | null; search_query: string;
  founder_name: string | null; founder_linkedin: string | null; founder_confidence: number;
  email: string | null; email_confidence: number; signals: string[]; services: string[];
  email_sequence: string[];
  company_profile?: { summary?: string; positioning?: string; audience?: string; key_services?: string[]; credibility_signals?: string[]; outreach_angle?: string; };
  status: string; run_id: string | null; source_url: string | null;
};

function statusBadge(s: string) {
  const m: Record<string, string> = { READY_TO_SEND: "badge-ready", DEAD_LEAD: "badge-dead", SENT: "badge-completed" };
  return `badge ${m[s] || "badge-default"}`;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button onClick={copy} className="btn btn-ghost" style={{ padding: "2px 8px", fontSize: "0.75rem" }}>
      <Copy size={12} /> {copied ? "Copied!" : "Copy"}
    </button>
  );
}

export default function LeadDetailPage() {
  const params = useParams<{ leadId: string }>();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    abortRef.current = ac;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/leads/${params.leadId}`, { signal: ac.signal });
        if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || "Not found");
        setLead(await res.json()); setErr(null);
      } catch (e) {
        if (e instanceof Error && e.name === "AbortError") return;
        setLead(null); setErr(e instanceof Error ? e.message : "Failed.");
      } finally { setLoading(false); }
    })();
    return () => ac.abort();
  }, [params.leadId]);

  const del = async () => {
    setWorking(true);
    try {
      const r = await fetch(`${API_URL}/api/leads/${params.leadId}`, { method: "DELETE" });
      if (r.ok) { router.push("/leads"); return; }
      const d = await r.json().catch(() => null);
      setMsg(d?.detail || "Failed to delete.");
    } catch { setMsg("Failed."); } finally { setWorking(false); }
  };

  if (loading) return <main className="shell"><div className="empty"><RefreshCw className="animate-spin" size={16} style={{ marginRight: 8 }} /> Loading…</div></main>;
  if (!lead) return <main className="shell"><div className="empty">{err || "Not found."}</div></main>;

  const p = lead.company_profile || {};
  const emailLabels = ["Day 0 — Initial outreach", "Day 3 — Follow up", "Day 10 — Close the loop"];

  return (
    <main className="shell">
      <div className="page-header">
        <Link href="/leads" className="back-link"><ArrowLeft size={14} /> Leads</Link>
        <p className="eyebrow">Lead Detail</p>
        <h1>{lead.company_name || lead.domain || lead.search_query}</h1>
        <div className="meta-row">
          <span className={statusBadge(lead.status)}>{lead.status.replaceAll("_", " ")}</span>
          {lead.domain && <a className="btn-link" href={`https://${lead.domain}`} target="_blank" rel="noreferrer"><ExternalLink size={13} /> {lead.domain}</a>}
          {lead.founder_linkedin && <a className="btn-link" href={lead.founder_linkedin} target="_blank" rel="noreferrer"><ExternalLink size={13} /> LinkedIn</a>}
          {lead.run_id && <Link className="btn-link" href={`/runs/${lead.run_id}`}>View run</Link>}
          <button className="btn btn-danger" onClick={del} disabled={working}><Trash2 size={14} /> Delete</button>
        </div>
      </div>

      {msg && <div className="callout callout-error" style={{ marginBottom: 24 }}>{msg}</div>}

      {/* Key data grid */}
      <div className="surface-grid" style={{ marginBottom: 32 }}>
        <div className="surface-cell">
          <p className="cell-label">Founder</p>
          <p className="cell-value">{lead.founder_name || "—"}</p>
          <p className="cell-sub">{Math.round(lead.founder_confidence * 100)}% confidence</p>
        </div>
        <div className="surface-cell">
          <p className="cell-label">Email</p>
          <p className="cell-value" style={{ fontFamily: "var(--mono)", fontSize: "0.88rem" }}>{lead.email || "—"}</p>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <p className="cell-sub" style={{ margin: 0 }}>{Math.round(lead.email_confidence * 100)}% confidence</p>
            {lead.email && <CopyButton text={lead.email} />}
          </div>
        </div>
        <div className="surface-cell">
          <p className="cell-label">Services extracted</p>
          <p className="cell-value">{lead.services.length}</p>
        </div>
        <div className="surface-cell">
          <p className="cell-label">Signals captured</p>
          <p className="cell-value">{lead.signals.length}</p>
        </div>
      </div>

      <div className="two-col">
        {/* Company Profile */}
        <div className="section">
          <h2 className="section-title" style={{ marginBottom: 16 }}>Company Profile</h2>
          {p.summary ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <p style={{ color: "var(--ink-secondary)", lineHeight: 1.75 }}>{p.summary}</p>
              {p.positioning && <div className="surface" style={{ padding: 16 }}><p className="cell-label">Positioning</p><p style={{ color: "var(--ink-secondary)", marginTop: 4, lineHeight: 1.6 }}>{p.positioning}</p></div>}
              {p.audience && <div className="surface" style={{ padding: 16 }}><p className="cell-label">Audience</p><p style={{ color: "var(--ink-secondary)", marginTop: 4, lineHeight: 1.6 }}>{p.audience}</p></div>}
              {p.outreach_angle && <div className="angle-block"><p className="angle-label">Outreach Angle</p><p style={{ color: "var(--ink)", lineHeight: 1.6 }}>{p.outreach_angle}</p></div>}
              {(p.key_services?.length ?? 0) > 0 && <div><p className="cell-label" style={{ marginBottom: 8 }}>Key Services</p><div className="tag-group">{p.key_services!.map(s => <span key={s} className="tag">{s}</span>)}</div></div>}
              {(p.credibility_signals?.length ?? 0) > 0 && <div><p className="cell-label" style={{ marginBottom: 8 }}>Credibility</p><div className="tag-group">{p.credibility_signals!.map(s => <span key={s} className="tag">{s}</span>)}</div></div>}
            </div>
          ) : <div className="empty"><p>No profile yet.</p></div>}
        </div>

        {/* Signals & Services */}
        <div className="section">
          <h2 className="section-title" style={{ marginBottom: 16 }}>Extracted Data</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div>
              <p className="cell-label" style={{ marginBottom: 8 }}>Signals ({lead.signals.length})</p>
              {lead.signals.length > 0
                ? <div className="tag-group">{lead.signals.map((s, i) => <span key={i} className="tag">{s}</span>)}</div>
                : <p style={{ color: "var(--ink-muted)", fontSize: "0.85rem" }}>None captured.</p>}
            </div>
            <div>
              <p className="cell-label" style={{ marginBottom: 8 }}>Services ({lead.services.length})</p>
              {lead.services.length > 0
                ? <div className="tag-group">{lead.services.map((s, i) => <span key={i} className="tag">{s}</span>)}</div>
                : <p style={{ color: "var(--ink-muted)", fontSize: "0.85rem" }}>None extracted.</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Email Sequence */}
      <div className="section" style={{ marginTop: 8 }}>
        <div className="section-head">
          <h2 className="section-title">Email Sequence</h2>
          {lead.email_sequence.length > 0 && <span className="badge badge-ready">{lead.email_sequence.length} drafted</span>}
        </div>
        {lead.email_sequence.length === 0 ? (
          <div className="empty"><p>No drafts generated yet.</p></div>
        ) : (
          lead.email_sequence.map((email, i) => (
            <div key={`${lead.lead_id}-e-${i}`} className="seq-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <p className="seq-label">{emailLabels[i] || `Email ${i + 1}`}</p>
                <CopyButton text={email} />
              </div>
              <p className="seq-body">{email}</p>
            </div>
          ))
        )}
      </div>
    </main>
  );
}
