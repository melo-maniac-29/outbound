import asyncio
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, urlunparse

import requests

MAX_CRAWL_PAGES = 8
MAX_DISCOVERED_LINKS = 12
MAX_SITEMAP_URLS = 12
MAX_MARKDOWN_CHARS = 12000

PAGE_HINTS = (
    "about",
    "company",
    "story",
    "mission",
    "vision",
    "who-we-are",
    "team",
    "leadership",
    "founder",
    "overview",
    "contact",
    "services",
    "solutions",
    "products",
    "work",
)

BLOCKED_HINTS = (
    "blog",
    "news",
    "press",
    "case-study",
    "case-studies",
    "careers",
    "jobs",
    "events",
    "podcast",
    "articles",
    "article",
    "directory",
    "watch",
)


def normalize_seed_url(seed_url: str) -> str:
    parsed = urlparse(seed_url if seed_url.startswith("http") else f"https://{seed_url}")
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or parsed.path
    return urlunparse((scheme, netloc, "", "", "", ""))


def base_domain(seed_url: str) -> str:
    parsed = urlparse(normalize_seed_url(seed_url))
    return parsed.netloc.removeprefix("www.").lower()


def same_domain(candidate_url: str, seed_url: str) -> bool:
    candidate_domain = urlparse(candidate_url).netloc.removeprefix("www.").lower()
    return bool(candidate_domain) and candidate_domain == base_domain(seed_url)


def normalize_url(candidate_url: str, seed_url: str) -> str:
    if candidate_url.startswith("/"):
        return urljoin(normalize_seed_url(seed_url), candidate_url)
    return candidate_url


def link_priority(url: str, label: str | None = None) -> int:
    parsed = urlparse(url)
    path = parsed.path.lower().strip("/")
    label_text = (label or "").lower()

    score = 0
    if not path:
        score += 12

    for hint in PAGE_HINTS:
        if hint in path:
            score += 6
        if hint in label_text:
            score += 4

    for hint in BLOCKED_HINTS:
        if hint in path or hint in label_text:
            score -= 8

    path_parts = [part for part in path.split("/") if part]
    if len(path_parts) <= 1:
        score += 2
    if len(path_parts) > 3:
        score -= 2

    if path.endswith((".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip")):
        score -= 12

    return score


def _request_text(url: str, timeout: int = 8) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; OutboundAgent/1.0)"},
    )
    if response.status_code >= 400:
        return ""
    return response.text or ""


def _extract_sitemap_locations(xml_text: str) -> tuple[list[str], list[str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], []

    sitemap_locations: list[str] = []
    page_locations: list[str] = []
    for loc in root.findall(".//{*}loc"):
        value = (loc.text or "").strip()
        if not value:
            continue
        if root.tag.endswith("sitemapindex"):
            sitemap_locations.append(value)
        else:
            page_locations.append(value)
    return sitemap_locations, page_locations


def discover_sitemap_candidates(seed_url: str, limit: int = MAX_SITEMAP_URLS) -> list[str]:
    normalized = normalize_seed_url(seed_url)
    parsed = urlparse(normalized)
    candidates = []

    robots_url = urljoin(normalized, "/robots.txt")
    try:
        robots_text = _request_text(robots_url)
        for line in robots_text.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                if sitemap_url:
                    candidates.append(sitemap_url)
    except Exception:
        pass

    for fallback in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
        candidates.append(urljoin(f"{parsed.scheme}://{parsed.netloc}", fallback))

    discovered: list[str] = []
    visited_sitemaps: set[str] = set()

    while candidates and len(discovered) < limit:
        sitemap_url = candidates.pop(0)
        if sitemap_url in visited_sitemaps:
            continue
        visited_sitemaps.add(sitemap_url)
        try:
            sitemap_text = _request_text(sitemap_url)
        except Exception:
            continue
        if not sitemap_text:
            continue

        nested_sitemaps, page_locations = _extract_sitemap_locations(sitemap_text)
        for nested in nested_sitemaps:
            if nested not in visited_sitemaps:
                candidates.append(nested)

        for page_url in page_locations:
            if not same_domain(page_url, seed_url):
                continue
            if page_url not in discovered:
                discovered.append(page_url)
            if len(discovered) >= limit:
                break

    return discovered


def discover_internal_candidates(markdown: str, seed_url: str, limit: int = MAX_DISCOVERED_LINKS) -> list[tuple[str, int]]:
    seed_root = normalize_seed_url(seed_url)
    discovered: list[tuple[str, int]] = []
    seen: set[str] = set()
    pattern = r"\[([^\]]+)\]\((https?://[^)]+|/[^)\s]+)\)"

    for label, raw_url in re.findall(pattern, markdown):
        candidate = normalize_url(raw_url.strip(), seed_root)
        if not candidate.startswith(("http://", "https://")):
            continue
        if not same_domain(candidate, seed_url):
            continue
        parsed = urlparse(candidate)
        candidate = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        if candidate in seen:
            continue
        seen.add(candidate)
        discovered.append((candidate, link_priority(candidate, label)))
        if len(discovered) >= limit:
            break

    return discovered


def build_initial_queue(seed_url: str) -> list[tuple[int, str]]:
    normalized = normalize_seed_url(seed_url)
    queue: list[tuple[int, str]] = [(100, normalized)]
    for sitemap_url in discover_sitemap_candidates(normalized):
        if same_domain(sitemap_url, normalized):
            queue.append((link_priority(sitemap_url), sitemap_url))
    return queue


def push_candidate(queue: list[tuple[int, str]], seen: set[str], candidate: str, score: int) -> None:
    parsed = urlparse(candidate)
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    if normalized in seen:
        return
    seen.add(normalized)
    queue.append((score, normalized))


async def crawl_node(url: str) -> str:
    """
    Crawl the homepage, sitemap URLs, and internal links discovered from the site itself.
    This avoids site-specific page guessing and lets the target site tell us what matters.
    """
    from crawl4ai import AsyncWebCrawler

    seed_url = normalize_seed_url(url)
    queue = build_initial_queue(seed_url)
    queued: set[str] = {candidate for _, candidate in queue}
    visited: set[str] = set()
    sections: list[str] = []

    async with AsyncWebCrawler() as crawler:
        while queue and len(visited) < MAX_CRAWL_PAGES:
            queue.sort(key=lambda item: (-item[0], item[1]))
            _, candidate = queue.pop(0)
            if candidate in visited:
                continue
            visited.add(candidate)

            try:
                result = await crawler.arun(
                    url=candidate,
                    word_count_threshold=10,
                    bypass_cache=False,
                )
                markdown = (result.markdown or "").strip()
                if markdown:
                    sections.append(f"# Source: {candidate}\n\n{markdown[:MAX_MARKDOWN_CHARS]}")
                    for discovered_url, score in discover_internal_candidates(markdown, candidate, limit=MAX_DISCOVERED_LINKS):
                        push_candidate(queue, queued, discovered_url, score)
            except Exception as exc:
                print(f"Crawl candidate failed for {candidate}: {exc}")

    if not sections:
        raise RuntimeError(f"Unable to crawl any candidate pages for {url}")

    return "\n\n".join(sections)


if __name__ == "__main__":
    markdown_output = asyncio.run(crawl_node("https://example.com"))
    print(markdown_output[:500])
