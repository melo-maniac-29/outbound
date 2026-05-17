import Link from "next/link";
import { ArrowRight, CheckCircle2, LayoutDashboard, Route, ShieldCheck, Sparkles } from "lucide-react";

const highlights = [
  {
    title: "Search to draft",
    text: "Discover agencies, crawl their sites, extract the decision-maker, and generate a ready-to-review sequence.",
    icon: Route,
  },
  {
    title: "Review-first output",
    text: "The pipeline stops at READY_TO_SEND until the send flow is re-enabled and validated.",
    icon: ShieldCheck,
  },
  {
    title: "PostgreSQL-backed",
    text: "Runs and leads persist in PostgreSQL so recovery and inspection stay simple.",
    icon: CheckCircle2,
  },
];

const steps = [
  "Enter a search query or a direct domain.",
  "Review the latest runs and lead records in the dashboard.",
  "Open a lead, inspect the extracted signals, and approve drafts later.",
];

export default function LandingPage() {
  return (
    <main className="landing-shell">
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="eyebrow">Outbound Nexus</p>
          <h1>First page, proper dashboard, and a pipeline that stays honest about what is live.</h1>
          <p className="landing-text">
            This workspace is now split the right way: a clean landing page, a separate dashboard, and detail pages for
            runs and leads. The backend stays review-first until the send flow is ready.
          </p>
          <div className="cta-row">
            <Link className="primary-cta" href="/dashboard">
              Open Dashboard
              <ArrowRight size={18} />
            </Link>
            <Link className="secondary-cta" href="/settings">
              Prompt Settings
            </Link>
          </div>
        </div>

        <div className="landing-aside">
          <div className="landing-card accent-card">
            <p className="mini-label">Current state</p>
            <strong>Review-first</strong>
            <span>Ready to send is the terminal state for now.</span>
          </div>
          <div className="landing-card">
            <p className="mini-label">Primary tools</p>
            <strong>LangGraph + PostgreSQL</strong>
            <span>Discovery, crawl, extraction, and persistence stay wired together.</span>
          </div>
        </div>
      </section>

      <section className="feature-grid">
        {highlights.map((item) => {
          const Icon = item.icon;
          return (
            <article key={item.title} className="feature-card">
              <Icon size={20} />
              <h2>{item.title}</h2>
              <p>{item.text}</p>
            </article>
          );
        })}
      </section>

      <section className="split-panel">
        <div className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Workflow</p>
              <h2>What happens next</h2>
            </div>
          </div>
          <div className="step-list">
            {steps.map((step, index) => (
              <div key={step} className="step-item">
                <span>{index + 1}</span>
                <p>{step}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Navigation</p>
              <h2>Useful pages</h2>
            </div>
          </div>
          <div className="route-links">
            <Link href="/dashboard" className="route-link">
              <LayoutDashboard size={18} />
              Dashboard
            </Link>
            <Link href="/settings" className="route-link">
              <Sparkles size={18} />
              Prompt settings
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
