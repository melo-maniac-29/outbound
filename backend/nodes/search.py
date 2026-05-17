import os
from urllib.parse import urlparse
from tavily import TavilyClient

def normalize_url(url: str) -> str:
    """Extract domain from URL for duplicate filtering."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return url

def search_node(state_or_query) -> dict:
    """
    Search discovery using Tavily.
    Input: search string
    Output: list of company URLs / domains
    """
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    # If called within a graph with LeadState, it might extract the query.
    # Otherwise, it can be called directly to generate leads.
    query = state_or_query.search_query if hasattr(state_or_query, 'search_query') else state_or_query
    
    # We want to find company websites
    response = client.search(
        query=query,
        search_depth="basic",
        max_results=5
    )
    
    urls = []
    seen_domains = set()
    
    for r in response.get("results", []):
        url = r.get("url")
        domain = normalize_url(url)
        
        # Duplicate filtering
        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            urls.append({
                "source_url": url,
                "domain": domain,
                "title": r.get("title")
            })
            
    return {"discovered_urls": urls}
