import asyncio
from urllib.parse import urljoin, urlparse


def candidate_urls(seed_url: str) -> list[str]:
    parsed = urlparse(seed_url if seed_url.startswith("http") else f"https://{seed_url}")
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        urljoin(base, "/about"),
        urljoin(base, "/about-us"),
        urljoin(base, "/team"),
        urljoin(base, "/leadership"),
        urljoin(base, "/contact"),
        base,
    ]
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped

async def crawl_node(url: str) -> str:
    """
    Crawls the company homepage plus likely leadership pages and returns combined markdown.
    """
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        sections: list[str] = []
        for candidate in candidate_urls(url):
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
