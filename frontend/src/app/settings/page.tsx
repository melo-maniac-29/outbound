"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, RefreshCw, Save } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function SettingsPage() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`${API_URL}/api/settings`);
      const data = await res.json();
      setPrompt(data.draft_system_prompt ?? "");
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
      body: JSON.stringify({ draft_system_prompt: prompt }),
    });
    if (res.ok) {
      setMessage("Draft system prompt saved.");
    } else {
      setMessage("Failed to save settings.");
    }
    setSaving(false);
  };

  return (
    <main className="shell">
      <section className="panel route-panel">
        <Link href="/" className="back-link"><ArrowLeft size={16} />Back to dashboard</Link>
        <p className="eyebrow">Settings</p>
        <h1 className="route-title">Draft System Prompt</h1>
        <p className="hero-text">This prompt is used by the draft node for all future email sequence generation.</p>
      </section>

      <section className="panel">
        {loading ? (
          <div className="empty-state"><RefreshCw className="animate-spin" />Loading settings...</div>
        ) : (
          <>
            <label className="field">
              <span>System prompt</span>
              <textarea
                className="text-area"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={18}
              />
            </label>
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
