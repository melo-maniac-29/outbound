import os
from urllib.parse import urlparse
from tavily import TavilyClient

BLOCKED_DOMAINS = {
    "apple.com",
    "prnewswire.com",
    "practicalecommerce.com",
    "youtube.com",
    "linkedin.com",
    "www.linkedin.com",
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "www.youtube.com",
}


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


def infer_company_name(title: str | None, domain: str) -> str | None:
    stem = domain.split(".")[0].replace("-", " ").replace("_", " ")
    inferred = stem.title() if stem else None
    if title:
        cleaned_title = title.split("|")[0].split("-")[0].strip()
        if cleaned_title and len(cleaned_title.split()) <= 4:
            return cleaned_title
    return inferred


def is_company_candidate(domain: str, url: str) -> bool:
    if not domain:
        return False

    normalized_domain = domain.removeprefix("www.")
    if normalized_domain in BLOCKED_DOMAINS:
        return False

    blocked_suffixes = ("linkedin.com", "youtube.com", "apple.com")
    if normalized_domain.endswith(blocked_suffixes):
        return False

    if normalized_domain.startswith(("careers.", "jobs.", "podcasts.")):
        return False

    parsed = urlparse(url or "")
    lowered_url = (url or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    blocked_markers = (
        "/blog/",
        "/blogs/",
        "/news/",
        "/news-releases/",
        "/case-study",
        "/case-studies",
        "/directory/",
        "/careers",
        "/jobs",
        "/podcast",
        "/watch",
        "/press-release",
    )
    if any(marker in lowered_url for marker in blocked_markers):
        return False

    if path_parts and path_parts[0] in {"in", "company", "posts", "article", "articles"}:
        return False

    allowed_first_parts = {"about", "about-us", "team", "leadership", "contact", "services", "work", "pages"}
    if len(path_parts) > 2 and path_parts[0] not in allowed_first_parts:
        return False

    return True

def search_node(state_or_query, max_companies: int = 5) -> dict:
    """
    Search discovery using Tavily.
    Input: search string
    Output: list of company URLs / domains
    """
    api_key = os.getenv("TAVILY_API_KEY")
    
    # If called within a graph with LeadState, it might extract the query.
    # Otherwise, it can be called directly to generate leads.
    query = state_or_query.search_query if hasattr(state_or_query, 'search_query') else state_or_query
    
    # We want to find company websites
    if not api_key or api_key == "dummy" or not query:
        return {"discovered_urls": []}

    client = TavilyClient(api_key=api_key)
    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max(max_companies * 3, 8)
        )
    except Exception as exc:
        print(f"Search node error: {exc}")
        return {"discovered_urls": []}
    
    urls = []
    seen_domains = set()
    
    for r in response.get("results", []):
        url = r.get("url")
        domain = normalize_url(url)
        
        if not is_company_candidate(domain, url):
            continue

        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            urls.append({
                "source_url": url,
                "domain": domain,
                "title": r.get("title"),
                "company_name": infer_company_name(r.get("title"), domain),
            })
            if len(urls) >= max_companies:
                break
            
    return {"discovered_urls": urls}
