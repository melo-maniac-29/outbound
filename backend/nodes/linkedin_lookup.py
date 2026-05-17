import os


def linkedin_lookup_node(founder_name: str | None, company_name: str | None, domain: str | None, existing_linkedin: str | None = None) -> dict:
    """
    Look up a founder LinkedIn profile using the founder name plus company context.
    This is intentionally conservative: it only returns a person profile URL on linkedin.com/in/.
    """
    if existing_linkedin:
        return {"founder_linkedin": existing_linkedin}

    if not founder_name:
        return {"founder_linkedin": None}

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "dummy":
        return {"founder_linkedin": None}

    try:
        from tavily import TavilyClient
    except ImportError:
        print("Tavily client is not installed.")
        return {"founder_linkedin": None}

    context_bits = [founder_name, company_name or "", domain or "", "LinkedIn"]
    query = " ".join(bit for bit in context_bits if bit).strip()
    client = TavilyClient(api_key=api_key)

    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
        )
    except Exception as exc:
        print(f"LinkedIn lookup failed for {founder_name}: {exc}")
        return {"founder_linkedin": None}

    for result in response.get("results", []):
        url = result.get("url") or ""
        title = (result.get("title") or "").lower()
        content = (result.get("content") or "").lower()
        if "linkedin.com/in/" not in url.lower():
            continue
        founder_token = founder_name.lower().split()[0]
        if founder_token and founder_token not in f"{title} {content}":
            continue
        return {"founder_linkedin": url}

    return {"founder_linkedin": None}
