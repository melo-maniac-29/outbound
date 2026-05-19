"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, RefreshCw, Square, Trash2, Wifi, WifiOff } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Lead = { lead_id: string; company_name: string | null; domain: string | null; founder_name: string | null; email: string | null; status: string; };
type RunDetail = { run_id: string; query: string; requested_companies: number; discovered_companies: number; processed_companies: number; ready_to_send_count?: number; source_type: string; status: string; error?: string | null; leads: Lead[]; };

const TERMINAL = new Set(["COMPLETED", "EXHAUSTED", "STOPPED", "FAILED"]);

function statusBadge(s: string) {
  const m: Record<string, string> = { RUNNING: "badge-running", COMPLETED: "badge-completed", EXHAUSTED: "badge-failed", STOPPED: "badge-default", FAILED: "badge-failed", READY_TO_SEND: "badge-ready", DEAD_LEAD: "badge-dead" };
  return `badge ${m[s] || "badge-default"}`;
}

export default function RunDetailPage() {
  const params = useParams<{ runId: string }>();
  const router = useRouter();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [connected, setConnected] = useState(false);
  const [working, setWorking] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let retryTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      esRef.current?.close();
      const es = new EventSource(`${API_URL}/api/runs/${params.runId}/stream`);
      esRef.current = es;

      es.onopen = () => { setConnected(true); setErr(null); };

      es.onmessage = (evt) => {
        try {
          const data: RunDetail = JSON.parse(evt.data);
          setRun(data);
        } catch { /* ignore */ }
      };

      es.addEventListener("done", () => {
        setConnected(false);
        es.close();
        // Fetch one final snapshot after stream closes
        fetch(`${API_URL}/api/runs/${params.runId}`)
          .then(r => r.json()).then(setRun).catch(() => null);
      });

      es.addEventListener("error", (evt: Event & { data?: string }) => {
        if (evt instanceof MessageEvent) {
          try { const d = JSON.parse(evt.data); setErr(d.detail || "Stream error"); } catch { setErr("Stream error"); }
          es.close(); return;
        }
        setConnected(false);
        es.close();
        retryTimer = setTimeout(connect, 5000);
      });
    };

    connect();

    return () => {
      clearTimeout(retryTimer);
      esRef.current?.close();
    };
  }, [params.runId]);

  const stop = async () => {
    setWorking(true); setMsg(null);
    try {
      const r = await fetch(`${API_URL}/api/runs/${params.runId}/stop`, { method: "POST" });
      setMsg(r.ok ? "Stop requested." : "Failed.");
    } catch { setMsg("Failed."); } finally { setWorking(false); }
  };

  const del = async () => {
    setWorking(true);
    try {
      const r = await fetch(`${API_URL}/api/runs/${params.runId}?purge_leads=true`, { method: "DELETE" });
      if (r.ok) { router.push("/runs"); return; }
      setMsg("Failed to delete.");
    } catch { setMsg("Failed."); } finally { setWorking(false); }
  };

  if (!run && !err) return (
    <main className="shell">
      <div className="empty" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <RefreshCw className="animate-spin" size={16} /> Connecting to stream…
      </div>
    </main>
  );

  if (err && !run) return (
    <main className="shell"><div className="empty">{err}</div></main>
  );

  if (!run) return null;

  const ready = typeof run.ready_to_send_count === "number" ? run.ready_to_send_count : run.leads.filter(l => l.status === "READY_TO_SEND").length;
  const isRunning = run.status === "RUNNING";

  return (
    <main className="shell">
      <div className="page-header">
        <Link href="/runs" className="back-link"><ArrowLeft size={14} /> Runs</Link>
        <p className="eyebrow">Run Detail</p>
        <h1>{run.query}</h1>
        <div className="meta-row">
          <span className={statusBadge(run.status)}>{run.status}</span>
          <span style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", gap: 5, color: connected ? "var(--teal)" : "var(--muted)" }}>
            {connected ? <><Wifi size={11} /> live</> : <><WifiOff size={11} /> offline</>}
          </span>
          {isRunning && <button className="btn btn-danger" onClick={stop} disabled={working}><Square size={14} /> Stop</button>}
          <button className="btn btn-ghost" onClick={del} disabled={working}><Trash2 size={14} /> Delete</button>
        </div>
      </div>

      {run.error && <div className="callout callout-error" style={{ marginBottom: 24 }}>{run.error}</div>}
      {msg && <div className="callout callout-info" style={{ marginBottom: 24 }}>{msg}</div>}

      <div className="surface-grid" style={{ marginBottom: 40 }}>
        <div className="surface-cell"><p className="cell-label">Target</p><p className="cell-value">{run.requested_companies} companies</p></div>
        <div className="surface-cell"><p className="cell-label">Draft-ready</p><p className="cell-value" style={{ color: "var(--teal)" }}>{ready}/{run.requested_companies}</p></div>
        <div className="surface-cell"><p className="cell-label">Leads attempted</p><p className="cell-value">{run.discovered_companies}</p></div>
        <div className="surface-cell"><p className="cell-label">Pipeline finished</p><p className="cell-value">{run.processed_companies}</p></div>
      </div>

      <div className="section">
        <div className="section-head">
          <h2 className="section-title">Leads ({run.leads.length})</h2>
        </div>
        <div className="data-list">
          {run.leads.map(lead => (
            <Link key={lead.lead_id} href={`/leads/${lead.lead_id}`} className="data-row data-row-3col">
              <div>
                <span className="primary">{lead.company_name || lead.domain}</span>
                <div className="secondary" style={{ marginTop: 2 }}>
                  {lead.founder_name || "founder pending"} · {lead.email || "email pending"}
                </div>
              </div>
              <span className="mono">{lead.domain}</span>
              <span className={statusBadge(lead.status)}>{lead.status.replaceAll("_", " ")}</span>
            </Link>
          ))}
          {run.leads.length === 0 && <div className="empty"><p>No leads yet.</p></div>}
        </div>
      </div>
    </main>
  );
}
