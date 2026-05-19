import Link from "next/link";
import { ArrowRight, Brain, Globe, LayoutDashboard, Mail, Search, Settings, ShieldCheck, Sparkles, Zap } from "lucide-react";

const pipeline = [
  { icon: Search, label: "Search", desc: "Tavily finds companies" },
  { icon: Globe, label: "Crawl", desc: "Scrapes up to 8 pages" },
  { icon: Brain, label: "Extract", desc: "Pulls founder & signals" },
  { icon: Mail, label: "Enrich", desc: "Finds verified email" },
  { icon: Sparkles, label: "Draft", desc: "3-email sequence" },
  { icon: ShieldCheck, label: "Review", desc: "You approve first" },
];

export default function LandingPage() {
  return (
    <main className="landing-shell">
      <section className="landing-hero">
        <div>
          <p className="eyebrow">Outbound Nexus</p>
          <h1>Search to draft. You approve the send.</h1>
          <p className="hero-sub">
            Fully automated lead discovery, website crawling, founder extraction, and personalized email drafting.
            Everything stops for human review before anything goes out.
          </p>
          <div className="cta-row">
            <Link className="btn btn-primary" href="/dashboard">
              Open Dashboard <ArrowRight size={16} />
            </Link>
            <Link className="btn btn-ghost" href="/settings">
              <Settings size={14} /> Settings
            </Link>
          </div>
        </div>
        <div className="hero-aside">
          <div className="hero-card">
            <p className="hero-card-label">Pipeline mode</p>
            <p className="hero-card-value">Review-first</p>
            <p className="hero-card-desc">Drafts are held until you approve them.</p>
          </div>
          <div className="hero-card">
            <p className="hero-card-label">Stack</p>
            <p className="hero-card-value">LangGraph + PostgreSQL</p>
            <p className="hero-card-desc">Stateful workflow with crash recovery.</p>
          </div>
        </div>
      </section>

      <div className="pipeline-grid">
        {pipeline.map((step, i) => {
          const Icon = step.icon;
          return (
            <div key={step.label} className="pipeline-step">
              <p className="step-num">0{i + 1}</p>
              <Icon size={20} style={{ marginBottom: 8, color: "var(--ink-secondary)" }} />
              <p className="step-name">{step.label}</p>
              <p className="step-desc">{step.desc}</p>
            </div>
          );
        })}
      </div>

      <div className="landing-bottom">
        <div>
          <p className="section-label" style={{ marginBottom: 16 }}>Navigate</p>
          <div className="landing-nav-links">
            <Link href="/dashboard" className="landing-nav-link"><LayoutDashboard size={16} /> Dashboard</Link>
            <Link href="/runs" className="landing-nav-link"><Zap size={16} /> Runs</Link>
            <Link href="/leads" className="landing-nav-link"><Mail size={16} /> Leads</Link>
            <Link href="/settings" className="landing-nav-link"><Settings size={16} /> Settings</Link>
          </div>
        </div>
        <div>
          <p className="section-label" style={{ marginBottom: 16 }}>How it works</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              "Enter a search query or paste a direct domain.",
              "Pipeline discovers, crawls, extracts, and drafts automatically.",
              "Open any lead to review signals and email drafts before sending.",
            ].map((s, i) => (
              <div key={i} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: "0.78rem", fontWeight: 700, color: "var(--accent)", minWidth: 24 }}>0{i+1}</span>
                <p style={{ color: "var(--ink-secondary)", fontSize: "0.88rem", lineHeight: 1.6 }}>{s}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
