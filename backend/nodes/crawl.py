import asyncio
import re
from urllib.parse import urljoin, urlparse


def candidate_urls(seed_url: str) -> list[str]:
    parsed = urlparse(seed_url if seed_url.startswith("http") else f"https://{seed_url}")
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        urljoin(base, "/about"),
        urljoin(base, "/about-us"),
        urljoin(base, "/our-company"),
        urljoin(base, "/founders-message"),
        urljoin(base, "/team"),
        urljoin(base, "/leadership"),
        urljoin(base, "/contact"),
        urljoin(base, "/services"),
        urljoin(base, "/energy"),
        urljoin(base, "/informatics"),
        urljoin(base, "/infrastructure"),
        base,
    ]
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def discover_internal_candidates(markdown: str, seed_url: str, limit: int = 8) -> list[str]:
    parsed = urlparse(seed_url if seed_url.startswith("http") else f"https://{seed_url}")
    base = f"{parsed.scheme}://{parsed.netloc}"
    base_domain = parsed.netloc.removeprefix("www.")
    discovered: list[str] = []
    patterns = [
        r"\[[^\]]+\]\((https?://[^)]+)\)",
        r"\[[^\]]+\]\((/[^\)]+)\)",
    ]
    for pattern in patterns:
        for raw_url in re.findall(pattern, markdown):
            candidate = raw_url.strip()
            if candidate.startswith("/"):
                candidate = urljoin(base, candidate)
            if not candidate.startswith(("http://", "https://")):
                continue
            parsed_candidate = urlparse(candidate)
            candidate_domain = parsed_candidate.netloc.removeprefix("www.")
            if candidate_domain != base_domain:
                continue
            if candidate not in discovered:
                discovered.append(candidate)
            if len(discovered) >= limit:
                return discovered
    return discovered

async def crawl_node(url: str) -> str:
    """
    Crawls the company homepage plus likely leadership pages and returns combined markdown.
    """
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        sections: list[str] = []
        initial_candidates = candidate_urls(url)
        base_page = initial_candidates[-1]
        remaining_candidates = initial_candidates[:-1]
        discovered_candidates: list[str] = []

        try:
            result = await crawler.arun(
                url=base_page,
                word_count_threshold=10,
                bypass_cache=False,
            )
            markdown = (result.markdown or "").strip()
            if markdown:
                sections.append(f"# Source: {base_page}\n\n{markdown[:12000]}")
                discovered_candidates = discover_internal_candidates(markdown, url)
        except Exception as exc:
            print(f"Crawl candidate failed for {base_page}: {exc}")

        for candidate in remaining_candidates + discovered_candidates:
            try:
                result = await crawler.arun(
                    url=candidate,
                    word_count_threshold=10,
                    bypass_cache=False,
                )
                markdown = (result.markdown or "").strip()
                if markdown:
                    sections.append(f"# Source: {candidate}\n\n{markdown[:12000]}")
            except Exception as exc:
                print(f"Crawl candidate failed for {candidate}: {exc}")

        if not sections:
            raise RuntimeError(f"Unable to crawl any candidate pages for {url}")

        return "\n\n".join(sections)

# Small test wrapper if run directly
if __name__ == "__main__":
    markdown_output = asyncio.run(crawl_node("https://example.com"))
    print(markdown_output[:500])
