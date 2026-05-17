"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Building2, Mail, RefreshCw, Square, Trash2, User } from "lucide-react";

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

export default function RunDetailPage() {
  const params = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`${API_URL}/api/runs/${params.runId}`);
      const data = await res.json();
      setRun(data);
      setLoading(false);
    };
    void load();
  }, [params.runId]);

  const refreshRun = async () => {
    const res = await fetch(`${API_URL}/api/runs/${params.runId}`);
    const data = await res.json();
    setRun(data);
  };

  const stopRun = async () => {
    setWorking(true);
    setMessage(null);
    const res = await fetch(`${API_URL}/api/runs/${params.runId}/stop`, { method: "POST" });
    if (res.ok) {
      setMessage("Run stop requested.");
      await refreshRun();
    } else {
      const data = await res.json().catch(() => null);
      setMessage(data?.detail ?? "Failed to stop run.");
    }
    setWorking(false);
  };

  const deleteRun = async () => {
    setWorking(true);
    setMessage(null);
    const res = await fetch(`${API_URL}/api/runs/${params.runId}?purge_leads=true`, { method: "DELETE" });
    if (res.ok) {
      router.push("/dashboard");
      router.refresh();
      return;
    }
    const data = await res.json().catch(() => null);
    setMessage(data?.detail ?? "Failed to delete run.");
    setWorking(false);
  };

  if (loading) {
    return (
      <main className="shell">
        <div className="panel empty-state">
          <RefreshCw className="animate-spin" />
          Loading run...
        </div>
      </main>
    );
  }

  if (!run) {
    return (
      <main className="shell">
        <div className="panel empty-state">Run not found.</div>
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
        <p className="eyebrow">Run Detail</p>
        <h1 className="route-title">{run.query}</h1>
        <div className="route-meta-grid">
          <div className="metric-box">
            <Building2 size={16} />
            <div>
              <span>Requested</span>
              <strong>{run.requested_companies}</strong>
            </div>
          </div>
          <div className="metric-box">
            <Building2 size={16} />
            <div>
              <span>Discovered</span>
              <strong>{run.discovered_companies}</strong>
            </div>
          </div>
          <div className="metric-box">
            <Mail size={16} />
            <div>
              <span>Processed</span>
              <strong>{run.processed_companies}</strong>
            </div>
          </div>
          <div className="metric-box">
            <User size={16} />
            <div>
              <span>Status</span>
              <strong>{run.status}</strong>
            </div>
          </div>
        </div>
        <div className="action-row">
          {run.status === "RUNNING" ? (
            <button className="danger-button" type="button" onClick={stopRun} disabled={working}>
              <Square size={16} />
              Stop Run
            </button>
          ) : null}
          <button className="danger-button ghost" type="button" onClick={deleteRun} disabled={working}>
            <Trash2 size={16} />
            Delete Run
          </button>
        </div>
        {run.error && <div className="error-banner">{run.error}</div>}
        {message && <div className="info-banner">{message}</div>}
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
