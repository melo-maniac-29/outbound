"use client";

import { useState, useEffect } from 'react';
import { Search, Loader2, Globe, User, Mail, Zap, RefreshCw } from 'lucide-react';

const API_URL = 'http://localhost:8000';

export default function Home() {
  const [query, setQuery] = useState('');
  const [leads, setLeads] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchLeads = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${API_URL}/api/leads`);
      const data = await res.json();
      setLeads(data.leads || []);
    } catch (err) {
      console.error("Failed to fetch leads", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLeads();
    const interval = setInterval(fetchLeads, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    
    setIsSearching(true);
    try {
      await fetch(`${API_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      setQuery('');
      fetchLeads();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="app-container">
      <header>
        <h1>Outbound Nexus</h1>
        <p className="subtitle">Autonomous AI Agent Outreach System</p>
      </header>

      <form className="search-container" onSubmit={handleSearch}>
        <input 
          type="text" 
          className="search-input" 
          placeholder="e.g. boutique email marketing agency founder linkedin..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={isSearching}
        />
        <button type="submit" className="btn-primary" disabled={isSearching}>
          {isSearching ? <Loader2 className="animate-spin" /> : <Search />}
          Initiate Agent
        </button>
      </form>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Active Leads Timeline</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          {isRefreshing ? <RefreshCw size={16} className="animate-spin" /> : <div style={{width:8, height:8, borderRadius:'50%', background:'var(--success)'}}></div>}
          Live Sync Active
        </div>
      </div>

      <div className="leads-grid">
        {leads.length === 0 ? (
          <div style={{gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--text-muted)'}}>
            <Zap size={48} style={{ margin: '0 auto 1rem', opacity: 0.2 }} />
            <p>No leads discovered yet. Enter a search query to dispatch the AI agent.</p>
          </div>
        ) : leads.map((lead) => (
          <div key={lead.lead_id} className="glass-panel lead-card">
            <div className="lead-header">
              <div className="lead-domain">
                <Globe size={20} color="var(--accent-primary)" />
                {lead.domain || lead.search_query}
              </div>
              <span className={`status-badge status-${lead.status}`}>
                {lead.status.replace('_', ' ')}
              </span>
            </div>

            <div className="data-row">
              <div className="data-label"><User size={16} />Founder</div>
              <div className="data-value">{lead.founder_name || 'Extracting...'}</div>
            </div>
            
            <div className="data-row">
              <div className="data-label"><Mail size={16} />Email</div>
              <div className="data-value">{lead.email || 'Pending...'}</div>
            </div>

            {lead.email_sequence && lead.email_sequence.length > 0 && (
              <div className="email-sequence">
                <h4>Generated Sequence ({lead.email_sequence.length} Emails)</h4>
                <div className="email-body">
                  {lead.email_sequence[0]}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
