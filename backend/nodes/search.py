import os
import re
from urllib.parse import urlparse

BLOCKED_DOMAINS = {
    "apple.com",
    "open.spotify.com",
    "spotify.com",
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


def normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def is_brand_query(query: str) -> bool:
    tokens = [token for token in query.split() if token]
    return len(tokens) == 1 and len(query) <= 24 and not query.startswith("http")


def is_company_candidate(domain: str, url: str, query: str | None = None, title: str | None = None) -> bool:
    if not domain:
        return False

    normalized_domain = domain.removeprefix("www.")
    if normalized_domain in BLOCKED_DOMAINS:
        return False

    blocked_suffixes = ("linkedin.com", "youtube.com", "apple.com")
    if normalized_domain.endswith(blocked_suffixes):
        return False

    blocked_subdomains = (
        ".spotify.com",
        ".youtube.com",
        ".linkedin.com",
        ".facebook.com",
        ".instagram.com",
        ".x.com",
        ".twitter.com",
    )
    if normalized_domain.endswith(blocked_subdomains):
        return False

    if normalized_domain.startswith(("careers.", "jobs.", "podcasts.")):
        return False

    parsed = urlparse(url or "")
    lowered_url = (url or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if query and is_brand_query(query):
        query_token = normalize_token(query)
        domain_token = normalize_token(normalized_domain)
        if query_token and query_token not in domain_token:
            return False
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

    return True

def query_variants(query: str) -> list[str]:
    if is_brand_query(query):
        return [
            query,
            f'"{query}" official site',
            f'"{query}" company',
            f'"{query}" contact',
        ]
    return [
        query,
        f"{query} company",
        f"{query} official site",
        f"{query} contact",
        f"{query} team",
        f"{query} about",
    ]


def search_node(
    state_or_query,
    max_companies: int = 5,
    max_attempts: int = 4,
    exclude_domains: list[str] | set[str] | None = None,
) -> dict:
    """
    Search discovery using Tavily.
    Input: search string
    Output: list of company URLs / domains
    """
    api_key = os.getenv("TAVILY_API_KEY")
    
    # If called within a graph with LeadState, it might extract the query.
    # Otherwise, it can be called directly to generate leads.
    query = state_or_query.search_query if hasattr(state_or_query, 'search_query') else state_or_query
    original_query = query.strip() if isinstance(query, str) else query
    
    # We want to find company websites
    if not api_key or api_key == "dummy" or not original_query:
        return {"discovered_urls": []}

    try:
        from tavily import TavilyClient
    except ImportError:
        print("Tavily client is not installed.")
        return {"discovered_urls": []}

    client = TavilyClient(api_key=api_key)
    urls = []
    seen_domains = set()
    excluded = set()
    if exclude_domains:
        excluded = {normalize_url(domain).lower().removeprefix("www.") for domain in exclude_domains if domain}

    for variant in query_variants(original_query)[:max_attempts]:
        try:
            response = client.search(
                query=variant,
                search_depth="basic",
                max_results=max(max_companies * 4, 10)
            )
        except Exception as exc:
            print(f"Search node error for '{variant}': {exc}")
            continue

        for r in response.get("results", []):
            url = r.get("url")
            domain = normalize_url(url)
            normalized_domain = domain.lower().removeprefix("www.")
            title = r.get("title")

            if not is_company_candidate(domain, url, query=original_query, title=title):
                continue

            if not domain:
                continue

            if normalized_domain in excluded:
                continue

            if domain not in seen_domains:
                seen_domains.add(domain)
                urls.append({
                    "source_url": url,
                    "domain": domain,
                    "title": title,
                    "company_name": infer_company_name(title, domain),
                })
                if len(urls) >= max_companies:
                    return {"discovered_urls": urls}

    return {"discovered_urls": urls}
