import asyncio
from crawl4ai import AsyncWebCrawler

async def crawl_node(url: str) -> str:
    """
    Crawls the website using Crawl4AI and returns clean markdown.
    Handles page fetching, JS rendering, and anti-bot measures.
    """
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            word_count_threshold=10,
            bypass_cache=False,
        )
        return result.markdown

# Small test wrapper if run directly
if __name__ == "__main__":
    markdown_output = asyncio.run(crawl_node("https://example.com"))
    print(markdown_output[:500])
