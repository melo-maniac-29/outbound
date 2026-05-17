"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, RefreshCw, Save } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function SettingsPage() {
  const [prompt, setPrompt] = useState("");
  const [dedupeAcrossDb, setDedupeAcrossDb] = useState(true);
  const [bucketRounds, setBucketRounds] = useState("6");
  const [variantLimit, setVariantLimit] = useState("4");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`${API_URL}/api/settings`);
      const data = await res.json();
      setPrompt(data.draft_system_prompt ?? "");
      setDedupeAcrossDb((data.search_dedupe_across_db ?? "true").toString().toLowerCase() === "true");
      setBucketRounds((data.search_bucket_rounds ?? "6").toString());
      setVariantLimit((data.search_variant_limit ?? "4").toString());
      setLoading(false);
    };
    void load();
  }, []);

  const save = async () => {
    setSaving(true);
    setMessage(null);
    const res = await fetch(`${API_URL}/api/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        draft_system_prompt: prompt,
        search_dedupe_across_db: String(dedupeAcrossDb),
        search_bucket_rounds: bucketRounds,
        search_variant_limit: variantLimit,
      }),
    });
    if (res.ok) {
      setMessage("Settings saved.");
    } else {
      setMessage("Failed to save settings.");
    }
    setSaving(false);
  };

  return (
    <main className="shell">
      <section className="panel route-panel">
        <Link href="/dashboard" className="back-link">
          <ArrowLeft size={16} />
          Back to dashboard
        </Link>
        <p className="eyebrow">Settings</p>
        <h1 className="route-title">Draft System Prompt</h1>
        <p className="hero-text">This prompt is used by the draft node for all future email sequence generation.</p>
      </section>

      <section className="panel">
        {loading ? (
          <div className="empty-state">
            <RefreshCw className="animate-spin" />
            Loading settings...
          </div>
        ) : (
          <>
            <label className="field">
              <span>System prompt</span>
              <textarea className="text-area" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={18} />
            </label>
            <label className="field">
              <span>Search dedupe across whole DB</span>
              <select className="text-input" value={String(dedupeAcrossDb)} onChange={(e) => setDedupeAcrossDb(e.target.value === "true")}>
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </label>
            <label className="field">
              <span>Search bucket rounds</span>
              <input
                className="text-input"
                type="number"
                min={1}
                max={12}
                value={bucketRounds}
                onChange={(e) => setBucketRounds(e.target.value)}
              />
            </label>
            <label className="field">
              <span>Search variant limit per bucket</span>
              <input
                className="text-input"
                type="number"
                min={1}
                max={8}
                value={variantLimit}
                onChange={(e) => setVariantLimit(e.target.value)}
              />
            </label>
            <p className="supporting-text">
              Exact domain repeats are still blocked by the database unique index. This setting controls how aggressively
              the search loop filters already-known domains before saving a new lead.
            </p>
            <div className="control-row">
              <button className="primary-button" type="button" onClick={save} disabled={saving}>
                {saving ? <RefreshCw size={18} className="animate-spin" /> : <Save size={18} />}
                Save Prompt
              </button>
            </div>
            {message && <div className="info-banner">{message}</div>}
          </>
        )}
      </section>
    </main>
  );
}
