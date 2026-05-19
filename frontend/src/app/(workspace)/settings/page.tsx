"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, RefreshCw, Save } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function SettingsPage() {
  const [dedupeAcrossDb, setDedupeAcrossDb] = useState(true);
  const [bucketRounds, setBucketRounds] = useState("6");
  const [variantLimit, setVariantLimit] = useState("4");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/settings`);
        if (!res.ok) throw new Error();
        const d = await res.json();
        setDedupeAcrossDb((d.search_dedupe_across_db ?? "true").toString().toLowerCase() === "true");
        setBucketRounds((d.search_bucket_rounds ?? "6").toString());
        setVariantLimit((d.search_variant_limit ?? "4").toString());
        setLoadError(null);
      } catch { setLoadError("Failed to load."); } finally { setLoading(false); }
    })();
  }, []);

  const save = async () => {
    setSaving(true); setMessage(null);
    const res = await fetch(`${API_URL}/api/settings`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ search_dedupe_across_db: String(dedupeAcrossDb), search_bucket_rounds: bucketRounds, search_variant_limit: variantLimit }),
    });
    setMessage(res.ok ? "Settings saved." : "Failed to save."); setSaving(false);
  };

  return (
    <main className="shell">
      <div className="page-header">
        <Link href="/dashboard" className="back-link"><ArrowLeft size={14} /> Dashboard</Link>
        <p className="eyebrow">Configuration</p>
        <h1>Search Settings</h1>
        <p>Control how the discovery pipeline finds companies.</p>
      </div>

      {loading ? <div className="empty"><RefreshCw className="animate-spin" /> Loading...</div> : loadError ? <div className="empty">{loadError}</div> : (
        <>
          <div className="surface-grid" style={{ marginBottom: 32 }}>
            <div className="surface-cell">
              <p className="cell-label">Dedupe across DB</p>
              <p className="cell-sub" style={{ marginBottom: 12 }}>Skip domains already in the database, not just the current run.</p>
              <select className="form-input" value={String(dedupeAcrossDb)} onChange={e => setDedupeAcrossDb(e.target.value === "true")}>
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </div>
            <div className="surface-cell">
              <p className="cell-label">Bucket rounds</p>
              <p className="cell-sub" style={{ marginBottom: 12 }}>Query phrasings per search wave. Higher = wider discovery net.</p>
              <input className="form-input" type="number" min={1} max={12} value={bucketRounds} onChange={e => setBucketRounds(e.target.value)} />
            </div>
          </div>

          <div className="surface" style={{ marginBottom: 32 }}>
            <p className="cell-label">Variant limit per bucket</p>
            <p className="cell-sub" style={{ marginBottom: 12 }}>Tavily calls per bucket. Total per wave = rounds × limit.</p>
            <input className="form-input" type="number" min={1} max={8} value={variantLimit} onChange={e => setVariantLimit(e.target.value)} style={{ maxWidth: 200 }} />
          </div>

          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />} Save Settings
          </button>
          {message && <div className={`callout ${message.includes("saved") ? "callout-info" : "callout-error"}`}>{message}</div>}
        </>
      )}
    </main>
  );
}
